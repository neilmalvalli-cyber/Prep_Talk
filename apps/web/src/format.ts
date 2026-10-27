import type {Provider} from './api'

export const stageNames:Record<string,string>={SETUP:'Setup',RESUME_ROLE_DIALOGUE:'Experience & role',CLAIM_CONFIRMATION:'Experience & role',BASELINE_INCIDENT:'Reasoning exercise',CODING:'Coding',REVIEW:'Reflection',COACHED_RETRY:'Guided practice',TRANSFER:'Transfer exercise',REPORT:'Wrap-up',COMPLETED:'Completed'}
// Order of the stages a candidate moves through; used for the progress rail.
export const stageOrder=['RESUME_ROLE_DIALOGUE','BASELINE_INCIDENT','CODING','REVIEW','COACHED_RETRY','TRANSFER','REPORT']
const roleNames:Record<string,string>={backend:'Backend Engineer',frontend:'Frontend Engineer',fullstack:'Full-stack Engineer',backend_engineer:'Backend Engineer',frontend_engineer:'Frontend Engineer',fullstack_engineer:'Full-stack Engineer'}

export const stageLabel=(stage:string)=>stageNames[stage]||stage.replaceAll('_',' ').toLowerCase()
export const roleLabel=(role:string)=>roleNames[role]||role.replaceAll('_',' ')
export const providerLabel=(provider:Provider|string)=>provider==='codex'?'OpenAI':provider==='groq'?'Groq':provider==='openrouter'?'OpenRouter':provider
export const shortDate=(seconds:number)=>new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(new Date(seconds*1000))
export const clock=(seconds:number)=>`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(Math.floor(seconds%60)).padStart(2,'0')}`
