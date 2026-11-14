"""Run a real WebEngine integration check and save screenshots/state evidence."""
import json
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app.window import MainWindow
from app.theme import apply_theme


def main():
    app=QApplication([]);apply_theme(app)
    window=MainWindow();window.show();window.timer.stop()
    window.editor_tabs.setCurrentIndex(1)
    def wait(predicate,seconds=30):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            app.processEvents();time.sleep(.03)
            if predicate():return
        raise AssertionError('Timeout waiting for 3D viewer')
    def state():
        result=[]
        window.preview3d.web.page().runJavaScript('JSON.stringify(window.preview?.state())',result.append)
        wait(lambda:bool(result),5)
        return json.loads(result[0]) if result[0] else {}
    try:
        wait(lambda:window.preview3d.ready)
        wait(lambda:state().get('updates',0)>0 and state().get('loads',0)>0)
        before=state();assert not before['error'],before
        window.change(lambda:setattr(window.project.layers[0],'color','#ee3344'))
        wait(lambda:state()['updates']>before['updates'])
        after=state();assert before['loads']==after['loads'];assert before['camera']==after['camera']
        from app.photo_dialog import PhotoDialog
        from PIL import Image,ImageDraw
        photo=Image.new('RGB',(800,800),'white')
        ImageDraw.Draw(photo).rectangle((160,320,640,400),fill='#1254b8')
        photo.save('output/projection_synthetic_photo.png')
        dialog=PhotoDialog(window)
        dialog.path=str(Path('output/projection_synthetic_photo.png').resolve());dialog.clear()
        for p in [[.1,.1],[.9,.1],[.9,.9],[.1,.9]]:dialog.photo.add(*p)
        for p in [[.42,.63],[.58,.63],[.58,.82],[.42,.82]]:dialog.uv.add(*p)
        dialog.stripe_points=[[.2,.4],[.8,.4],[.8,.5],[.2,.5]]
        dialog.show();dialog.calculate()
        wait(lambda:dialog.result is not None)
        dialog.grab().save('output/photo_projection_dialog.png')
        previous_updates=state()['updates'];previous_layers=len(window.project.layers)
        dialog.accept_result()
        wait(lambda:len(window.project.layers)==previous_layers+2)
        wait(lambda:state()['updates']>previous_updates)
        assert len(window.project.photo_calibrations)==1
        window.undo();assert len(window.project.layers)==previous_layers
        window.redo();assert len(window.project.layers)==previous_layers+2
        window.preview3d.command('view','front')
        for _ in range(25):app.processEvents();time.sleep(.03)
        window.grab().save('output/photo_projection_3d.png')
        assert after['flipY'] is False
        window.preview3d.checker.setChecked(True)
        wait(lambda:True,1)
        for view in ('front','back','left','right'):
            window.preview3d.command('view',view)
            for _ in range(20):app.processEvents();time.sleep(.03)
            window.grab().save(f'output/preview3d_short_{view}.png')
        from unittest.mock import patch
        from PySide6.QtWidgets import QMessageBox
        with patch('app.window.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
            window.template_combo.setCurrentIndex(1)
        wait(lambda:state()['selected']=='long_sleeve' and state()['loads']==2)
        window.preview3d.shorts.setChecked(True)
        wait(lambda:state()['loads']==3)
        window.preview3d.command('view','front')
        for _ in range(30):app.processEvents();time.sleep(.03)
        window.grab().save('output/preview3d_long_shorts.png')
        window.preview3d.shorts.setChecked(False)
        wait(lambda:not state()['shortsVisible'])
        Path('output/preview3d_test.json').write_text(json.dumps(state(),indent=2))
        print('PASS: GLB load, texture update, camera preservation, sleeve switch, shorts toggle')
    finally:
        window.saved_state=window.project.to_dict();window.close();app.processEvents()


if __name__=='__main__':main()
