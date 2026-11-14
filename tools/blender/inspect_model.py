"""Run with blender --background --disable-autoexec FILE --python SCRIPT -- REPORT."""
import bpy
import hashlib
import json
import sys
from pathlib import Path


def inspect():
    objects = []
    for obj in bpy.data.objects:
        entry = dict(name=obj.name, type=obj.type, collections=[c.name for c in obj.users_collection],
                     parent=obj.parent.name if obj.parent else None,
                     matrix_world=[list(row) for row in obj.matrix_world],
                     materials=[s.material.name if s.material else None for s in obj.material_slots],
                     vertex_groups=[g.name for g in obj.vertex_groups],
                     modifiers=[dict(name=m.name,type=m.type) for m in obj.modifiers],
                     hidden=obj.hide_render)
        if obj.type == 'MESH':
            mesh = obj.data
            entry['vertices'] = [list(v.co) for v in mesh.vertices]
            entry['faces'] = [dict(vertices=list(p.vertices),loops=list(p.loop_indices),material=p.material_index) for p in mesh.polygons]
            entry['uv_layers'] = {uv.name:[list(v.uv) for v in uv.data] for uv in mesh.uv_layers}
            entry['active_uv'] = mesh.uv_layers.active.name if mesh.uv_layers.active else None
        objects.append(entry)
    materials = []
    for material in bpy.data.materials:
        nodes = material.node_tree
        materials.append(dict(name=material.name,nodes=[dict(name=n.name,type=n.type,image=n.image.name if n.type=='TEX_IMAGE' and n.image else None) for n in nodes.nodes] if nodes else [],links=[dict(source=l.from_node.name,target=l.to_node.name,socket=l.to_socket.name) for l in nodes.links] if nodes else []))
    source = Path(bpy.data.filepath)
    return dict(source=source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),blender=bpy.app.version_string,
                objects=objects,materials=materials,
                images=[dict(name=i.name,path=i.filepath,size=list(i.size),packed=bool(i.packed_file)) for i in bpy.data.images])


if __name__ == '__main__':
    target = Path(sys.argv[sys.argv.index('--')+1])
    target.parent.mkdir(parents=True,exist_ok=True)
    report = inspect()
    target.write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
    print(json.dumps([dict(name=o['name'],type=o['type'],vertices=len(o.get('vertices',[])),materials=o['materials'],uv=list(o.get('uv_layers',{}))) for o in report['objects']],ensure_ascii=False))
