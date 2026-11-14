import unittest
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
from app.preview3d.widget import AssetServer
from tools.validate_preview_uv import glb


class PreviewAssetsTests(unittest.TestCase):
    def test_models_have_independent_materials_and_uv(self):
        for name,prefix in [('Collar_0','Jersey'),('Collar_0_LS','Jersey'),('Shorts_0','Shorts')]:
            data,access=glb(Path('assets/models')/(name+'.glb'))
            self.assertEqual(len(data['meshes']),1)
            primitive=data['meshes'][0]['primitives'][0]
            uv=access(primitive['attributes']['TEXCOORD_0'])
            self.assertEqual(uv.shape[1],2)
            self.assertTrue(data['materials'][primitive['material']]['name'].startswith(prefix))
            self.assertTrue(((uv>=-.001)&(uv<=1.001)).all())

    def test_offline_assets_and_allowlist(self):
        server=AssetServer()
        try:
            base=server.url.removesuffix('index.html')
            for name in ['index.html','viewer.js','vendor/three.module.js','models/Collar_0.glb']:
                with urlopen(base+name) as response:self.assertGreater(len(response.read()),0)
            with self.assertRaises(HTTPError):urlopen(base+'../../README.md')
        finally:server.close()
