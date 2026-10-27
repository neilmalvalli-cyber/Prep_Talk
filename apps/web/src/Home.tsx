import {useEffect,useState} from 'react'
import {ArrowRight,ArrowUpRight} from 'lucide-react'
import {api,errorMessage,type AppSettings,type HistoryEntry,type Readiness,type Session} from './api'
import Sphere from './Sphere'
import LiquidGlass from './LiquidGlass'
import {providerLabel,roleLabel,stageLabel,shortDate} from './format'

type Props={user?:{name?:string|null;username?:string|null}|null;settings:AppSettings;onStart:()=>void;onSettings:()=>void;onHistory:()=>void;onOpen:(s:Session)=>void;onReport:(s:Session)=>void}

function greeting(){const hour=new Date().getHours();return hour<12?'Good morning':hour<18?'Good afternoon':'Good evening'}

export default function Home({user,settings,onStart,onSettings,onHistory,onOpen,onReport}:Props){
 const [ready,setReady]=useState<Readiness|null>(null),[rows,setRows]=useState<HistoryEntry[]|null>(null),[error,setError]=useState('')
 useEffect(()=>{api.readiness().then(setReady).catch(e=>setError(errorMessage(e)));api.sessions().then(setRows).catch(e=>{setRows([]);setError(errorMessage(e))})},[])
 const active=rows?.find(row=>row.stage!=='COMPLETED')
 const provider=ready?.providers[settings.provider]
 const first=(user?.name||user?.username||'').split(' ')[0]
 async function openRow(id:string,report:boolean){try{const s=await api.session(id);if(report)onReport(s);else onOpen(s)}catch(e){setError(errorMessage(e))}}
 const checks:Array<{label:string;value:string;state:'good'|'warn'|'idle';hint:string}>=[
  {label:'AI provider',value:provider?.validated?`${providerLabel(settings.provider)} connected`:provider?.status==='configured'?`${providerLabel(settings.provider)} not tested`:providerLabel(settings.provider)+' key missing',state:provider?.validated?'good':'warn',hint:provider?.validated?'Interview and review models verified.':'Run the connection test in Settings before your first interview.'},
  {label:'Local voice',value:ready?.voice.ready?'Ready':'Not available',state:ready?.voice.ready?'good':'idle',hint:ready?.voice.ready?'Speech recognition and synthesis run on this machine.':'Optional. You can type every answer.'},
  {label:'Code runner',value:ready?.runner.configured?'Connected':'Not configured',state:ready?.runner.configured?'good':'idle',hint:ready?.runner.configured?'Python and C++ run on the isolated runner.':'Optional. Coding tasks can still be written and explained.'},
 ]
 return <main className="page">
  <header className="page-head">
   <div><span className="idx">(Overview)</span><h1>{greeting()}{first?`, ${first}`:''}.<br/><em>Ready for a round?</em></h1></div>
   <p className="lede">Each interview starts from your resume, follows up on what you say, then gives you a report tied to your own answers.</p>
  </header>
  {error&&<p className="notice notice-error" role="alert">{error}</p>}
  <div className="home-grid">
   <section className="start-panel" aria-labelledby="start-title">
    <div className="start-copy">
     <span className="idx">{active?'(In progress)':'(Next session)'}</span>
     <h2 id="start-title">{active?<>Pick up your <em>{roleLabel(active.role).toLowerCase()}</em> interview.</>:<>Start a mock <em>interview.</em></>}</h2>
     <p>{active?`Paused at ${stageLabel(active.stage).toLowerCase()}. Your answers so far are saved.`:'Choose a role, review the experience you want to discuss, and talk it through. Most rounds take 15–25 minutes.'}</p>
     <div className="start-actions">{active?<><LiquidGlass shape="rounded" className="glass-button"><button className="btn btn-light" onClick={()=>openRow(active.id,false)}>Resume interview <ArrowRight size={16}/></button></LiquidGlass><button className="btn btn-line-light" onClick={()=>openRow(active.id,true)}>View progress</button></>:<LiquidGlass shape="rounded" className="glass-button"><button className="btn btn-light" onClick={onStart}>Set up an interview <ArrowRight size={16}/></button></LiquidGlass>}</div>
    </div>
    <div className="start-art"><Sphere size="medium" idleWaveform/></div>
   </section>
   <section className="card readiness" aria-labelledby="readiness-title">
    <div className="card-head"><h2 id="readiness-title">System check</h2><button className="link-button" onClick={onSettings}>Settings</button></div>
    <ul>{checks.map(check=><li key={check.label}><span className={`dot dot-${ready?check.state:'idle'}`}/><div><span className="mono">{check.label}</span><b>{ready?check.value:'Checking…'}</b><small>{check.hint}</small></div></li>)}</ul>
   </section>
  </div>
  <section className="section" aria-labelledby="recent-title">
   <div className="section-head"><h2 id="recent-title">Recent interviews</h2>{!!rows?.length&&<button className="link-button" onClick={onHistory}>View all <ArrowUpRight size={14}/></button>}</div>
   {rows===null?<p className="muted" role="status">Loading…</p>:rows.length?<ul className="session-list">{rows.slice(0,4).map(row=><li key={row.id} className="session-row">
    <div className="session-main"><b>{roleLabel(row.role)}</b><span className="muted">{row.experience} · {providerLabel(row.provider)}</span></div>
    <span className={`status-pill ${row.stage==='COMPLETED'?'status-done':'status-live'}`}>{row.stage==='COMPLETED'?'Completed':row.paused?'Paused':stageLabel(row.stage)}</span>
    <span className="mono muted session-date">{shortDate(row.created)}</span>
    <div className="session-actions">{row.stage!=='COMPLETED'&&<button className="btn btn-line btn-sm" onClick={()=>openRow(row.id,false)}>Resume</button>}<button className="btn btn-ghost btn-sm" onClick={()=>openRow(row.id,true)}>Report</button></div>
   </li>)}</ul>:<div className="empty"><p>No interviews yet. Your first report will appear here.</p><button className="btn btn-dark" onClick={onStart}>Set up an interview <ArrowRight size={16}/></button></div>}
  </section>
 </main>
}
