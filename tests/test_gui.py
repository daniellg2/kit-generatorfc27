import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from app.theme import apply_theme
from app.window import MainWindow
from core.layers.model import Region
from core.projects.storage import load_project, save_project


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_theme(cls.app)

    def setUp(self):
        recovery=patch.object(MainWindow,'recover')
        recovery.start()
        self.addCleanup(recovery.stop)
        self.window = MainWindow()
        self.window.show()
        self.app.processEvents()
        self.window.timer.stop()

    def tearDown(self):
        self.window.saved_state = self.window.project.to_dict()
        with patch('app.window.Path.unlink'):
            self.window.close()
        self.app.processEvents()

    def test_edit_undo_redo_and_roundtrip(self):
        window = self.window
        window.add_layer("stripes")
        self.assertEqual(len(window.project.layers),2)
        window.props["rotation"].setValue(35)
        self.assertEqual(window.current_layer().rotation,35)
        window.undo()
        self.assertEqual(window.current_layer().rotation,0)
        window.redo()
        self.assertEqual(window.current_layer().rotation,35)
        region = Region("Frente manual",[[.36,.6],[.64,.6],[.64,.9],[.36,.9]])
        window.change(lambda:window.project.regions.append(region))
        window.layer_region.setCurrentIndex(1)
        self.assertEqual(window.current_layer().region,region.id)
        window.fit_region()
        self.assertAlmostEqual(window.current_layer().width,.28)
        window.move_layer(.01,.02)
        self.assertAlmostEqual(window.current_layer().x,.51)
        with TemporaryDirectory() as directory:
            path = Path(directory)/"project.json"
            save_project(window.project,path)
            self.assertEqual(load_project(path).to_dict(),window.project.to_dict())
        self.assertGreater(window.canvas.scene().itemsBoundingRect().width(),0)

    def test_switch_template_and_aspect_lock(self):
        window = self.window
        window.template_combo.setCurrentIndex(1)
        self.assertIn("long_sleeve",window.project.template)
        window.add_layer("fill")
        window.props["width"].setValue(.3)
        self.assertAlmostEqual(window.current_layer().height,.3)
        window.props["keep_aspect"].setChecked(False)
        window.props["width"].setValue(.4)
        self.assertAlmostEqual(window.current_layer().height,.3)

    def test_canvas_draw_region_vertices(self):
        window = self.window
        with patch("app.window.QInputDialog.getItem",return_value=("Frente",True)):
            window.finish_draw("region",[[.36,.6],[.64,.6],[.64,.9],[.36,.9]])
        self.assertEqual(len(window.project.regions),1)
        window.move_vertex(0,.37,.61)
        self.assertEqual(window.current_region().points[0],[.37,.61])
        with patch("app.window.QInputDialog.getText",return_value=("Escudo",True)):
            window.finish_draw("landmark",[[.55,.65]])
        self.assertEqual(window.current_region().landmarks["Escudo"],[.55,.65])
        window.add_layer("fill")
        with patch("app.window.QInputDialog.getItem",return_value=("Frente / Escudo",True)):
            window.align_landmark()
        self.assertEqual(window.current_layer().x,.55)

    def test_svg_original_art(self):
        from core.rendering.compositor import load_art
        with TemporaryDirectory() as directory:
            svg = Path(directory)/"logo.svg"
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><rect width="100" height="50" fill="red"/></svg>')
            image = load_art(svg)
            self.assertEqual(image.width/image.height,2)
            self.assertEqual(image.getpixel((20,20)),(255,0,0,255))

    def test_mouse_drag_and_clean_export(self):
        from PIL import Image
        from core.rendering.compositor import render
        window = self.window
        window.add_layer("fill")
        layer = window.current_layer()
        window.change(lambda:setattr(layer,"y",.3))
        window.canvas.fit()
        self.app.processEvents()
        w,h = window.canvas.dimensions
        start = window.canvas.mapFromScene(QPointF(.5*w,.3*h))
        end = window.canvas.mapFromScene(QPointF(.53*w,.32*h))
        QTest.mousePress(window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start)
        QTest.mouseMove(window.canvas.viewport(),end)
        QTest.mouseRelease(window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end)
        self.assertAlmostEqual(window.current_layer().x,.53,delta=.003)
        self.assertAlmostEqual(window.current_layer().y,.32,delta=.003)
        window.uv_opacity.setValue(100)
        window.grid_check.setChecked(True)
        with TemporaryDirectory() as directory:
            path = Path(directory)/"clean.png"
            with patch("app.window.QDialog.exec",return_value=QDialog.DialogCode.Accepted),patch("app.window.QFileDialog.getSaveFileName",return_value=(str(path),"PNG")):
                window.export_dialog()
            with Image.open(path) as exported:
                self.assertEqual(exported.tobytes(),render(window.project).tobytes())


if __name__ == "__main__":
    unittest.main()
