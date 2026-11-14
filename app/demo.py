from pathlib import Path
from core.layers.model import Layer, Project


ROOT = Path(__file__).resolve().parents[1]


def new_project(sleeve="short_sleeve"):
    project = Project(template=str(ROOT / f"assets/uv_templates/{sleeve}.png"),
                   mask=str(ROOT / f"assets/uv_templates/{sleeve}_mask.png"),
                   layers=[Layer("01 · Cor base", color="#f7f7f4")])
    for filename in ("example_black.png", "example_blue.png", "example_red.png"):
        path = ROOT / "assets/references" / filename
        if path.exists():
            project.references.append({"path":str(path),"role":"Exemplo UV"})
    return project


def cruzeiro_demo():
    project = new_project()
    project.name = "Cruzeiro · estudo manual"
    project.notes = ("Referência frontal do Cruzeiro disponível em assets/references/cruzeiro_reference.png. "
                     "Camadas de detalhes começam ocultas: calibre as regiões, selecione cada camada, "
                     "associe a região, use Enquadrar e ative a visibilidade. Gola polo exige validar o modelo 3D. "
                     "Reservas são landmarks do editor, nunca letras/logos exportados.")
    for name in ("Ombro esquerdo · calibrar", "Ombro direito · calibrar"):
        project.layers.append(Layer(name, color="#0647ab", width=.12,height=.04,visible=False))
    for side in ("esquerdo", "direito"):
        for index in range(3):
            project.layers.append(Layer(f"Listra {index+1} · ombro {side}",color="#0647ab",width=.08,height=.008,visible=False))
    for side in ("esquerda", "direita"):
        for color, label in (("#0647ab","azul"),("#f7ce36","amarela")):
            project.layers.append(Layer(f"Faixa {label} · manga {side}",color=color,width=.12,height=.015,visible=False))
    project.layers.append(Layer("Gola branca · calibrar polo",color="#ffffff",width=.08,height=.04,visible=False))
    for filename in ("cruzeiro_reference.png",):
        path = ROOT / "assets/references" / filename
        if path.exists():
            project.references.append({"path":str(path),"role":"Frente"})
    return project
