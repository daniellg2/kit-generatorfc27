"""Offscreen GUI smoke and screenshots, without changing user project files."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from app.theme import apply_theme
from app.window import MainWindow
from app.demo import ROOT
from core.layers.model import Region
from core.uv.templates import read_image


def main():
    app = QApplication([])
    apply_theme(app)
    window = MainWindow()
    window.timer.stop()
    window.show()
    app.processEvents()
    window.canvas.fit()
    app.processEvents()
    window.grab().save(str(ROOT / "output/editor_preview.png"))
    window.resize(1100,760)
    app.processEvents()
    window.canvas.fit()
    window.grab().save(str(ROOT / "output/editor_compact.png"))
    region = Region("Região manual · exemplo",[[.37,.60],[.63,.60],[.63,.88],[.37,.88]],landmarks={"Reserva de arte":[.55,.66]})
    window.change(lambda:window.project.regions.append(region))
    window.region_id = region.id
    window.add_layer("stripes")
    window.fit_region()
    window.props["rotation"].setValue(25)
    window.tabs.setCurrentIndex(1)
    window.resize(1480,940)
    app.processEvents()
    window.canvas.fit()
    window.grab().save(str(ROOT / "output/editor_calibration.png"))
    for sleeve in ("short_sleeve","long_sleeve"):
        image = read_image(ROOT / f"assets/uv_templates/{sleeve}_mask.png")
        image.thumbnail((640,640))
        image.save(ROOT / f"output/{sleeve}_mask_preview.png")
    window.saved_state = window.project.to_dict()
    window.close()


if __name__ == "__main__":
    main()
