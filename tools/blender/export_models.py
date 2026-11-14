"""Export explicitly selected objects without saving or editing the source BLEND."""
import argparse
import bpy
import hashlib
import json
import sys
from pathlib import Path


def export_objects(names, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
    manifest = dict(source_sha256=source_hash, models=[], limitations=[
        'Preview exports evaluated geometry in the current pose; animation and armatures are not exported.',
        'Procedural Blender material nodes are replaced by a neutral Principled material for editor textures.'])
    for name in names:
        original = bpy.data.objects.get(name)
        if original is None or original.type != 'MESH':
            raise ValueError('Expected an existing mesh: ' + name)
        scene = bpy.data.scenes.new('FC27 export temporary')
        mesh = bpy.data.meshes.new_from_object(original.evaluated_get(bpy.context.evaluated_depsgraph_get()), preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get())
        obj = bpy.data.objects.new(name,mesh)
        scene.collection.objects.link(obj)
        obj.matrix_world = original.matrix_world.copy()
        mesh.materials.clear()
        for slot in original.material_slots:
            mat = bpy.data.materials.new((slot.material.name if slot.material else 'Material') + ' Preview')
            mat.use_nodes = True
            mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .8
            mesh.materials.append(mat)
        stem = name.replace(' ','_')
        previous_scene = bpy.context.window.scene
        try:
            bpy.context.window.scene = scene
            obj.select_set(True)
            scene.view_layers[0].objects.active = obj
            bpy.context.view_layer.update()
            bpy.ops.export_scene.gltf(filepath=str(directory/(stem+'.glb')),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_yup=True)
            mesh.calc_loop_triangles()
            uv = mesh.uv_layers.active
            geometry = dict(name=name,source_sha256=source_hash,uv_name=uv.name if uv else None,
                matrix_world=[list(r) for r in obj.matrix_world],
                vertices=[list(v.co) for v in mesh.vertices],
                triangles=[dict(vertices=list(t.vertices),uv=[list(uv.data[i].uv) for i in t.loops] if uv else [],material=t.material_index,face=t.polygon_index) for t in mesh.loop_triangles],
                materials=[s.material.name if s.material else None for s in original.material_slots])
            (directory/(stem+'.json')).write_text(json.dumps(geometry),encoding='utf-8')
            manifest['models'].append(dict(object=name,glb=stem+'.glb',geometry=stem+'.json',triangles=len(mesh.loop_triangles)))
        finally:
            bpy.context.window.scene = previous_scene
            bpy.data.objects.remove(obj,do_unlink=True)
            bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(scene)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--objects',nargs='+',required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    export_objects(args.objects,args.output)
