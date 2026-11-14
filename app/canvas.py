from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QImage, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


def pixmap(image):
    image = image.convert("RGBA")
    return QPixmap.fromImage(QImage(image.tobytes(), image.width, image.height, image.width*4, QImage.Format.Format_RGBA8888).copy())


class Canvas(QGraphicsView):
    drawn = Signal(str, list)
    moved = Signal(float, float)
    resized = Signal(float, float)
    vertexMoved = Signal(int, float, float)
    clicked = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(320, 320)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.mode = "select"
        self.points = []
        self.grid = False
        self.dimensions = (1024, 1024)
        self.selected_layer = None
        self.region_points = []
        self.drag = None
        self.panning = None
        self.initial_fit = True

    def set_mode(self, mode):
        self.mode = mode
        self.points = []
        self.setCursor(Qt.CursorShape.ArrowCursor if mode == "select" else Qt.CursorShape.CrossCursor)
        self.viewport().update()

    def display(self, image, guide, regions, selected_region, layer, opacity, show_regions):
        self.scene().clear()
        self.dimensions = image.size
        w, h = image.size
        self.scene().setSceneRect(0, 0, w, h)
        self.scene().addPixmap(pixmap(image))
        if guide and opacity:
            overlay = self.scene().addPixmap(pixmap(guide))
            overlay.setOpacity(opacity)
        self.region_points = []
        for region in regions:
            if not show_regions:
                continue
            selected = region.id == selected_region
            points = [QPointF(x*w,y*h) for x,y in region.points]
            pen = QPen(QColor("#ffd16b" if selected else "#66b8ff"), 1.5)
            pen.setCosmetic(True)
            self.scene().addPolygon(QPolygonF(points), pen, QBrush(QColor(70,150,255,22)))
            text = self.scene().addSimpleText(region.name)
            text.setBrush(QColor("#ffd16b" if selected else "#8dcbff"))
            text.setPos(points[0])
            text.setFlag(text.GraphicsItemFlag.ItemIgnoresTransformations)
            for name, (x,y) in region.landmarks.items():
                self.scene().addEllipse(x*w-3,y*h-3,6,6,pen,QBrush(QColor("#ffd16b")))
                label = self.scene().addSimpleText(name)
                label.setBrush(QColor("#ffd16b"))
                label.setPos(x*w+5,y*h)
                label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations)
            if selected:
                self.region_points = region.points
                for p in points:
                    self.scene().addEllipse(p.x()-4,p.y()-4,8,8,pen,QBrush(QColor("#ffd16b")))
        self.selected_layer = layer
        if layer:
            pen = QPen(QColor("#f3f7ff"), 1, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            item = self.scene().addRect(-layer.width*w/2,-layer.height*h/2,layer.width*w,layer.height*h,pen)
            item.setPos(layer.x*w,layer.y*h)
            item.setRotation(layer.rotation)
            self.scene().addEllipse(layer.x*w-3,layer.y*h-3,6,6,pen,QBrush(QColor("#f3f7ff")))
        if self.initial_fit:
            self.fit()
            self.initial_fit = False

    def fit(self):
        self.fitInView(self.sceneRect().adjusted(-28,-28,28,28), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        factor = 1.18 if event.angleDelta().y() > 0 else 1/1.18
        current = self.transform().m11()
        if .08 <= current*factor <= 12:
            self.scale(factor, factor)
        event.accept()

    def normalized(self, event):
        p = self.mapToScene(event.position().toPoint())
        return p.x()/self.dimensions[0], p.y()/self.dimensions[1]

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.finish()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x,y = self.normalized(event)
        if self.mode != "select":
            if 0 <= x <= 1 and 0 <= y <= 1:
                if self.mode == "landmark":
                    self.drawn.emit("landmark", [[x,y]])
                    self.set_mode("select")
                else:
                    self.points.append([x,y])
                    self.viewport().update()
            return
        for i,(px,py) in enumerate(self.region_points):
            if abs(x-px)*self.dimensions[0]*self.transform().m11() < 10 and abs(y-py)*self.dimensions[1]*self.transform().m11() < 10:
                self.drag = ("vertex", i)
                return
        self.clicked.emit(x,y)
        if self.selected_layer:
            self.drag = ("layer", x, y)

    def mouseMoveEvent(self, event):
        if self.panning is not None:
            delta = event.position() - self.panning
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-round(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-round(delta.y()))
            self.panning = event.position()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.drag and event.button() == Qt.MouseButton.LeftButton:
            x,y = self.normalized(event)
            if self.drag[0] == "vertex":
                self.vertexMoved.emit(self.drag[1], max(0,min(1,x)), max(0,min(1,y)))
            else:
                dx,dy = x-self.drag[1], y-self.drag[2]
                if abs(dx)+abs(dy) > .0001:
                    self.moved.emit(dx,dy)
            self.drag = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish()
        elif event.key() == Qt.Key.Key_Escape:
            self.set_mode("select")
        elif event.key() == Qt.Key.Key_Backspace and self.points:
            self.points.pop()
            self.viewport().update()
        elif event.key() == Qt.Key.Key_F:
            self.fit()
        else:
            super().keyPressEvent(event)

    def finish(self):
        required = 2 if self.mode == "curve" else 3
        if len(self.points) >= required:
            mode, points = self.mode, self.points[:]
            self.set_mode("select")
            self.drawn.emit(mode, points)

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#14181f"))
        w,h = self.dimensions
        painter.save()
        painter.setClipRect(QRectF(0,0,w,h))
        tile = 32
        for y in range(max(0,int(rect.top()/tile)*tile), min(h,int(rect.bottom())+tile),tile):
            for x in range(max(0,int(rect.left()/tile)*tile),min(w,int(rect.right())+tile),tile):
                painter.fillRect(x,y,tile,tile,QColor("#262c35" if (x//tile+y//tile)%2 else "#20252d"))
        if self.grid:
            pen = QPen(QColor("#455263"),1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            for i in range(1,16):
                painter.drawLine(QPointF(w*i/16,0),QPointF(w*i/16,h))
                painter.drawLine(QPointF(0,h*i/16),QPointF(w,h*i/16))
            pen.setColor(QColor("#768aa6"))
            painter.setPen(pen)
            painter.drawLine(QPointF(w/2,0),QPointF(w/2,h))
            painter.drawLine(QPointF(0,h/2),QPointF(w,h/2))
        painter.restore()

    def drawForeground(self, painter, rect):
        if self.points:
            pen = QPen(QColor("#ffd16b"),2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            pts = [QPointF(x*self.dimensions[0],y*self.dimensions[1]) for x,y in self.points]
            painter.drawPolyline(QPolygonF(pts))
            for p in pts:
                painter.drawEllipse(p,3,3)
