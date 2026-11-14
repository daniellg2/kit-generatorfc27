"""Replaceable local analyzer contract. Results stay in photo coordinates."""
from dataclasses import dataclass
from typing import Protocol
import cv2
import numpy as np
from PIL import Image
from core.uv.templates import read_image


@dataclass
class Analysis:
    palette: list[str]
    mask: Image.Image
    lines: list
    warning: str


class ReferenceAnalyzer(Protocol):
    def analyze(self, path: str) -> Analysis: ...


class OpenCVAnalyzer:
    def analyze(self, path):
        photo = read_image(path).convert("RGB")
        photo.thumbnail((640, 640))
        rgb = np.asarray(photo).copy()
        h, w = rgb.shape[:2]
        if min(h, w) < 32:
            raise ValueError("Referência pequena demais para análise (mínimo 32 px).")
        mask = np.zeros((h, w), np.uint8)
        warning = "Experimental: cores incluem iluminação; linhas podem ser dobras. A máscara não é uma calibração UV."
        try:
            cv2.grabCut(rgb, mask, (w//10, h//20, w*8//10, h*9//10), np.zeros((1,65)), np.zeros((1,65)), 3, cv2.GC_INIT_WITH_RECT)
            foreground = np.uint8((mask == 1) | (mask == 3)) * 255
            if np.count_nonzero(foreground) < w*h*.02:
                raise ValueError("Segmentação vazia")
        except (cv2.error, ValueError):
            foreground = np.full((h, w), 255, np.uint8)
            warning += " Segmentação falhou: paleta calculada na imagem inteira."
        pixels = rgb[foreground > 0][::3]
        quantized = Image.fromarray(pixels.reshape(1, -1, 3)).quantize(colors=6)
        palette = quantized.getpalette()
        colors = sorted(quantized.getcolors(), reverse=True)
        swatches = ["#%02x%02x%02x" % tuple(palette[i*3:i*3+3]) for _, i in colors]
        edges = cv2.Canny(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), 70, 160)
        edges[foreground == 0] = 0
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 45, minLineLength=min(w,h)//5, maxLineGap=12)
        suggestions = []
        if lines is not None:
            for x1,y1,x2,y2 in lines[:20, 0]:
                suggestions.append([[float(x1/w),float(y1/h)], [float(x2/w),float(y2/h)]])
        return Analysis(swatches, Image.fromarray(foreground), suggestions, warning)
