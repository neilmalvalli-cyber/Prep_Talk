import {useEffect,useState} from 'react'
import {ArrowRight,Check,FileUp,Plus,Trash2} from 'lucide-react'
import LiquidGlass from './LiquidGlass'
import {api,errorMessage,type AppSettings,type Language,type Readiness,type ResumeClaim,type ResumeContext,type Role,type Session} from './api'
import Sphere from './Sphere'

const levels=[['junior','Junior / student'],['intermediate','Intermediate']] as const
const durations=[15,25,40,60]
const languages=[['python','Python 3.11'],['cpp','C++20']] as const
const optionalFields={technology:'Technology or decision',result:'Result',measurement:'How you measured it',confidentiality:'Details to keep private'} as const

export default function Setup({settings,onSettings,onStart}:{settings:AppSettings;onSettings:()=>void;onStart:(s:Session)=>void}){
 const [roles,setRoles]=useState<Role[]>([]),[ready,setReady]=useState<Readiness|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 const [resume,setResume]=useState<ResumeContext|null>(null),[text,setText]=useState(''),[context,setContext]=useState(''),[claims,setClaims]=useState<ResumeClaim[]>([]),[fileName,setFileName]=useState('')
 const [role,setRole]=useState('backend_engineer'),[experience,setExperience]=useState('junior'),[language,setLanguage]=useState<Language>('python'),[duration,setDuration]=useState(25),[job,setJob]=useState(''),[consent,setConsent]=useState(false),[confirmed,setConfirmed]=useState(false),[record,setRecord]=useState(false),[retention,setRetention]=useState<'30_days'|'delete_on_close'>('30_days')
 useEffect(()=>{api.roles().then(setRoles).catch(e=>setError(errorMessage(e)));api.readiness().then(setReady).catch(e=>setError(errorMessage(e)))},[])
 const profile=roles.find(r=>r.role_id===role),level=profile?.levels[experience],config=settings.providers[settings.provider]
 const providerName=settings.provider==='codex'?'OpenAI':settings.provider==='groq'?'Groq':'OpenRouter and its approved downstream providers'
 const providerShort=settings.provider==='codex'?'OpenAI':settings.provider==='groq'?'Groq':'OpenRouter'
 const providerVerified=Boolean(ready?.providers[settings.provider].validated)
 const claimsReady=claims.length>0&&!claims.some(c=>!c.contribution.trim())
 const checklist:Array<[string,boolean]>=[['Resume details reviewed',Boolean(resume)&&confirmed&&claimsReady&&Boolean(context.trim())],['Data processing consent given',consent],[`${providerShort} connection verified`,providerVerified]]
 const canStart=!busy&&checklist.every(([,done])=>done)
 async function extract(value:File|string){setError('');setBusy(true);try{const result=await api.uploadResume(value);if(resume)await api.deleteResume(resume.id).catch(()=>{});setResume(result);setText(result.text);setContext(result.context);setClaims(result.claims);setConfirmed(false)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 function editClaim(index:number,field:keyof ResumeClaim,value:string){setClaims(rows=>rows.map((c,i)=>i===index?{...c,[field]:value}:c));setConfirmed(false)}
 async function start(){setBusy(true);setError('');try{if(!resume||!claims.length||claims.some(c=>!c.contribution.trim())||!confirmed||!consent)throw new Error('Review your resume details, then confirm the details and provider consent before starting.');const session=await api.createSession({resume_id:resume.id,context,claims,role:role.replace('_engineer',''),experience,language,duration_minutes:duration,job_text:job,cloud_consent:consent,record_audio:record,retention,idempotency_key:crypto.randomUUID()});onStart(session)}catch(e){setError(errorMessage(e))}finally{setBusy(false)}}
 return <main className="page">
  <header className="page-head"><div><span className="idx">(New interview)</span><h1>Set up your <em>interview.</em></h1></div><p className="lede">Choose the role and the experience you want to talk about. Nothing is sent to your AI provider until you start.</p></header>
  {error&&<div role="alert" className="notice notice-error">{error}</div>}
  <div className="setup-grid"><div className="setup-main">
   <section className="card setup-section rv" aria-labelledby="resume-title">
    <div className="section-label"><span className="idx">(01)</span><h2 id="resume-title">Your resume</h2></div>
    <label className={`dropzone ${busy?'is-busy':''}`}><input type="file" accept=".pdf,.txt" disabled={busy} onChange={e=>{const file=e.target.files?.[0];if(file){setFileName(file.name);extract(file)}}}/><FileUp size={20}/><span><b>{fileName||'Upload a resume'}</b><small>PDF or TXT · up to 10 MiB and 20 pages · read on this machine</small></span><span className="btn btn-line btn-sm" aria-hidden="true">Choose file</span></label>
    <div className="or-rule"><span>or paste text</span></div>
    <label className="field">Resume text<textarea className="textarea-lg" value={text} maxLength={50000} onChange={e=>{setText(e.target.value);setConfirmed(false)}} placeholder="Paste projects and responsibilities. Image-only PDFs need pasted text."/></label>
    <button className="btn btn-line" disabled={busy||!text.trim()} onClick={()=>extract(text)}>{busy?'Extracting locally…':'Review pasted text'}</button>
    {resume&&<div className="resume-review reveal-in">
     {resume.redaction_note&&<p className="hint">{resume.redaction_note}</p>}
     <label className="field">Selected context to share<textarea className="textarea-lg" value={context} maxLength={50000} onChange={e=>{setContext(e.target.value);setConfirmed(false)}}/><small>Remove unrelated personal information, confidential details and anything you do not want to discuss.</small></label>
     <div className="claims">
      <div className="claims-head"><h3>Experience to discuss</h3><span className="mono muted">{claims.length} {claims.length===1?'entry':'entries'}</span></div>
      <p className="hint">Suggested from your resume text. Check them for missing or misplaced details.</p>
      {!claims.length&&<p className="hint">No experience entries found. Add one below, or edit the pasted text and review it again.</p>}
      {claims.map((claim,i)=><details className="claim" key={i}><summary><span className="claim-index mono">{String(i+1).padStart(2,'0')}</span><span className="claim-title"><b>{claim.project||'Experience'}</b><small>{claim.contribution?claim.contribution.slice(0,140)+(claim.contribution.length>140?'…':''):'Add what you worked on'}</small></span></summary>
       <div className="claim-body">
        <label className="field">Project or activity<input value={claim.project} maxLength={500} onChange={e=>editClaim(i,'project',e.target.value)} placeholder="Name of the project, role or activity"/></label>
        <label className="field">What you did<textarea rows={4} value={claim.contribution} maxLength={5000} onChange={e=>editClaim(i,'contribution',e.target.value)}/></label>
        <details className="subtle-details"><summary>Optional details</summary><p className="hint">Leave anything blank that your resume does not establish.</p><div className="field-pair">{(Object.keys(optionalFields) as Array<keyof typeof optionalFields>).map(field=><label className="field" key={field}>{optionalFields[field]}<input value={claim[field]} maxLength={field==='technology'?1000:2000} onChange={e=>editClaim(i,field,e.target.value)}/></label>)}</div></details>
        {claim.source_bullet&&<details className="subtle-details"><summary>Resume source{claim.page?` · page ${claim.page}`:''}</summary><blockquote>{claim.source_bullet}</blockquote></details>}
        <button className="btn btn-ghost btn-sm" onClick={()=>{setClaims(rows=>rows.filter((_,j)=>j!==i));setConfirmed(false)}}><Trash2 size={14}/>Remove entry</button>
       </div>
      </details>)}
      <button className="btn btn-line btn-sm" disabled={claims.length>=50} onClick={()=>{setClaims(rows=>[...rows,{source_bullet:'',page:null,offset:0,project:'',contribution:'',technology:'',result:'',measurement:'',confidentiality:''}]);setConfirmed(false)}}><Plus size={14}/>Add experience</button>
     </div>
     <label className="check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>I have reviewed these details and the resume text to be shared.</span></label>
    </div>}
   </section>
   <section className="card setup-section rv" aria-labelledby="role-title">
    <div className="section-label"><span className="idx">(02)</span><h2 id="role-title">Role and format</h2></div>
    <div className="role-cards" role="group" aria-label="Role">{roles.map(r=><button className="role-card spot" key={r.role_id} aria-pressed={role===r.role_id} onClick={()=>setRole(r.role_id)}><b>{r.title}</b><small>{r.levels[experience]?.competencies.join(', ').replaceAll('_',' ')}</small><span className="role-check"><Check size={13}/></span></button>)}</div>
    <div className="segment-row">
     <div className="segment-field"><span className="field-label" id="level-label">Experience level</span><div className="segmented" role="group" aria-labelledby="level-label">{levels.map(([value,label])=><button key={value} aria-pressed={experience===value} onClick={()=>setExperience(value)}>{label}</button>)}</div></div>
     <div className="segment-field"><span className="field-label" id="duration-label">Duration</span><div className="segmented" role="group" aria-labelledby="duration-label">{durations.map(n=><button key={n} aria-pressed={duration===n} onClick={()=>setDuration(n)}>{n} min</button>)}</div></div>
     <div className="segment-field"><span className="field-label" id="language-label">Coding language</span><div className="segmented" role="group" aria-labelledby="language-label">{languages.map(([value,label])=><button key={value} aria-pressed={language===value} onClick={()=>setLanguage(value)}>{label}</button>)}</div></div>
    </div>
    {level&&<div className="objectives"><h3>What this round covers</h3><p>{level.expectations}</p><ul>{level.question_objectives.map(objective=><li key={objective}>{objective}</li>)}</ul></div>}
    <details className="subtle-details"><summary>Add a job description (optional)</summary><label className="field">Job description<textarea className="textarea-md" maxLength={12000} value={job} onChange={e=>setJob(e.target.value)} placeholder="Paste the posting to steer questions toward it."/></label></details>
   </section>
   <section className="card setup-section rv" aria-labelledby="privacy-title">
    <div className="section-label"><span className="idx">(03)</span><h2 id="privacy-title">Privacy and retention</h2></div>
    <ul className="data-flow">
     <li><b>Stays on this machine</b><span>Raw microphone audio, resume extraction and speech processing. Recording is off unless you turn it on.</span></li>
     <li><b>Sent to {providerName}</b><span>Your selected resume text and transcript{settings.provider==='codex'?', using the account signed in on the API host and its subscription allowance':', on the selected models and routes'}.{settings.provider!=='codex'&&' At topic boundaries the assessment model may group conversation points, which can incur cost.'}</span></li>
     <li><b>At the end</b><span>The review model rates your recorded answers and submitted code for provisional practice feedback. Code you run goes to the separate runner when one is configured.</span></li>
     <li><b>Deletion</b><span>Deleting locally does not delete data held by the provider. Machine administrators can access local files.</span></li>
    </ul>
    <div className="field-pair">
     <label className="field">Local retention<select value={retention} onChange={e=>setRetention(e.target.value as typeof retention)}><option value="30_days">Keep until {new Date(Date.now()+30*86400000).toLocaleDateString()} (30 days)</option><option value="delete_on_close">Delete when the interview ends</option></select></label>
    </div>
    <label className="check"><input type="checkbox" checked={record} onChange={e=>setRecord(e.target.checked)}/><span>Keep a local recording of my microphone for this session (optional)</span></label>
    <label className="check"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/><span>I consent to my selected resume text and transcript being processed by {providerName}{settings.provider==='codex'?' through the signed-in subscription account':' on the selected provider and routes'}, and to an end-of-interview practice rating using my saved answers and submitted code.</span></label>
   </section>
  </div>
  <aside className="setup-aside rv rv-d1"><LiquidGlass className="summary-glass"><div className="summary">
   <div className="summary-head"><Sphere size="small"/><div><span className="idx">(Session)</span><h2>{profile?.title||'Interview'}</h2><p className="muted">{levels.find(([v])=>v===experience)?.[1]} · {duration} min · {language==='python'?'Python':'C++'}</p></div></div>
   <dl className="summary-list">
    <div><dt>Provider</dt><dd>{providerShort}</dd></div>
    <div><dt>Interview model</dt><dd translate="no">{config.live_model||'Not selected'}</dd></div>
    <div><dt>Review model</dt><dd translate="no">{config.assessment_model||'Not selected'}</dd></div>
    {settings.provider==='openrouter'&&<div><dt>Routes</dt><dd>{config.live_route||'unset'} / {config.assessment_route||'unset'}</dd></div>}
    <div><dt>Local voice</dt><dd>{ready?ready.voice.ready?'Ready':'Unavailable — type answers':'Checking…'}</dd></div>
    <div><dt>Recording</dt><dd>{record?'On':'Off'}</dd></div>
   </dl>
   <ul className="checklist" aria-label="Before you start">{checklist.map(([label,done])=><li key={label} className={done?'done':''}><span className="check-dot">{done&&<Check size={11}/>}</span>{label}</li>)}</ul>
   {!providerVerified&&ready&&<button className="btn btn-line btn-block btn-sm" onClick={onSettings}>Verify provider in settings</button>}
   <button className="btn btn-dark btn-block" disabled={!canStart} onClick={start}>{busy?'Preparing…':'Start interview'}<ArrowRight size={16}/></button>
   <p className="hint">Voice starts with the interview. Your browser may ask for microphone access; you can always type.</p>
  </div></LiquidGlass></aside></div>
 </main>
}
