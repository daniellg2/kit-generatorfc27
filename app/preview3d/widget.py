"""Lazy offline WebEngine viewer; loopback serves only explicitly allowed assets."""
import base64
import hashlib
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QFileDialog

ROOT = Path(__file__).resolve().parents[2]


class AssetServer:
    def __init__(self):
        assets = {}
        base = Path(__file__).parent
        for path in base.rglob('*'):
            if path.suffix in {'.js','.html'}:
                assets['/'+path.relative_to(base).as_posix()] = path
        for name in ('Collar_0.glb','Collar_0_LS.glb','Shorts_0.glb'):
            assets['/models/'+name] = ROOT/'assets/models'/name
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path=assets.get(urlsplit(self.path).path)
                if not path or not path.is_file():
                    self.send_error(404);return
                data=path.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type',{'.js':'text/javascript','.html':'text/html','.glb':'model/gltf-binary'}[path.suffix])
                self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data)
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}/index.html'

    def close(self):
        self.server.shutdown();self.server.server_close()


class Preview3D(QWidget):
    sleeveRequested=Signal(int)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.web=None;self.server=None;self.ready=False;self.model='short_sleeve'
        self.pending=None;self.last_digest=None
        self.polls=0
        layout=QVBoxLayout(self)
        controls=QHBoxLayout()
        for text,view in [('Frente','front'),('Costas','back'),('Esquerda','left'),('Direita','right'),('Centralizar','front')]:
            b=QPushButton(text);b.clicked.connect(lambda checked=False,v=view:self.command('view',v));controls.addWidget(b)
        layout.addLayout(controls)
        options=QHBoxLayout()
        for text,index in [('Manga curta',0),('Manga longa',1)]:
            b=QPushButton(text);b.clicked.connect(lambda checked=False,i=index:self.sleeveRequested.emit(i));options.addWidget(b)
        self.shorts=QCheckBox('Short');self.shorts.toggled.connect(self.select_model);options.addWidget(self.shorts)
        self.checker=QCheckBox('Teste UV');self.checker.toggled.connect(lambda v:self.command('diagnostic',v));options.addWidget(self.checker)
        self.flat=QCheckBox('Cor sem luz');self.flat.toggled.connect(lambda v:self.command('flat',v));options.addWidget(self.flat)
        layout.addLayout(options)
        b=QPushButton('Textura independente do short…');b.clicked.connect(self.load_shorts);layout.addWidget(b)
        self.status=QLabel('Arraste: girar · scroll: zoom · direito: pan. Máscaras raster têm pequenas divergências nas bordas UV; modelos preservados.')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        self.body=QVBoxLayout();layout.addLayout(self.body,1)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180);self.timer.timeout.connect(self.flush)

    def showEvent(self,event):
        super().showEvent(event)
        if self.web is None:self.start()
        self.timer.start()

    def start(self):
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.server=AssetServer()
            self.web=QWebEngineView(self)
            self.body.addWidget(self.web)
            self.web.loadFinished.connect(self.loaded)
            self.web.setUrl(QUrl(self.server.url))
        except Exception as error:
            self.status.setText(f'Prévia 3D indisponível: {error}. O editor UV continua disponível.')

    def loaded(self,ok):
        if not ok:
            self.status.setText('Não foi possível carregar o visualizador local.');return
        self.web.page().runJavaScript('Boolean(window.preview)',self.check_ready)

    def check_ready(self,ready):
        if not ready:
            self.polls+=1
            if self.polls>=100:
                self.status.setText('Falha ao iniciar WebGL. Verifique o driver gráfico e reinicie o aplicativo.');return
            QTimer.singleShot(100,lambda:self.loaded(True));return
        self.ready=True;self.select_model();self.last_digest=None;self.flush()

    def command(self,name,*args):
        if self.ready:
            self.web.page().runJavaScript(f'window.preview.{name}('+','.join(json.dumps(a) for a in args)+')')

    def select_model(self,*args):
        self.command('select',self.model,self.shorts.isChecked())

    def update_texture(self,image,template):
        model=Path(template).stem
        if model not in {'short_sleeve','long_sleeve'}:
            self.status.setText('UV personalizado: correspondência com estes modelos não validada. A prévia foi suspensa.')
            if self.web:self.web.hide()
            return
        if self.web:self.web.show()
        if model!=self.model:
            self.model=model;self.select_model()
        self.pending=image.copy()
        if self.isVisible():self.timer.start()

    def flush(self):
        if not self.ready or self.pending is None:return
        image=self.pending.copy();image.thumbnail((1024,1024))
        digest=hashlib.sha256(image.tobytes()).digest()
        if digest==self.last_digest:return
        self.last_digest=digest
        stream=io.BytesIO();image.save(stream,format='PNG')
        self.command('texture','shirt','data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode())

    def load_shorts(self):
        from core.uv.templates import read_image
        from PySide6.QtWidgets import QMessageBox
        path,_=QFileDialog.getOpenFileName(self,'Textura do short','','PNG (*.png)')
        if not path:return
        try:
            image=read_image(path);image.thumbnail((1024,1024))
            stream=io.BytesIO();image.save(stream,format='PNG')
            self.command('texture','shorts','data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode())
        except Exception as error:QMessageBox.warning(self,'Textura inválida',str(error))

    def shutdown(self):
        self.ready=False;self.polls=100
        self.timer.stop()
        if self.web:self.web.setUrl(QUrl('about:blank'))
        if self.server:self.server.close();self.server=None
