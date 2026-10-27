export type Provider = 'groq' | 'openrouter' | 'codex'
export type Language = 'python' | 'cpp'
export type Role = {role_id:string;title:string;description?:string;competencies?:string[];levels:Record<string,{expectations:string;competencies:string[];question_objectives:string[];coding_problem:string}>}
export type ResumeClaim = {source_bullet:string;page:number|null;offset:number;project:string;contribution:string;technology:string;result:string;measurement:string;confidentiality:string}
export type ResumeContext = {id:string;text:string;context:string;claims:ResumeClaim[];redaction_note?:string}
export type ProviderConfig = {live_model:string;assessment_model:string;live_route:string;assessment_route:string;paid_opt_in:boolean}
export type AppSettings = {provider:Provider;providers:Record<Provider,ProviderConfig>;revision:number}
export type Model = {id:string;name?:string;pricing?:Record<string,string>|null;supported_parameters?:string[];structured_outputs?:boolean}
export type SpeechDelivery = {status:'buffering'|'playing'|'estimated_complete'|'interrupted'|'closed'|'unavailable';generated_text_chars:number;displayed_text_chars:number;generated_audio_ms:number;estimated_played_ms:number;timing:Record<string,number>;delivery_note:string}
export type Turn = {id:string;role:string;text:string;version:number;versions?:Array<{version:number;text:string;kind:string}>;delivery:string;stage:string;created:number;generation_id?:string;support_level?:string;speech_delivery?:SpeechDelivery;timing?:Record<string,unknown>}
export type Event = {id:string;kind:string;stage:string;created:number;text?:string;detail?:string;card_id?:string;utterance_id?:string;version?:number;[key:string]:unknown}
export type Scenario = {coaching?:{lesson:string;guided_steps:string[]}|null;scenario_id?:string;title?:string;general_role_exercise:boolean;initial_facts:Array<{fact_id:string;text:string}>;available_cards:Array<{card_id:string;title:string}>;revealed_cards:Array<{card_id:string;text:string;source:string}>}
export type CodingProblem = {problem_id:string;title:string;statement:string;contract:{stdin:string;stdout:string;complexity_expectation?:string};public_tests:Array<{stdin:string;stdout:string}>}
export type Session = {id:string;revision:number;stage:string;role:string;experience:string;language:Language;paused:boolean;created:number;expires:number;duration_minutes:number;generation_id:string;turn_id:string;context:string;claims:ResumeClaim[];snapshot:{provider:Provider;config:ProviderConfig};turns:Turn[];events:Event[];scenario:Scenario|null;coding_problem:CodingProblem|null;duration_reached:boolean;last_error?:{code:string;message:string}|null;retention:'30_days'|'delete_on_close';practice_objective?:string;draft_answer?:string}
export type HistoryEntry = Pick<Session,'id'|'role'|'experience'|'stage'|'created'|'expires'|'revision'|'paused'> & {provider:Provider}
export type Execution = {id?:string;status?:string;result?:{kind?:string;public?:Array<{kind:string;stdout?:string;stderr?:string;expected_stdout?:string}>;public_summary?:{passed:number;total:number};hidden?:{passed:number;total:number};compile?:{stdout?:string;stderr?:string}}}
export type Submission = {id:string;session_id:string;language:Language;source:string;mode:'run'|'submit';status:string;detail?:string;execution?:Execution}
export type Finding = {id:string;criterion:string;status:string;rating:number|null;utterance_id?:string;source_version?:number;source_event_id?:string;quote?:string;evidence?:string;inference:string;coaching:string;support_level:string}
export type CriterionCoverage = {criterion_id:string;name:string;rubric_version:number;rating:null;status:'not_observed'|'insufficient_evidence';source_utterance_ids:string[];source_event_ids:string[];explanation:string}
export type ConversationMemory = {status:'unavailable'|'provisional_conversational_coverage';answered_points:Array<{question_turn_ids:string[];answers:Array<{utterance_id:string;source_version:number;event_id:string;quote:string}>}>;unresolved_details:Array<{question_turn_id:string;excerpt:string}>;questions:Array<{id:string;stage:string;text:string}>}
export type PracticeReview = {status:'current'|'stale';model:string;generated_at:number;source_revision:number;overall_score:number|null;assessed_answers:number;summary:string;answers:Array<{utterance_id:string;source_version:number;quote:string;score:number|null;verdict:'correct'|'partial'|'incorrect'|'not_assessable';reason:string;improvement:string}>;limitations:string[]}
export type Report = {session_id:string;revision:number;status:'pending'|'complete'|'partial'|'unavailable';findings:Finding[];criterion_coverage:CriterionCoverage[];excluded_findings:number;technical_assessment_status:string;code_review_status:string;claims:ResumeClaim[];topics_tested:string[];next_practice_action:string;timeline:Event[];turns:Turn[];coding_outcomes:Submission[];reference_review:Array<{reference_id:string;scenario_id:string;causal_reference:Record<string,unknown>;criterion_anchors?:unknown}>;unresolved_questions:string[];conversation_memory:ConversationMemory;practice_review:PracticeReview|null;calibration_limitation:string;automatic_ratings_enabled:boolean;snapshot:Session['snapshot']}
export type Readiness = {voice:{ready:boolean;status?:string;detail:string;missing?:string[]};providers:Record<Provider,{status:string;validated:boolean}>;runner:{configured:boolean};assessment:{automatic_ratings:boolean;reason:string}}
export type DeleteResult = {deleted:boolean;cleanup_pending?:boolean;session_id:string;note:string}

export class ApiError extends Error {
 constructor(message:string,readonly status:number,readonly detail?:unknown){super(message);this.name='ApiError'}
}
let cachedToken='',cachedTokenExpiry=0
export function clearApiToken(){cachedToken='';cachedTokenExpiry=0}
export async function getApiToken(){
 if(cachedToken&&Date.now()<cachedTokenExpiry-15000)return cachedToken
 const response=await fetch('/api/auth/token',{credentials:'same-origin'})
 const body=await response.json().catch(()=>undefined)
 if(!response.ok||typeof body?.token!=='string')throw new ApiError('Sign in again to continue.',response.status)
 cachedToken=body.token
 try{cachedTokenExpiry=JSON.parse(atob(cachedToken.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).exp*1000}catch{cachedTokenExpiry=Date.now()+60000}
 return cachedToken
}
async function request<T>(path:string,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers)
 headers.set('Authorization',`Bearer ${await getApiToken()}`)
 if(init.body&&!(init.body instanceof FormData))headers.set('Content-Type','application/json')
 const response=await fetch(path,{...init,headers,credentials:'same-origin'})
 const body=await response.json().catch(()=>undefined)
 if(!response.ok){const detail=body?.detail;throw new ApiError(typeof detail==='string'?detail:`Request failed (${response.status}). Reload state or review the entered values.`,response.status,detail)}
 return body as T
}
const json=(method:string,value:unknown):RequestInit=>({method,body:JSON.stringify(value)})
const mutation=(revision:number,fields:Record<string,unknown>={})=>({...fields,expected_revision:revision,idempotency_key:crypto.randomUUID()})
const sid=(id:string)=>`/api/sessions/${encodeURIComponent(id)}`
export const api={
 roles:async()=>(await request<{roles:Role[]}>('/api/roles')).roles,
 uploadResume:(file:File|string)=>{if(typeof file==='string')return request<ResumeContext>('/api/resumes',json('POST',{text:file}));const form=new FormData();form.append('file',file);return request<ResumeContext>('/api/resumes',{method:'POST',body:form})},
 deleteResume:(id:string)=>request(`/api/resumes/${encodeURIComponent(id)}`,{method:'DELETE'}),
 settings:()=>request<AppSettings>('/api/settings'),
 updateSettings:(value:AppSettings)=>request<AppSettings>('/api/settings',json('PATCH',value)),
 models:(provider:Provider)=>request<{models:Model[];fetched_at:number;pricing_note?:string}>(`/api/providers/${provider}/models`),
 routes:(model:string)=>request<{data:{endpoints:Array<{provider_name?:string;tag?:string;provider_tag?:string;supported_parameters?:string[];pricing?:unknown}>}}>(`/api/providers/openrouter/models/${encodeURIComponent(model)}/endpoints`),
 testProvider:(provider:Provider,config:ProviderConfig)=>request<{status:string;provider:Provider;detail?:string}>(`/api/providers/${provider}/test`,json('POST',config)),
 readiness:()=>request<Readiness>('/api/readiness'),
 warmVoice:()=>request<Readiness['voice']>('/api/voice/warmup',json('POST',{})),
 sessions:async()=>(await request<{sessions:HistoryEntry[]}>('/api/sessions')).sessions,
 session:(id:string)=>request<Session>(sid(id)),
 createSession:(value:unknown)=>request<Session>('/api/sessions',json('POST',value)),
 submitAnswer:(id:string,revision:number,text:string)=>request<Session>(sid(id)+'/answers',json('POST',mutation(revision,{text}))),
 action:(id:string,revision:number,action:string,fields:Record<string,unknown>={})=>request<Session|DeleteResult>(sid(id)+'/actions',json('POST',mutation(revision,{action,...fields}))),
 offer:(body:{session_id:string;sdp:string;type:'offer'})=>request<{sdp:string;type:'answer';generation_id:string}>('/api/offer',json('POST',body)),
 submitCode:(id:string,revision:number,language:Language,source:string,mode:'run'|'submit')=>request<{session:Session;submission:Submission}>(sid(id)+'/submissions',json('POST',mutation(revision,{language,source,mode}))),
 submission:(id:string)=>request<Submission>(`/api/submissions/${encodeURIComponent(id)}`),
 cancelSubmission:(id:string,jobId:string,revision:number)=>request<{session:Session;submission:Submission}>(sid(id)+`/submissions/${encodeURIComponent(jobId)}/cancel`,json('POST',mutation(revision))),
 correctUtterance:(id:string,utteranceId:string,text:string,revision:number)=>request<Session>(sid(id)+`/utterances/${encodeURIComponent(utteranceId)}`,json('PATCH',mutation(revision,{text}))),
 disputeFinding:(id:string,findingId:string,text:string,revision:number)=>request<Session>(sid(id)+`/findings/${encodeURIComponent(findingId)}/disputes`,json('POST',mutation(revision,{text}))),
 report:(id:string)=>request<Report>(sid(id)+'/report'),
 practiceReview:(id:string,revision:number)=>request<Session>(sid(id)+'/practice-review',json('POST',mutation(revision))),
 deleteSession:(id:string)=>request<DeleteResult>(sid(id),{method:'DELETE'}),
}
export const errorMessage=(error:unknown)=>error instanceof Error?error.message:'Request failed. Reload state and try again.'

