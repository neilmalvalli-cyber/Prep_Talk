import LiquidGlass from './LiquidGlass'
import {lazy,Suspense,useEffect,useRef,useState} from 'react'
import {api,errorMessage,getApiToken,type Language,type Session,type Submission} from './api'
import Sphere from './Sphere'
import Logo from './Logo'
import {ThemeScope} from './Theme'
import {Mic,MicOff,Check,Pause,Play,Square,RotateCcw,Send,Volume2,Pencil,SkipForward,ArrowRight,FileText} from 'lucide-react'
import {useVoice,type VoiceState} from './useVoice'
import {clock,providerLabel,roleLabel,stageLabel,stageOrder} from './format'
const LocalEditor=lazy(()=>import('./editor'))

const labels:Record<VoiceState,string>={ready:'Ready when you are',listening:'Listening',muted:'Microphone off · type your answer',processing:'Preparing a question',speaking:'Interviewer speaking',thinking:'Take your time',paused:'Interview paused',reconnecting:'Reconnecting',error:'Voice unavailable · typing still works',completed:'Interview complete'}
const exerciseStages=['BASELINE_INCIDENT','COACHED_RETRY','TRANSFER']
type Tab='conversation'|'exercise'|'coding'|'reference'
const tabFor=(stage:string):Tab=>stage==='CODING'?'coding':exerciseStages.includes(stage)?'exercise':['REVIEW'].includes(stage)?'reference':'conversation'

function ExecutionResult({submission}:{submission:Submission}){
 const result=submission.execution?.result
 const summary=result?.public_summary
 return <div className="run-result" role="status">
  <div className="run-head"><span className={`status-pill ${['passed','complete','completed'].includes(submission.status)?'status-done':/fail|error|unavailable|timeout|cancel/.test(submission.status)?'status-bad':'status-live'}`}>{submission.status.replaceAll('_',' ')}</span>{summary&&<span className="mono">{summary.passed} / {summary.total} public checks</span>}{result?.hidden&&<span className="mono muted">{result.hidden.passed} / {result.hidden.total} hidden</span>}</div>
  {submission.detail&&<p>{submission.detail}</p>}
  {result?.compile?.stderr&&<pre className="code-out">{result.compile.stderr}</pre>}
  {result?.public?.map((test,i)=><details key={i} className="subtle-details"><summary>Example {i+1} · {test.kind.replaceAll('_',' ')}</summary>{test.stdout!=null&&<><span className="mono muted">Output</span><pre className="code-out">{test.stdout||'(empty)'}</pre></>}{test.expected_stdout!=null&&<><span className="mono muted">Expected</span><pre className="code-out">{test.expected_stdout}</pre></>}{test.stderr&&<><span className="mono muted">Errors</span><pre className="code-out">{test.stderr}</pre></>}</details>)}
  {submission.execution&&<details className="subtle-details"><summary>Raw execution record</summary><pre className="code-out">{JSON.stringify(submission.execution,null,2)}</pre></details>}
 </div>
}

export default function Interview({initial,onExit,onReport}:{initial:Session;onExit:()=>void;onReport:(session:Session)=>void}){
 const [session,setSession]=useState(initial),[error,setError]=useState(''),[requestBusy,setBusy]=useState(false),[answer,setAnswer]=useState(initial.draft_answer||''),[editingAnswerId,setEditingAnswerId]=useState<string|null>(null),[editingText,setEditingText]=useState(''),[editBusy,setEditBusy]=useState(false),[tab,setTab]=useState<Tab>(tabFor(initial.stage))
 const [hypothesis,setHypothesis]=useState(''),[conclusion,setConclusion]=useState(''),[objective,setObjective]=useState(initial.practice_objective||''),[elapsed,setElapsed]=useState(0)
 const [language,setLanguage]=useState<Language>(initial.language),[drafts,setDrafts]=useState<Record<Language,string>>({python:'def solve():\n    # Write your solution here\n    pass\n\nif __name__ == "__main__":\n    solve()\n',cpp:'#include <iostream>\n\nint main() {\n    // Write your solution here.\n    return 0;\n}\n'}),[submission,setSubmission]=useState<Submission|null>(null),[review,setReview]=useState<string[]>([])
 const transcript=useRef<HTMLDivElement>(null),followTranscript=useRef(true)
 useEffect(()=>{const panel=transcript.current;if(panel&&followTranscript.current)panel.scrollTop=panel.scrollHeight},[session.turns])
 const previousStage=useRef(session.stage)
 useEffect(()=>{if(previousStage.current===session.stage)return;previousStage.current=session.stage;setHypothesis('');setConclusion('');setTab(tabFor(session.stage));const heading=document.querySelector<HTMLElement>('[data-stage-heading]')||document.querySelector<HTMLElement>('.room h1');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true})}},[session.stage])
 const code=drafts[language]
 async function refresh(){try{const next=await api.session(initial.id);setSession(current=>next.revision>=current.revision?next:current)}catch(e){setError(errorMessage(e))}}
 const voice=useVoice(session,refresh,setError)
 useEffect(()=>{if(!session.paused&&session.stage!=='COMPLETED')void voice.connect()},[session.id,session.paused])
 const busy=requestBusy||voice.disconnecting||editBusy
 const live=useRef({session,voice});live.current={session,voice}
 const current=session.turns.filter(t=>t.role==='assistant').at(-1)
 const generating=session.turns.some(t=>t.delivery==='generating')
 const displayed=useRef({generation:'',characters:0,complete:false})
 useEffect(()=>{
  if(!voice.connected||!current?.generation_id||current.generation_id!==session.generation_id||!current.text.length)return
  const prior=displayed.current
  if(prior.generation!==current.generation_id){prior.generation=current.generation_id;prior.characters=0;prior.complete=false}
  const complete=current.delivery!=='generating'
  if(prior.characters===0||current.text.length-prior.characters>=64||(complete&&!prior.complete)){
   voice.send('text_displayed',{generation_id:current.generation_id,characters:current.text.length,client_time_ms:performance.timeOrigin+performance.now()})
   prior.characters=current.text.length;prior.complete=complete
  }
 },[current?.generation_id,current?.text,current?.delivery,voice.connected,session.generation_id])
 useEffect(()=>{if(session.draft_answer)setAnswer(current=>current||session.draft_answer||'')},[session.draft_answer])
 useEffect(()=>{const tick=()=>setElapsed(Math.max(0,Math.floor(Date.now()/1000-session.created)));tick();const timer=setInterval(tick,1000);return()=>clearInterval(timer)},[session.created])
 useEffect(()=>{
  const controller=new AbortController()
  const apply=(item:any)=>{
   if(item.session_id&&item.session_id!==initial.id)return
   if(['state','complete','error','voice_error'].includes(item.type)&&item.generation_id&&item.generation_id!==live.current.session.generation_id)return
   if(item.type==='delta')setSession(s=>{if(s.generation_id!==item.generation_id)return s;const existing=s.turns.find(t=>t.id===item.turn_id);const turn=existing?{...existing,text:item.text_so_far??existing.text+item.text}:{id:item.turn_id,role:'assistant',text:item.text_so_far??item.text,version:1,stage:s.stage,delivery:'generating',created:Date.now()/1000,generation_id:item.generation_id};return {...s,turns:existing?s.turns.map(t=>t.id===item.turn_id?turn:t):[...s.turns,turn]}})
   else if(item.type==='state'){if(!live.current.voice.connected)live.current.voice.setState(item.state)}
   else if(['complete','resync','connected','execution'].includes(item.type)){refresh();if(item.type==='complete'&&!live.current.voice.connected)live.current.voice.setState('ready')}
   else if(item.type==='error'){setError(item.error?.message||'Provider response incomplete. Retry explicitly or continue by typing.');refresh();live.current.voice.setState('error')}
   else if(item.type==='voice_error'){setError(item.message);live.current.voice.setState('error')}
  }
  const consume=async()=>{while(!controller.signal.aborted){try{
   const token=await getApiToken(),response=await fetch(`/api/sessions/${encodeURIComponent(initial.id)}/stream`,{headers:{Authorization:`Bearer ${token}`},signal:controller.signal})
   if(!response.ok||!response.body){setError('Live updates are unavailable. Reload saved state to continue.');return}
   const reader=response.body.getReader(),decoder=new TextDecoder();let buffer=''
   while(!controller.signal.aborted){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let boundary;while((boundary=buffer.indexOf('\n\n'))>=0){const frame=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);const data=frame.split(/\r?\n/).filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trim()).join('\n');if(!data)continue;try{apply(JSON.parse(data))}catch{setError('Live update could not be read. Reload saved state.')}}}
   if(controller.signal.aborted)return
   live.current.voice.stopPlayback();live.current.voice.setState('reconnecting');setError('Live connection interrupted. Reconnecting; audio will not replay.')
   void refresh()
  }catch{if(controller.signal.aborted)return;live.current.voice.stopPlayback();live.current.voice.setState('reconnecting');setError('Live connection interrupted. Reconnecting; audio will not replay.')}
   await new Promise(resolve=>setTimeout(resolve,1000))
   }}
  void consume();return()=>controller.abort()
 },[initial.id])
 useEffect(()=>{if(!submission||!['queued','running'].includes(submission.status))return;const timer=setInterval(()=>api.submission(submission.id).then(setSubmission).catch(e=>setError(errorMessage(e))),600);return()=>clearInterval(timer)},[submission?.id,submission?.status])
 useEffect(()=>{if(['REVIEW','COACHED_RETRY','REPORT','COMPLETED'].includes(session.stage))api.report(session.id).then(r=>setReview(r.reference_review.map(v=>JSON.stringify(v.causal_reference,null,2)))).catch(e=>setError(errorMessage(e)))},[session.stage])
 async function action(name:string,fields:Record<string,unknown>={}){
  setError('');setBusy(true)
  if(['stop','pause','keep_thinking','end','repeat','advance','skip'].includes(name))voice.stopPlayback()
  try{const result=await api.action(session.id,session.revision,name,name==='pause'?{text:answer,...fields}:fields)
   if('stage' in result){setSession(result);if(result.stage==='COMPLETED'){voice.disconnect();onReport(result)}else if(name==='keep_thinking')voice.setState('thinking');else if(name==='pause')voice.setState('paused');else if(name==='resume')voice.setState('ready')}
   else{voice.disconnect();onExit()}
  }catch(e){setError(errorMessage(e));await refresh()}finally{setBusy(false)}
 }
 async function sendAnswer(event:React.FormEvent){event.preventDefault();if(!answer.trim())return;setBusy(true);setError('');try{let state=session;if(generating){voice.stopPlayback();const stopped=await api.action(session.id,session.revision,'stop');if(!('stage' in stopped))return;state=stopped}setSession(await api.submitAnswer(state.id,state.revision,answer));setAnswer('');voice.setState('processing')}catch(e){setError(errorMessage(e));refresh()}finally{setBusy(false)}}
 async function saveAnswerEdit(event:React.FormEvent){event.preventDefault();const text=editingText.trim();if(!editingAnswerId||!text)return;setEditBusy(true);setError('');try{setSession(await api.correctUtterance(session.id,editingAnswerId,text,session.revision));setEditingAnswerId(null);setEditingText('')}catch(e){setError(errorMessage(e))}finally{setEditBusy(false)}}
 async function run(mode:'run'|'submit'){setBusy(true);setError('');try{const result=await api.submitCode(session.id,session.revision,language,code,mode);setSession(result.session);setSubmission(result.submission)}catch(e){setError(errorMessage(e));refresh()}finally{setBusy(false)}}
 async function cancelRun(){if(!submission)return;setBusy(true);setError('');try{const result=await api.cancelSubmission(session.id,submission.id,session.revision);setSession(result.session);setSubmission(result.submission)}catch(e){setError(errorMessage(e));refresh()}finally{setBusy(false)}}
 async function leave(){if(!session.paused&&session.stage!=='COMPLETED')await action('pause');voice.disconnect();onExit()}
 const state=session.paused?'paused':session.stage==='COMPLETED'?'completed':voice.state
 const synthetic=exerciseStages.includes(session.stage)
 const workspace:Tab|null=session.stage==='CODING'?'coding':synthetic?'exercise':['REVIEW','COACHED_RETRY'].includes(session.stage)?'reference':null
 const showWorkspace=tab!=='conversation'&&workspace!==null
 const stageIndex=stageOrder.indexOf(session.stage)
 const workspaceLabel={exercise:'Exercise',coding:'Code',reference:'Reference',conversation:'Conversation'}
 const questionText=current?.text||(session.turns.length?'':'Your first question will appear here.')
 const userTurns=session.turns.filter(t=>t.role==='user').length

 const controls=<LiquidGlass className={`dock ${showWorkspace?'dock-compact':''}`}>
  <div className="dock-row">
   <div className="dock-item"><button className={`cbtn ${voice.connected?'':'cbtn-off'}`} onClick={()=>voice.connected?voice.disconnectAndPause():voice.connect()} disabled={busy||voice.starting||(session.paused&&!voice.connected)} aria-label={voice.starting?'Starting voice…':voice.connected?'Disconnect and pause':'Enable voice'}>{voice.connected?<Mic size={19}/>:<MicOff size={19}/>}</button><span>{voice.starting?'Starting':voice.connected?'Voice on':'Voice off'}</span></div>
   <div className="dock-item"><button className="cbtn" aria-label="Done speaking" onClick={()=>{if(voice.connected)voice.send('done_speaking');else setError('Type and send your completed answer below.')}}><Check size={19}/></button><span>Done</span></div>
   <div className="dock-item"><button className="cbtn" aria-label="Keep thinking" onClick={()=>{voice.send('keep_thinking');if(!voice.connected)action('keep_thinking');voice.setState('thinking')}}><Pause size={19}/></button><span>Think</span></div>
   <div className="dock-item"><button className="cbtn" aria-label="Stop interviewer" onClick={()=>action('stop')}><Square size={16}/></button><span>Stop</span></div>
   <div className="dock-item"><button className="cbtn" aria-label="Repeat question" onClick={()=>action('repeat')} disabled={busy||session.paused}><RotateCcw size={18}/></button><span>Repeat</span></div>
   {voice.playbackBlocked&&<div className="dock-item"><button className="cbtn cbtn-accent" aria-label="Play audio" onClick={voice.resumePlayback}><Volume2 size={19}/></button><span>Play audio</span></div>}
  </div>
 </LiquidGlass>

 return <ThemeScope theme="dark"><main className="room" data-theme="dark">
  <header className="room-top">
   <div className="room-top-l"><Logo onClick={leave}/><span className="divider"/><span className="pill">{roleLabel(session.role)}</span><span className="pill pill-quiet">{session.experience}</span><span className="pill pill-quiet">{providerLabel(session.snapshot.provider)}</span></div>
   <div className="room-top-r"><span className="timer mono" aria-label={`Elapsed ${Math.floor(elapsed/60)} of ${session.duration_minutes} minutes`}><span className={`rec ${session.paused?'rec-paused':''}`}/>{clock(elapsed)}<span className="muted"> / {session.duration_minutes}:00</span></span><button className="btn btn-line btn-sm" onClick={()=>action(session.paused?'resume':'pause')} disabled={busy}>{session.paused?<><Play size={14}/>Resume interview</>:<><Pause size={14}/>Pause interview</>}</button><button className="btn btn-danger btn-sm" onClick={()=>action('end')} disabled={busy}><Square size={12}/>End interview</button></div>
  </header>
  <ol className="stage-rail" aria-label="Interview stages">{stageOrder.map((stage,i)=><li key={stage} className={i<stageIndex||session.stage==='COMPLETED'?'done':i===stageIndex?'current':''} aria-current={i===stageIndex?'step':undefined}><span className="mono">{String(i+1).padStart(2,'0')}</span>{stageLabel(stage)}</li>)}</ol>
  <div className="room-notices">
   {error&&error!==session.last_error?.message&&<div className="notice notice-error" role="alert"><span>{error}</span><button className="link-button" onClick={()=>{setError('');refresh()}}>Reload state</button></div>}
   {session.last_error&&<div className="notice notice-error" role="status"><span>{session.last_error.message} Your saved answer is still here; resume to continue.</span></div>}
   {voice.disconnecting&&<p className="notice" role="status">Disconnecting voice and saving the pause…</p>}
   {session.duration_reached&&<div className="notice" role="status"><span>You have reached your planned time. Take longer or wrap up; pace does not affect the review.</span><button className="link-button" onClick={()=>action('extend')}>Add 10 minutes</button><button className="link-button" onClick={()=>action('end')}>Wrap up</button></div>}
  </div>
  <div className="room-body">
   <section className="stage" aria-label="Interview">
    {workspace&&<div className="segmented stage-tabs" role="group" aria-label="Workspace"><button aria-pressed={!showWorkspace} onClick={()=>setTab('conversation')}>Conversation</button><button aria-pressed={showWorkspace} onClick={()=>setTab(workspace)}>{workspaceLabel[workspace]}</button></div>}
    {!showWorkspace?<div className="stage-center">
     <Sphere size="large" state={state} level={voice.level} playbackLevel={voice.playbackLevel}/>
     <span className={`live-status status-${state}`} role="status" aria-live="polite">{labels[state]}</span>
     <h1 className="sr-only">Your interview · {stageLabel(session.stage)}</h1>
     <p className={`question ${generating?'is-generating':''}`} aria-live="polite">{questionText}{generating&&<span className="caret" aria-hidden="true"/>}</p>
     {current?.delivery==='incomplete'&&<p className="hint">Response incomplete. {session.paused?'Resume the interview before retrying. ':''}<button className="link-button" disabled={session.paused} onClick={()=>action('retry')}>Retry</button></p>}
     {controls}
    </div>:<div className="workspace">
     <div className="interviewer-strip"><Sphere size="tiny" state={state} level={voice.level} playbackLevel={voice.playbackLevel}/><div><span className={`live-status status-${state}`}>{labels[state]}</span><p>{current?.text||'Preparing your first question…'}</p></div>{controls}</div>
     {synthetic&&tab==='exercise'&&<section className="panel">
      <span className="idx">(Exercise)</span><h2 data-stage-heading tabIndex={-1}>{session.scenario?.title}</h2>
      <p className="hint">A synthetic role exercise. These facts do not describe your own past project.</p>
      <div className="facts">{session.scenario?.initial_facts.map(f=><p key={f.fact_id}>{f.text}</p>)}</div>
      {session.scenario?.coaching&&<div className="callout"><h3>Guided practice</h3><p>{session.scenario.coaching.lesson}</p><ol>{session.scenario.coaching.guided_steps.map(step=><li key={step}>{step}</li>)}</ol></div>}
      {session.stage==='COACHED_RETRY'&&review.length>0&&<details className="subtle-details"><summary>Reference from the first exercise</summary>{review.map((text,i)=><pre className="code-out" key={i}>{text}</pre>)}</details>}
      <h3 className="sub-head">Evidence you can request</h3>
      <div className="evidence-actions">{session.scenario?.available_cards.map(card=>{const revealed=session.scenario?.revealed_cards.some(c=>c.card_id===card.card_id);return <button className={`evidence-card ${revealed?'is-revealed':''}`} key={card.card_id} disabled={busy||session.paused||revealed} onClick={()=>action('evidence',{card_id:card.card_id})}><FileText size={15}/><span>{revealed?'Revealed':'Request'}<b>{card.title}</b></span></button>})}</div>
      {!!session.scenario?.revealed_cards.length&&<div className="revealed">{session.scenario.revealed_cards.map(card=><article key={card.card_id}><span className="mono">{card.card_id.replaceAll('_',' ')}</span><p>{card.text}</p><small>{card.source}</small></article>)}</div>}
      <div className="reasoning-grid">
       <div className="field"><label htmlFor="hypothesis">Your explanation</label><textarea id="hypothesis" value={hypothesis} onChange={e=>setHypothesis(e.target.value)} placeholder="What do you think is happening, and why?"/><button className="btn btn-line btn-sm" disabled={busy||session.paused||!hypothesis.trim()} onClick={()=>action('hypothesis',{text:hypothesis})}>Save explanation</button></div>
       <div className="field"><label htmlFor="conclusion">Conclusion and how to verify it</label><textarea id="conclusion" value={conclusion} onChange={e=>setConclusion(e.target.value)} placeholder="What would you check to confirm it?"/><button className="btn btn-line btn-sm" disabled={busy||session.paused||!conclusion.trim()} onClick={()=>action('conclusion',{text:conclusion})}>Save conclusion</button></div>
      </div>
      {session.stage==='COACHED_RETRY'&&<div className="objective-row"><label className="field">Practice objective you choose<input value={objective} onChange={e=>setObjective(e.target.value)}/></label><button className="btn btn-line btn-sm" onClick={()=>action('practice_objective',{text:objective})} disabled={!objective.trim()}>Set objective</button><button className="btn btn-line btn-sm" onClick={()=>action('hint')} disabled={busy||session.paused||!session.practice_objective?.trim()}>Request a hint</button></div>}
     </section>}
     {session.stage==='CODING'&&tab==='coding'&&<section className="panel coding-panel">
      <div className="panel-head"><div><span className="idx">(Coding)</span><h2 data-stage-heading tabIndex={-1}>{session.coding_problem?.title}</h2></div><div className="segmented" role="group" aria-label="Language">{(['python','cpp'] as const).map(value=><button key={value} aria-pressed={language===value} onClick={()=>setLanguage(value)}>{value==='python'?'Python 3.11':'C++20'}</button>)}</div></div>
      <div className="problem">
       <p>{session.coding_problem?.statement}</p>
       <dl className="contract"><div><dt>Input</dt><dd>{session.coding_problem?.contract.stdin}</dd></div><div><dt>Output</dt><dd>{session.coding_problem?.contract.stdout}</dd></div>{session.coding_problem?.contract.complexity_expectation&&<div><dt>Complexity</dt><dd>{session.coding_problem.contract.complexity_expectation}</dd></div>}</dl>
       {session.coding_problem?.public_tests.map((test,i)=><details key={i} className="subtle-details"><summary>Public example {i+1}</summary><div className="example"><div><span className="mono muted">Input</span><pre className="code-out">{test.stdin}</pre></div><div><span className="mono muted">Expected</span><pre className="code-out">{test.stdout}</pre></div></div></details>)}
      </div>
      <div className="editor-frame"><Suspense fallback={<p className="editor-loading" role="status">Loading the code editor…</p>}><LocalEditor height="360px" language={language==='python'?'python':'cpp'} value={code} onChange={(v:string|undefined)=>setDrafts(current=>({...current,[language]:v||''}))}/></Suspense></div>
      <p className="hint">Tab moves between controls. Ctrl+M (Ctrl+Shift+M on macOS) switches Tab to indentation inside the editor.</p>
      <div className="code-actions"><span className="hint">Code runs on your separate, isolated runner.</span><button className="btn btn-line" onClick={()=>run('run')} disabled={busy}>Run examples</button><button className="btn btn-light" onClick={()=>run('submit')} disabled={busy}>Submit code</button></div>
      {submission&&<>{['queued','running'].includes(submission.status)&&<button className="btn btn-line btn-sm" onClick={cancelRun} disabled={busy}>Cancel execution</button>}<ExecutionResult submission={submission}/></>}
     </section>}
     {['REVIEW','COACHED_RETRY'].includes(session.stage)&&tab==='reference'&&<section className="panel">
      <span className="idx">(Reflection)</span><h2 data-stage-heading tabIndex={-1}>Exercise reference</h2>
      <p className="hint">Compare your reasoning with the authored reference, then choose what you want to practise next. No automated rating is made here.</p>
      {review.map((text,i)=><pre className="code-out" key={i}>{text}</pre>)}
      <div className="objective-row"><label className="field">Next practice objective<input value={objective} onChange={e=>setObjective(e.target.value)}/></label><button className="btn btn-line btn-sm" onClick={()=>action('practice_objective',{text:objective})} disabled={!objective.trim()}>Set objective</button></div>
     </section>}
    </div>}
    <div className="stage-footer"><button className="btn btn-ghost" onClick={()=>action('skip')} disabled={busy||session.paused}><SkipForward size={15}/>Skip this stage</button><span className="footer-spacer"/><button className="btn btn-line" onClick={()=>onReport(session)}>View report</button><LiquidGlass shape="rounded" className="glass-button"><button className="btn btn-light" onClick={()=>action('advance')} disabled={busy||session.paused}>{session.stage==='REPORT'?'Complete interview':'Continue to next stage'}<ArrowRight size={15}/></button></LiquidGlass></div>
   </section>
   <aside className="transcript" aria-label="Conversation">
    <div className="transcript-head"><h2>Transcript</h2><span className="mono muted">{userTurns} {userTurns===1?'answer':'answers'}</span></div>
    <div className="transcript-list" ref={transcript} onScroll={e=>{const panel=e.currentTarget;followTranscript.current=panel.scrollHeight-panel.scrollTop-panel.clientHeight<64}} tabIndex={0} aria-label="Conversation transcript">
     {session.turns.length===0&&<p className="transcript-empty">Your first question will appear here. Speak or type your answer.</p>}
     {session.turns.map(turn=><article className={`turn turn-${turn.role==='assistant'?'ai':'you'}`} key={turn.id}>
      <header><span className="mono">{turn.role==='assistant'?'Interviewer':'You'}</span>{turn.version>1&&<span className="mono muted">edited · v{turn.version}</span>}{turn.role==='user'&&editingAnswerId!==turn.id&&<button type="button" className="turn-edit" disabled={busy} aria-label="Edit answer" title="Edit answer" onClick={()=>{setEditingAnswerId(turn.id);setEditingText(turn.text);setError('')}}><Pencil size={13}/></button>}</header>
      {editingAnswerId===turn.id?<form className="answer-editor" onSubmit={saveAnswerEdit}><label htmlFor={`answer-edit-${turn.id}`} className="sr-only">Edit your answer</label><textarea id={`answer-edit-${turn.id}`} autoFocus maxLength={12000} value={editingText} onChange={event=>setEditingText(event.target.value)} disabled={editBusy}/><div><button className="btn btn-light btn-sm" type="submit" disabled={editBusy||!editingText.trim()}>{editBusy?'Saving…':'Save answer'}</button><button className="btn btn-ghost btn-sm" type="button" onClick={()=>{setEditingAnswerId(null);setEditingText('')}} disabled={editBusy}>Cancel</button></div></form>:<p>{turn.text}</p>}
      {['interrupted','incomplete'].includes(turn.delivery)&&<small className="muted">{turn.delivery} · the text shown may not all have been heard</small>}
      {turn.speech_delivery&&<details className="subtle-details"><summary>Audio details</summary><small>{turn.speech_delivery.status==='estimated_complete'?'Playback estimated complete; hearing is not verified.':`Audio delivery ${turn.speech_delivery.status.replaceAll('_',' ')}; repeat if needed.`}</small></details>}
      {turn.role==='user'&&turn.versions&&turn.versions.length>1&&<details className="subtle-details"><summary>Previous versions</summary>{turn.versions.slice(0,-1).map(version=><p key={version.version} className="muted">v{version.version} ({version.kind}): {version.text}</p>)}</details>}
     </article>)}
    </div>
    <form className="composer" onSubmit={sendAnswer}>
     <label htmlFor="typed-answer" className="sr-only">Type your answer</label>
     <textarea id="typed-answer" value={answer} onChange={e=>setAnswer(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();e.currentTarget.form?.requestSubmit()}}} maxLength={12000} disabled={session.paused} placeholder="Type your answer. “I don’t know” is a fine answer."/>
     <div className="composer-bar"><small className="muted">Speak or type · Ctrl+Enter to send</small><button className="btn btn-light btn-sm" type="submit" disabled={busy||session.paused||!answer.trim()} aria-label="Send answer">Send<Send size={14}/></button></div>
     {session.draft_answer&&<details className="subtle-details"><summary>Saved draft</summary><p className="muted">{session.draft_answer}</p><button type="button" className="link-button" onClick={()=>setAnswer(session.draft_answer||'')}>Use saved draft</button></details>}
    </form>
   </aside>
  </div>
 </main></ThemeScope>
}
