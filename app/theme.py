def apply_theme(app):
    from pathlib import Path
    from PySide6.QtGui import QFontDatabase
    # Offscreen Windows sessions may not enumerate system fonts.
    if not QFontDatabase.families():
        for name in ("segoeui.ttf", "segoeuib.ttf"):
            path = Path("C:/Windows/Fonts") / name
            if path.exists():
                QFontDatabase.addApplicationFont(str(path))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)


STYLE = """
* { font-family: 'Segoe UI'; font-size: 12px; }
QMainWindow, QDialog { background: #12161d; color: #e8edf7; }
QWidget { color: #e8edf7; }
QWidget#panel { background: #1a202a; border-radius: 10px; }
QWidget#properties { background: #1a202a; }
QLabel#brand { font-size: 23px; font-weight: 700; letter-spacing: -0.5px; }
QLabel#subtitle { color: #91a2b9; font-size: 11px; }
QLabel#section { color: #84b9ff; font-size: 11px; font-weight: 700; }
QLabel#notice { color: #d8bb7b; background: #302a20; padding: 9px; border-radius: 5px; }
QPushButton, QToolButton { background: #283241; border: 1px solid #38465a; border-radius: 5px; padding: 7px 10px; }
QPushButton:hover, QToolButton:hover { background: #36465c; border-color: #76acff; }
QPushButton:pressed, QToolButton:pressed { background: #1e314b; }
QPushButton#primary { background: #2865d5; border-color: #4288ff; font-weight: 600; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 1px solid #88bcff; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { background: #111721; color: #f0f4ff; border: 1px solid #364355; border-radius: 4px; padding: 5px; min-height: 20px; }
QComboBox QAbstractItemView { background: #202b3b; selection-background-color: #285a9f; }
QListWidget { background: #131a24; border: 1px solid #303b4c; border-radius: 5px; outline: none; }
QListWidget::item { padding: 9px 6px; border-bottom: 1px solid #202a37; }
QListWidget::item:selected { background: #253e61; color: #ffffff; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #1a202a; color: #93a7c3; padding: 10px 9px; border-bottom: 2px solid #273243; }
QTabBar::tab:selected { color: #d8e9ff; border-bottom: 2px solid #5d9cff; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #141b25; width: 9px; }
QScrollBar::handle:vertical { background: #43516a; min-height: 25px; border-radius: 4px; }
QScrollBar:horizontal { background: #141b25; height: 9px; }
QScrollBar::handle:horizontal { background: #43516a; min-width: 25px; border-radius: 4px; }
QToolBar { background: #1a202a; spacing: 5px; padding: 6px; border: none; }
QStatusBar { color: #9eafc5; background: #161d27; }
QMenuBar, QMenu { background: #1b2532; color: #e8edf7; }
QMenu::item:selected { background: #2a5186; }
QSplitter::handle { background: #12161d; width: 8px; }
QCheckBox { spacing: 8px; padding: 3px 0; }
QSlider::groove:horizontal { background: #38465a; height: 4px; }
QSlider::handle:horizontal { background: #77aeff; width: 12px; margin: -5px 0; border-radius: 6px; }
QToolTip { background: #24334a; color: #fff; border: 1px solid #5e85bc; }
"""
