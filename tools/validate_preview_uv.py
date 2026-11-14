"""Compare exported GLB corner UVs to Blender extraction and existing raster masks."""
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def glb(path):
    raw=Path(path).read_bytes()
    magic,version,length=struct.unpack_from('<III',raw)
    if magic!=0x46546c67 or version!=2 or length!=len(raw):raise ValueError('Invalid GLB')
    n=struct.unpack_from('<I',raw,12)[0]
    data=json.loads(raw[20:20+n]);offset=20+n
    binary=raw[offset+8:]
    def accessor(index):
        a=data['accessors'][index];v=data['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        return np.ndarray((a['count'],width),dtype=dtype,buffer=binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dtype).itemsize*width),np.dtype(dtype).itemsize)).copy()
    return data,accessor


def validate():
    results=[]
    for name,template in [('Collar_0','short_sleeve'),('Collar_0_LS','long_sleeve'),('Shorts_0',None)]:
        path=Path('assets/models')/name
        data,access=glb(path.with_suffix('.glb'))
        assert len(data['meshes'])==1
        primitive=data['meshes'][0]['primitives'][0]
        uv=access(primitive['attributes']['TEXCOORD_0'])
        indices=access(primitive['indices']).ravel()
        corners=uv[indices].reshape(-1,3,2)
        source=json.loads(path.with_suffix('.json').read_text())
        original=np.asarray([t['uv'] for t in source['triangles']])
        original[:,:,1]=1-original[:,:,1]
        # Export may reorder triangle corners; compare quantized per-triangle signatures.
        def signature(triangles):
            return sorted(tuple(sorted(tuple(p) for p in np.rint(t*10000).astype(int))) for t in triangles)
        identical=signature(corners)==signature(original)
        result=dict(model=name,triangles=len(corners),corner_uvs_match_blender=identical,materials=[m['name'] for m in data['materials']])
        assert identical,result
        if template:
            mask=Image.new('L',(2048,2048));draw=ImageDraw.Draw(mask)
            for triangle in corners:draw.polygon([tuple(p*2047) for p in triangle],fill=255)
            expected=np.asarray(Image.open(f'assets/uv_templates/{template}_mask.png'))>0
            actual=np.asarray(mask)>0
            result['mask_iou']=float(np.count_nonzero(actual&expected)/np.count_nonzero(actual|expected))
            result['geometry_outside_raster_pixels']=int(np.count_nonzero(actual&~expected))
            mask.save(f'output/{name}_geometry_mask.png')
        results.append(result)
    Path('output/uv_validation.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
    return results


if __name__=='__main__':validate()
