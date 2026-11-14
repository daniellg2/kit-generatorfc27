"""Local planar calibration, bound to real mesh triangles by barycentric anchors."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw


class MeshSurface:
    def __init__(self,path):
        self.path=str(Path(path).resolve())
        raw=Path(path).read_bytes()
        self.digest=hashlib.sha256(raw).hexdigest()
        self.data=json.loads(raw)
        self.triangles=np.asarray([t['uv'] for t in self.data['triangles']],dtype=float)
        self.triangles[:,:,1]=1-self.triangles[:,:,1]

    def anchor(self,point):
        p=np.asarray(point,dtype=float)
        for index,t in enumerate(self.triangles):
            matrix=np.column_stack((t[1]-t[0],t[2]-t[0]))
            if abs(np.linalg.det(matrix))<1e-12:continue
            b,c=np.linalg.solve(matrix,p-t[0]);a=1-b-c
            if min(a,b,c)>=-1e-7:
                return dict(triangle=index,weights=[float(a),float(b),float(c)])
        raise ValueError('Ponto fora da superfície UV geométrica. Escolha um ponto dentro de uma ilha.')

    def uv(self,anchor):
        weights=np.asarray(anchor['weights'],dtype=float)
        if weights.shape!=(3,) or not np.isfinite(weights).all() or min(weights)<-1e-7 or abs(sum(weights)-1)>1e-6:
            raise ValueError('Coordenadas baricêntricas inválidas.')
        index=anchor['triangle']
        if not isinstance(index,int) or not 0<=index<len(self.triangles):raise ValueError('Triângulo inválido.')
        return weights@self.triangles[index]

    def position(self,anchor):
        self.uv(anchor)
        t=self.data['triangles'][anchor['triangle']]
        return np.asarray(anchor['weights'])@np.asarray([self.data['vertices'][v] for v in t['vertices']])

    def mask(self,size):
        image=Image.new('L',size);draw=ImageDraw.Draw(image)
        for t in self.triangles:
            draw.polygon([tuple(p*np.asarray([size[0]-1,size[1]-1])) for p in t],fill=255)
        return image


def homography(photo_points,anchors,surface):
    source=np.asarray(photo_points,dtype=float)
    target=np.asarray([surface.uv(a) for a in anchors])
    if source.shape!=(4,2) or target.shape!=(4,2) or not np.isfinite(source).all() or (source<0).any() or (source>1).any():
        raise ValueError('Marque quatro pares normalizados por região, na mesma ordem ao redor do contorno.')
    for name,polygon in (('fotografia',source),('UV',target)):
        if not cv2.isContourConvex(polygon.astype(np.float32)) or abs(cv2.contourArea(polygon.astype(np.float32)))<1e-6:
            raise ValueError(f'Os pontos da {name} estão cruzados ou não formam quatro cantos externos. Use Ordenar cantos no modo 1 e confira os pares numerados antes de recalcular.')
    matrix=cv2.getPerspectiveTransform(source.astype(np.float32),target.astype(np.float32))
    if not np.isfinite(matrix).all() or abs(np.linalg.det(matrix))<1e-10:raise ValueError('Calibração degenerada.')
    return matrix


def transform(points,matrix):
    result=cv2.perspectiveTransform(np.asarray(points,dtype=np.float64).reshape(-1,1,2),matrix).reshape(-1,2)
    if not np.isfinite(result).all() or (result<0).any() or (result>1).any():
        raise ValueError('A projeção saiu do UV; ajuste as correspondências.')
    return result.tolist()
