import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from PIL import Image
from PySide6.QtCore import Qt,QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QGraphicsPixmapItem
from app.photo_dialog import PointsView
from unittest.mock import patch
from PySide6.QtWidgets import QWidget
from app.photo_dialog import PhotoDialog
from app.demo import new_project


class PhotoPointsTests(unittest.TestCase):
    def test_explicit_corner_order_repairs_crossing(self):
        app=QApplication.instance() or QApplication([])
        view=PointsView(4)
        view.show_image(Image.new('RGB',(800,800),'white'))
        for point in ((.2,.2),(.2,.8),(.8,.2),(.8,.8)):view.add(*point)
        view.order_corners()
        import numpy as np
        np.testing.assert_allclose(view.values(),[[.2,.2],[.8,.2],[.8,.8],[.2,.8]],atol=1e-6)
        view.close()

    def test_generate_directly_without_prior_preview(self):
        app=QApplication.instance() or QApplication([])
        parent=QWidget();parent.project=new_project()
        dialog=PhotoDialog(parent)
        try:
            self.assertTrue(dialog.apply.isEnabled())
            with patch('app.photo_dialog.QMessageBox.warning') as warning:
                dialog.apply.click()
                self.assertIn('Foto: 0/4',warning.call_args.args[2])
            for p in [[.1,.1],[.9,.1],[.9,.9],[.1,.9]]:dialog.photo.add(*p)
            for p in [[.42,.63],[.58,.63],[.58,.82],[.42,.82]]:dialog.uv.add(*p)
            with patch('app.photo_dialog.ProjectionWorker') as worker:
                dialog.apply.click()
                worker.return_value.start.assert_called_once()
                self.assertTrue(dialog.commit_pending)
                self.assertFalse(dialog.apply.isEnabled())
                dialog.calculation_finished()
                self.assertTrue(dialog.apply.isEnabled())
                dialog.worker=None
        finally:dialog.close();parent.close()

    def test_background_survives_clicks_drag_and_mode_reset(self):
        app=QApplication.instance() or QApplication([])
        view=PointsView(4);view.resize(450,550)
        view.show_image(Image.new('RGB',(800,800),'red'));view.show();app.processEvents()
        try:
            for x,y in ((.2,.2),(.7,.2),(.7,.6),(.2,.6)):
                p=view.mapFromScene(QPointF(x*800,y*800))
                QTest.mouseClick(view.viewport(),Qt.MouseButton.LeftButton,pos=p)
                app.processEvents()
                self.assertIn(view.background_item,view.scene().items())
                pixel=view.grab().toImage().pixelColor(view.mapFromScene(QPointF(400,400)))
                self.assertGreater(pixel.red(),200)
                self.assertLess(pixel.green(),30)
            self.assertEqual(len(view.markers),4)
            start=view.mapFromScene(view.markers[0].pos())
            end=view.mapFromScene(QPointF(240,240))
            QTest.mousePress(view.viewport(),Qt.MouseButton.LeftButton,pos=start)
            QTest.mouseMove(view.viewport(),end)
            QTest.mouseRelease(view.viewport(),Qt.MouseButton.LeftButton,pos=end)
            app.processEvents()
            self.assertAlmostEqual(view.values()[0][0],.3,delta=.01)
            self.assertIn(view.background_item,view.scene().items())
            view.show_image(Image.new('RGB',(800,800),'blue'))
            self.assertEqual(len(view.markers),0)
            self.assertEqual(sum(isinstance(i,QGraphicsPixmapItem) for i in view.scene().items()),1)
        finally:view.close()
