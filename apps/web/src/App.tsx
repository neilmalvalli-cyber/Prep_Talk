import LiquidGlass from './LiquidGlass'
import {ThemeToggle} from './Theme'
import {useEffect,useLayoutEffect,useRef,useState} from 'react'

import {Activity,ArrowRight,AudioLines,ChevronDown,FileText,LogOut,MicOff,Pause,Play,Settings2,ShieldCheck,UserRound,X} from 'lucide-react'

import {api,clearApiToken,errorMessage,type AppSettings,type Session} from './api'
import {authClient} from './auth'

import Sphere from './Sphere'

import Setup from './Setup'

import Interview from './Interview'

import Review from './Review'

import History from './History'

import Settings from './Settings'



type Screen='home'|'setup'|'interview'|'settings'|'history'|'report'

const initialSettings:AppSettings={provider:'groq',providers:{groq:{live_model:'openai/gpt-oss-20b',assessment_model:'openai/gpt-oss-120b',live_route:'',assessment_route:'',paid_opt_in:false},openrouter:{live_model:'',assessment_model:'',live_route:'',assessment_route:'',paid_opt_in:false},codex:{live_model:'gpt-6-luna',assessment_model:'gpt-6-luna',live_route:'',assessment_route:'',paid_opt_in:false}},revision:0}

export default function App(){

 const [screen,setScreen]=useState<Screen>('home'),[settings,setSettings]=useState(initialSettings),[session,setSession]=useState<Session|null>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[sampleOpen,setSampleOpen]=useState(false),[sampleAnswer,setSampleAnswer]=useState<'ttl'|'invalidation'>('ttl'),[authMode,setAuthMode]=useState<'sign-in'|'sign-up'>('sign-up'),[name,setName]=useState(''),[username,setUsername]=useState(''),[email,setEmail]=useState(''),[password,setPassword]=useState(''),[profileName,setProfileName]=useState(''),[profileUsername,setProfileUsername]=useState(''),[profileImage,setProfileImage]=useState(''),[authBusy,setAuthBusy]=useState(false),[profileBusy,setProfileBusy]=useState(false),[signOutBusy,setSignOutBusy]=useState(false)
 const auth=authClient.useSession(),user=auth.data?.user,authenticated=Boolean(user),checked=!auth.isPending
 const previousView=useRef<string|null>(null)
 const profileMenu=useRef<HTMLDetailsElement>(null)
 useEffect(()=>{
  const revealPicker=(event:PointerEvent|KeyboardEvent)=>{
   const select=event.target
   if(!(select instanceof HTMLSelectElement)||select.disabled||select.matches(':open')||!CSS.supports('appearance','base-select'))return
   if(event instanceof KeyboardEvent&&!['ArrowDown','ArrowUp','Enter',' '].includes(event.key))return
   const menuHeight=Math.min(360,window.innerHeight/2,select.options.length*44+14)
   if(window.innerHeight-select.getBoundingClientRect().bottom<menuHeight+12)select.scrollIntoView({block:'center',behavior:'instant'})
  }
  document.addEventListener('pointerdown',revealPicker,true)
  document.addEventListener('keydown',revealPicker,true)
  return()=>{document.removeEventListener('pointerdown',revealPicker,true);document.removeEventListener('keydown',revealPicker,true)}
 },[])
 useEffect(()=>{
  const outside=(event:PointerEvent)=>{const menu=profileMenu.current;if(menu?.open&&event.target instanceof Node&&!menu.contains(event.target))menu.open=false}
  const escape=(event:KeyboardEvent)=>{const menu=profileMenu.current;if(event.key==='Escape'&&menu?.open){menu.open=false;menu.querySelector('summary')?.focus()}}
  document.addEventListener('pointerdown',outside)
  document.addEventListener('keydown',escape)
  return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape)}
 },[])

 useLayoutEffect(()=>{clearApiToken()},[user?.id])
 useEffect(()=>{if(user){setProfileName(user.name||'');setProfileUsername(user.username||'');setProfileImage(user.image||'')}},[user?.id,user?.name,user?.username,user?.image])

 useEffect(()=>{if(authenticated)api.settings().then(setSettings).catch(e=>setError(errorMessage(e)))},[authenticated])

 useEffect(()=>{const hidden=()=>document.documentElement.classList.toggle('page-hidden',document.hidden);hidden();document.addEventListener('visibilitychange',hidden);return()=>{document.removeEventListener('visibilitychange',hidden);document.documentElement.classList.remove('page-hidden')}},[])

 useEffect(()=>{if(!sampleOpen)return;const trigger=document.activeElement as HTMLElement|null;const close=(e:KeyboardEvent)=>{if(e.key==='Escape')setSampleOpen(false);if(e.key==='Tab'){const dialog=document.querySelector('[role="dialog"]');const controls=Array.from(dialog?.querySelectorAll<HTMLElement>('button')||[]);if(e.shiftKey&&document.activeElement===controls[0]){e.preventDefault();controls.at(-1)?.focus()}else if(!e.shiftKey&&document.activeElement===controls.at(-1)){e.preventDefault();controls[0]?.focus()}}};document.addEventListener('keydown',close);document.querySelector<HTMLElement>('[role="dialog"] button')?.focus();return()=>{document.removeEventListener('keydown',close);if(trigger?.isConnected)trigger.focus()}},[sampleOpen])

 function focusContent(){const heading=document.querySelector<HTMLElement>('main h1');if(heading){heading.tabIndex=-1;heading.focus()}}

 useEffect(()=>{if(!checked)return;const view=`${screen}:${authenticated}`;const previous=previousView.current;previousView.current=view;if(previous===null||previous===view)return;focusContent()},[screen,authenticated,checked])

 const go=(value:Screen)=>{setScreen(value);setError('');setMessage('');window.scrollTo(0,0)}
 const startSetup=()=>{if(!authenticated)setAuthMode('sign-up');go('setup')}

 async function submitAuth(e:React.FormEvent){e.preventDefault();if(authBusy)return;setAuthBusy(true);setError('');try{const result=authMode==='sign-up'?await authClient.signUp.email({name,email,password,username}):await authClient.signIn.email({email,password});if(result.error)throw new Error(result.error.message);setPassword('')}catch(e){setError(errorMessage(e))}finally{setAuthBusy(false)}}
 async function saveProfile(e:React.FormEvent){e.preventDefault();if(profileBusy)return;setProfileBusy(true);setError('');try{const result=await authClient.updateUser({name:profileName,username:profileUsername,image:profileImage||null});if(result.error)throw new Error(result.error.message);await auth.refetch();setMessage('Profile saved.')}catch(e){setError(errorMessage(e))}finally{setProfileBusy(false)}}
 async function signOut(){if(signOutBusy)return;clearApiToken();setSignOutBusy(true);setError('');try{const result=await authClient.signOut();if(result.error)throw new Error(result.error.message);setName('');setUsername('');setEmail('');setPassword('');setProfileName('');setProfileUsername('');setProfileImage('');setSession(null);setAuthMode('sign-up');setScreen('home');setMessage('You are signed out.')}catch(e){setError(errorMessage(e))}finally{setSignOutBusy(false)}}

 function open(s:Session){setSession(s);go('interview')}

 function review(s:Session){setSession(s);go('report')}

 if(!checked)return <main className="auth-screen"><p role="status">Checking your account…</p></main>

 if(!authenticated&&screen!=='home')return <main className="auth-screen"><div className="auth-theme"><ThemeToggle/></div><form className="auth-card" onSubmit={submitAuth}><h1>{authMode==='sign-up'?'Create your Fieldnote account':'Sign in to Fieldnote'}</h1><p>{authMode==='sign-up'?'Create an account to set up interviews and return to your saved sessions.':'Continue to your saved interviews and settings.'}</p>{authMode==='sign-up'&&<><label className="field-label">Name<input name="name" value={name} onChange={e=>setName(e.target.value)} autoComplete="name" maxLength={80} required/></label><label className="field-label">Username<input name="username" value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" spellCheck={false} minLength={3} maxLength={30} required/><small>Use 3–30 letters, numbers or underscores.</small></label></>}<label className="field-label">Email<input name="email" type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" spellCheck={false} required/></label><label className="field-label">Password<input name="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete={authMode==='sign-up'?'new-password':'current-password'} minLength={8} required/></label>{error&&<p role="alert">{error}</p>}<button className="button-primary" disabled={authBusy}>{authBusy?(authMode==='sign-up'?'Creating account…':'Signing in…'):(authMode==='sign-up'?'Create account':'Sign in')}</button><button className="button-quiet" type="button" onClick={()=>{setAuthMode(authMode==='sign-up'?'sign-in':'sign-up');setError('')}}>{authMode==='sign-up'?'Already have an account? Sign in':'New to Fieldnote? Create an account'}</button><button className="button-quiet" type="button" onClick={()=>go('home')}>Back to landing page</button></form></main>

 return <div className={`app-shell screen-${screen} ${screen==='interview'?'interview-app':''}`}><button className="skip-link" onClick={focusContent}>Skip to main content</button><header className="topbar"><button className="brand" onClick={()=>go('home')}><span className="brand-mark"><AudioLines size={17}/></span><span>Fieldnote</span></button><nav aria-label="Main navigation"><button onClick={()=>{go('home');setTimeout(()=>document.getElementById('how')?.scrollIntoView({behavior:'smooth'}),0)}}>How it works</button>{authenticated&&<><button onClick={()=>go('settings')}>Settings</button><button onClick={()=>go('history')}>My interviews</button></>}</nav><ThemeToggle/>{authenticated?<details ref={profileMenu} className="profile-menu"><summary aria-label="Open profile menu"><span className="profile-avatar">{user?.image?<img src={user.image} alt="" width={30} height={30}/>:<UserRound size={17}/>}</span><span>{user?.username||user?.name||'Your profile'}</span><ChevronDown size={14}/></summary><div className="profile-menu-content"><form onSubmit={saveProfile}><h2>Profile</h2><label className="field-label">Name<input name="profileName" value={profileName} onChange={e=>setProfileName(e.target.value)} autoComplete="name" maxLength={80}/></label><label className="field-label">Username<input name="profileUsername" value={profileUsername} onChange={e=>setProfileUsername(e.target.value)} autoComplete="username" spellCheck={false} minLength={3} maxLength={30}/></label><label className="field-label">Profile picture URL<input name="profileImage" type="url" value={profileImage} onChange={e=>setProfileImage(e.target.value)} placeholder="https://…"/></label><button className="button-primary" type="submit" disabled={profileBusy}>{profileBusy?'Saving…':'Save profile'}</button></form><button className="button-quiet" type="button" onClick={signOut} disabled={signOutBusy}><LogOut size={15}/>{signOutBusy?' Signing out…':' Sign out'}</button></div></details>:<button className="button-quiet" onClick={()=>{setAuthMode('sign-in');go('setup')}}>Sign in</button>}<LiquidGlass shape="pill" className="glass-nav-action"><button className="top-cta" onClick={startSetup}>{authenticated?'Set up an interview':'Create account'} <ArrowRight size={15}/></button></LiquidGlass></header>

 {error&&<div className="notice error-notice" role="alert"><span>{error}</span><button onClick={()=>setError('')}>Dismiss</button></div>}{message&&<div className="notice" role="status">{message}</div>}

  {screen==='home'&&<><main><section className="hero"><div className="hero-copy"><h1>Talk through your experience.</h1><p className="hero-lede">Rehearse a technical interview built around your resume. Speak or type, follow the questions where they lead, then review the moments worth revisiting.</p><div className="hero-actions"><button className="button-primary" onClick={startSetup}>{authenticated?'Set up an interview':'Create an account to get started'} <ArrowRight size={17}/></button><button className="button-quiet" onClick={()=>setSampleOpen(true)}><Play size={15}/> View example</button></div><p className="privacy-line"><ShieldCheck size={15}/><span>Audio stays on your local speech server. After you review and start, your selected resume text, answers, and any job description you provide go to your chosen provider. Running code sends it to a configured runner; your selected review model rates your answers and prepares feedback when the interview ends.</span> <button onClick={()=>document.getElementById('privacy')?.scrollIntoView({behavior:'smooth'})}>How your data is used</button></p></div><div className="hero-art"><div className="orb-stage"><div className="orb-caption caption-top"><span className="mini-wave"><i/><i/><i/></span><span>Interviewer, ready when you are</span></div><Sphere idleWaveform/><div className="sample-question"><span className="question-mark">“</span><p>Tell me about a decision you made that changed how your team worked.</p><span className="sample-label">Example interview question</span></div><div className="orb-caption caption-bottom"><span className="tiny-line"/> Listening starts only when you do</div></div></div></section>

  <section className="workflow" id="how"><div className="section-heading"><h2>Practice from your own work.</h2></div><div className="steps"><article><div className="step-icon"><FileText size={19}/></div><h3>Start with your experience</h3><p>Review the resume details you want to discuss. Choose a role and set the pace.</p></article><article><div className="step-icon"><AudioLines size={19}/></div><h3>Follow the thread</h3><p>Questions respond to your answers, clarify details, and make room to think.</p></article><article><div className="step-icon"><Activity size={19}/></div><h3>Review your practice</h3><p>Review specific moments from the conversation, correct the transcript, and shape your next practice.</p></article></div></section>

  <section className="branch-example"><div className="branch-intro"><h2>One answer shapes the next.</h2><p>Choose a reply to see how the follow-up changes with the technical detail.</p></div><div className="branch-flow"><div className="chat-bubble interviewer-bubble"><span>Interviewer</span><p>“We cached product details to reduce repeat reads.” How did you keep the displayed price current after an update?</p></div><div className="sample-choices" role="group" aria-label="Choose a sample answer"><button type="button" aria-pressed={sampleAnswer==='ttl'} onClick={()=>setSampleAnswer('ttl')}>“We set a 30-second TTL when an entry is cached; reads do not extend it.”</button><button type="button" aria-pressed={sampleAnswer==='invalidation'} onClick={()=>setSampleAnswer('invalidation')}>“After a successful write, we delete the product key.”</button></div><div className="branch-item selected-branch" aria-live="polite"><span className="branch-node"/><p><b>Interviewer follow-up</b><span>{sampleAnswer==='ttl'?'If the price changes just after the entry is cached, how long could the old price remain visible? What freshness does the product require?':'If the database write succeeds but key deletion fails, what might a reader return? How would you detect the gap?'}</span></p></div><span className="synthetic-tag">Synthetic scenario with illustrative facts; no real interview or AI request.</span></div></section>

  <section className="privacy-section" id="privacy"><div className="privacy-icon"><ShieldCheck size={22}/></div><div><h2>Choose what you share.</h2><p>Microphone audio stays on the local speech host. Your selected resume text, interview answers, and any job description you provide go to the provider you choose after consent. Running code sends it to a configured runner; your selected review model also rates your answers and prepares feedback when the interview ends. Recording is off by default.</p></div><div className="privacy-points"><span><MicOff size={15}/> Typed answers always available</span><span><Pause size={15}/> Pause or stop any time</span><span><Settings2 size={15}/> Choose Groq, OpenRouter or OpenAI</span><span><X size={15}/> Delete a session and its local data</span></div></section>

  <section className="last-call"><div><h2>Ready for a practice round?</h2><p>A role-specific conversation, grounded in your own experience.</p></div><button className="button-primary" onClick={startSetup}>{authenticated?'Set up an interview':'Create an account to get started'} <ArrowRight size={17}/></button></section></main><footer><span>Fieldnote</span><span>Technical interview practice.</span>{authenticated&&<button onClick={()=>go('settings')}>Settings</button>}</footer></>}



 {screen==='setup'&&<Setup settings={settings} onSettings={()=>go('settings')} onStart={open}/>}

 {screen==='settings'&&<Settings settings={settings} onSave={async next=>{setSettings(await api.updateSettings(next))}} onError={setError} onMessage={setMessage}/>}

 {screen==='interview'&&session&&<Interview initial={session} onExit={()=>go('history')} onReport={review}/>}

 {screen==='history'&&<History onOpen={open} onReport={review} onStart={()=>go('setup')}/>}

 {screen==='report'&&session&&<Review session={session} onBack={()=>go('history')}/>}

  {sampleOpen&&<div className="modal-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setSampleOpen(false)}}><section className="sample-modal" role="dialog" aria-modal="true" aria-labelledby="sample-title"><button className="modal-close" onClick={()=>setSampleOpen(false)} aria-label="Close example"><X size={19}/></button><h2 id="sample-title">A follow-up in context.</h2><p className="modal-intro">Synthetic example. The interviewer responds to the candidate’s answer; nothing is sent to an AI provider.</p><div className="sample-exchange"><div className="chat-bubble interviewer-bubble"><span>Interviewer</span><p>“We cached product details to reduce repeat reads.” How did you keep the displayed price current after an update?</p></div><div className="chat-bubble candidate-bubble"><span>Candidate · synthetic</span><p>{sampleAnswer==='ttl'?'“We set a 30-second TTL when an entry is cached; reads do not extend it.”':'“After a successful write, we delete the product key.”'}</p></div><div className="chat-bubble interviewer-bubble"><span>Interviewer follow-up</span><p>{sampleAnswer==='ttl'?'If the price changes just after the entry is cached, how long could the old price remain visible? What freshness does the product require?':'If the database write succeeds but key deletion fails, what might a reader return? How would you detect the gap?'}</p></div></div><button className="button-primary" onClick={()=>{setSampleOpen(false);startSetup()}}>{authenticated?'Set up an interview':'Create an account to get started'} <ArrowRight size={16}/></button></section></div>}

 </div>

}

