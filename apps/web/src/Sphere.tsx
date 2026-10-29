import {useEffect,useRef,useState,type RefObject} from 'react'
import type {Orb,OrbMode} from './orb/engine'

type Size='large'|'medium'|'small'|'tiny'
type Analysers=RefObject<{mic:AnalyserNode|null;playback:AnalyserNode|null}>
// Fewer particles where the orb is small; the shape reads the same.
const density:Record<Size,number>={large:1,medium:.75,small:.3,tiny:.2}

function modeFor(state:string):OrbMode{
 if(state==='listening')return 'listen'
 if(state==='speaking')return 'speak'
 if(state==='processing'||state==='thinking')return 'think'
 if(['paused','error','reconnecting','completed','muted'].includes(state))return 'rest'
 return 'idle'
}

// The glass listening orb. Three.js loads on first use and the render loop runs
// only while the orb is on screen and the tab is visible.
export default function Sphere({size='large',state='ready',level=0,playbackLevel=0,analysers}:{size?:Size;state?:string;level?:number;playbackLevel?:number;analysers?:Analysers}){
 const canvas=useRef<HTMLCanvasElement>(null),orb=useRef<Orb|null>(null),[ready,setReady]=useState(false),[failed,setFailed]=useState(false)
 const input=useRef({state,level,playbackLevel,analysers})
 input.current={state,level,playbackLevel,analysers}
 useEffect(()=>{
  const element=canvas.current
  if(!element)return
  let cancelled=false,visible=false,frame=0
  const sync=()=>{
   const current=input.current,mode=modeFor(current.state)
   const analyser=mode==='listen'?current.analysers?.current?.mic??null:mode==='speak'?current.analysers?.current?.playback??null:null
   orb.current?.update({mode,analyser,level:mode==='speak'?current.playbackLevel:current.level})
   frame=requestAnimationFrame(sync)
  }
  const activate=()=>orb.current?.setActive(visible&&!document.hidden)
  const view=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;activate()})
  const resize=new ResizeObserver(()=>orb.current?.resize())
  import('./orb/engine').then(({createOrb})=>{
   if(cancelled)return
   try{orb.current=createOrb(element,{density:density[size]})}catch{setFailed(true);return}
   setReady(true);view.observe(element);resize.observe(element);sync();activate()
  }).catch(()=>{if(!cancelled)setFailed(true)})
  document.addEventListener('visibilitychange',activate)
  return()=>{cancelled=true;cancelAnimationFrame(frame);view.disconnect();resize.disconnect();document.removeEventListener('visibilitychange',activate);orb.current?.dispose();orb.current=null}
 },[size])
 return <div className={`sphere-wrap sphere-${size} sphere-${state} ${ready?'orb-ready':''} ${failed?'orb-failed':''}`} aria-hidden="true">
  <canvas ref={canvas} className="orb-canvas"/>
 </div>
}
