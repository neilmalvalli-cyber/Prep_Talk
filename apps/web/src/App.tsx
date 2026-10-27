import {useEffect,useLayoutEffect,useRef,useState} from 'react'
import {ArrowLeft,ChevronDown,LogOut,Menu,ShieldCheck,UserRound,Mic,FileText,LineChart} from 'lucide-react'
import {api,clearApiToken,errorMessage,type AppSettings,type Session} from './api'
import {authClient} from './auth'
import {ThemeToggle} from './Theme'
import Logo from './Logo'
import Sphere from './Sphere'
import Home from './Home'
import Setup from './Setup'
import Interview from './Interview'
import Review from './Review'
import History from './History'
import Settings from './Settings'
import {transition} from './motion'

type Screen='home'|'setup'|'interview'|'settings'|'history'|'report'

const initialSettings:AppSettings={provider:'groq',providers:{groq:{live_model:'openai/gpt-oss-20b',assessment_model:'openai/gpt-oss-120b',live_route:'',assessment_route:'',paid_opt_in:false},openrouter:{live_model:'',assessment_model:'',live_route:'',assessment_route:'',paid_opt_in:false},codex:{live_model:'gpt-6-luna',assessment_model:'gpt-6-luna',live_route:'',assessment_route:'',paid_opt_in:false}},revision:0}
const navItems:Array<[Screen,string]>=[['home','Overview'],['setup','New interview'],['history','Interviews'],['settings','Settings']]

export default function App(){
 const [screen,setScreen]=useState<Screen>('home'),[settings,setSettings]=useState(initialSettings),[session,setSession]=useState<Session|null>(null),[error,setError]=useState(''),[message,setMessage]=useState('')
 // The marketing page links to /#signup for new visitors.
 const [authMode,setAuthMode]=useState<'sign-in'|'sign-up'>(()=>location.hash==='#signup'?'sign-up':'sign-in'),[name,setName]=useState(''),[username,setUsername]=useState(''),[email,setEmail]=useState(''),[password,setPassword]=useState('')
 const [profileName,setProfileName]=useState(''),[profileUsername,setProfileUsername]=useState(''),[profileImage,setProfileImage]=useState(''),[authBusy,setAuthBusy]=useState(false),[profileBusy,setProfileBusy]=useState(false),[signOutBusy,setSignOutBusy]=useState(false)
 const auth=authClient.useSession(),user=auth.data?.user,authenticated=Boolean(user),checked=!auth.isPending
 const previousView=useRef<string|null>(null)
 const profileMenu=useRef<HTMLDetailsElement>(null)
 const mobileMenu=useRef<HTMLDetailsElement>(null)
 useEffect(()=>{
  // Native base-select pickers open downward; keep the menu on screen.
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
  const outside=(event:PointerEvent)=>{for(const menu of [profileMenu.current,mobileMenu.current])if(menu?.open&&event.target instanceof Node&&!menu.contains(event.target))menu.open=false}
  const escape=(event:KeyboardEvent)=>{const menu=profileMenu.current;if(event.key==='Escape'&&menu?.open){menu.open=false;menu.querySelector('summary')?.focus()}}
  document.addEventListener('pointerdown',outside)
  document.addEventListener('keydown',escape)
  return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape)}
 },[])

 useLayoutEffect(()=>{clearApiToken()},[user?.id])
 useEffect(()=>{if(user){setProfileName(user.name||'');setProfileUsername(user.username||'');setProfileImage(user.image||'')}},[user?.id,user?.name,user?.username,user?.image])
 useEffect(()=>{if(authenticated)api.settings().then(setSettings).catch(e=>setError(errorMessage(e)))},[authenticated])
 useEffect(()=>{const hidden=()=>document.documentElement.classList.toggle('page-hidden',document.hidden);hidden();document.addEventListener('visibilitychange',hidden);return()=>{document.removeEventListener('visibilitychange',hidden);document.documentElement.classList.remove('page-hidden')}},[])

 function focusContent(){const heading=document.querySelector<HTMLElement>('main h1');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true})}}
 useEffect(()=>{if(!checked)return;const view=`${screen}:${authenticated}`;const previous=previousView.current;previousView.current=view;if(previous===null||previous===view)return;focusContent()},[screen,authenticated,checked])

 const go=(value:Screen)=>transition(()=>{setScreen(value);setError('');setMessage('');window.scrollTo(0,0)})

 async function submitAuth(e:React.FormEvent){e.preventDefault();if(authBusy)return;setAuthBusy(true);setError('');try{const result=authMode==='sign-up'?await authClient.signUp.email({name,email,password,username}):await authClient.signIn.email({email,password});if(result.error)throw new Error(result.error.message);setPassword('');setScreen('home')}catch(e){setError(errorMessage(e))}finally{setAuthBusy(false)}}
 async function saveProfile(e:React.FormEvent){e.preventDefault();if(profileBusy)return;setProfileBusy(true);setError('');try{const result=await authClient.updateUser({name:profileName,username:profileUsername,image:profileImage||null});if(result.error)throw new Error(result.error.message);await auth.refetch();setMessage('Profile saved.')}catch(e){setError(errorMessage(e))}finally{setProfileBusy(false)}}
 async function signOut(){if(signOutBusy)return;clearApiToken();setSignOutBusy(true);setError('');try{const result=await authClient.signOut();if(result.error)throw new Error(result.error.message);setName('');setUsername('');setEmail('');setPassword('');setProfileName('');setProfileUsername('');setProfileImage('');setSession(null);setAuthMode('sign-in');setScreen('home');setMessage('You are signed out.')}catch(e){setError(errorMessage(e))}finally{setSignOutBusy(false)}}

 function open(s:Session){transition(()=>{setSession(s);setScreen('interview');setError('');setMessage('');window.scrollTo(0,0)})}
 function review(s:Session){transition(()=>{setSession(s);setScreen('report');setError('');setMessage('');window.scrollTo(0,0)})}

 if(!checked)return <main className="auth-screen auth-checking"><p role="status" className="mono">Checking your account…</p></main>

 if(!authenticated)return <main className="auth-screen">
  <section className="auth-form-side">
   <div className="auth-top"><Logo onClick={()=>{location.href='/'}}/><div className="auth-top-r"><a className="link-button" href="/"><ArrowLeft size={14}/>Back to home</a><ThemeToggle/></div></div>
   <form className="auth-form" key={authMode} onSubmit={submitAuth}>
    <span className="idx">{authMode==='sign-up'?'(New account)':'(Welcome back)'}</span>
    <h1>{authMode==='sign-up'?<>Create your <em>account.</em></>:<>Sign in to <em>practise.</em></>}</h1>
    <p className="lede">{authMode==='sign-up'?'Your interviews, transcripts and reports stay with your account on this server.':'Pick up where you left off: saved interviews, reports and settings.'}</p>
    {message&&<p className="notice" role="status">{message}</p>}
    {authMode==='sign-up'&&<div className="field-pair"><label className="field">Name<input name="name" value={name} onChange={e=>setName(e.target.value)} autoComplete="name" maxLength={80} required/></label><label className="field">Username<input name="username" value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" spellCheck={false} minLength={3} maxLength={30} required/><small>3–30 letters, numbers or underscores</small></label></div>}
    <label className="field">Email<input name="email" type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" spellCheck={false} required/></label>
    <label className="field">Password<input name="password" type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete={authMode==='sign-up'?'new-password':'current-password'} minLength={8} required/>{authMode==='sign-up'&&<small>At least 8 characters</small>}</label>
    {error&&<p className="form-error" role="alert">{error}</p>}
    <button className="btn btn-dark btn-block" disabled={authBusy}>{authBusy?(authMode==='sign-up'?'Creating account…':'Signing in…'):(authMode==='sign-up'?'Create account':'Sign in')}</button>
    <p className="auth-switch">{authMode==='sign-up'?'Already have an account?':'New to PrepTalk?'} <button type="button" className="link-button" onClick={()=>transition(()=>{setAuthMode(authMode==='sign-up'?'sign-in':'sign-up');setError('');setMessage('')})}>{authMode==='sign-up'?'Sign in':'Create an account'}</button></p>
   </form>
   <p className="auth-foot"><ShieldCheck size={14}/> Microphone audio is processed on your local speech server.</p>
  </section>
  <section className="auth-art" aria-hidden="true">
   <div className="auth-art-inner">
    <div className="float"><Sphere size="large" idleWaveform/></div>
    <h2>Rehearse out loud.<br/><em>Walk in ready.</em></h2>
    <ul>
     <li><FileText size={15}/><span>Questions built from your resume and target role</span></li>
     <li><Mic size={15}/><span>Answer by voice or by typing, at your own pace</span></li>
     <li><LineChart size={15}/><span>A report linked to the answers you actually gave</span></li>
    </ul>
   </div>
  </section>
 </main>

 if(screen==='interview'&&session)return <Interview initial={session} onExit={()=>go('history')} onReport={review}/>

 return <div className={`app-shell screen-${screen}`}>
  <button className="skip-link" onClick={focusContent}>Skip to main content</button>
  <header className="nav">
   <div className="nav-box">
    <Logo onClick={()=>go('home')}/>
    <nav className="nav-links" aria-label="Main navigation">{navItems.map(([target,label])=><button key={target} aria-current={screen===target||(target==='history'&&screen==='report')?'page':undefined} onClick={()=>go(target)}>{label}</button>)}</nav>
   </div>
   <div className="nav-box nav-box-r">
    <details ref={mobileMenu} className="mobile-menu"><summary aria-label="Open navigation"><Menu size={18}/></summary><nav className="mobile-panel" aria-label="Mobile navigation">{navItems.map(([target,label])=><button key={target} aria-current={screen===target?'page':undefined} onClick={()=>{if(mobileMenu.current)mobileMenu.current.open=false;go(target)}}>{label}</button>)}</nav></details>
    <ThemeToggle/>
    <details ref={profileMenu} className="profile-menu"><summary aria-label="Open profile menu"><span className="avatar">{user?.image?<img src={user.image} alt="" width={28} height={28}/>:<UserRound size={15}/>}</span><span className="profile-name">{user?.username||user?.name||'Profile'}</span><ChevronDown size={14}/></summary>
     <div className="profile-panel"><form onSubmit={saveProfile}><span className="idx">(Profile)</span><label className="field">Name<input name="profileName" value={profileName} onChange={e=>setProfileName(e.target.value)} autoComplete="name" maxLength={80}/></label><label className="field">Username<input name="profileUsername" value={profileUsername} onChange={e=>setProfileUsername(e.target.value)} autoComplete="username" spellCheck={false} minLength={3} maxLength={30}/></label><label className="field">Profile picture URL<input name="profileImage" type="url" value={profileImage} onChange={e=>setProfileImage(e.target.value)} placeholder="https://…"/></label><button className="btn btn-dark btn-block" type="submit" disabled={profileBusy}>{profileBusy?'Saving…':'Save profile'}</button></form><button className="btn btn-ghost btn-block" type="button" onClick={signOut} disabled={signOutBusy}><LogOut size={15}/>{signOutBusy?'Signing out…':'Sign out'}</button></div>
    </details>
   </div>
  </header>
  <div className="page-notices">{error&&<div className="notice notice-error" role="alert"><span>{error}</span><button className="link-button" onClick={()=>setError('')}>Dismiss</button></div>}{message&&<div className="notice" role="status"><span>{message}</span><button className="link-button" onClick={()=>setMessage('')}>Dismiss</button></div>}</div>
  {screen==='home'&&<Home user={user} settings={settings} onStart={()=>go('setup')} onSettings={()=>go('settings')} onHistory={()=>go('history')} onOpen={open} onReport={review}/>}
  {screen==='setup'&&<Setup settings={settings} onSettings={()=>go('settings')} onStart={open}/>}
  {screen==='settings'&&<Settings settings={settings} onSave={async next=>{setSettings(await api.updateSettings(next))}} onError={setError} onMessage={setMessage}/>}
  {screen==='history'&&<History onOpen={open} onReport={review} onStart={()=>go('setup')}/>}
  {screen==='report'&&session&&<Review session={session} onBack={()=>go('history')}/>}
  <footer className="foot"><span>© {new Date().getFullYear()} PrepTalk</span><span className="mono">Practice feedback · not a hiring assessment</span></footer>
 </div>
}
