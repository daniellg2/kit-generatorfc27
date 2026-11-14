"""Guide and clipping mask are independent. No anatomical correspondence is inferred."""
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw


@lru_cache(maxsize=8)
def _read(path, stamp):
    with Image.open(path) as im:
        if im.width * im.height > 32_000_000:
            raise ValueError("Imagem excede 32 megapixels.")
        return im.convert("RGBA")


def read_image(path):
    p = Path(path)
    return _read(str(p.resolve()), p.stat().st_mtime_ns).copy()


def derive_mask(path):
    """Experimental envelope for supplied gray-cell/black-background wireframes."""
    image = read_image(path)
    gray = np.asarray(image.convert("L"))
    cells = np.uint8(gray > 40) * 255
    # shortcut: raster envelopes have pixel uncertainty; import a verified mask for exact borders.
    closed = cv2.morphologyEx(cells, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(255 - closed)
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] < 1000:
            closed[labels == i] = 255
    if not np.any(closed) or np.all(closed):
        raise ValueError("Não foi possível extrair o limite. Importe uma máscara PNG preto/branco.")
    return Image.fromarray(closed)


def template_mask(project, size):
    mask = read_image(project.mask).convert("L") if project.mask else derive_mask(project.template)
    if mask.size != read_image(project.template).size:
        raise ValueError("Máscara e guia UV devem ter as mesmas dimensões originais.")
    return mask.resize(size, Image.Resampling.NEAREST)


def polygon_mask(points, size):
    im = Image.new("L", size)
    ImageDraw.Draw(im).polygon([(round(x * (size[0] - 1)), round(y * (size[1] - 1))) for x, y in points], fill=255)
    return im


def guide_overlay(project, size):
    guide = read_image(project.template).resize(size, Image.Resampling.LANCZOS)
    gray = np.asarray(guide.convert("L"))
    mask = np.asarray(template_mask(project, size))
    rgba = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    rgba[:, :, :3] = (63, 171, 255)
    rgba[:, :, 3] = np.where((gray < 100) & (mask > 0), 230, 0).astype(np.uint8)
    return Image.fromarray(rgba)
