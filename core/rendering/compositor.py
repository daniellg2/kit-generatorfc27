"""CPU compositor. Guides and editor handles never enter this pipeline."""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageDraw
from core.uv.templates import polygon_mask, read_image, template_mask
from core.projects.storage import atomic_write


def load_art(path, size=None):
    if Path(path).suffix.lower() != ".svg":
        return read_image(path)
    # QtSvg avoids the extra native Cairo dependency on Windows.
    from PySide6.QtCore import QByteArray, QRectF
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    raw = Path(path).read_bytes()
    if len(raw) > 10_000_000 or b"<!ENTITY" in raw.upper() or b"<!DOCTYPE" in raw.upper():
        raise ValueError("SVG inválido ou excede 10 MB. Use um SVG independente, sem DTD.")
    renderer = QSvgRenderer(QByteArray(raw))
    if not renderer.isValid():
        raise ValueError("SVG inválido.")
    natural = renderer.defaultSize()
    w, h = natural.width(), natural.height()
    if w <= 0 or h <= 0:
        w = h = 512
    bound = max(size or (1024, 1024))
    scale = min(bound / max(w, h), 8)
    w, h = max(1, round(w * scale)), max(1, round(h * scale))
    image = QImage(w, h, QImage.Format.Format_RGBA8888)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, w, h))
    painter.end()
    return Image.frombytes("RGBA", (w, h), bytes(image.constBits()), "raw", "RGBA", image.bytesPerLine())


def layer_size(layer, size):
    return max(1, round(layer.width * size[0])), max(1, round(layer.height * size[1]))


def _curve(points):
    """Catmull-Rom curve passing through the user control points."""
    if len(points) == 2:
        return points
    padded = [points[0], *points, points[-1]]
    result = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = map(np.asarray, padded[i-1:i+3])
        for t in np.linspace(0, 1, 20):
            result.append(tuple(.5 * ((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t*t*t)))
    return result


def layer_art(layer, size):
    w, h = layer_size(layer, size)
    angle = math.radians(layer.rotation)
    rotated_area = (abs(w*math.cos(angle))+abs(h*math.sin(angle))) * (abs(w*math.sin(angle))+abs(h*math.cos(angle)))
    if w*h > 16_777_216 or rotated_area > 33_554_432:
        raise ValueError(f"Camada '{layer.name}' excede o limite de memória. Reduza o tamanho ou a resolução de exportação.")
    color = ImageColor.getcolor(layer.color, "RGBA")
    if layer.kind == "image":
        image = load_art(layer.source, (w, h))
        if layer.keep_aspect:
            factor = min(w / image.width, h / image.height)
            image = image.resize((max(1, round(image.width * factor)), max(1, round(image.height * factor))), Image.Resampling.LANCZOS)
            art = Image.new("RGBA", (w, h))
            art.alpha_composite(image, ((w-image.width)//2, (h-image.height)//2))
        else:
            art = image.resize((w, h), Image.Resampling.LANCZOS)
        if layer.recolor:
            alpha = art.getchannel("A")
            art = Image.new("RGBA", art.size, color)
            art.putalpha(ImageChops.multiply(alpha, Image.new("L", art.size, color[3])))
    elif layer.kind == "pattern":
        tile = load_art(layer.source, (w, h))
        tw = max(2, round(layer.tile_scale * size[0]))
        th = max(2, round(tw * tile.height / tile.width))
        if tw * th > 16_777_216:
            raise ValueError("Padrão grande demais; diminua a escala.")
        tile = tile.resize((tw, th), Image.Resampling.LANCZOS)
        art = Image.new("RGBA", (w, h))
        ox, oy = round(layer.offset_x*size[0]) % tw, round(layer.offset_y*size[1]) % th
        for y in range(oy-th, h, th):
            for x in range(ox-tw, w, tw):
                art.alpha_composite(tile, (x, y))
    else:
        art = Image.new("RGBA", (w, h))
        draw = ImageDraw.Draw(art)
        stroke = max(1, round(layer.stroke * min(size)))
        if layer.kind == "fill":
            draw.rectangle((0, 0, w-1, h-1), fill=None if layer.outline else color, outline=color, width=stroke)
        elif layer.kind == "stripes":
            spacing = max(2, round(layer.spacing * size[1]))
            thick = max(1, round(layer.thickness * size[1]))
            for y in range(0, h, spacing):
                draw.rectangle((0, y, w-1, y+thick-1), fill=color)
        else:
            pts = [(x*(w-1), y*(h-1)) for x, y in layer.points]
            if layer.kind == "polygon":
                draw.polygon(pts, fill=None if layer.outline else color)
                if layer.outline:
                    draw.line([*pts, pts[0]], fill=color, width=stroke, joint="curve")
            else:
                draw.line(_curve(pts), fill=color, width=stroke, joint="curve")
    if layer.flip_x:
        art = art.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if layer.flip_y:
        art = art.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if layer.rotation:
        art = art.rotate(-layer.rotation, Image.Resampling.BICUBIC, expand=True)
    if layer.opacity != 1:
        art.putalpha(art.getchannel("A").point(lambda a: round(a * layer.opacity)))
    return art


def render(project, size=None):
    project.validate()
    original = read_image(project.template).size
    size = size or (project.export_width, round(project.export_width * original[1] / original[0]))
    if min(size) < 1 or size[0]*size[1] > 16_777_216:
        raise ValueError("Exportação limitada a 16 megapixels para uso de memória em CPU.")
    if abs(size[0]/size[1] - original[0]/original[1]) > 1/min(size):
        raise ValueError("A exportação deve preservar as proporções do UV.")
    mask = template_mask(project, size)
    regions = {r.id: r for r in project.regions}
    result = Image.new("RGBA", size)
    for layer in project.layers:
        if not layer.visible or layer.opacity == 0:
            continue
        art = layer_art(layer, size)
        surface = Image.new("RGBA", size)
        surface.alpha_composite(art, (round(layer.x*size[0]-art.width/2), round(layer.y*size[1]-art.height/2)))
        if layer.region:
            surface.putalpha(ImageChops.multiply(surface.getchannel("A"), polygon_mask(regions[layer.region].points, size)))
        result = Image.alpha_composite(result, surface)
    result.putalpha(ImageChops.multiply(result.getchannel("A"), mask))
    return result


def export_png(project, path):
    sources = [project.template,project.mask,*[l.source for l in project.layers],*[r["path"] for r in project.references]]
    if Path(path).resolve() in [Path(p).resolve() for p in sources if p]:
        raise ValueError("A exportação não pode sobrescrever um arquivo original do projeto.")
    image = render(project)
    atomic_write(path, lambda p: image.save(p, format="PNG"))
    return image.size
