// The glass listening orb: a particle field suspended in a glass sphere (IOR 2.0),
// ported from glass-orb.html for embedding. The glass needs the dark studio
// backdrop to refract, so it renders opaquely and CSS masks the canvas to a circle.
import * as THREE from 'three'
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js'
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js'
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js'
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js'
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js'
import sphereUrl from './glass-sphere.glb?url'

export type OrbMode='idle'|'listen'|'speak'|'think'|'rest'
// Live audio for the orb: an analyser when one exists, otherwise a 0..1 level.
export type OrbInput={mode:OrbMode;analyser:AnalyserNode|null;level:number}
export type Orb={update:(input:OrbInput)=>void;setActive:(active:boolean)=>void;resize:()=>void;dispose:()=>void}

const SPHERE_R=2.7729*0.99
const BLOB_R=1.42
// Canvas height in sphere radii; the CSS mask in app.css fades out beyond the glass.
const FIT=2.5

const NOISE=`
vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;} vec4 mod289(vec4 x){return x-floor(x*(1./289.))*289.;}
vec4 permute(vec4 x){return mod289(((x*34.)+1.)*x);} vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-.85373472095314*r;}
float snoise(vec3 v){const vec2 C=vec2(1./6.,1./3.);const vec4 D=vec4(0.,.5,1.,2.);
vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.-g;vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);
vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+C.yyy;vec3 x3=x0-D.yyy;i=mod289(i);
vec4 p=permute(permute(permute(i.z+vec4(0.,i1.z,i2.z,1.))+i.y+vec4(0.,i1.y,i2.y,1.))+i.x+vec4(0.,i1.x,i2.x,1.));
float n_=.142857142857;vec3 ns=n_*D.wyz-D.xzx;vec4 j=p-49.*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.*x_);
vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.-abs(x)-abs(y);vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);
vec4 s0=floor(b0)*2.+1.;vec4 s1=floor(b1)*2.+1.;vec4 sh=-step(h,vec4(0.));vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
vec4 m=max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);m=m*m;
return 42.*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));}`

// Soft studio environment: feathered softboxes placed like the .blend's lights.
function studioEnvironment(pmrem:THREE.PMREMGenerator){
 const scene=new THREE.Scene()
 scene.add(new THREE.Mesh(new THREE.SphereGeometry(10,64,32),new THREE.ShaderMaterial({
  side:THREE.BackSide,
  vertexShader:`varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader:`varying vec3 vP;
   float box(vec3 d, vec3 c, float r0, float r1){ return smoothstep(cos(r0), cos(r1), dot(d, normalize(c))); }
   float panel(vec3 d, vec3 c, vec2 size, float feather){
    c = normalize(c); float k = dot(d, c); if(k <= 0.0) return 0.0;
    vec3 r = normalize(cross(vec3(0.,1.,0.), c)); vec3 u = cross(c, r);
    vec2 q = vec2(dot(d, r), dot(d, u)) / k;
    vec2 e = smoothstep(size, size - feather, abs(q));
    return e.x * e.y;
   }
   void main(){
    vec3 d = normalize(vP);
    vec3 c = mix(vec3(0.012,0.014,0.017), vec3(0.03,0.034,0.04), smoothstep(-0.4, 0.8, d.y));
    c += vec3(1.0,0.97,0.93) * 2.3 * panel(d, vec3(-0.75,0.55,0.75), vec2(0.26,0.42), 0.2);
    c += vec3(1.0,0.55,0.28) * 1.3 * panel(d, vec3(0.95,0.25,0.35), vec2(0.10,0.55), 0.08);
    c += vec3(0.55,0.58,0.64) * 0.16 * smoothstep(-0.1, 1.0, d.y);
    c += vec3(0.35,0.38,0.45) * 0.10 * box(d, vec3(-0.2,0.3,-1.0), 1.2, 0.3);
    c += vec3(0.05,0.04,0.035) * smoothstep(0.0, -0.8, d.y);
    c += vec3(0.08,0.06,0.05) * exp(-pow(d.y*7.0, 2.0));
    gl_FragColor = vec4(c, 1.);
   }`
 })))
 return pmrem.fromScene(scene,0.015).texture
}

function particles(density:number){
 const counts={shell:Math.round(16000*density),inner:Math.round(7000*density),motes:Math.round(2600*density)}
 const total=counts.shell+counts.inner+counts.motes
 const dir=new Float32Array(total*3),seed=new Float32Array(total*4),type=new Float32Array(total),radius=new Float32Array(total)
 for(let i=0;i<total;i++){
  const u=Math.random()*2-1,th=Math.random()*Math.PI*2,s=Math.sqrt(1-u*u)
  dir.set([s*Math.cos(th),u,s*Math.sin(th)],i*3)
  seed.set([Math.random(),Math.random(),Math.random(),Math.random()],i*4)
  if(i<counts.shell){type[i]=0;radius[i]=1}
  else if(i<counts.shell+counts.inner){type[i]=1;radius[i]=Math.cbrt(Math.random())*0.92}
  else{type[i]=2;radius[i]=1.75+Math.random()*(SPHERE_R*0.9-1.75)}
 }
 const geometry=new THREE.BufferGeometry()
 geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(total*3),3))
 geometry.setAttribute('aDir',new THREE.BufferAttribute(dir,3))
 geometry.setAttribute('aSeed',new THREE.BufferAttribute(seed,4))
 geometry.setAttribute('aType',new THREE.BufferAttribute(type,1))
 geometry.setAttribute('aR',new THREE.BufferAttribute(radius,1))
 geometry.boundingSphere=new THREE.Sphere(new THREE.Vector3(),SPHERE_R)
 return geometry
}

const vertexShader=`
 uniform float uFlow,uRipple,uSwirl,uBreath,uListen,uThink,uLevel,uPixel,uBlobR,uVoice,uRest;
 uniform float uBands[8]; uniform vec3 uFront,uCIdle,uCListen,uCSpeak,uCThink;
 attribute vec3 aDir; attribute vec4 aSeed; attribute float aType; attribute float aR;
 varying vec3 vCol; varying float vA;
 ${NOISE}
 vec3 rotY(vec3 p,float a){float c=cos(a),s=sin(a);return vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);}
 void main(){
  vec3 d = aDir;
  float swirl = uSwirl*(0.55+0.9*aSeed.x)*(1.0-0.55*abs(d.y));
  if(aType>1.5) swirl += uFlow*(0.25+0.3*aSeed.y);
  d = rotY(d, swirl);
  float n  = snoise(d*1.35 + vec3(0.0, uFlow, uFlow*0.4));
  float n2 = snoise(d*3.4 - vec3(uFlow*1.4));
  float lat = d.y*0.5+0.5;
  int bi = int(clamp(floor(lat*7.999),0.0,7.0));
  float band = uBands[bi];
  float ang = acos(clamp(dot(d, uFront), -1.0, 1.0));
  float ripple = sin(ang*9.0 - uRipple) * exp(-ang*0.85);
  float r; vec3 p;
  if(aType<0.5){
   r = uBlobR*(1.0 + n*0.065 + n2*0.022 + uBreath*0.018
       + uListen*(band*0.30*(0.55+0.45*n2) + ripple*(0.03+uLevel*0.14))
       + uThink*0.05*sin(d.y*10.0 + uSwirl*3.0));
   p = d*r;
  } else if(aType<1.5){
   vec3 j = vec3(snoise(aSeed.xyz*5.0+uFlow*0.35), snoise(aSeed.yzw*5.0+uFlow*0.35), snoise(aSeed.zwx*5.0+uFlow*0.35));
   r = aR*uBlobR*(1.0 + n*0.07 + uListen*uLevel*0.18);
   p = normalize(d + 0.16*j)*r;
  } else {
   r = aR + 0.07*sin(uFlow*2.5 + aSeed.w*6.283) + uListen*uLevel*0.08*aSeed.z;
   p = d*r; p.y *= 0.92;
  }
  p += uFront*uListen*(aType<1.5 ? 0.16 : 0.05);
  vec4 mv = modelViewMatrix*vec4(p,1.0);
  gl_Position = projectionMatrix*mv;
  vec3 nV = normalize(normalMatrix*d);
  float rim = 1.0-abs(nV.z);
  float wave = 0.5+0.5*sin(d.y*7.0 - uFlow*3.2 + n*2.4);
  // Candidate speech tints violet, interviewer speech stays cyan.
  vec3 base = mix(uCIdle, mix(uCListen, uCSpeak, uVoice), uListen);
  base = mix(base, uCThink, uThink*(1.0-uListen));
  float a;
  if(aType<0.5){
   a = 0.18 + 0.55*pow(rim,2.2) + 0.32*pow(wave,6.0) + uListen*(0.35*band + 0.25*max(ripple,0.0)*uLevel);
   gl_PointSize = (1.5 + 1.6*aSeed.w + uListen*band*1.4) * uPixel * (12.0 / -mv.z);
  } else if(aType<1.5){
   a = 0.12 + 0.2*aSeed.z + 0.25*pow(wave,4.0) + uListen*uLevel*0.4;
   gl_PointSize = (1.2 + 1.8*aSeed.w) * uPixel * (12.0 / -mv.z);
   base = mix(base, vec3(1.0), 0.25);
  } else {
   a = (0.08 + 0.3*pow(aSeed.z,3.0)) * (0.7 + 0.6*sin(uFlow*4.0 + aSeed.x*30.0));
   gl_PointSize = (1.0 + 2.2*pow(aSeed.w,4.0)) * uPixel * (12.0 / -mv.z);
  }
  vCol = base; vA = a*(1.0 + 0.6*uThink*wave)*(1.0 - 0.45*uRest);
 }`

const fragmentShader=`
 varying vec3 vCol; varying float vA;
 void main(){
  vec2 c = gl_PointCoord-0.5; float d = length(c);
  if(d>0.5) discard;
  float s = smoothstep(0.5,0.0,d); s*=s;
  gl_FragColor = vec4(vCol*vA*1.6, s);
 }`

function glowTexture(){
 const canvas=document.createElement('canvas');canvas.width=canvas.height=128
 const g=canvas.getContext('2d')!,gr=g.createRadialGradient(64,64,0,64,64,64)
 gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(.25,'rgba(255,255,255,.35)');gr.addColorStop(1,'rgba(255,255,255,0)')
 g.fillStyle=gr;g.fillRect(0,0,128,128);return new THREE.CanvasTexture(canvas)
}

export function createOrb(canvas:HTMLCanvasElement,{density=1}:{density?:number}={}):Orb{
 const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)')
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance'})
 renderer.setPixelRatio(Math.min(devicePixelRatio,2))
 renderer.toneMapping=THREE.ACESFilmicToneMapping
 renderer.toneMappingExposure=0.9

 const scene=new THREE.Scene()
 const camera=new THREE.PerspectiveCamera(35,1,0.1,200)
 camera.position.set(0.06,0.6,14)
 const pmrem=new THREE.PMREMGenerator(renderer)
 const environment=studioEnvironment(pmrem)
 scene.environment=environment

 // Dark studio sweep with a soft warm horizon, so the glass has something to bend.
 const backdrop=new THREE.Mesh(new THREE.SphereGeometry(60,48,24),new THREE.ShaderMaterial({
  side:THREE.BackSide,depthWrite:false,
  vertexShader:`varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader:`varying vec3 vP;
   void main(){
    float y = vP.y;
    vec3 top = vec3(0.012,0.016,0.02), mid = vec3(0.035,0.04,0.045);
    vec3 c = mix(mid, top, smoothstep(0.0, 0.7, y));
    c = mix(c, vec3(0.006,0.007,0.008), smoothstep(0.0,-0.6,y));
    c += vec3(0.11,0.05,0.02) * exp(-pow((y+0.05)*11.0, 2.0)) * (0.6+0.4*smoothstep(-1.,1.,vP.x));
    c += vec3(0.05,0.08,0.1) * exp(-pow((y-0.35)*5.0, 2.0)) * smoothstep(0.2,-1.,vP.x);
    gl_FragColor = vec4(c,1.);
   }`
 }))
 backdrop.renderOrder=-1
 scene.add(backdrop)

 const uniforms={
  uFlow:{value:0},uRipple:{value:0},uSwirl:{value:0},uBreath:{value:0},
  uListen:{value:0},uThink:{value:0},uLevel:{value:0},uVoice:{value:0},uRest:{value:0},
  uBands:{value:new Array(8).fill(0)},
  uFront:{value:new THREE.Vector3(0,0,1)},
  uPixel:{value:1},uBlobR:{value:BLOB_R},
  uCIdle:{value:new THREE.Color('#8fe6ff')},uCListen:{value:new THREE.Color('#7f6bff')},uCSpeak:{value:new THREE.Color('#a9f0ff')},uCThink:{value:new THREE.Color('#d9cffd')},
 }
 const geometry=particles(density)
 const material=new THREE.ShaderMaterial({uniforms,vertexShader,fragmentShader,transparent:false,depthWrite:false,blending:THREE.AdditiveBlending})
 const points=new THREE.Points(geometry,material)
 points.frustumCulled=false
 scene.add(points)
 const glowMap=glowTexture()
 const core=new THREE.Sprite(new THREE.SpriteMaterial({map:glowMap,blending:THREE.AdditiveBlending,depthWrite:false,transparent:false,opacity:.25}))
 core.scale.setScalar(3.4);scene.add(core)

 let glass:THREE.Mesh|null=null,disposed=false
 new GLTFLoader().load(sphereUrl,gltf=>{
  if(disposed)return
  gltf.scene.traverse(object=>{
   const mesh=object as THREE.Mesh
   if(!mesh.isMesh)return
   const m=mesh.material as THREE.MeshPhysicalMaterial
   m.transmission=1;m.ior=2.0;m.roughness=0;m.metalness=0
   m.thickness=0.5;m.attenuationColor=new THREE.Color('#e3f1f3');m.attenuationDistance=4
   m.clearcoat=0;m.envMapIntensity=1.0;m.specularIntensity=0.9;m.iridescence=0.04;m.iridescenceIOR=1.3
   glass=mesh
  })
  scene.add(gltf.scene)
 },undefined,error=>console.error('Orb model failed to load',error))

 const composer=new EffectComposer(renderer)
 composer.addPass(new RenderPass(scene,camera))
 const bloom=new UnrealBloomPass(new THREE.Vector2(1,1),0.5,0.45,0.75)
 composer.addPass(bloom)
 composer.addPass(new OutputPass())

 function resize(){
  const w=Math.max(1,canvas.clientWidth),h=Math.max(1,canvas.clientHeight)
  renderer.setSize(w,h,false);composer.setSize(w,h)
  camera.aspect=w/h
  // Frame the glass tightly with a little room for the bloom.
  const fit=SPHERE_R*FIT,vfov=THREE.MathUtils.degToRad(camera.fov)
  camera.position.setLength(Math.max(fit/2/Math.tan(vfov/2),fit/2/(Math.tan(vfov/2)*camera.aspect)))
  camera.updateProjectionMatrix()
  // Keep particles the same size relative to the glass as in the original scene.
  const spherePx=Math.min(w,h)*2*SPHERE_R/fit
  uniforms.uPixel.value=renderer.getPixelRatio()*0.00152*spherePx*camera.position.length()/12
  render(performance.now())
 }

 const bands=new Array(8).fill(0),smoothBands=new Array(8).fill(0)
 let input:OrbInput={mode:'idle',analyser:null,level:0}
 let level=0,listenS=0,thinkS=0,voiceS=0,restS=0,last=performance.now(),elapsed=0,frame=0,active=false,simT=0,simNext=0,simAmp=0,simTarget=0
 let timeBuf=new Float32Array(1024),freqBuf=new Uint8Array(512)
 const front=new THREE.Vector3(0,0,1)

 function readAnalyser(analyser:AnalyserNode){
  if(timeBuf.length!==analyser.fftSize)timeBuf=new Float32Array(analyser.fftSize)
  if(freqBuf.length!==analyser.frequencyBinCount)freqBuf=new Uint8Array(analyser.frequencyBinCount)
  analyser.getFloatTimeDomainData(timeBuf)
  let sum=0;for(let i=0;i<timeBuf.length;i++)sum+=timeBuf[i]*timeBuf[i]
  analyser.getByteFrequencyData(freqBuf)
  const nyquist=analyser.context.sampleRate/2,bins=freqBuf.length
  for(let b=0;b<8;b++){
   const f0=80*Math.pow(100,b/8),f1=80*Math.pow(100,(b+1)/8)
   const i0=Math.max(1,Math.floor(f0/nyquist*bins)),i1=Math.max(i0+1,Math.ceil(f1/nyquist*bins))
   let peak=0;for(let i=i0;i<i1&&i<bins;i++)peak=Math.max(peak,freqBuf[i])
   bands[b]=Math.pow(peak/255,1.6)
  }
  return Math.sqrt(sum/timeBuf.length)
 }
 // Without an analyser, shape speech-like bands from the level alone.
 function bandsFromLevel(dt:number,value:number){
  simT+=dt
  if(simT>simNext){simTarget=Math.random()<0.18?0.3:0.6+Math.random()*0.4;simNext=simT+0.09+Math.random()*0.18}
  simAmp+=(simTarget-simAmp)*Math.min(1,dt*22)
  const f1=2+Math.sin(simT*3.1)*1.5,f2=5+Math.sin(simT*1.7+1)*1.5,amp=simAmp*value
  for(let b=0;b<8;b++)bands[b]=amp*(0.25+0.75*Math.exp(-Math.pow(b-f1,2)/1.4)+0.5*Math.exp(-Math.pow(b-f2,2)/1.2))
 }

 function render(now:number){
  let dt=Math.min(0.05,(now-last)/1000);last=now
  if(reduceMotion.matches)dt*=0.35
  elapsed+=dt
  const speaking=input.mode==='listen'||input.mode==='speak'
  let target=0
  if(speaking&&input.analyser){
   const rms=readAnalyser(input.analyser)
   const dbfs=rms>1e-5?20*Math.log10(rms):-Infinity
   target=Number.isFinite(dbfs)?THREE.MathUtils.clamp((dbfs+58)/46,0,1):0
  }else if(speaking){target=THREE.MathUtils.clamp(input.level,0,1);bandsFromLevel(dt,target)}
  else bands.fill(0)
  level+=(target-level)*Math.min(1,dt*(target>level?18:5))
  for(let i=0;i<8;i++)smoothBands[i]+=(bands[i]-smoothBands[i])*Math.min(1,dt*(bands[i]>smoothBands[i]?20:6))
  // The orb leans in only while someone is audibly talking.
  const talking=speaking&&level>0.08
  listenS+=((talking?1:0)-listenS)*Math.min(1,dt*3.2)
  thinkS+=((input.mode==='think'?1:0)-thinkS)*Math.min(1,dt*2.4)
  voiceS+=((input.mode==='speak'?1:0)-voiceS)*Math.min(1,dt*4)
  restS+=((input.mode==='rest'?1:0)-restS)*Math.min(1,dt*2)

  uniforms.uFlow.value+=dt*(0.12+listenS*0.28+thinkS*0.35)*(1-0.7*restS)
  uniforms.uRipple.value+=dt*(2.6+level*7.0)
  uniforms.uSwirl.value+=dt*thinkS*1.4
  uniforms.uBreath.value=Math.sin(elapsed*0.9)
  uniforms.uListen.value=listenS;uniforms.uThink.value=thinkS;uniforms.uLevel.value=level;uniforms.uVoice.value=voiceS;uniforms.uRest.value=restS
  for(let i=0;i<8;i++)uniforms.uBands.value[i]=smoothBands[i]
  uniforms.uFront.value.lerp(front.copy(camera.position).normalize(),0.15)

  const listenColor=uniforms.uCListen.value.clone().lerp(uniforms.uCSpeak.value,voiceS)
  core.material.color.copy(uniforms.uCIdle.value).lerp(listenColor,listenS).lerp(uniforms.uCThink.value,thinkS*(1-listenS))
  core.material.opacity=(0.05+0.02*Math.sin(elapsed*0.9)+listenS*(0.05+level*0.18)+thinkS*0.06)*(1-0.5*restS)
  core.scale.setScalar(3.2+listenS*level*1.0)
  bloom.strength=0.55+listenS*(0.2+level*0.45)+thinkS*0.15
  if(glass)(glass.material as THREE.MeshPhysicalMaterial).iridescence=0.06+thinkS*0.3
  composer.render()
 }
 function loop(now:number){frame=0;if(!active||disposed)return;render(now);frame=requestAnimationFrame(loop)}
 function setActive(next:boolean){
  if(next===active)return
  active=next
  if(active){last=performance.now();frame=requestAnimationFrame(loop)}else cancelAnimationFrame(frame)
 }
 function dispose(){
  disposed=true;cancelAnimationFrame(frame)
  geometry.dispose();material.dispose();glowMap.dispose();backdrop.geometry.dispose();(backdrop.material as THREE.Material).dispose();core.material.dispose();environment.dispose();pmrem.dispose()
  scene.traverse(object=>{const mesh=object as THREE.Mesh;if(mesh.isMesh){mesh.geometry.dispose();(mesh.material as THREE.Material).dispose()}})
  composer.dispose();renderer.dispose();renderer.forceContextLoss()
 }
 resize()
 return {update:next=>{input=next},setActive,resize,dispose}
}
