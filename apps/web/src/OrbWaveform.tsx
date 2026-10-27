import {useEffect,useRef} from 'react'

// Keep interview motion tied to playback; the homepage may use a quiet idle drift.
export default function OrbWaveform({speaking,level,idleMotion=false}:{speaking:boolean;level:number;idleMotion?:boolean}){
 const canvas=useRef<HTMLCanvasElement>(null),audio=useRef({speaking,level,idleMotion}),redraw=useRef<()=>void>(()=>{})
 audio.current={speaking,level,idleMotion}
 useEffect(()=>{
  const element=canvas.current
  if(!element)return
  const ctx=element.getContext('2d')
  if(!ctx)return
  const motion=matchMedia('(prefers-reduced-motion: reduce)')
  let frame=0,width=0,height=0,phase=0,energy=0,last=0,inView=false
  function draw(time:number){
   frame=0
   const idle=audio.current.idleMotion&&!audio.current.speaking&&inView
   const moving=(audio.current.speaking||idle)&&!motion.matches&&!document.hidden
   const dt=last?Math.min(40,time-last):16;last=time
   const target=audio.current.speaking&&moving?Math.max(0,Math.min(1,audio.current.level)):0
   energy+=(target-energy)*.18
   if(moving)phase+=dt*(idle?.0006:.0015+energy*.004)
   else{energy=0;phase=0}
   ctx!.clearRect(0,0,width,height)
   // The path's ends meet the glass rim; layered spectra stay inside the sphere.
   const dark=document.documentElement.dataset.theme==='dark'
   const gradient=ctx!.createLinearGradient(0,0,width,0)
   if(dark){gradient.addColorStop(0,'#b9d1bd');gradient.addColorStop(.24,'#dcefd9');gradient.addColorStop(.43,'#c0cfb3');gradient.addColorStop(.5,'#f7faee');gradient.addColorStop(.59,'#e4ddc6');gradient.addColorStop(.78,'#b4d1bd');gradient.addColorStop(1,'#d0dac7')}
   else{gradient.addColorStop(0,'#7c9b89');gradient.addColorStop(.24,'#bed6bf');gradient.addColorStop(.46,'#d4ddc5');gradient.addColorStop(.53,'#fff');gradient.addColorStop(.68,'#b8c9b1');gradient.addColorStop(.84,'#a0c2ac');gradient.addColorStop(1,'#829d89')}
   for(let layer=5;layer>=0;layer--){
    ctx!.beginPath()
    for(let step=0;step<=96;step++){
     const t=step/96,envelope=Math.sin(Math.PI*t)
     const amplitude=height*(idle?.03:.065+energy*.14)
     const wave=Math.sin(t*Math.PI*2+phase)*envelope*amplitude
     const ripple=moving?Math.sin(t*Math.PI*6-phase*1.6)*envelope*height*(idle?.003:.018*energy):0
     const y=height*.51+wave+ripple+(layer-2.5)*height*.006*envelope
     if(step===0)ctx!.moveTo(0,y);else ctx!.lineTo(t*width,y)
    }
    ctx!.strokeStyle=gradient;ctx!.globalAlpha=layer===0?1:.16
    ctx!.lineWidth=layer===0?Math.max(1.2,width*.007):width*(.015+layer*.008)
    ctx!.shadowColor=layer%2?'#c3dfbf':dark?'#e6dec7':'#a4c3a5';ctx!.shadowBlur=layer===0?width*.035:width*.09
    ctx!.stroke()
   }
   ctx!.globalAlpha=1;ctx!.shadowBlur=0
   if(moving)frame=requestAnimationFrame(draw)
  }
  function refresh(){cancelAnimationFrame(frame);frame=requestAnimationFrame(draw)}
  const observer=new ResizeObserver(()=>{
   const rect=element!.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2)
   width=element!.clientWidth||rect.width;height=element!.clientHeight||rect.height
   element!.width=Math.round(width*ratio);element!.height=Math.round(height*ratio)
   ctx!.setTransform(ratio,0,0,ratio,0,0);refresh()
  })
  const visibility=new IntersectionObserver(([entry])=>{inView=entry.isIntersecting;refresh()})
  visibility.observe(element)
  observer.observe(element);motion.addEventListener('change',refresh);document.addEventListener('visibilitychange',refresh)
  // React changes speaking without recreating the canvas or the WebGL renderer.
  redraw.current=refresh
  refresh()
  return()=>{cancelAnimationFrame(frame);observer.disconnect();visibility.disconnect();motion.removeEventListener('change',refresh);document.removeEventListener('visibilitychange',refresh);redraw.current=()=>{}}
 },[])
 useEffect(()=>{redraw.current()},[speaking,idleMotion])
 return <canvas ref={canvas} className="orb-waveform" aria-hidden="true"/>
}
