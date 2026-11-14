"""Atomic JSON storage; paths in memory are absolute, on disk relative when possible."""
import json
import os
from pathlib import Path
from core.layers.model import Project


def atomic_write(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        writer(temp)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def asset_fields(data):
    yield data, "template"
    yield data, "mask"
    for layer in data["layers"]:
        yield layer, "source"
    for ref in data["references"]:
        yield ref, "path"


def save_project(project, path):
    project.validate()
    data = project.to_dict()
    base = Path(path).resolve().parent
    for obj, key in asset_fields(data):
        if obj.get(key):
            try:
                obj[key] = Path(os.path.relpath(Path(obj[key]).resolve(), base)).as_posix()
            except ValueError:  # Different Windows drives.
                obj[key] = str(Path(obj[key]).resolve())
    atomic_write(path, lambda p: p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"))


def load_project(path):
    path = Path(path).resolve()
    if path.stat().st_size > 10_000_000:
        raise ValueError("JSON excede 10 MB.")
    data = json.loads(path.read_text(encoding="utf-8"))
    project = Project.from_dict(data)
    data = project.to_dict()
    for obj, key in asset_fields(data):
        if obj.get(key):
            obj[key] = str((path.parent / obj[key]).resolve())
    return Project.from_dict(data)


def missing_assets(project):
    return sorted({obj[key] for obj, key in asset_fields(project.to_dict()) if obj.get(key) and not Path(obj[key]).is_file()})
