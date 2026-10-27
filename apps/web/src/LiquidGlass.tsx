import {useEffect,useRef,useState,type HTMLAttributes} from 'react'
import Container,{type GlassShape} from './vendor/liquid-glass-js/container'
import {useTheme} from './Theme'
import './liquid-glass.css'

// The library owns refraction, blur and shape masking. This adapter owns the
// decorative source and lifecycle; it never captures the application's DOM.
class SurfaceRenderer extends Container {
 private material=document.createElement('canvas')
 private program:WebGLProgram|null=null
 private disposed=false
 override init(){this.createElement()}
 override getPosition(){return {x:this.material.width/2,y:this.material.height/2}}
 override createProgram(gl:WebGLRenderingContext,vertex:string,fragment:string){
  // Blend a clear center with stronger Fresnel reflections and dispersion at the rim.
  const output='gl_FragColor = vec4(color.rgb, mask);'
  const source=this.type==='circle'&&fragment.includes(output)?fragment.replace('void main() {','uniform float u_darkMode;\n    void main() {').replace(output,`
    vec2 spherePoint = (coord - 0.5) * 2.0;
    float radius = clamp(length(spherePoint), 0.0, 1.0);
    float fresnel = pow(radius, 3.2);
    float rim = smoothstep(0.88, 0.985, radius);
    float lightAngle = max(0.0, dot(normalize(spherePoint + vec2(0.0001)), normalize(vec2(-0.65, -0.8))));
    float broadReflection = pow(lightAngle, 10.0) * mix(0.3, 0.13, u_darkMode);
    float sharpReflection = pow(lightAngle, 54.0) * mix(0.42, 0.9, u_darkMode);
    float specular = (broadReflection + sharpReflection) * smoothstep(0.42, 0.86, radius);
    float opacity = mask * clamp(0.22 + fresnel * 0.56 + specular * 0.48, 0.0, 0.92);
    vec3 glassColor = mix(color.rgb, vec3(0.94, 0.985, 1.0), clamp(rim * 0.92 + specular * 1.2, 0.0, 1.0));
    float prism = smoothstep(0.87, 0.97, radius) * (1.0 - smoothstep(0.97, 1.0, radius));
    vec3 edgeSpectrum = vec3(0.70, 0.83, 0.88) + 0.08 * cos(vec3(0.0, 0.8, 1.6) + atan(spherePoint.y, spherePoint.x) * 2.0);
    glassColor = mix(glassColor, edgeSpectrum, prism * 0.5);
    gl_FragColor = vec4(glassColor * opacity, opacity);
  `):fragment
  this.program=super.createProgram(gl,vertex,source)
  return this.program
 }
 override startRenderLoop(){
  this.render=()=>{
   const refs=this.gl_refs,gl=refs.gl
   if(!gl||gl.isContextLost()||this.disposed)return
   gl.clear(gl.COLOR_BUFFER_BIT)
   gl.uniform1f(refs.scrollYLoc!,0)
   const position=this.getPosition()
   gl.uniform2f(refs.containerPositionLoc!,position.x,position.y)
   gl.drawArrays(gl.TRIANGLES,0,6)
  }
  this.render()
 }
 mount(host:HTMLDivElement,dark:boolean,shape:GlassShape){
  this.gl=this.canvas.getContext('webgl',{preserveDrawingBuffer:true,alpha:true})
  // Leave the host clean when WebGL is unavailable; CSS remains the fallback.
  if(!this.gl){this.element.remove();return false}
  host.appendChild(this.element)
  this.element.setAttribute('aria-hidden','true')
  this.element.classList.add('liquid-glass-renderer')
  return this.resize(host,dark,shape)
 }
 resize(host:HTMLDivElement,dark:boolean,shape:GlassShape){
  if(!this.gl||this.gl.isContextLost()||this.disposed)return false
  const rect=host.getBoundingClientRect()
  const width=Math.max(1,Math.round(rect.width)),height=Math.max(1,Math.round(rect.height))
  // Measure layout dimensions, independent of the voice orb's CSS transform.
  this.width=host.clientWidth||width;this.height=host.clientHeight||height
  this.borderRadius=shape==='circle'?Math.min(this.width,this.height)/2:shape==='pill'?this.height/2:parseFloat(getComputedStyle(host).borderRadius)||24
  this.canvas.width=this.width;this.canvas.height=this.height
  this.canvas.style.width='100%';this.canvas.style.height='100%'
  this.canvas.style.borderRadius='inherit';this.canvas.style.boxShadow='none'
  this.canvas.style.zIndex='0'
  this.element.style.borderRadius='inherit'
  this.paintMaterial(dark,shape)
  if(!this.program){this.setupShader(this.material)}else{
   const gl=this.gl
   gl.bindTexture(gl.TEXTURE_2D,this.gl_refs.texture!)
   gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.material)
   // Uniform names are stable in the pinned upstream shader.
   gl.uniform2f(gl.getUniformLocation(this.program,'u_resolution'),this.width,this.height)
   gl.uniform2f(gl.getUniformLocation(this.program,'u_textureSize'),this.material.width,this.material.height)
   gl.uniform1f(gl.getUniformLocation(this.program,'u_borderRadius'),this.borderRadius)
   gl.viewport(0,0,this.width,this.height)
   this.render?.()
  }
  if(shape==='circle'&&this.program){
   const gl=this.gl
   gl.uniform1f(gl.getUniformLocation(this.program,'u_blurRadius'),.7)
   gl.uniform1f(gl.getUniformLocation(this.program,'u_edgeIntensity'),.16)
   gl.uniform1f(gl.getUniformLocation(this.program,'u_rimIntensity'),.3)
   gl.uniform1f(gl.getUniformLocation(this.program,'u_darkMode'),dark?1:0)
   this.render?.()
  }
  return Boolean(this.gl_refs.gl)
 }
 private paintMaterial(dark:boolean,shape:GlassShape){
  const canvas=this.material
  canvas.width=Math.min(1536,Math.round(Math.max(256,this.width*1.25)));canvas.height=Math.min(1024,Math.round(Math.max(256,this.height*1.25)))
  const ctx=canvas.getContext('2d')!
  const w=canvas.width,h=canvas.height,orb=shape==='circle'
  if(orb){
   // Let cool ambient color and broad reflections define the glass body.
   const body=ctx.createLinearGradient(0,0,0,h)
   if(dark){body.addColorStop(0,'#2a3f4b');body.addColorStop(.38,'#132530');body.addColorStop(.72,'#22414f');body.addColorStop(1,'#4d6f80')}
   else{body.addColorStop(0,'#eef2f5');body.addColorStop(.38,'#b9ccd6');body.addColorStop(.72,'#c4d8e0');body.addColorStop(1,'#f5f7f9')}
   ctx.fillStyle=body;ctx.fillRect(0,0,w,h)
   const caustic=ctx.createRadialGradient(w*.5,h*.82,0,w*.5,h*.82,w*.32)
   caustic.addColorStop(0,dark?'rgba(207,224,230,.24)':'rgba(255,255,255,.65)');caustic.addColorStop(.3,dark?'rgba(163,201,213,.15)':'rgba(220,234,240,.3)');caustic.addColorStop(1,'rgba(210,230,255,0)')
   ctx.fillStyle=caustic;ctx.fillRect(0,0,w,h)
   const reflectionRadius=w*(dark?.16:.2)
   const reflection=ctx.createRadialGradient(w*.29,h*.19,0,w*.29,h*.19,reflectionRadius)
   reflection.addColorStop(0,dark?'rgba(255,255,255,.14)':'rgba(255,255,255,.48)');reflection.addColorStop(.22,dark?'rgba(225,236,240,.06)':'rgba(243,248,250,.22)');reflection.addColorStop(1,'rgba(220,230,255,0)')
   ctx.fillStyle=reflection;ctx.fillRect(0,0,w,h);return
  }
  ctx.fillStyle=dark?'#1c2c35':'#e8edf0';ctx.fillRect(0,0,w,h)
  const bloom=ctx.createRadialGradient(w*.36,h*.28,0,w*.5,h*.5,Math.max(w,h)*.68)
  bloom.addColorStop(0,dark?'#557585':'#ffffff')
  bloom.addColorStop(.35,dark?'#2f4b59':'#dde8ed')
  bloom.addColorStop(.7,dark?'#152a35':'#b3c8d2');bloom.addColorStop(1,dark?'#18282f':'#f1f4f6')
  ctx.fillStyle=bloom;ctx.fillRect(0,0,w,h)
  // Soft curved reflections keep non-circular glass controls dimensional without sampling text.
  ctx.save();ctx.translate(w*.5,h*.5);ctx.rotate(-.4)
  ctx.strokeStyle=dark?'rgba(207,224,230,.28)':'rgba(255,255,255,.75)';ctx.lineWidth=8
  ctx.beginPath();ctx.ellipse(0,0,w*.3,h*.34,0,0,Math.PI*2);ctx.stroke()
  ctx.strokeStyle=dark?'rgba(163,201,213,.18)':'rgba(62,111,142,.18)';ctx.lineWidth=14
  ctx.beginPath();ctx.ellipse(w*.05,h*.1,w*.38,h*.4,0,0,Math.PI*2);ctx.stroke();ctx.restore()
 }
 destroy(){
  if(this.disposed)return
  this.disposed=true
  const gl=this.gl
  if(gl){
   if(this.program){for(const shader of gl.getAttachedShaders(this.program)||[])gl.deleteShader(shader);gl.deleteProgram(this.program)}
   if(this.gl_refs.texture)gl.deleteTexture(this.gl_refs.texture)
   if(this.gl_refs.positionBuffer)gl.deleteBuffer(this.gl_refs.positionBuffer)
   if(this.gl_refs.texcoordBuffer)gl.deleteBuffer(this.gl_refs.texcoordBuffer)
   gl.getExtension('WEBGL_lose_context')?.loseContext()
  }
  Container.instances=Container.instances.filter(instance=>instance!==this)
  this.element.remove()
 }
}

export default function LiquidGlass({shape='rounded',className='',children,...props}:HTMLAttributes<HTMLDivElement>&{shape?:GlassShape}){
 const host=useRef<HTMLDivElement>(null),[ready,setReady]=useState(false)
 const {theme}=useTheme()
 useEffect(()=>{
  const element=host.current
  if(!element)return
  let frame=0,active=true
  const renderer=new SurfaceRenderer({type:shape,tintOpacity:shape==='circle'?.015:theme==='dark'?.035:.09})
  const lost=(event:Event)=>{event.preventDefault();renderer.destroy();if(active)setReady(false)}
  renderer.canvas.addEventListener('webglcontextlost',lost)
  try{setReady(renderer.mount(element,theme==='dark',shape))}catch{setReady(false)}
  const observer=new ResizeObserver(()=>{
   cancelAnimationFrame(frame)
   frame=requestAnimationFrame(()=>{if(active)try{setReady(renderer.resize(element,theme==='dark',shape))}catch{setReady(false)}})
  })
  observer.observe(element)
  return()=>{active=false;observer.disconnect();cancelAnimationFrame(frame);renderer.canvas.removeEventListener('webglcontextlost',lost);renderer.destroy()}
 },[theme,shape])
 return <div {...props} ref={host} className={`liquid-glass ${ready?'liquid-glass-ready':''} ${className}`} data-glass-renderer={ready?'webgl':'fallback'}>{children}</div>
}
