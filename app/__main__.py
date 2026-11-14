import logging
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from app.demo import ROOT
from app.theme import apply_theme


def main():
    (ROOT / "output").mkdir(exist_ok=True)
    logging.basicConfig(filename=ROOT / "output" / "app.log",level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s",encoding="utf-8")
    app = QApplication(sys.argv)
    app.setApplicationName("FC27 Kit Generator")
    app.setOrganizationName("FC27KitGenerator")
    apply_theme(app)
    def error_hook(kind,error,trace):
        logging.error("Erro não tratado",exc_info=(kind,error,trace))
        QMessageBox.warning(None,"Erro recuperável",f"{error}\nConsulte output/app.log. O projeto atual pode ser salvo.")
    sys.excepthook = error_hook
    try:
        from app.window import MainWindow
        window = MainWindow()
    except Exception:
        logging.exception("Falha ao iniciar")
        QMessageBox.critical(None,"Não foi possível iniciar","Verifique os UVs e máscaras em assets/uv_templates. Consulte output/app.log.")
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
