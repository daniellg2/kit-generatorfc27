"""Generate solid editable shapes; never automatically bake photo lighting."""
import copy
from pathlib import Path
from PIL import ImageDraw
import numpy as np
from core.layers.model import Layer, Region, uid
from core.projection.photo_to_uv import homography,transform
from core.uv.templates import read_image,polygon_mask


def palette(photo,polygon):
    mask=polygon_mask(polygon,photo.size)
    pixels=np.asarray(photo.convert('RGB'))[np.asarray(mask)>0]
    if not len(pixels):raise ValueError('Área fotográfica vazia.')
    from PIL import Image
    sample=Image.fromarray(pixels[::max(1,len(pixels)//50000)].reshape(1,-1,3)).quantize(colors=5)
    colors=sample.getpalette()
    return ['#%02x%02x%02x'%tuple(colors[i*3:i*3+3]) for count,i in sorted(sample.getcolors(),reverse=True)]


def generate(project,surface,photo_path,name,photo_points,anchors,stripe_points,directory):
    matrix=homography(photo_points,anchors,surface)
    photo=read_image(photo_path)
    colors=palette(photo,photo_points)
    region_points=[surface.uv(a).tolist() for a in anchors]
    result=copy.deepcopy(project)
    region=Region(name,region_points)
    result.regions.append(region)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    mask_path=directory/(uid()+'.png')
    surface.mask(read_image(project.template).size).save(mask_path)
    layers=[Layer(name+' · cor sugerida (revisar)',color=colors[0],region=region.id,mask_source=str(mask_path.resolve()))]
    if stripe_points:
        if len(stripe_points)<3:raise ValueError('Selecione ao menos três pontos para a faixa.')
        import cv2
        for p in stripe_points:
            if cv2.pointPolygonTest(np.asarray(photo_points,np.float32),tuple(p),False)<0:
                raise ValueError('A faixa deve estar dentro da região calibrada da foto.')
        projected=transform(stripe_points,matrix)
        color=palette(photo,stripe_points)[0]
        layers.append(Layer(name+' · faixa da foto',kind='polygon',points=projected,color=color,region=region.id,mask_source=str(mask_path.resolve())))
    result.layers.extend(layers)
    calibration=dict(name=name,source=str(Path(photo_path).resolve()),mesh=surface.path,mesh_sha256=surface.digest,photo_points=photo_points,anchors=anchors,stripe_points=stripe_points)
    result.photo_calibrations.append(calibration)
    if not any(r['path']==calibration['source'] for r in result.references):result.references.append(dict(path=calibration['source'],role=name))
    result.validate()
    return result,colors
