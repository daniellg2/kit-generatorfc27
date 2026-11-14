import * as THREE from './vendor/three.module.js';
import {OrbitControls} from './vendor/OrbitControls.js';
import {GLTFLoader} from './vendor/GLTFLoader.js';

const scene=new THREE.Scene(); scene.background=new THREE.Color('#30343b');
const camera=new THREE.PerspectiveCamera(35,1,.001,1000);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.NoToneMapping;
document.body.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=false;
scene.add(new THREE.AmbientLight(0xffffff,1.6));
const light=new THREE.DirectionalLight(0xffffff,2.2);light.position.set(3,4,5);scene.add(light);
const fill=new THREE.DirectionalLight(0xffffff,1.2);fill.position.set(-3,2,-4);scene.add(fill);
const loader=new GLTFLoader(), cache=new Map(), textures={shirt:null,shorts:null}, revisions={shirt:0,shorts:0};
let selected='short_sleeve', shortsVisible=false, diagnostic=false, flat=false, initialized=false;
const paths={short_sleeve:'Collar_0.glb',long_sleeve:'Collar_0_LS.glb',shorts:'Shorts_0.glb'};
const stats={loads:0,updates:0,ready:false,error:null};
function draw(){renderer.render(scene,camera);}
controls.addEventListener('change',draw);
function resize(){renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/Math.max(1,innerHeight);camera.updateProjectionMatrix();draw();}
addEventListener('resize',resize);
function checker(){
 const c=document.createElement('canvas');c.width=c.height=1024;const ctx=c.getContext('2d');
 const colors=['#e84f4f','#44b56a','#487ee8','#e9bd36'];
 for(let y=0;y<4;y++)for(let x=0;x<4;x++){
 ctx.fillStyle=colors[(y>=2?2:0)+(x>=2?1:0)];ctx.fillRect(x*256,y*256,256,256);
 ctx.strokeStyle='#101010';ctx.lineWidth=4;ctx.strokeRect(x*256,y*256,256,256);
 ctx.fillStyle='white';ctx.font='bold 48px sans-serif';ctx.fillText(`${y*4+x+1}`,x*256+20,y*256+65);
 ctx.font='28px sans-serif';ctx.fillText('U →',x*256+65,y*256+125);ctx.fillText('TOP ↑',x*256+65,y*256+180);
 }
 const t=new THREE.CanvasTexture(c);t.flipY=false;t.colorSpace=THREE.SRGBColorSpace;return t;
}
const testTexture=checker();
function materialFor(mesh,piece){
 const old=mesh.material;
 const parameters={map:diagnostic?testTexture:textures[piece],color:0xffffff,side:THREE.DoubleSide,transparent:true,depthWrite:true,alphaTest:.001};
 mesh.material=flat?new THREE.MeshBasicMaterial(parameters):new THREE.MeshStandardMaterial({...parameters,roughness:.85,metalness:0});
 if(Array.isArray(old))old.forEach(m=>m.dispose());else old?.dispose();
}
function applyMaterials(){for(const [key,root] of cache)root.traverse(m=>{if(m.isMesh)materialFor(m,key==='shorts'?'shorts':'shirt');});draw();}
async function load(key){
 if(cache.has(key))return cache.get(key);
 const gltf=await loader.loadAsync('/models/'+paths[key]);
 const root=gltf.scene;
 root.traverse(m=>{if(m.isMesh){if(!m.geometry.attributes.uv)throw Error('Modelo sem UV: '+key);materialFor(m,key==='shorts'?'shorts':'shirt');}});
 root.visible=false;scene.add(root);cache.set(key,root);stats.loads++;return root;
}
function bounds(){const box=new THREE.Box3();for(const root of cache.values())if(root.visible)box.expandByObject(root);return box;}
function view(which='front'){
 const box=bounds();if(box.isEmpty())return;
 const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());
 const distance=Math.max(size.y,size.x/Math.max(camera.aspect,.3),size.z)*1.8;
 const direction={front:[0,0,1],back:[0,0,-1],left:[-1,0,0],right:[1,0,0]}[which]||[0,0,1];
 controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(...direction).multiplyScalar(distance));
 camera.near=Math.max(.001,distance/1000);camera.far=distance*100;camera.updateProjectionMatrix();controls.update();draw();
}
async function select(key,showShorts=false){
 if(!(key in paths)||key==='shorts')throw Error('Modelo inválido');
 selected=key;shortsVisible=showShorts;
 await load(key);if(showShorts)await load('shorts');
 for(const [name,root] of cache)root.visible=name===selected||(name==='shorts'&&shortsVisible);
 if(!initialized){initialized=true;view();}else draw();
}
async function texture(piece,url){
 if(!(piece in textures))throw Error('Peça inválida');
 const revision=++revisions[piece];
 const t=await new THREE.TextureLoader().loadAsync(url);
 if(revision!==revisions[piece]){t.dispose();return;}
 t.flipY=false;t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());
 const old=textures[piece];textures[piece]=t;
 for(const [key,root] of cache)if((key==='shorts'?'shorts':'shirt')===piece)root.traverse(m=>{if(m.isMesh){m.material.map=diagnostic?testTexture:t;m.material.needsUpdate=true;}});
 old?.dispose();stats.updates++;draw();
}
window.preview={select,texture,view,diagnostic(value){diagnostic=value;applyMaterials();},flat(value){flat=value;applyMaterials();},
 state(){return {...stats,selected,shortsVisible,camera:camera.position.toArray(),target:controls.target.toArray(),models:[...cache.keys()],textureSizes:Object.fromEntries(Object.entries(textures).map(([k,t])=>[k,t?[t.image.width,t.image.height]:null])),flipY:textures.shirt?.flipY};}};
function failure(e){stats.error=String(e);document.querySelector('#error').textContent='Falha na prévia 3D: '+e;}
addEventListener('unhandledrejection',e=>failure(e.reason));addEventListener('error',e=>failure(e.message));
resize();stats.ready=true;
