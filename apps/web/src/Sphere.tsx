import {type CSSProperties} from 'react'
import LiquidGlass from './LiquidGlass'
import OrbWaveform from './OrbWaveform'
export default function Sphere({small=false,state='ready',level=0,playbackLevel=0,idleWaveform=false}:{small?:boolean;state?:string;level?:number;playbackLevel?:number;idleWaveform?:boolean}){
 return <div className={`sphere-wrap ${small?'sphere-small':''} sphere-${state}`} style={{'--audio-level':level} as CSSProperties} aria-hidden="true"><LiquidGlass className="sphere" shape="circle"><OrbWaveform speaking={state==='speaking'} level={playbackLevel} idleMotion={idleWaveform}/><b/></LiquidGlass><div className="sphere-halo"/></div>
}
