import {useEffect,useRef} from 'react'

type Props={interviewerLevel:number;candidateLevel:number;active:boolean;idleMotion?:boolean;dark:boolean}

// Liquid held inside the glass sphere. The surface sloshes with the interviewer's
// playback and with the candidate's microphone; it settles flat when nobody speaks.
export default function OrbWaveform({interviewerLevel,candidateLevel,active,idleMotion=false,dark}:Props){
 const canvas=useRef<HTMLCanvasElement>(null),audio=useRef({interviewerLevel,candidateLevel,active,idleMotion,dark}),redraw=useRef<()=>void>(()=>{})
 audio.current={interviewerLevel,candidateLevel,active,idleMotion,dark}
 useEffect(()=>{
  const element=canvas.current
  if(!element)return
  const ctx=element.getContext('2d')
  if(!ctx)return
  const motion=matchMedia('(prefers-reduced-motion: reduce)')
  let frame=0,width=0,height=0,phase=0,energy=0,voice=0,tilt=0,last=0,inView=false
  function surface(t:number,amplitude:number,offset:number){
   // Two travelling waves plus a slow tilt read as liquid rather than a signal trace.
   return Math.sin(t*Math.PI*2+phase+offset)*amplitude+Math.sin(t*Math.PI*5.2-phase*1.7+offset)*amplitude*.35+(t-.5)*tilt*height
  }
  function draw(time:number){
   frame=0
   const state=audio.current
   const live=(state.active||state.idleMotion)&&inView&&!motion.matches&&!document.hidden
   const dt=last?Math.min(40,time-last):16;last=time
   const interviewer=Math.max(0,Math.min(1,state.interviewerLevel)),candidate=Math.max(0,Math.min(1,state.candidateLevel))
   const target=live&&state.active?Math.max(interviewer,candidate*.85):0
   energy+=(target-energy)*.14
   // 1 = interviewer speaking, 0 = candidate; drives the surface tint.
   if(interviewer>.02||candidate>.02)voice+=((interviewer>=candidate?1:0)-voice)*.08
   if(live){phase+=dt*(.0011+energy*.0045);tilt=Math.sin(time*.00045)*(.012+energy*.03)}
   else{energy=0;tilt=0}
   ctx!.clearRect(0,0,width,height)
   const dark=state.dark,level=height*.56
   const amplitude=height*(live?.011+energy*.075:0)
   // Back layer gives depth through the glass.
   ctx!.beginPath();ctx!.moveTo(0,height)
   for(let step=0;step<=64;step++){const t=step/64;ctx!.lineTo(t*width,level-height*.012+surface(t,amplitude*.8,2.1))}
   ctx!.lineTo(width,height);ctx!.closePath()
   ctx!.fillStyle=dark?'rgba(163,201,213,.16)':'rgba(62,111,142,.16)';ctx!.fill()
   // Front body of liquid.
   const body=ctx!.createLinearGradient(0,level-amplitude,0,height)
   if(dark){body.addColorStop(0,'rgba(163,201,213,.42)');body.addColorStop(.45,'rgba(62,111,142,.5)');body.addColorStop(1,'rgba(34,71,92,.72)')}
   else{body.addColorStop(0,'rgba(163,201,213,.62)');body.addColorStop(.5,'rgba(62,111,142,.5)');body.addColorStop(1,'rgba(34,71,92,.68)')}
   ctx!.beginPath();ctx!.moveTo(0,height)
   for(let step=0;step<=96;step++){const t=step/96;ctx!.lineTo(t*width,level+surface(t,amplitude,0))}
   ctx!.lineTo(width,height);ctx!.closePath();ctx!.fillStyle=body;ctx!.fill()
   // Caustic glow under the surface.
   const caustic=ctx!.createRadialGradient(width*.5,height*.86,0,width*.5,height*.86,width*.42)
   caustic.addColorStop(0,dark?'rgba(207,224,230,.22)':'rgba(255,255,255,.34)');caustic.addColorStop(1,'rgba(255,255,255,0)')
   ctx!.fillStyle=caustic;ctx!.fill()
   // The bright meniscus line the team liked from the original waveform.
   const glow=ctx!.createLinearGradient(0,0,width,0)
   const mid=voice>.5?'#ffffff':'#CFE0E6'
   glow.addColorStop(0,dark?'rgba(163,201,213,.5)':'rgba(62,111,142,.55)');glow.addColorStop(.5,mid);glow.addColorStop(1,dark?'rgba(163,201,213,.5)':'rgba(62,111,142,.55)')
   for(let layer=2;layer>=0;layer--){
    ctx!.beginPath()
    for(let step=0;step<=96;step++){const t=step/96,y=level+surface(t,amplitude,0);if(step===0)ctx!.moveTo(0,y);else ctx!.lineTo(t*width,y)}
    ctx!.strokeStyle=glow;ctx!.globalAlpha=layer===0?.95:.18
    ctx!.lineWidth=layer===0?Math.max(1.2,width*.008):width*(.02+layer*.014)
    ctx!.shadowColor=dark?'#A3C9D5':'#ffffff';ctx!.shadowBlur=layer===0?width*.03:width*.08
    ctx!.stroke()
   }
   ctx!.globalAlpha=1;ctx!.shadowBlur=0
   if(live)frame=requestAnimationFrame(draw)
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
  redraw.current=refresh
  refresh()
  return()=>{cancelAnimationFrame(frame);observer.disconnect();visibility.disconnect();motion.removeEventListener('change',refresh);document.removeEventListener('visibilitychange',refresh);redraw.current=()=>{}}
 },[])
 useEffect(()=>{redraw.current()},[active,idleMotion,dark])
 return <canvas ref={canvas} className="orb-liquid" aria-hidden="true"/>
}
