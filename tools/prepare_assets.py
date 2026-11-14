"""One-time deterministic mask generation and demo project creation."""
from pathlib import Path
from app.demo import ROOT, cruzeiro_demo
from core.projects.storage import save_project
from core.uv.templates import derive_mask


def main():
    for sleeve in ("short_sleeve", "long_sleeve"):
        directory = ROOT / "assets/uv_templates"
        path = directory / f"{sleeve}_mask.png"
        if not path.exists():
            derive_mask(directory / f"{sleeve}.png").save(path)
            print(f"Máscara raster inicial: {path.name} (revisar limites)")
    save_project(cruzeiro_demo(), ROOT / "assets/cruzeiro_demo.json")


if __name__ == "__main__":
    main()
