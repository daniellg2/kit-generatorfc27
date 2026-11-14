import json
import os
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from core.projection.photo_to_uv import MeshSurface,homography,transform
from core.generation.kit_generator import generate
from core.layers.model import Project
from core.projects.storage import save_project,load_project
from core.rendering.compositor import render,export_png


class ProjectionTests(unittest.TestCase):
    def test_known_projection_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            mesh=root/'mesh.json'
            mesh.write_text(json.dumps(dict(vertices=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],triangles=[dict(vertices=[0,1,2],uv=[[0,1],[1,1],[1,0]]),dict(vertices=[0,2,3],uv=[[0,1],[1,0],[0,0]])])))
            surface=MeshSurface(mesh)
            points=[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]
            targets=(np.asarray(points)*.75+.1).tolist()
            anchors=[surface.anchor(p) for p in targets]
            for p,a in zip(targets,anchors):np.testing.assert_allclose(surface.uv(a),p,atol=1e-8)
            matrix=homography(points,anchors,surface)
            stripe=[[.2,.4],[.8,.4],[.8,.5],[.2,.5]]
            error=np.linalg.norm(np.asarray(transform(stripe,matrix))-(np.asarray(stripe)*.75+.1),axis=1).max()*2048
            self.assertLess(error,.001)
            photo=root/'photo.png';image=Image.new('RGB',(400,400),'white')
            ImageDraw.Draw(image).rectangle((80,160,320,200),fill='#034dc8');image.save(photo)
            guide=root/'guide.png';Image.new('RGB',(400,400),'red').save(guide)
            mask=root/'mask.png';Image.new('L',(400,400),255).save(mask)
            project=Project(template=str(guide),mask=str(mask),export_width=400)
            result,colors=generate(project,surface,photo,'Manga',points,anchors,stripe,root/'generated')
            self.assertEqual(project.layers,[])
            self.assertEqual(len(result.layers),2)
            self.assertEqual(result.layers[-1].kind,'polygon')
            self.assertEqual(result.layers[-1].color,'#034dc8')
            output=render(result)
            self.assertEqual(output.getpixel((200,180)),(3,77,200,255))
            self.assertEqual(output.getpixel((0,0))[3],0)
            save_project(result,root/'project.json')
            restored=load_project(root/'project.json')
            self.assertEqual(restored.to_dict(),result.to_dict())
            export_png(restored,root/'out.png')
            with Image.open(root/'out.png') as out:self.assertEqual(out.tobytes(),output.tobytes())
            with self.assertRaises(ValueError):homography([[0,0]]*4,anchors,surface)

    def test_real_mesh_anchors_preserve_surface(self):
        surface=MeshSurface('assets/models/Collar_0.json')
        before=surface.triangles.copy()
        t=surface.triangles[100]
        point=t.mean(axis=0)
        anchor=surface.anchor(point)
        np.testing.assert_allclose(surface.uv(anchor),point,atol=1e-7)
        self.assertEqual(surface.position(anchor).shape,(3,))
        np.testing.assert_array_equal(surface.triangles,before)
        with self.assertRaises(ValueError):surface.anchor([0,0])
