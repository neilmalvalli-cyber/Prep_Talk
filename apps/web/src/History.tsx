import {useEffect,useState} from 'react'
import {ArrowRight,Trash2} from 'lucide-react'
import {api,errorMessage,type HistoryEntry,type Session} from './api'
import {providerLabel,roleLabel,shortDate,stageLabel} from './format'

export default function History({onOpen,onReport,onStart}:{onOpen:(s:Session)=>void;onReport:(s:Session)=>void;onStart:()=>void}){
 const [rows,setRows]=useState<HistoryEntry[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true)
 async function load(){try{setRows(await api.sessions())}catch(e){setError(errorMessage(e))}finally{setLoading(false)}}
 useEffect(()=>{load()},[])
 async function open(id:string,report=false){try{const s=await api.session(id);if(report)onReport(s);else onOpen(s)}catch(e){setError(errorMessage(e))}}
 async function remove(id:string){if(!confirm('Delete this interview, transcript, recordings, code, reports and derived local data? Provider retention remains separate.'))return;try{const result=await api.deleteSession(id);if(result.cleanup_pending)setError('Application records removed. Runner or filesystem cleanup is pending and will retry.');await load();const heading=document.querySelector<HTMLElement>('main h1');if(heading){heading.tabIndex=-1;heading.focus()}}catch(e){setError(errorMessage(e))}}
 return <main className="page">
  <header className="page-head"><div><span className="idx">(Interviews)</span><h1>Your <em>interviews.</em></h1></div><p className="lede">Resume a session or open its report. Saved interviews stay on this server until they expire or you delete them.</p></header>
  {error&&<p className="notice notice-error" role="alert">{error}</p>}
  {loading?<p className="muted" role="status">Loading interviews…</p>:rows.length?<section className="card table-card">
   <div className="table-head" aria-hidden="true"><span>Interview</span><span>Status</span><span>Started</span><span>Expires</span><span/></div>
   <ul className="session-list">{rows.map(row=><li className="session-row history-row" key={row.id}>
    <div className="session-main"><h2>{roleLabel(row.role)}</h2><span className="muted">{row.experience} · {providerLabel(row.provider)}</span></div>
    <span className={`status-pill ${row.stage==='COMPLETED'?'status-done':'status-live'}`}>{row.stage==='COMPLETED'?'Completed':row.paused?`Paused · ${stageLabel(row.stage)}`:stageLabel(row.stage)}</span>
    <span className="mono muted">{shortDate(row.created)}</span>
    <span className="mono muted">{new Date(row.expires*1000).toLocaleDateString()}</span>
    <div className="session-actions">{row.stage!=='COMPLETED'&&<button className="btn btn-line btn-sm" onClick={()=>open(row.id)}>Resume interview</button>}<button className="btn btn-ghost btn-sm" onClick={()=>open(row.id,true)}>Open report</button><button className="icon-button icon-danger" onClick={()=>remove(row.id)} aria-label="Delete interview" title="Delete interview"><Trash2 size={15}/></button></div>
   </li>)}</ul>
  </section>:<div className="empty card"><h2>No interviews yet</h2><p>Start a session to practise from your resume.</p><button className="btn btn-dark" onClick={onStart}>Set up an interview <ArrowRight size={16}/></button></div>}
 </main>
}
