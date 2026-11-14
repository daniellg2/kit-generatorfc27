import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from PIL import Image
from core.layers.model import Layer, Project, Region
from core.projects.storage import load_project, missing_assets, save_project
from core.rendering.compositor import export_png, layer_art, render
from core.uv.templates import derive_mask, polygon_mask
from core.detection.analyzer import OpenCVAnalyzer


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.guide = self.root / "uv.png"
        self.mask = self.root / "mask.png"
        Image.new("RGB", (200,100), "red").save(self.guide)
        m = Image.new("L", (200,100))
        m.paste(255,(10,10,190,90))
        m.save(self.mask)
        self.project = Project(template=str(self.guide),mask=str(self.mask),export_width=200)

    def test_rgba_dimensions_clip_and_no_uv(self):
        self.project.layers = [Layer("base",color="#ffffff")]
        out = self.root / "out.png"
        self.assertEqual(export_png(self.project,out),(200,100))
        with Image.open(out) as im:
            self.assertEqual(im.mode,"RGBA")
            self.assertEqual(im.getpixel((0,0)),(255,255,255,0))
            self.assertEqual(im.getpixel((100,50)),(255,255,255,255))
        self.project.layers = []
        self.assertIsNone(render(self.project).getbbox())

    def test_position_composition_visibility_and_opacity(self):
        self.project.layers = [Layer("base",color="#0000ff"), Layer("small",color="#ff0000",x=.25,y=.5,width=.2,height=.2,opacity=.5)]
        im = render(self.project)
        self.assertEqual(im.getpixel((50,50)),(128,0,127,255))
        self.assertEqual(im.getpixel((150,50)),(0,0,255,255))
        self.project.layers[-1].visible = False
        self.assertEqual(render(self.project).getpixel((50,50)),(0,0,255,255))

    def test_region_normalized_at_multiple_sizes(self):
        region = Region("front",[[.1,.1],[.5,.1],[.5,.9],[.1,.9]])
        self.project.regions = [region]
        self.project.layers = [Layer("base",color="#00ff00",region=region.id)]
        for size in ((200,100),(400,200)):
            im = render(self.project,size)
            self.assertEqual(im.getpixel((round(.3*size[0]),size[1]//2)),(0,255,0,255))
            self.assertEqual(im.getpixel((round(.75*size[0]),size[1]//2))[3],0)

    def test_image_aspect_flip_rotation_recolor(self):
        art = self.root / "art.png"
        im = Image.new("RGBA",(40,20),"red")
        im.paste("blue",(20,0,40,20))
        im.save(art)
        layer = Layer("logo",kind="image",source=str(art),width=.4,height=.8)
        image = layer_art(layer,(200,100))
        self.assertEqual(image.getchannel("A").getbbox(),(0,20,80,60))
        self.assertEqual(image.getpixel((10,30)),(255,0,0,255))
        layer.flip_x = True
        self.assertEqual(layer_art(layer,(200,100)).getpixel((10,30)),(0,0,255,255))
        layer.rotation = 90
        rotated = layer_art(layer,(200,100))
        self.assertEqual(rotated.getchannel("A").getbbox(),(20,0,60,80))
        layer.recolor,layer.color = True,"#00ff00"
        self.assertEqual(layer_art(layer,(200,100)).getpixel((30,30)),(0,255,0,255))

    def test_project_relative_paths_and_roundtrip(self):
        region = Region("Gola",[[.1,.1],[.2,.1],[.2,.2]],landmarks={"logo":[.15,.15]},reference_role="Gola")
        self.project.regions = [region]
        self.project.layers = [Layer("base",region=region.id)]
        self.project.references = [{"path":str(self.guide),"role":"Frente"}]
        path = self.root / "nested" / "project.json"
        save_project(self.project,path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["template"],"../uv.png")
        self.assertEqual(load_project(path).to_dict(),self.project.to_dict())
        self.assertEqual(missing_assets(load_project(path)),[])

    def test_invalid_save_preserves_previous_file(self):
        path = self.root / "project.json"
        save_project(self.project,path)
        before = path.read_bytes()
        self.project.layers = [Layer("bad",opacity=float("nan"))]
        with self.assertRaises(ValueError):save_project(self.project,path)
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_validation_and_missing_files(self):
        self.project.layers = [Layer("bad",region="unknown")]
        with self.assertRaises(ValueError):self.project.validate()
        self.project.layers = []
        self.project.regions = [Region("bad",[[0,0],[1,0],[2,1]])]
        with self.assertRaises(ValueError):self.project.validate()
        self.project.regions = []
        self.project.mask = str(self.root/"missing.png")
        self.assertEqual(len(missing_assets(self.project)),1)
        with self.assertRaises(FileNotFoundError):render(self.project)

    def test_pattern_mask_offset(self):
        path = self.root / "tile.png"
        tile = Image.new("RGBA",(2,2),"red")
        tile.putpixel((0,0),(0,0,255,255))
        tile.save(path)
        self.project.layers = [Layer("pattern",kind="pattern",source=str(path),tile_scale=.02)]
        first = render(self.project)
        self.project.layers[0].offset_x = .01
        second = render(self.project)
        self.assertNotEqual(first.getpixel((20,20)),second.getpixel((20,20)))
        self.assertEqual(second.getpixel((0,0))[3],0)

    def test_shapes_curve_stripes(self):
        for kind,points in (("polygon",[[0,0],[1,0],[.5,1]]),("curve",[[0,0],[.5,1],[1,0]]),("stripes",[])):
            self.project.layers = [Layer(kind,kind=kind,points=points,color="#ff0000",width=.5,height=.5)]
            self.assertIsNotNone(render(self.project).getbbox())

    def test_mask_size_and_export_aspect(self):
        with self.assertRaises(ValueError):render(self.project,(100,100))
        Image.new("L",(20,20),255).save(self.mask)
        with self.assertRaises(ValueError):render(self.project)

    def test_export_cannot_overwrite_original(self):
        before = self.guide.read_bytes()
        self.project.layers = [Layer("base")]
        with self.assertRaises(ValueError):export_png(self.project,self.guide)
        self.assertEqual(self.guide.read_bytes(),before)

    def test_supplied_uv_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        for sleeve in ("short_sleeve","long_sleeve"):
            self.project.template = str(root/f"assets/uv_templates/{sleeve}.png")
            self.project.mask = str(root/f"assets/uv_templates/{sleeve}_mask.png")
            self.project.layers = [Layer("base")]
            im = render(self.project,(512,512))
            self.assertEqual(im.getpixel((0,0))[3],0)
            self.assertEqual(im.getpixel((256,100)),(255,255,255,255))
            self.assertEqual(im.getpixel((238,260))[3],0)  # Opening beside the separate collar island.
            mask = Image.open(self.project.mask).resize((512,512),Image.Resampling.NEAREST)
            np.testing.assert_array_equal(np.asarray(im.getchannel("A")),np.asarray(mask))

    def test_detection_has_no_uv_side_effect(self):
        path = self.root/"reference.png"
        im = Image.new("RGB",(200,200),"#eeeeee")
        im.paste("#1645af",(50,20,150,180))
        im.paste("#ffcc00",(60,70,140,85))
        im.save(path)
        before = copy.deepcopy(self.project.to_dict())
        result = OpenCVAnalyzer().analyze(str(path))
        self.assertTrue(result.palette)
        self.assertEqual(result.mask.size,(200,200))
        self.assertIn("Experimental",result.warning)
        self.assertEqual(self.project.to_dict(),before)


if __name__ == "__main__":
    unittest.main()
