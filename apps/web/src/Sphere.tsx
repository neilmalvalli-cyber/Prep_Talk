import {type CSSProperties} from 'react'
import LiquidGlass from './LiquidGlass'
import OrbWaveform from './OrbWaveform'
import {useTheme} from './Theme'

const ACTIVE=new Set(['listening','speaking','processing','thinking'])

export default function Sphere({size='large',state='ready',level=0,playbackLevel=0,idleWaveform=false}:{size?:'large'|'medium'|'small'|'tiny';state?:string;level?:number;playbackLevel?:number;idleWaveform?:boolean}){
 const {theme}=useTheme()
 return <div className={`sphere-wrap sphere-${size} sphere-${state}`} style={{'--audio-level':Math.max(level,playbackLevel)} as CSSProperties} aria-hidden="true">
  <div className="sphere-halo"/>
  <LiquidGlass className="sphere" shape="circle"><OrbWaveform interviewerLevel={state==='speaking'?playbackLevel:0} candidateLevel={state==='listening'?level:0} active={ACTIVE.has(state)} idleMotion={idleWaveform} dark={theme==='dark'}/><b/></LiquidGlass>
 </div>
}
