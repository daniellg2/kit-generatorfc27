"""Four-point regional correspondence editor with draggable numbered anchors."""
import copy
from pathlib import Path
from PySide6.QtCore import Qt,QPointF,QThread,Signal
from PySide6.QtGui import QPen,QColor,QBrush
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QFileDialog,QMessageBox,QGraphicsEllipseItem,QGraphicsItem,QGraphicsPixmapItem
from app.canvas import Canvas,pixmap
from app.demo import ROOT
from core.projection.photo_to_uv import MeshSurface
from core.generation.kit_generator import generate
from core.rendering.compositor import render
from core.uv.templates import read_image


class Point(QGraphicsEllipseItem):
    def __init__(self,x,y,index):
        super().__init__(-6,-6,12,12)
        self.setBrush(QBrush(QColor('#ffd16b')));self.setPen(QPen(QColor('black')))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPos(x,y)
        self.index=index


class PointsView(Canvas):
    def __init__(self,limit=None):
        super().__init__();self.markers=[];self.limit=limit;self.image=None
        self.background_item=QGraphicsPixmapItem()
        self.background_item.setZValue(-1)
        self.scene().addItem(self.background_item)

    def show_image(self,image):
        self.image=image.copy();self.image.thumbnail((800,800))
        for marker in self.markers:self.scene().removeItem(marker)
        self.markers=[];self.dimensions=self.image.size
        # Reuse the background and retain its wrapper across hit tests and mode changes.
        self.background_item.setPixmap(pixmap(self.image))
        self.scene().setSceneRect(0,0,*self.image.size);self.fit()

    def add(self,x,y):
        if self.limit and len(self.markers)>=self.limit:return
        w,h=self.dimensions
        marker=Point(x*w,y*h,len(self.markers)+1)
        self.scene().addItem(marker);self.markers.append(marker)
        text=self.scene().addSimpleText(str(marker.index));text.setBrush(QColor('#ff8000'));text.setParentItem(marker);text.setPos(8,-12)

    def values(self):
        w,h=self.dimensions
        return [[m.pos().x()/w,m.pos().y()/h] for m in self.markers]

    def order_corners(self):
        import cv2
        import numpy as np
        points=np.asarray(self.values(),dtype=np.float32)
        if points.shape!=(4,2):raise ValueError('Marque quatro pontos antes de ordenar os cantos.')
        hull=cv2.convexHull(points).reshape(-1,2)
        if len(hull)!=4:raise ValueError('Um ponto está dentro do triângulo dos outros. Arraste-o para um canto externo.')
        center=hull.mean(axis=0)
        hull=hull[np.argsort(np.arctan2(hull[:,1]-center[1],hull[:,0]-center[0]))]
        hull=np.roll(hull,-int(np.argmin(hull.sum(axis=1))),axis=0)
        for marker,point in zip(self.markers,hull):
            marker.setPos(float(point[0])*self.dimensions[0],float(point[1])*self.dimensions[1])
        self.viewport().update()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            item=self.itemAt(event.position().toPoint())
            if isinstance(item,Point) or (item and isinstance(item.parentItem(),Point)):
                return super(Canvas,self).mousePressEvent(event)
            x,y=self.normalized(event)
            if 0<=x<=1 and 0<=y<=1:self.add(x,y)
        else:super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        super(Canvas,self).mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        super(Canvas,self).mouseReleaseEvent(event)

    def drawForeground(self,painter,rect):
        painter.setPen(QPen(QColor('#ffb543'),2))
        points=[m.pos() for m in self.markers]
        for a,b in zip(points,points[1:]):painter.drawLine(a,b)


class ProjectionWorker(QThread):
    completed=Signal(object,object)
    failed=Signal(str)
    def __init__(self,args):super().__init__();self.args=args
    def run(self):
        try:
            result,colors=generate(*self.args)
            image=render(result,(768,768))
            self.completed.emit((result,image),colors)
        except Exception as error:self.failed.emit(str(error))


class PhotoDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.path='';self.result=None;self.worker=None;self.commit_pending=False
        stem=Path(window.project.template).stem
        filename={'short_sleeve':'Collar_0.json','long_sleeve':'Collar_0_LS.json'}.get(stem)
        if not filename:raise ValueError('Escolha Collar 0 manga curta ou longa antes de calibrar.')
        self.surface=MeshSurface(ROOT/'assets/models'/filename)
        self.setWindowTitle('Gerar a partir de foto · '+stem);self.resize(1350,850)
        layout=QVBoxLayout(self)
        self.notice=QLabel('Cruzeiro: cruzeiro_reference.png ausente; importe a foto original.' if not (ROOT/'assets/references/cruzeiro_reference.png').exists() else 'Importe uma foto ou recupere a última calibração.')
        self.notice.setWordWrap(True);layout.addWidget(self.notice)
        bar=QHBoxLayout();layout.addLayout(bar)
        self.region=QComboBox();self.region.addItems(['Frente','Costas','Manga esquerda','Manga direita','Ombro esquerdo','Ombro direito','Gola','Punhos','Barra','Detalhe'])
        bar.addWidget(self.region)
        def add(text,callback):
            b=QPushButton(text);b.clicked.connect(callback);bar.addWidget(b);return b
        add('Importar foto',self.import_photo)
        add('Limpar pontos',self.clear)
        add('Ordenar cantos',self.order_corners)
        add('Última calibração',self.restore)
        self.mode=QComboBox();self.mode.addItems(['1 · Quatro correspondências','2 · Contorno da faixa na foto']);bar.addWidget(self.mode)
        self.recalculate=add('Recalcular prévia',self.calculate)
        self.apply=add('Gerar camadas e conferir em 3D',self.accept_result)
        views=QHBoxLayout();layout.addLayout(views,1)
        self.photo=PointsView(4);self.uv=PointsView(4);self.preview=Canvas()
        for title,view in [('FOTO · pontos 1–4 / contorno da faixa',self.photo),('UV GEOMÉTRICO · mesmos pontos 1–4',self.uv),('COMPOSIÇÃO · prévia',self.preview)]:
            box=QVBoxLayout();box.addWidget(QLabel(title));box.addWidget(view);views.addLayout(box)
        self.mesh_image=self.surface.mask((800,800)).convert('RGBA')
        self.uv.show_image(self.mesh_image)
        self.photo_points=[];self.stripe_points=[]
        self.mode.currentIndexChanged.connect(self.switch_mode)
        layout.addWidget(QLabel('Calibre uma pequena região plana visível por vez. Marque 4 pares na mesma ordem ao redor do contorno; arraste para corrigir.\nDepois contorne uma faixa dentro da região na foto. Outras partes permanecem sem cobertura. Recalcule após qualquer ajuste.'))
        reference=ROOT/'assets/references/cruzeiro_reference.png'
        if reference.exists():
            self.path=str(reference);self.clear()
            self.notice.setText('Referência frontal do Cruzeiro carregada. Marque as correspondências; costas e detalhes ocultos não estão cobertos.')

    def clear(self):
        self.photo_points=[];self.stripe_points=[];self.mode.blockSignals(True);self.mode.setCurrentIndex(0);self.mode.blockSignals(False)
        self.photo.limit=4
        if self.path:self.photo.show_image(read_image(self.path))
        self.uv.show_image(self.mesh_image);self.result=None;self.apply.setEnabled(True)

    def import_photo(self):
        path,_=QFileDialog.getOpenFileName(self,'Foto original','','Imagens (*.png *.jpg *.jpeg *.webp)')
        if path:
            try:read_image(path)
            except Exception as e:QMessageBox.warning(self,'Foto inválida',str(e));return
            self.path=path;self.clear()

    def order_corners(self):
        try:
            if self.mode.currentIndex()!=0:raise ValueError('Volte ao modo 1 · Quatro correspondências para ordenar os pares.')
            # Explicit opt-in: independent ordering changes pair assignments, never mesh coordinates.
            if len(self.photo.markers)!=4 or len(self.uv.markers)!=4:raise ValueError('Marque quatro pontos na foto e quatro no UV.')
            self.photo.order_corners();self.uv.order_corners()
            self.notice.setText('Cantos ordenados em cada painel: 1 superior esquerdo → 2 superior direito → 3 inferior direito → 4 inferior esquerdo. Confira os pares; ilhas UV rotacionadas podem exigir correspondência manual. Recalcule a prévia.')
            self.result=None
        except Exception as error:QMessageBox.warning(self,'Verifique os cantos',str(error))

    def switch_mode(self,index):
        if not self.path:return
        if index==1:self.photo_points=self.photo.values()
        else:self.stripe_points=self.photo.values()
        self.photo.limit=None if index else 4
        self.photo.show_image(read_image(self.path))
        for p in (self.stripe_points if index else self.photo_points):self.photo.add(*p)

    def restore(self):
        calibrations=self.window.project.photo_calibrations
        if not calibrations:return
        c=calibrations[-1]
        if c['mesh_sha256']!=self.surface.digest:
            QMessageBox.warning(self,'Outro modelo','Calibração pertence a outra geometria.');return
        try:
            self.path=c['source'];self.clear()
            self.photo_points=c['photo_points'];self.stripe_points=c['stripe_points']
            for p in self.photo_points:self.photo.add(*p)
            for a in c['anchors']:self.uv.add(*self.surface.uv(a))
            self.region.setCurrentText(c['name'])
        except Exception as e:QMessageBox.warning(self,'Calibração inválida',str(e))

    def calculate(self):
        if self.worker and self.worker.isRunning():return
        try:
            if not self.path:raise ValueError('Importe uma fotografia.')
            if self.mode.currentIndex()==0:self.photo_points=self.photo.values()
            else:self.stripe_points=self.photo.values()
            count=len(self.uv.markers)
            if len(self.photo_points)!=4 or count!=4:
                raise ValueError(f'Marque quatro pontos correspondentes em cada painel. Foto: {len(self.photo_points)}/4; UV: {count}/4. Use o modo 1 para completar os pares.')
            anchors=[self.surface.anchor(p) for p in self.uv.values()]
            args=(copy.deepcopy(self.window.project),self.surface,self.path,self.region.currentText(),self.photo_points,anchors,self.stripe_points,ROOT/'output/generated')
            self.worker=ProjectionWorker(args);self.recalculate.setEnabled(False);self.apply.setEnabled(False)
            self.notice.setText('Calculando cor, correspondências e recorte geométrico…')
            self.worker.completed.connect(self.completed);self.worker.failed.connect(self.failure)
            self.worker.finished.connect(self.calculation_finished);self.worker.start()
        except Exception as e:self.failure(str(e))

    def completed(self,payload,colors):
        self.result,image=payload
        self.preview.display(image,None,[],'',None,0,False);self.preview.fit()
        self.apply.setEnabled(True)
        self.notice.setText('Paleta sugerida: '+', '.join(colors)+' · Somente esta região está coberta. Cores exigem revisão: iluminação pode afetar a amostragem.')
        if self.commit_pending:
            self.commit_pending=False
            self.window.change(lambda:setattr(self.window,'project',copy.deepcopy(self.result)))
            self.window.editor_tabs.setCurrentIndex(1)
            self.accept()

    def failure(self,message):
        self.commit_pending=False
        QMessageBox.warning(self,'Projeção não concluída',message)

    def calculation_finished(self):
        self.recalculate.setEnabled(True)
        self.apply.setEnabled(True)

    def accept_result(self):
        # Always recalculate to avoid applying stale points after a mouse adjustment.
        if self.worker and self.worker.isRunning():return
        self.commit_pending=True
        self.calculate()

    def reject(self):
        if self.worker and self.worker.isRunning():return
        super().reject()
