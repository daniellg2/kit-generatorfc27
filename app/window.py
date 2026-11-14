import copy
import functools
import logging
import math
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSpinBox, QSplitter, QTabWidget, QToolBar, QVBoxLayout, QWidget,
)
from app.canvas import Canvas, pixmap
from app.demo import ROOT, cruzeiro_demo, new_project
from core.detection.analyzer import OpenCVAnalyzer
from core.layers.model import Layer, Project, Region, uid
from core.projects.storage import load_project, missing_assets, save_project
from core.rendering.compositor import export_png, load_art, render
from core.uv.templates import derive_mask, guide_overlay, read_image


def safe(fn):
    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as error:
            logging.exception("Falha na operação %s", fn.__name__)
            QMessageBox.warning(self, "Operação não concluída", str(error))
            return None
    return wrapped


def label(text, kind="section"):
    widget = QLabel(text)
    widget.setObjectName(kind)
    widget.setWordWrap(True)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("primary")
    return widget


def row(*widgets):
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0,0,0,0)
    for w in widgets:
        layout.addWidget(w)
    return box


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = new_project()
        self.path = None
        self.selected_id = self.project.layers[0].id
        self.region_id = ""
        self.undo_stack, self.redo_stack = [], []
        self.saved_state = self.project.to_dict()
        self.refreshing = False
        self.guide_key = None
        self.guide = None
        self.analysis = None
        self.setWindowTitle("FC27 Kit Generator")
        self.resize(1480, 940)
        self.setMinimumSize(1050, 700)
        self.build_ui()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.autosave)
        self.timer.start(45000)
        QTimer.singleShot(0, self.recover)

    def build_ui(self):
        menu = self.menuBar().addMenu("Projeto")
        for title, shortcut, callback in (
            ("Novo", "Ctrl+N", self.new), ("Abrir…", "Ctrl+O", self.open),
            ("Salvar", "Ctrl+S", self.save), ("Salvar como…", "Ctrl+Shift+S", self.save_as),
            ("Demonstração Cruzeiro", "", self.demo), ("Exportar PNG…", "Ctrl+E", self.export_dialog),
        ):
            action = QAction(title, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(callback)
            menu.addAction(action)
        edit = self.menuBar().addMenu("Editar")
        for title, shortcut, callback in (("Desfazer","Ctrl+Z",self.undo),("Refazer","Ctrl+Y",self.redo),("Duplicar camada","Ctrl+D",self.duplicate)):
            action = QAction(title,self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            edit.addAction(action)
        tools = QToolBar("Ferramentas",self)
        tools.setMovable(False)
        self.addToolBar(tools)
        for text, mode in (("Selecionar / mover","select"),("Região UV","region"),("Polígono","polygon"),("Curva","curve"),("Landmark","landmark")):
            action = QAction(text,self)
            action.triggered.connect(lambda checked=False,m=mode:self.set_tool(m))
            tools.addAction(action)
        tools.addSeparator()
        tools.addAction("Enquadrar [F]",lambda:self.canvas.fit())
        tools.addAction("Desfazer",self.undo)
        tools.addAction("Refazer",self.redo)

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14,10,14,8)
        header = QHBoxLayout()
        titlebox = QVBoxLayout()
        titlebox.addWidget(label("FC27  /  KIT GENERATOR","brand"))
        titlebox.addWidget(label("ESTÚDIO DE TEXTURAS UV     •     LOCAL / CPU","subtitle"))
        header.addLayout(titlebox)
        header.addStretch()
        self.project_label = label("Novo uniforme","subtitle")
        header.addWidget(self.project_label)
        header.addWidget(button("Gerar a partir de foto",self.generate_photo,True))
        header.addWidget(button("Salvar projeto",self.save))
        header.addWidget(button("Exportar PNG",self.export_dialog,True))
        outer.addLayout(header)
        split = QSplitter()
        outer.addWidget(split,1)
        self.setCentralWidget(central)

        left = QWidget()
        left.setObjectName("panel")
        left.setMinimumWidth(265)
        left.setMaximumWidth(390)
        ll = QVBoxLayout(left)
        ll.addWidget(label("01   MOLDE & CONTEÚDO"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(["Collar 0 · manga curta","Collar 0 LS · manga longa","UV personalizado"])
        self.template_combo.currentIndexChanged.connect(self.switch_template)
        ll.addWidget(self.template_combo)
        ll.addWidget(row(button("Carregar UV…",self.import_template),button("Máscara…",self.import_mask)))
        self.tabs = QTabWidget()
        ll.addWidget(self.tabs,1)
        layers_tab = QWidget()
        layout = QVBoxLayout(layers_tab)
        layout.setContentsMargins(0,10,0,0)
        self.layer_list = QListWidget()
        self.layer_list.currentItemChanged.connect(self.select_layer)
        self.layer_list.itemChanged.connect(self.toggle_layer)
        layout.addWidget(self.layer_list,1)
        layout.addWidget(row(button("↑",lambda:self.reorder(1)),button("↓",lambda:self.reorder(-1)),button("Duplicar",self.duplicate),button("Excluir",self.delete_layer)))
        layout.addWidget(row(button("+ Cor / forma",lambda:self.add_layer("fill")),button("+ Faixas",lambda:self.add_layer("stripes"))))
        layout.addWidget(row(button("+ PNG / SVG",lambda:self.import_art(False)),button("+ Padrão",lambda:self.import_art(True))))
        layout.addWidget(label("Topo da lista = frente da composição.\nTodos os elementos são recortados pelo molde.","subtitle"))
        self.tabs.addTab(layers_tab,"Camadas")

        regions_tab = QWidget()
        layout = QVBoxLayout(regions_tab)
        layout.setContentsMargins(0,10,0,0)
        self.region_list = QListWidget()
        self.region_list.currentItemChanged.connect(self.select_region)
        layout.addWidget(self.region_list,1)
        layout.addWidget(button("+ Desenhar região",lambda:self.set_tool("region"),True))
        layout.addWidget(row(button("Renomear",self.rename_region),button("Redesenhar",lambda:self.set_tool("replace_region")),button("Excluir",self.delete_region)))
        layout.addWidget(button("+ Landmark / reserva de logo",lambda:self.set_tool("landmark")))
        layout.addWidget(button("Remover landmark…",self.delete_landmark))
        self.region_role = QComboBox()
        self.region_role.addItems(["Sem correspondência","Frente","Costas","Lateral","Manga esquerda","Manga direita","Gola","Punhos","Detalhe"])
        self.region_role.currentTextChanged.connect(self.set_region_role)
        layout.addWidget(label("REFERÊNCIA DA REGIÃO"))
        layout.addWidget(self.region_role)
        layout.addWidget(button("Salvar calibração…",self.save_calibration))
        layout.addWidget(button("Carregar calibração…",self.load_calibration))
        layout.addWidget(label("Clique para criar vértices; Enter conclui. Selecione uma região e arraste seus pontos amarelos para editar.","subtitle"))
        self.tabs.addTab(regions_tab,"Regiões")

        refs_tab = QWidget()
        layout = QVBoxLayout(refs_tab)
        layout.setContentsMargins(0,10,0,0)
        self.ref_list = QListWidget()
        self.ref_list.currentRowChanged.connect(self.show_reference)
        self.ref_list.itemDoubleClicked.connect(self.view_reference)
        layout.addWidget(self.ref_list,1)
        self.ref_preview = QLabel("Importe uma foto ou exemplo UV")
        self.ref_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ref_preview.setMinimumHeight(170)
        self.ref_preview.setWordWrap(True)
        layout.addWidget(self.ref_preview)
        layout.addWidget(row(button("+ Referência",self.import_reference),button("Remover",self.delete_reference)))
        layout.addWidget(row(button("Ampliar",self.view_reference),button("Usar como camada",self.reference_as_layer)))
        layout.addWidget(button("Analisar referência · experimental",self.analyze))
        self.coverage = label("Nenhuma referência importada.","notice")
        layout.addWidget(self.coverage)
        self.tabs.addTab(refs_tab,"Fotos")
        split.addWidget(left)

        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(0,0,0,0)
        viewbar = QHBoxLayout()
        viewbar.addWidget(label("02   TEXTURA UV"))
        viewbar.addStretch()
        self.show_regions = QCheckBox("Regiões")
        self.show_regions.setChecked(True)
        self.show_regions.toggled.connect(self.refresh_canvas)
        viewbar.addWidget(self.show_regions)
        self.grid_check = QCheckBox("Grade / eixos")
        self.grid_check.toggled.connect(self.toggle_grid)
        viewbar.addWidget(self.grid_check)
        viewbar.addWidget(QLabel("Malha"))
        self.uv_opacity = QSlider(Qt.Orientation.Horizontal)
        self.uv_opacity.setRange(0,100)
        self.uv_opacity.setValue(38)
        self.uv_opacity.setMaximumWidth(120)
        self.uv_opacity.valueChanged.connect(self.refresh_canvas)
        viewbar.addWidget(self.uv_opacity)
        cl.addLayout(viewbar)
        self.canvas = Canvas()
        self.canvas.drawn.connect(self.finish_draw)
        self.canvas.moved.connect(self.move_layer)
        self.canvas.vertexMoved.connect(self.move_vertex)
        self.canvas.clicked.connect(self.pick_layer)
        from app.preview3d.widget import Preview3D
        self.editor_tabs = QTabWidget()
        self.editor_tabs.addTab(self.canvas,"Editor UV")
        self.preview3d = Preview3D()
        self.preview3d.sleeveRequested.connect(self.template_combo.setCurrentIndex)
        self.editor_tabs.addTab(self.preview3d,"Prévia 3D")
        cl.addWidget(self.editor_tabs,1)
        self.hint = label("Scroll: zoom  ·  botão central: pan  ·  arraste: mover camada  ·  F: enquadrar","subtitle")
        cl.addWidget(self.hint)
        split.addWidget(center)

        right = QWidget()
        right.setObjectName("panel")
        right.setMinimumWidth(270)
        right.setMaximumWidth(370)
        rl = QVBoxLayout(right)
        rl.addWidget(label("03   PROPRIEDADES"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("properties")
        formbox = QVBoxLayout(content)
        formbox.setContentsMargins(0,0,8,0)
        form = QFormLayout()
        self.property_form = form
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.props = {}
        name = QLineEdit()
        name.editingFinished.connect(self.apply_properties)
        self.props["name"] = name
        form.addRow("Nome",name)
        self.layer_region = QComboBox()
        self.layer_region.currentIndexChanged.connect(self.apply_properties)
        form.addRow("Recortar em",self.layer_region)
        for key, title, lo, hi, step in (
            ("x","Centro X",-2,3,.005),("y","Centro Y",-2,3,.005),
            ("width","Largura",.001,2,.005),("height","Altura",.001,2,.005),
            ("rotation","Rotação °",-360,360,1),("opacity","Opacidade",0,1,.05),
            ("stroke","Traço / contorno",.0001,1,.001),
            ("spacing","Passo das faixas",.002,2,.005),("thickness","Espessura faixa",.001,2,.005),
            ("tile_scale","Escala do padrão",.005,2,.01),
            ("offset_x","Desloc. padrão X",-2,2,.01),("offset_y","Desloc. padrão Y",-2,2,.01),
        ):
            widget = QDoubleSpinBox()
            widget.setRange(lo,hi)
            widget.setDecimals(4 if key != "rotation" else 1)
            widget.setSingleStep(step)
            widget.setKeyboardTracking(False)
            widget.valueChanged.connect(lambda value,k=key:self.apply_properties(changed=k))
            self.props[key] = widget
            form.addRow(title,widget)
        formbox.addLayout(form)
        self.color_button = button("Cor da camada",self.choose_color)
        formbox.addWidget(self.color_button)
        for key,title in (("keep_aspect","Preservar proporções"),("flip_x","Espelhar horizontal"),("flip_y","Espelhar vertical"),("recolor","Recolorir imagem pelo alfa"),("outline","Somente contorno")):
            widget = QCheckBox(title)
            widget.toggled.connect(self.apply_properties)
            self.props[key] = widget
            formbox.addWidget(widget)
        formbox.addWidget(row(button("Enquadrar na região",self.fit_region),button("Centralizar",self.center_layer)))
        formbox.addWidget(button("Alinhar a landmark…",self.align_landmark))
        formbox.addWidget(label("Coordenadas em frações do UV. Rotação positiva segue o sentido horário. O vínculo de região recorta; não deforma a arte.","subtitle"))
        formbox.addWidget(label("EXPORTAÇÃO"))
        self.export_width = QSpinBox()
        self.export_width.setRange(64,8192)
        self.export_width.setSingleStep(256)
        self.export_width.setKeyboardTracking(False)
        self.export_width.valueChanged.connect(self.set_export_width)
        formbox.addWidget(row(QLabel("Largura (px)"),self.export_width))
        formbox.addWidget(button("Resolução original do UV",self.original_resolution))
        formbox.addWidget(button("Prévia / exportar PNG RGBA",self.export_dialog,True))
        self.notes = label("","notice")
        formbox.addWidget(self.notes)
        formbox.addStretch()
        scroll.setWidget(content)
        rl.addWidget(scroll,1)
        split.addWidget(right)
        split.setSizes([290,850,300])
        split.setStretchFactor(1,1)
        self.statusBar().showMessage("Pronto · calibre a correspondência das regiões antes da reconstrução.")

    def current_layer(self):
        return next((l for l in self.project.layers if l.id == self.selected_id),None)

    @safe
    def generate_photo(self):
        from app.photo_dialog import PhotoDialog
        PhotoDialog(self).exec()

    def current_region(self):
        return next((r for r in self.project.regions if r.id == self.region_id),None)

    def change(self, callback):
        before = self.project.to_dict()
        try:
            callback()
            self.project.validate()
            if self.project.to_dict() == before:
                return
            self.refresh_canvas()
        except Exception:
            self.project = Project.from_dict(before)
            self.refresh()
            raise
        self.undo_stack.append(before)
        self.undo_stack = self.undo_stack[-40:]
        self.redo_stack.clear()
        self.refresh()

    @safe
    def refresh(self, *args):
        self.refreshing = True
        try:
            self.project_label.setText(self.project.name + ("  •" if self.dirty() else ""))
            self.setWindowTitle(f"{self.project.name}{' *' if self.dirty() else ''} — FC27 Kit Generator")
            template = Path(self.project.template).stem
            self.template_combo.setCurrentIndex(0 if template == "short_sleeve" else 1 if template == "long_sleeve" else 2)
            self.layer_list.clear()
            for layer in reversed(self.project.layers):
                item = QListWidgetItem(layer.name)
                item.setData(Qt.ItemDataRole.UserRole,layer.id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if layer.visible else Qt.CheckState.Unchecked)
                item.setToolTip(layer.kind + (" · " + layer.source if layer.source else ""))
                self.layer_list.addItem(item)
                if layer.id == self.selected_id:
                    self.layer_list.setCurrentItem(item)
            self.region_list.clear()
            for region in self.project.regions:
                item = QListWidgetItem(region.name)
                item.setData(Qt.ItemDataRole.UserRole,region.id)
                self.region_list.addItem(item)
                if region.id == self.region_id:
                    self.region_list.setCurrentItem(item)
            self.layer_region.clear()
            self.layer_region.addItem("Todo o molde","")
            for r in self.project.regions:
                self.layer_region.addItem(r.name,r.id)
            layer = self.current_layer()
            for key,widget in self.props.items():
                widget.setEnabled(layer is not None)
                if layer:
                    value = getattr(layer,key)
                    if isinstance(widget,QLineEdit): widget.setText(value)
                    elif isinstance(widget,QCheckBox): widget.setChecked(value)
                    else: widget.setValue(value)
            if layer:
                self.layer_region.setCurrentIndex(max(0,self.layer_region.findData(layer.region)))
                self.color_button.setText(f"Cor   {layer.color.upper()}")
                self.color_button.setStyleSheet(f"border-left: 12px solid {layer.color};")
            kind = layer.kind if layer else ""
            for key in ("spacing","thickness","tile_scale","offset_x","offset_y","stroke"):
                relevant = kind == "stripes" if key in {"spacing","thickness"} else kind == "pattern" if key in {"tile_scale","offset_x","offset_y"} else kind in {"fill","polygon","curve"}
                self.property_form.setRowVisible(self.props[key],relevant)
            self.props["recolor"].setVisible(kind == "image")
            self.props["outline"].setVisible(kind in {"fill","polygon"})
            region = self.current_region()
            self.region_role.setCurrentText(region.reference_role if region and region.reference_role else "Sem correspondência")
            current_ref = self.ref_list.currentRow()
            self.ref_list.clear()
            for ref in self.project.references:
                self.ref_list.addItem(f"{ref['role']} · {Path(ref['path']).name}")
            if self.project.references:
                self.ref_list.setCurrentRow(max(0,min(current_ref,len(self.project.references)-1)))
            else:
                self.ref_preview.setPixmap(QPixmap())
                self.ref_preview.setText("Importe uma foto ou exemplo UV")
            self.export_width.setValue(self.project.export_width)
            roles = {r["role"] for r in self.project.references}
            uncovered = [r.name for r in self.project.regions if not r.reference_role or r.reference_role not in roles]
            self.coverage.setText("Sem referência associada: " + ", ".join(uncovered) if uncovered else ("Calibre as regiões para verificar cobertura." if not self.project.regions else "Regiões com referências associadas; confira os detalhes manualmente."))
            self.notes.setText("PNG de protótipo. Compatibilidade com FC 27 ainda não validada.\n" + ("Calibração anatômica pendente.\n" if not self.project.regions else "") + ("Máscara raster: revise os limites.\n" if self.project.mask and "_mask" in self.project.mask else "") + self.project.notes)
        finally:
            self.refreshing = False
        self.refresh_canvas()

    def refresh_canvas(self, *args):
        if not hasattr(self,"canvas"):
            return
        original = read_image(self.project.template).size
        factor = min(1,1024/max(original))
        size = tuple(max(1,round(v*factor)) for v in original)
        key = (self.project.template,self.project.mask,size,Path(self.project.template).stat().st_mtime_ns,Path(self.project.mask).stat().st_mtime_ns if self.project.mask else 0)
        if key != self.guide_key:
            self.guide = guide_overlay(self.project,size)
            self.guide_key = key
        image = render(self.project,size)
        self.preview3d.update_texture(image,self.project.template)
        self.canvas.display(image,self.guide,self.project.regions,self.region_id,self.current_layer(),self.uv_opacity.value()/100,self.show_regions.isChecked())

    def dirty(self):
        return self.project.to_dict() != self.saved_state

    @safe
    def apply_properties(self, *args, changed=None):
        if self.refreshing or not self.current_layer():
            return
        layer = self.current_layer()
        def update():
            old_w,old_h = layer.width,layer.height
            for key,widget in self.props.items():
                setattr(layer,key,widget.text() if isinstance(widget,QLineEdit) else widget.isChecked() if isinstance(widget,QCheckBox) else widget.value())
            if layer.keep_aspect and changed in {"width","height"}:
                if changed == "width": layer.height = layer.width*old_h/old_w
                else: layer.width = layer.height*old_w/old_h
            layer.region = self.layer_region.currentData() or ""
        self.change(update)

    @safe
    def select_layer(self, item, previous=None):
        if not self.refreshing:
            self.selected_id = item.data(Qt.ItemDataRole.UserRole) if item else ""
            self.refresh()

    @safe
    def select_region(self,item,previous=None):
        if not self.refreshing:
            self.region_id = item.data(Qt.ItemDataRole.UserRole) if item else ""
            self.refresh()

    @safe
    def toggle_layer(self,item):
        if self.refreshing:
            return
        layer = next(l for l in self.project.layers if l.id == item.data(Qt.ItemDataRole.UserRole))
        self.change(lambda:setattr(layer,"visible",item.checkState() == Qt.CheckState.Checked))

    @safe
    def pick_layer(self,x,y):
        if self.tabs.currentIndex() == 1:
            return
        for layer in reversed(self.project.layers):
            if not layer.visible:
                continue
            dx,dy = (x-layer.x)*self.canvas.dimensions[0],(y-layer.y)*self.canvas.dimensions[1]
            angle = math.radians(-layer.rotation)
            rx,ry = dx*math.cos(angle)-dy*math.sin(angle),dx*math.sin(angle)+dy*math.cos(angle)
            if abs(rx) <= layer.width*self.canvas.dimensions[0]/2 and abs(ry) <= layer.height*self.canvas.dimensions[1]/2:
                self.selected_id = layer.id
                self.refresh()
                return

    @safe
    def move_layer(self,dx,dy):
        layer = self.current_layer()
        if layer:
            self.change(lambda:(setattr(layer,"x",layer.x+dx),setattr(layer,"y",layer.y+dy)))

    @safe
    def move_vertex(self,index,x,y):
        region = self.current_region()
        if region:
            self.change(lambda:region.points.__setitem__(index,[x,y]))

    def set_tool(self,mode):
        if mode in {"replace_region","landmark"} and not self.current_region():
            self.statusBar().showMessage("Selecione ou desenhe uma região antes de usar esta ferramenta.")
            return
        if mode in {"region","replace_region","landmark"}:
            self.tabs.setCurrentIndex(1)
            self.selected_id = ""
            self.show_regions.setChecked(True)
        self.canvas.set_mode(mode)
        self.hint.setText("Clique para inserir pontos · Enter ou botão direito conclui · Backspace remove ponto · Esc cancela" if mode != "select" else "Scroll: zoom · botão central: pan · arraste: mover camada · F: enquadrar")
        self.canvas.setFocus()
        self.refresh_canvas()

    @safe
    def finish_draw(self,mode,points):
        if mode == "landmark":
            region = self.current_region()
            if not region: return
            name,ok = QInputDialog.getText(self,"Landmark / reserva","Nome (ex.: escudo Cruzeiro, Adidas, Betnacional):")
            if ok and name.strip():
                self.change(lambda:region.landmarks.__setitem__(name.strip(),points[0]))
        elif mode == "replace_region":
            region = self.current_region()
            if region: self.change(lambda:setattr(region,"points",points))
        elif mode == "region":
            name,ok = QInputDialog.getItem(self,"Nova região UV","Nome da região:",["Frente do torso","Costas do torso","Manga esquerda","Manga direita","Gola","Punho esquerdo","Punho direito","Barra inferior","Região adicional"],0,True)
            if ok and name.strip():
                region = Region(name.strip(),points)
                self.region_id = region.id
                self.change(lambda:self.project.regions.append(region))
        elif mode in {"polygon","curve"}:
            xs,ys = list(zip(*points))
            x0,y0,x1,y1 = min(xs),min(ys),max(xs),max(ys)
            w,h = max(.001,x1-x0),max(.001,y1-y0)
            local = [[(x-x0)/w,(y-y0)/h] for x,y in points]
            layer = Layer("Polígono" if mode == "polygon" else "Linha curva",kind=mode,x=x0+w/2,y=y0+h/2,width=w,height=h,points=local,color="#165fc9",region=self.region_id)
            self.selected_id = layer.id
            self.change(lambda:self.project.layers.append(layer))
            self.tabs.setCurrentIndex(0)
        self.canvas.set_mode("select")
        self.hint.setText("Scroll: zoom · botão central: pan · arraste: mover camada · F: enquadrar")

    @safe
    def add_layer(self,kind):
        layer = Layer("Área preenchida" if kind == "fill" else "Faixas · gire para diagonal",kind=kind,color="#1258c4",width=.25,height=.25,region=self.region_id)
        self.selected_id = layer.id
        self.change(lambda:self.project.layers.append(layer))

    @safe
    def import_art(self,pattern=False):
        path,_ = QFileDialog.getOpenFileName(self,"Importar padrão" if pattern else "Importar arte original","","Imagens (*.png *.svg *.jpg *.jpeg *.webp *.bmp)")
        if not path: return
        image = load_art(path)
        canvas = read_image(self.project.template)
        width = .15
        height = min(1,width*canvas.width/canvas.height*image.height/image.width)
        layer = Layer(Path(path).stem,"pattern" if pattern else "image",source=str(Path(path).resolve()),width=.6 if pattern else width,height=.6 if pattern else height,region=self.region_id)
        self.selected_id = layer.id
        self.change(lambda:self.project.layers.append(layer))

    @safe
    def duplicate(self,*args):
        layer = self.current_layer()
        if layer:
            new = copy.deepcopy(layer)
            new.id = uid()
            new.name += " · cópia"
            self.selected_id = new.id
            index = self.project.layers.index(layer)
            self.change(lambda:self.project.layers.insert(index+1,new))

    @safe
    def delete_layer(self):
        layer = self.current_layer()
        if layer:
            self.selected_id = ""
            self.change(lambda:self.project.layers.remove(layer))

    @safe
    def reorder(self,step):
        layer = self.current_layer()
        if layer:
            i = self.project.layers.index(layer)
            target = max(0,min(len(self.project.layers)-1,i+step))
            def swap():
                self.project.layers[i],self.project.layers[target] = self.project.layers[target],self.project.layers[i]
            self.change(swap)

    @safe
    def choose_color(self):
        layer = self.current_layer()
        if not layer: return
        color = QColorDialog.getColor(QColor(layer.color),self,"Cor da camada")
        if color.isValid(): self.change(lambda:setattr(layer,"color",color.name()))

    @safe
    def fit_region(self):
        layer = self.current_layer()
        if not layer or not layer.region:
            self.statusBar().showMessage("Escolha uma região em 'Recortar em'.")
            return
        region = next(r for r in self.project.regions if r.id == layer.region)
        xs,ys = zip(*region.points)
        def update():
            layer.x,layer.y = (min(xs)+max(xs))/2,(min(ys)+max(ys))/2
            layer.width,layer.height = max(.001,max(xs)-min(xs)),max(.001,max(ys)-min(ys))
            layer.rotation = 0
        self.change(update)

    @safe
    def center_layer(self):
        layer = self.current_layer()
        if layer: self.change(lambda:(setattr(layer,"x",.5),setattr(layer,"y",.5)))

    @safe
    def align_landmark(self):
        layer = self.current_layer()
        landmarks = {f"{r.name} / {name}":(r.id,p) for r in self.project.regions for name,p in r.landmarks.items()}
        if not layer or not landmarks:
            self.statusBar().showMessage("Crie landmarks em uma região e selecione uma camada.")
            return
        name,ok = QInputDialog.getItem(self,"Alinhar arte","Centro da camada no landmark:",list(landmarks),0,False)
        if ok:
            region_id,p = landmarks[name]
            self.change(lambda:(setattr(layer,"x",p[0]),setattr(layer,"y",p[1]),setattr(layer,"region",region_id)))

    @safe
    def rename_region(self):
        region = self.current_region()
        if not region:return
        name,ok = QInputDialog.getText(self,"Renomear região","Nome:",text=region.name)
        if ok and name.strip():self.change(lambda:setattr(region,"name",name.strip()))

    @safe
    def delete_region(self):
        region = self.current_region()
        if not region:return
        linked = [l for l in self.project.layers if l.region == region.id]
        if linked:
            QMessageBox.information(self,"Região em uso","Remova o vínculo das camadas antes de excluir esta região.")
            return
        self.region_id = ""
        self.change(lambda:self.project.regions.remove(region))

    @safe
    def delete_landmark(self):
        region = self.current_region()
        if not region or not region.landmarks:return
        name,ok = QInputDialog.getItem(self,"Remover landmark","Nome:",list(region.landmarks),0,False)
        if ok:self.change(lambda:region.landmarks.pop(name))

    @safe
    def set_region_role(self,text):
        region = self.current_region()
        if not self.refreshing and region:
            self.change(lambda:setattr(region,"reference_role","" if text == "Sem correspondência" else text))

    @safe
    def save_calibration(self):
        if not self.project.regions:return
        path,_ = QFileDialog.getSaveFileName(self,"Salvar calibração","calibracao.json","Projeto JSON (*.json)")
        if path:
            calibration = copy.deepcopy(self.project)
            calibration.layers,calibration.references = [],[]
            calibration.name = "Calibração · " + Path(calibration.template).stem
            save_project(calibration,path)

    @safe
    def load_calibration(self):
        path,_ = QFileDialog.getOpenFileName(self,"Carregar calibração","","Projeto JSON (*.json)")
        if not path:return
        calibration = load_project(path)
        if read_image(calibration.template).size != read_image(self.project.template).size or Path(calibration.template).read_bytes() != Path(self.project.template).read_bytes():
            raise ValueError("A calibração pertence a outro UV. Abra o arquivo como projeto para usar aquele molde.")
        def update():
            for r in calibration.regions:
                r.id = uid()
                self.project.regions.append(r)
        self.change(update)

    @safe
    def switch_template(self,index):
        if self.refreshing or index == 2:return
        sleeve = "short_sleeve" if index == 0 else "long_sleeve"
        self.replace_template(str(ROOT / f"assets/uv_templates/{sleeve}.png"),str(ROOT / f"assets/uv_templates/{sleeve}_mask.png"))

    def replace_template(self,path,mask):
        if self.project.regions or len(self.project.layers) > 1:
            answer = QMessageBox.question(self,"Trocar molde","A troca limpa a calibração e oculta as artes, pois a correspondência UV muda. Continuar?")
            if answer != QMessageBox.StandardButton.Yes:
                self.refresh()
                return
        read_image(path)
        def update():
            self.project.template,self.project.mask = path,mask
            self.project.regions = []
            for layer in self.project.layers:
                layer.region = ""
                if layer.kind != "fill" or layer.width < 1 or layer.height < 1:
                    layer.visible = False
        self.region_id = ""
        self.canvas.initial_fit = True
        self.change(update)

    @safe
    def import_template(self):
        path,_ = QFileDialog.getOpenFileName(self,"Carregar guia UV","","UV PNG (*.png)")
        if not path:return
        mask_path,_ = QFileDialog.getOpenFileName(self,"Escolha a máscara preto/branco do UV (mesmas dimensões)","","Máscara PNG (*.png)")
        if not mask_path:
            self.refresh()
            return
        self.replace_template(str(Path(path).resolve()),str(Path(mask_path).resolve()))

    @safe
    def import_mask(self):
        path,_ = QFileDialog.getOpenFileName(self,"Máscara preto/branco: branco permite arte; preto recorta","","Máscara PNG (*.png)")
        if path:self.change(lambda:setattr(self.project,"mask",str(Path(path).resolve())))

    def toggle_grid(self,value):
        self.canvas.grid = value
        self.canvas.viewport().update()

    @safe
    def import_reference(self):
        paths,_ = QFileDialog.getOpenFileNames(self,"Importar fotos ou exemplos UV","","Imagens (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not paths:return
        role,ok = QInputDialog.getItem(self,"Tipo de referência","Vista / detalhe:",["Frente","Costas","Lateral","Manga esquerda","Manga direita","Gola","Punhos","Detalhe","Exemplo UV"],0,False)
        if not ok:return
        for path in paths:read_image(path)
        self.change(lambda:self.project.references.extend({"path":str(Path(p).resolve()),"role":role} for p in paths))
        self.ref_list.setCurrentRow(len(self.project.references)-1)

    @safe
    def show_reference(self,index):
        if 0 <= index < len(self.project.references):
            image = read_image(self.project.references[index]["path"])
            image.thumbnail((300,230))
            self.ref_preview.setPixmap(pixmap(image))

    @safe
    def delete_reference(self):
        index = self.ref_list.currentRow()
        if index >= 0:self.change(lambda:self.project.references.pop(index))

    @safe
    def view_reference(self,*args):
        index = self.ref_list.currentRow()
        if index < 0:return
        image = read_image(self.project.references[index]["path"])
        image.thumbnail((1400,1400))
        dialog = QDialog(self)
        dialog.setWindowTitle("Referência original · sem correspondência UV automática")
        dialog.resize(850,850)
        layout = QVBoxLayout(dialog)
        canvas = Canvas()
        canvas.display(image,None,[],"",None,0,False)
        layout.addWidget(canvas)
        layout.addWidget(button("Fechar",dialog.accept))
        QTimer.singleShot(0,canvas.fit)
        dialog.exec()

    @safe
    def reference_as_layer(self):
        index = self.ref_list.currentRow()
        if index < 0:return
        reference = self.project.references[index]
        layer = Layer(Path(reference["path"]).stem + " · alinhar ao UV",kind="image",source=reference["path"],region=self.region_id)
        self.selected_id = layer.id
        self.change(lambda:self.project.layers.append(layer))
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage("Referência inserida intacta. Ajuste escala, posição e orientação; ela não é reprojetada automaticamente.")

    @safe
    def analyze(self):
        index = self.ref_list.currentRow()
        if index < 0:return
        self.statusBar().showMessage("Analisando imagem localmente…")
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = OpenCVAnalyzer().analyze(self.project.references[index]["path"])
        finally:
            QApplication.restoreOverrideCursor()
        dialog = QDialog(self)
        dialog.setWindowTitle("Análise experimental · confirmar antes de aplicar")
        dialog.resize(680,720)
        layout = QVBoxLayout(dialog)
        warning = label(result.warning + "\nFaixas da foto não têm correspondência UV automática.","notice")
        layout.addWidget(warning)
        from PIL import ImageDraw
        photo = read_image(self.project.references[index]["path"]).convert("RGBA")
        photo.thumbnail((500,360))
        draw = ImageDraw.Draw(photo)
        for p1,p2 in result.lines:
            draw.line((p1[0]*photo.width,p1[1]*photo.height,p2[0]*photo.width,p2[1]*photo.height),fill="#ffcb52",width=2)
        previews = row(QLabel(),QLabel())
        previews.layout().itemAt(0).widget().setPixmap(pixmap(photo))
        mask = result.mask.copy()
        mask.thumbnail((160,220))
        previews.layout().itemAt(1).widget().setPixmap(pixmap(mask.convert("RGBA")))
        layout.addWidget(previews)
        colors = QHBoxLayout()
        for color in result.palette:
            b = button(color,lambda checked=False,c=color:self.accept_palette(c))
            b.setStyleSheet(f"border-top: 10px solid {color}")
            colors.addWidget(b)
        layout.addLayout(colors)
        layout.addWidget(QLabel("Paleta: clique para criar uma camada de cor editável."))
        lines = QListWidget()
        for i,(a,b) in enumerate(result.lines):
            angle = math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
            lines.addItem(f"{i+1:02d} · linha de contraste · {angle:.1f}° · revisar posição e espessura")
        layout.addWidget(lines,1)
        @safe
        def accept_line(window):
            idx = lines.currentRow()
            if idx < 0:return
            if not window.current_region():
                raise ValueError("Selecione uma região calibrada antes de aceitar uma faixa.")
            a,b = result.lines[idx]
            angle = math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
            layer = Layer("Sugestão de faixa · revisar",kind="fill",width=.2,height=.012,rotation=angle,color=result.palette[0],region=window.region_id)
            window.selected_id = layer.id
            window.change(lambda:window.project.layers.append(layer))
            window.fit_region()
            window.change(lambda:(setattr(layer,"height",.012),setattr(layer,"rotation",angle)))
            window.statusBar().showMessage("Faixa aproximada adicionada; ajuste com base na referência.")
        layout.addWidget(button("Aceitar linha selecionada como faixa editável",lambda:accept_line(self)))
        layout.addWidget(button("Fechar / rejeitar restantes",dialog.accept))
        dialog.exec()
        self.statusBar().showMessage("Análise concluída · sugestões exigem revisão manual.")

    @safe
    def accept_palette(self,color):
        layer = Layer("Cor sugerida · revisar",color=color,region=self.region_id)
        self.selected_id = layer.id
        self.change(lambda:self.project.layers.append(layer))

    @safe
    def set_export_width(self,width):
        if not self.refreshing:self.change(lambda:setattr(self.project,"export_width",width))

    @safe
    def original_resolution(self):
        self.change(lambda:setattr(self.project,"export_width",read_image(self.project.template).width))

    @safe
    def export_dialog(self,*args):
        if not self.project.mask:
            raise ValueError("Defina uma máscara verificada antes de exportar.")
        original = read_image(self.project.template).size
        size = (self.project.export_width,round(self.project.export_width*original[1]/original[0]))
        if size[0]*size[1] > 16_777_216:
            raise ValueError("Escolha uma resolução de até 16 megapixels (4096 × 4096 para UV quadrado).")
        preview = render(self.project,(min(900,size[0]),round(min(900,size[0])*original[1]/original[0])))
        dialog = QDialog(self)
        dialog.setWindowTitle("Prévia de exportação · sem malha UV")
        dialog.resize(800,850)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label(f"PNG RGBA  /  {size[0]} × {size[1]} px"))
        canvas = Canvas()
        canvas.display(preview,None,[],"",None,0,False)
        layout.addWidget(canvas,1)
        QTimer.singleShot(0,canvas.fit)
        layout.addWidget(label("Sem guias, landmarks ou seleções. Compatibilidade no FC 27 depende de validação com textura funcional.","notice"))
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        controls.button(QDialogButtonBox.StandardButton.Save).setText("Exportar PNG…")
        controls.accepted.connect(dialog.accept)
        controls.rejected.connect(dialog.reject)
        layout.addWidget(controls)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            path,_ = QFileDialog.getSaveFileName(self,"Exportar textura",str(ROOT / "output" / "uniforme.png"),"PNG (*.png)")
            if path:
                path = str(Path(path).with_suffix(".png"))
                source_paths = [self.project.template,self.project.mask,*[l.source for l in self.project.layers if l.source],*[r["path"] for r in self.project.references]]
                if Path(path).resolve() in [Path(p).resolve() for p in source_paths if p]:
                    raise ValueError("Escolha outro destino para preservar os arquivos originais.")
                export_png(self.project,path)
                self.statusBar().showMessage(f"PNG exportado: {path}")

    @safe
    def undo(self,*args):
        if self.undo_stack:
            self.redo_stack.append(self.project.to_dict())
            self.project = Project.from_dict(self.undo_stack.pop())
            self.refresh()

    @safe
    def redo(self,*args):
        if self.redo_stack:
            self.undo_stack.append(self.project.to_dict())
            self.project = Project.from_dict(self.redo_stack.pop())
            self.refresh()

    def confirm_unsaved(self):
        if not self.dirty():return True
        answer = QMessageBox.question(self,"Alterações não salvas","Salvar o projeto antes de continuar?",QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:return bool(self.save())
        return answer == QMessageBox.StandardButton.Discard

    def install_project(self,project,path=None):
        self.project,self.path = project,path
        self.saved_state = project.to_dict()
        self.undo_stack,self.redo_stack = [],[]
        self.region_id = ""
        self.selected_id = project.layers[-1].id if project.layers else ""
        self.canvas.initial_fit = True
        self.canvas.set_mode("select")
        self.refresh()

    @safe
    def new(self,*args):
        if self.confirm_unsaved():self.install_project(new_project())

    @safe
    def demo(self,*args):
        if self.confirm_unsaved():
            self.install_project(cruzeiro_demo())
            self.saved_state = {}
            self.refresh()

    @safe
    def open(self,*args):
        if not self.confirm_unsaved():return
        path,_ = QFileDialog.getOpenFileName(self,"Abrir projeto","","Projeto JSON (*.json)")
        if not path:return
        project = load_project(path)
        missing = missing_assets(project)
        for asset in missing:
            replacement,_ = QFileDialog.getOpenFileName(self,f"Localizar arquivo ausente: {Path(asset).name}","","Arquivos (*)")
            if not replacement:return
            if project.template == asset:project.template = replacement
            if project.mask == asset:project.mask = replacement
            for l in project.layers:
                if l.source == asset:l.source = replacement
                if l.mask_source == asset:l.mask_source = replacement
            for c in project.photo_calibrations:
                for key in ('source','mesh'):
                    if c[key]==asset:c[key]=replacement
            for ref in project.references:
                if ref["path"] == asset:ref["path"] = replacement
        render(project,(256,round(256*read_image(project.template).height/read_image(project.template).width)))
        self.install_project(project,path)

    @safe
    def save(self,*args):
        if not self.path:return self.save_as()
        save_project(self.project,self.path)
        self.saved_state = self.project.to_dict()
        self.refresh()
        self.statusBar().showMessage(f"Projeto salvo: {self.path}")
        return True

    @safe
    def save_as(self,*args):
        path,_ = QFileDialog.getSaveFileName(self,"Salvar projeto",str(ROOT / "output" / "projeto.json"),"Projeto JSON (*.json)")
        if not path:return False
        path = str(Path(path).with_suffix(".json"))
        save_project(self.project,path)
        self.path = path
        self.saved_state = self.project.to_dict()
        self.refresh()
        return True

    def autosave(self):
        if self.dirty():
            try:
                save_project(self.project,ROOT / "output" / "autosave.recovery.json")
            except Exception:
                logging.exception("Falha na recuperação automática")
                self.statusBar().showMessage("Falha ao gravar recuperação automática; salve o projeto manualmente.")

    @safe
    def recover(self):
        path = ROOT / "output" / "autosave.recovery.json"
        if path.exists() and QMessageBox.question(self,"Recuperação","Há uma cópia de recuperação da sessão anterior. Abrir?") == QMessageBox.StandardButton.Yes:
            project = load_project(path)
            if missing_assets(project):
                raise ValueError("A recuperação contém arquivos ausentes. Abra output/autosave.recovery.json pelo menu Abrir para relocalizá-los.")
            self.install_project(project)
            self.saved_state = {}
            self.refresh()

    def closeEvent(self,event):
        if self.confirm_unsaved():
            self.preview3d.shutdown()
            (ROOT / "output" / "autosave.recovery.json").unlink(missing_ok=True)
            event.accept()
        else:event.ignore()
