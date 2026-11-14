"""Serializable editor state. All coordinates are fractions of the full UV canvas."""
from dataclasses import asdict, dataclass, field
from uuid import uuid4
import math
from PIL import ImageColor


def uid():
    return uuid4().hex


@dataclass
class Region:
    name: str
    points: list
    id: str = field(default_factory=uid)
    landmarks: dict = field(default_factory=dict)
    reference_role: str = ""


@dataclass
class Layer:
    name: str
    kind: str = "fill"
    id: str = field(default_factory=uid)
    x: float = .5
    y: float = .5
    width: float = 1.
    height: float = 1.
    rotation: float = 0.
    opacity: float = 1.
    color: str = "#ffffff"
    source: str = ""
    region: str = ""
    visible: bool = True
    flip_x: bool = False
    flip_y: bool = False
    keep_aspect: bool = True
    recolor: bool = False
    points: list = field(default_factory=list)
    stroke: float = .008
    spacing: float = .12
    thickness: float = .04
    tile_scale: float = .1
    offset_x: float = 0.
    offset_y: float = 0.
    outline: bool = False


@dataclass
class Project:
    name: str = "Novo uniforme"
    version: int = 1
    template: str = ""
    mask: str = ""
    regions: list[Region] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    references: list = field(default_factory=list)
    export_width: int = 2048
    notes: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("Formato/versão de projeto não suportado.")
        data = dict(data)
        data["layers"] = [Layer(**v) for v in data.get("layers", [])]
        data["regions"] = [Region(**v) for v in data.get("regions", [])]
        project = cls(**data)
        project.validate()
        return project

    def validate(self):
        if not 64 <= self.export_width <= 8192:
            raise ValueError("Largura de exportação inválida (64–8192).")
        if len(self.layers) > 500 or len(self.regions) > 200:
            raise ValueError("Projeto excede 500 camadas ou 200 regiões.")
        ids = [r.id for r in self.regions]
        if len(set(ids)) != len(ids) or len({l.id for l in self.layers}) != len(self.layers):
            raise ValueError("IDs duplicados no projeto.")
        for r in self.regions:
            self._points(r.points, 3)
            for p in r.landmarks.values():
                self._points([p], 1)
        for ref in self.references:
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str) or not isinstance(ref.get("role"), str):
                raise ValueError("Referência inválida.")
        for l in self.layers:
            if l.kind not in {"fill", "image", "pattern", "stripes", "polygon", "curve"}:
                raise ValueError("Tipo de camada desconhecido.")
            if l.region and l.region not in ids:
                raise ValueError(f"Região inexistente: {l.name}")
            ImageColor.getcolor(l.color, "RGBA")
            for k in ("x", "y", "width", "height", "rotation", "opacity", "stroke", "spacing", "thickness", "tile_scale", "offset_x", "offset_y"):
                if not isinstance(getattr(l, k), (int, float)) or not math.isfinite(getattr(l, k)):
                    raise ValueError(f"Coordenada inválida: {k}")
            if not (0 < l.width <= 2 and 0 < l.height <= 2 and -2 <= l.x <= 3 and -2 <= l.y <= 3):
                raise ValueError("Transformação fora dos limites do editor.")
            if not (0 <= l.opacity <= 1 and .002 <= l.spacing <= 2 and .001 <= l.thickness <= 2 and .005 <= l.tile_scale <= 2 and .0001 <= l.stroke <= 1):
                raise ValueError("Parâmetros de camada inválidos.")
            if l.kind in {"polygon", "curve"}:
                self._points(l.points, 3 if l.kind == "polygon" else 2)

    @staticmethod
    def _points(points, minimum):
        if not minimum <= len(points) <= 2000:
            raise ValueError("Quantidade de pontos inválida.")
        for p in points:
            if len(p) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in p):
                raise ValueError("Pontos devem estar normalizados entre 0 e 1.")
