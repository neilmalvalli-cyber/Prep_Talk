import {useEffect, useRef, useState, type ReactNode} from 'react'
import {ArrowLeft, ArrowRight, LoaderCircle, Pencil, RefreshCw, Square, Volume2} from 'lucide-react'
import {api, errorMessage, type Report as ReportData, type Session, type Turn} from './api'
import {roleLabel} from './format'
import {useCountUp} from './motion'
import {useVoice} from './useVoice'

const number = new Intl.NumberFormat(undefined, {maximumFractionDigits: 1})
const date = new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'})
const stageNames: Record<string, string> = {RESUME_ROLE_DIALOGUE: 'Experience & role', CODING: 'Coding discussion', REVIEW: 'Reflection', BASELINE_INCIDENT: 'Independent exercise', COACHED_RETRY: 'Guided practice', TRANSFER: 'Transfer exercise', REPORT: 'Report', COMPLETED: 'Completed'}
const readable = (value: string) => stageNames[value] || value.replaceAll('_', ' ').toLowerCase()
const verdicts = {correct: 'Correct', partial: 'Partly correct', incorrect: 'Incorrect', not_assessable: 'Not scored'}

function Count({value}: {value: number}) {
 return <>{Math.round(useCountUp(value, 1100))}</>
}

function ScoreRing({score, stale}: {score: number | null | undefined; stale: boolean}) {
 const radius = 88, circumference = 2 * Math.PI * radius
 const value = useCountUp(score == null ? 0 : Math.max(0, Math.min(100, score)), 1600)
 return <div className={`ring${stale ? ' ring-stale' : ''}`}>
  <svg viewBox="0 0 208 208" aria-hidden="true"><circle cx="104" cy="104" r={radius} className="ring-track"/><circle cx="104" cy="104" r={radius} className="ring-value" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - value / 100)}/></svg>
  <div className="ring-text">{score != null ? <><span className="ring-num">{Math.round(value)}</span><span className="mono">{stale ? 'PREVIOUS SCORE' : 'PRACTICE SCORE'}</span></> : <span className="ring-empty">—</span>}</div>
 </div>
}

function revealSection(id: string) {
 const target = document.getElementById(id)
 for (let parent: HTMLElement | null = target; parent; parent = parent.parentElement) {
  if (parent instanceof HTMLDetailsElement) parent.open = true
 }
}

function Reference({value}: {value: unknown}) {
 if (typeof value === 'string') return <p>{value}</p>
 if (Array.isArray(value)) return <ul>{value.map((item, index) => <li key={index}><Reference value={item}/></li>)}</ul>
 if (value && typeof value === 'object') return <dl>{Object.entries(value).map(([key, item]) => <div key={key}><dt>{readable(key)}</dt><dd><Reference value={item}/></dd></div>)}</dl>
 if (typeof value === 'number' || typeof value === 'boolean') return <p>{String(value)}</p>
 return null
}

function RecordGroup({title, children, id}: {title: string; children: ReactNode; id?: string}) {
 return <details className="review-record-group" id={id}><summary>{title}</summary><div className="review-record-content">{children}</div></details>
}

function questionFor(turn: Turn | undefined, turns: Turn[]) {
 if (!turn) return undefined
 return turns.slice(0, turns.findIndex(item => item.id === turn.id)).reverse().find(item => item.role === 'assistant' && item.stage === turn.stage && item.delivery === 'complete')
}

function EditedMessage({turn, version = turn.version}: {turn: Turn; version?: number}) {
 if (version <= 1) return null
 const previous = (turn.versions || []).filter(item => item.version < version).sort((a, b) => b.version - a.version)
 return <details className="review-edit-history" onPointerEnter={event => {if (event.pointerType === 'mouse') event.currentTarget.open = true}} onPointerLeave={event => {if (event.pointerType === 'mouse' && !event.currentTarget.contains(document.activeElement)) event.currentTarget.open = false}} onFocus={event => {if (event.target instanceof HTMLElement && event.target.matches(':focus-visible')) event.currentTarget.open = true}} onBlur={event => {if (!event.currentTarget.contains(event.relatedTarget as Node | null)) event.currentTarget.open = false}} onKeyDown={event => {if (event.key === 'Escape') {event.currentTarget.open = false; event.stopPropagation()}}}>
  <summary aria-label="Edited — show previous message">Edited</summary>
  <div className="review-edit-history-content"><strong>Previous message</strong>{previous.length ? <><p>{previous[0].text}</p>{previous.length > 1 && <details><summary>Earlier edits</summary>{previous.slice(1).map(item => <p key={item.version}>{item.text}</p>)}</details>}</> : <p>The previous text is unavailable in this saved transcript.</p>}</div>
 </details>
}

export default function Review({session: initial, onBack}: {session: Session; onBack: () => void}) {
 const [session, setSession] = useState(initial)
 const [report, setReport] = useState<ReportData | null>(null)
 const [error, setError] = useState('')
 const [loading, setLoading] = useState(true)
 const [notice, setNotice] = useState('')
 const [practiceBusy, setPracticeBusy] = useState(false)
 const [practiceError, setPracticeError] = useState('')
 const [editingAnswerId, setEditingAnswerId] = useState<string | null>(null)
 const [editingText, setEditingText] = useState('')
 const [editBusy, setEditBusy] = useState(false)
 const [editError, setEditError] = useState('')
 const [challengeId, setChallengeId] = useState<string | null>(null)
 const [challengeText, setChallengeText] = useState('')
 const [challengeBusy, setChallengeBusy] = useState(false)
 const [challengeError, setChallengeError] = useState('')
 const answerInput = useRef<HTMLTextAreaElement>(null)
 const challengeInput = useRef<HTMLTextAreaElement>(null)
 const automaticReviewStarted = useRef(false)
 const spokenReview = useRef<number | null>(null)
 const [speechError, setSpeechError] = useState('')
 const voice = useVoice(session, load, setSpeechError)
 const unsaved = (editingAnswerId !== null && editingText !== session.turns.find(turn => turn.id === editingAnswerId)?.text) || (challengeId !== null && challengeText.trim().length > 0)

 async function load() {
  setLoading(true)
  setError('')
  try {
   const [nextReport, nextSession] = await Promise.all([api.report(initial.id), api.session(initial.id)])
   setReport(nextReport)
   setSession(nextSession)
  } catch (failure) {setError(errorMessage(failure))}
  finally {setLoading(false)}
 }
 useEffect(() => {void load()}, [initial.id])
 useEffect(() => {
  if (!unsaved) return
  const prevent = (event: BeforeUnloadEvent) => {event.preventDefault(); event.returnValue = ''}
  window.addEventListener('beforeunload', prevent)
  return () => window.removeEventListener('beforeunload', prevent)
 }, [unsaved])
 useEffect(() => {if (editingAnswerId) {revealSection('review-transcript'); answerInput.current?.focus()}}, [editingAnswerId])
 useEffect(() => {if (challengeId) challengeInput.current?.focus()}, [challengeId])

 function discardChanges() {return !unsaved || window.confirm('Discard your unsaved changes?')}
 function editAnswer(turn: Turn) {
  if (editingAnswerId === turn.id) {revealSection('review-transcript'); answerInput.current?.focus(); return}
  if (!discardChanges()) return
  setEditingAnswerId(turn.id)
  setEditingText(turn.text)
  setEditError('')
  setChallengeId(null)
  setChallengeText('')
 }
 async function saveAnswerEdit(event: React.FormEvent) {
  event.preventDefault()
  if (!editingAnswerId) return
  if (!editingText.trim()) {setEditError('Enter an answer before saving.'); answerInput.current?.focus(); return}
  setEditBusy(true)
  setNotice('')
  setEditError('')
  try {
   setSession(await api.correctUtterance(session.id, editingAnswerId, editingText.trim(), session.revision))
   setEditingAnswerId(null)
   setEditingText('')
   setNotice('Answer saved. Previous versions are preserved.')
   await load()
  } catch (failure) {setEditError(errorMessage(failure))}
  finally {setEditBusy(false)}
 }
 async function saveChallenge(event: React.FormEvent) {
  event.preventDefault()
  if (!challengeId) return
  if (!challengeText.trim()) {setChallengeError('Describe the missing context before saving.'); challengeInput.current?.focus(); return}
  setChallengeBusy(true)
  setNotice('')
  setChallengeError('')
  try {
   setSession(await api.disputeFinding(session.id, challengeId, challengeText.trim(), session.revision))
   setChallengeId(null)
   setChallengeText('')
   setNotice('Challenge saved. The observation is marked for review.')
   await load()
  } catch (failure) {setChallengeError(errorMessage(failure))}
  finally {setChallengeBusy(false)}
 }
 async function generatePracticeReview() {
  if (practiceBusy) return
  setPracticeBusy(true)
  setNotice('')
  setPracticeError('')
  try {setSession(await api.practiceReview(session.id, session.revision)); await load(); setNotice('Practice review updated.')}
  catch (failure) {setPracticeError(errorMessage(failure))}
  finally {setPracticeBusy(false)}
 }

 useEffect(() => {
  const hasReviewableAnswers = session.turns.some(turn => turn.role === 'user' && Boolean(questionFor(turn, session.turns)?.text.includes('?')))
  if (session.stage !== 'COMPLETED' || !report || !hasReviewableAnswers || report.practice_review?.status === 'current' || automaticReviewStarted.current) return
  automaticReviewStarted.current = true
  void generatePracticeReview()
 }, [session.id, session.stage, session.revision, report?.practice_review?.status, report?.revision])

 const review = report?.practice_review
 const stale = Boolean(review && (review.status === 'stale' || report?.revision !== session.revision))
 function readFeedback() {setSpeechError(''); voice.disconnect(); void voice.connect()}
 useEffect(() => {
  if (stale || practiceBusy) {voice.disconnect(); return}
  if (session.stage !== 'COMPLETED' || !review || spokenReview.current === review.generated_at) return
  spokenReview.current = review.generated_at
  readFeedback()
 }, [session.stage, review?.generated_at, stale, practiceBusy])
 const score = review?.overall_score
 const hasAnswers = session.turns.some(turn => turn.role === 'user' && Boolean(questionFor(turn, session.turns)?.text.includes('?')))
 const answers = [...(review?.answers || [])].sort((left, right) => session.turns.findIndex(turn => turn.id === left.utterance_id) - session.turns.findIndex(turn => turn.id === right.utterance_id))
 const nextFocus = [...answers].filter(answer => answer.improvement && answer.score !== null).sort((left, right) => left.score! - right.score!)[0]
 const summary = review?.summary || (session.stage === 'COMPLETED' ? hasAnswers ? 'Your recorded answers are being reviewed for a provisional practice rating and feedback.' : 'No answer after the introduction could be reviewed. Answer an interview question to receive a rating and feedback.' : 'Generate a provisional practice rating and feedback from your recorded answers.')

 const questionsAsked = session.turns.filter(turn => turn.role === 'assistant' && turn.text.includes('?')).length
 const minutes = Math.max(1, Math.round(((session.turns.at(-1)?.created || session.created) - session.created) / 60))
 const verdictCounts = answers.reduce((counts, answer) => ({...counts, [answer.verdict]: (counts[answer.verdict] || 0) + 1}), {} as Record<string, number>)

 return <main className="page report" id="report-content">
  <div className="report-toolbar">
   <button className="link-button" type="button" onClick={() => {if (discardChanges()) onBack()}}><ArrowLeft size={15} aria-hidden="true"/>Interviews</button>
   <button className="link-button" type="button" onClick={load} disabled={loading || editBusy || challengeBusy}><RefreshCw size={14} aria-hidden="true"/>{loading ? 'Refreshing…' : 'Refresh report'}</button>
  </div>
  <header className="page-head"><div><span className="idx">(Report)</span><h1>Interview <em>report.</em></h1></div><p className="lede mono-meta">{roleLabel(session.role)} · {readable(session.experience)} · {date.format(new Date(session.created * 1000))}{session.stage !== 'COMPLETED' ? ' · in progress' : ''}</p></header>
  <p className={notice ? 'notice' : 'sr-only'} role="status">{notice}</p>
  {error && <div className="notice notice-error" role="alert"><span>{error}</span><button className="link-button" type="button" onClick={load} disabled={loading}>Retry loading report</button></div>}
  {!report ? <section className="card" aria-busy={loading}><h2>Practice review</h2><p className="muted" role="status">{loading ? 'Loading your saved report…' : 'Your report could not be loaded. Retry above.'}</p></section> : <>
   <div className="report-overview">
    <section className={`card score-card spot rv${stale ? ' is-stale' : ''}`} aria-labelledby="practice-score-title" aria-busy={practiceBusy}>
     <div className="card-head"><h2 id="practice-score-title"><span className="idx">(01)</span> {stale ? 'Previous practice score' : 'Practice score'}</h2>{review && !stale && <span className={`badge ${score != null && score >= 70 ? 'badge-good' : score != null && score >= 40 ? 'badge-warn' : ''}`}>{score == null ? 'Not scored' : score >= 70 ? 'Strong' : score >= 40 ? 'Developing' : 'Needs work'}</span>}</div>
     <ScoreRing score={score} stale={stale}/>
     {score != null && <meter className="sr-only" min={0} max={100} value={score} aria-label={stale ? 'Previous practice score, needs updating' : 'Provisional practice score'} aria-valuetext={`${number.format(score)} out of 100${stale ? ', from an earlier answer version' : ''}`}/>}
     {score == null && <p className="ring-caption">{review ? 'Not assessable yet' : hasAnswers && practiceBusy ? 'Reviewing answers…' : hasAnswers ? 'Not scored yet' : 'Not assessable'}</p>}
     <div className="stat-tiles">
      <div><b>{review ? <Count value={review.assessed_answers}/> : '—'}</b><span>Answers assessed</span></div>
      <div><b><Count value={questionsAsked}/></b><span>Questions asked</span></div>
      <div><b><Count value={report.coding_outcomes.length}/></b><span>Coding attempts</span></div>
      <div><b><Count value={minutes}/><small> min</small></b><span>Session length</span></div>
     </div>
    </section>
    <section className="card summary-card spot rv rv-d1" aria-labelledby="summary-title">
     <div className="card-head"><h2 id="summary-title"><span className="idx">(02)</span> Your review</h2>{review && <span className="mono muted">{review.model}</span>}</div>
     {stale && <p className="notice notice-warn" role="status">Your answers changed. Update the review before relying on this score.</p>}
     <div className="summary-text">{summary.split(/\n\s*\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
     {answers.length > 0 && <div className="verdict-row">{(['correct', 'partial', 'incorrect', 'not_assessable'] as const).filter(key => verdictCounts[key]).map(key => <span key={key} className={`verdict verdict-${key}`}><i/>{verdictCounts[key]} {verdicts[key].toLowerCase()}</span>)}</div>}
     <div className="summary-actions">
      {hasAnswers && <button className={review && !stale ? 'btn btn-line btn-sm' : 'btn btn-dark btn-sm'} type="button" onClick={generatePracticeReview} disabled={practiceBusy}>{practiceBusy ? <LoaderCircle size={15} className="spin" aria-hidden="true"/> : <RefreshCw size={14} aria-hidden="true"/>}{practiceBusy ? 'Reviewing answers…' : stale ? 'Update practice review' : review ? 'Review answers again' : 'Generate practice review'}</button>}
      {session.stage === 'COMPLETED' && review && !stale && <>
       <button className="btn btn-ghost btn-sm" type="button" onClick={readFeedback} disabled={voice.starting || practiceBusy}><Volume2 size={15} aria-hidden="true"/>{voice.starting ? 'Starting audio…' : 'Read feedback aloud'}</button>
       <button className="btn btn-ghost btn-sm" type="button" onClick={voice.disconnect} disabled={!voice.connected && !voice.starting}><Square size={12} aria-hidden="true"/>Stop audio</button>
       {voice.playbackBlocked && <button className="btn btn-ghost btn-sm" type="button" onClick={voice.resumePlayback}>Play audio</button>}
      </>}
     </div>
     {!hasAnswers && <p className="hint">Answer an interview question after your introduction to request a review.</p>}
     {practiceBusy && <p className="hint" role="status">The review model is rating your answers and preparing feedback. This can take a few minutes.</p>}
     {session.stage === 'COMPLETED' && review && !stale && voice.state === 'speaking' && <p className="hint" role="status">Reading your feedback aloud. Your microphone stays off.</p>}
     {practiceError && <p className="form-error" role="alert">{practiceError}</p>}
     {speechError && <p className="hint" role="alert">Audio: {speechError}</p>}
     <p className="fine-print">Provisional learning feedback · not a hiring assessment</p>
    </section>
   </div>
   {(nextFocus?.improvement || report.next_practice_action) && <aside className="next-focus rv"><div><span className="idx">{stale ? '(Previous focus)' : '(Next session)'}</span><p>{nextFocus?.improvement || report.next_practice_action}</p></div>{nextFocus && <a className="btn btn-line-light btn-sm" href={`#review-feedback-${nextFocus.utterance_id}`}>See the answer <ArrowRight size={14}/></a>}</aside>}
   <nav className="report-jumps" aria-label="Report sections"><a href="#review-feedback">Answer feedback</a><a href="#review-coding">Coding</a><a href="#review-transcript" onClick={() => revealSection('review-transcript')}>Transcript</a><a href="#review-records" onClick={() => revealSection('review-records')}>Sources</a></nav>
   <section className="section" id="review-feedback" aria-labelledby="feedback-title">
    <div className="section-head"><h2 id="feedback-title">Answer feedback</h2>{review && <span className="mono muted">{number.format(answers.length)} reviewed</span>}</div>
    {stale && <p className="hint">Feedback below refers to the answer versions reviewed previously.</p>}
    {!answers.length && <p className="empty-line">Answer-by-answer feedback appears here once the practice review finishes. Your saved transcript is below.</p>}
    <div className="feedback-list">{answers.map((answer, index) => {
     const turn = session.turns.find(item => item.id === answer.utterance_id)
     const question = questionFor(turn, session.turns)
     const reviewedText = turn?.versions?.find(version => version.version === answer.source_version)?.text || (turn?.version === answer.source_version ? turn.text : null)
     return <article className="card feedback spot rv" id={`review-feedback-${answer.utterance_id}`} key={answer.utterance_id}>
      <header className="feedback-head"><span className="idx">({String(index + 1).padStart(2, '0')})</span><span className="mono muted">{turn ? readable(turn.stage) : 'Recorded answer'}</span><span className={`verdict verdict-${answer.verdict}`}><i/>{verdicts[answer.verdict]}</span><span className="feedback-score">{answer.score === null ? '—' : <>{number.format(answer.score)}<small>/4</small></>}</span></header>
      <div className="exchange">
       <div className="exchange-q"><span className="mono">Interviewer</span><p>{question?.text || 'Question unavailable in the saved transcript.'}</p></div>
       <div className="exchange-a"><span className="mono">You</span><p>{reviewedText || answer.quote}</p>{!reviewedText && <small className="muted">Only the saved excerpt is available</small>}<div className="exchange-tools">{turn && <EditedMessage turn={turn} version={answer.source_version}/>}<span className="spacer"/>{turn && <button className="icon-button" type="button" aria-label="Edit answer" title="Edit answer" onClick={() => editAnswer(turn)} disabled={editBusy}><Pencil size={14} aria-hidden="true"/></button>}</div>{turn && turn.version > answer.source_version && <small className="muted">This review refers to your earlier answer. Update the review to include your edits.</small>}</div>
      </div>
      <div className="feedback-body"><h3>Assessment</h3><p>{answer.reason}</p></div>
      {answer.improvement && <div className="try-next"><h3>Try next</h3><p>{answer.improvement}</p></div>}
      <details className="subtle-details"><summary>Evidence quoted</summary><blockquote>{answer.quote}</blockquote></details>
     </article>
    })}</div>
   </section>
   <section className="section" id="review-coding" aria-labelledby="coding-title">
    <div className="section-head"><h2 id="coding-title">Coding</h2><span className="mono muted">{number.format(report.coding_outcomes.length)} {report.coding_outcomes.length === 1 ? 'attempt' : 'attempts'}</span></div>
    {!report.coding_outcomes.length && <p className="empty-line">No code execution was recorded. Skipped or unavailable execution is not scored as a failure.</p>}
    <div className="feedback-list">{report.coding_outcomes.map(job => <article className="card code-attempt rv" key={job.id}><header className="feedback-head"><b>{job.language === 'cpp' ? 'C++' : 'Python'}</b><span className="mono muted">{readable(job.mode)}</span><span className={`status-pill ${/fail|error|unavailable|timeout/.test(job.status) ? 'status-bad' : ['passed', 'complete', 'completed'].includes(job.status) ? 'status-done' : ''}`}>{readable(job.status)}</span>{job.execution?.result?.public_summary && <span className="mono feedback-score-sm">{number.format(job.execution.result.public_summary.passed)} / {number.format(job.execution.result.public_summary.total)} public checks</span>}</header>{job.detail && <p>{job.detail}</p>}<details className="subtle-details"><summary>Code and execution record</summary><p className="hint">Execution records cover only the tests actually run. Any AI code feedback is static reasoning unless a recorded result supports it.</p><pre className="code-out"><code>{job.source}</code></pre>{job.execution && <pre className="code-out">{JSON.stringify(job.execution, null, 2)}</pre>}</details></article>)}</div>
   </section>
   <section className="section" aria-labelledby="transcript-title"><div className="section-head"><h2 id="transcript-title">Conversation</h2><span className="mono muted">{number.format(session.turns.length)} messages</span></div><details className="card disclosure rv" id="review-transcript"><summary>Read or edit the transcript</summary>
    {!session.turns.length && <p className="empty-line">No conversation was recorded.</p>}
    <div className="transcript-review">{session.turns.map(turn => <article className={`turn turn-${turn.role === 'assistant' ? 'ai' : 'you'}`} id={`review-answer-${turn.id}`} key={turn.id}><header><span className="mono">{turn.role === 'assistant' ? 'Interviewer' : 'You'}</span><small className="mono muted">{date.format(new Date(turn.created * 1000))}</small></header>
     {editingAnswerId === turn.id ? <form className="answer-editor" onSubmit={saveAnswerEdit}><label htmlFor={`answer-edit-${turn.id}`}>Edit your answer</label><textarea id={`answer-edit-${turn.id}`} name="answer" autoComplete="off" ref={answerInput} maxLength={12000} value={editingText} onChange={event => setEditingText(event.target.value)} disabled={editBusy} aria-invalid={!!editError} aria-describedby={editError ? 'answer-edit-error' : undefined}/>{editError && <p id="answer-edit-error" role="alert" className="form-error">{editError}</p>}<div><button className="btn btn-dark btn-sm" type="submit" disabled={editBusy}>{editBusy ? 'Saving…' : 'Save answer'}</button><button className="btn btn-ghost btn-sm" type="button" disabled={editBusy} onClick={() => {if (discardChanges()) {setEditingAnswerId(null); setEditingText('')}}}>Cancel</button></div></form> : <><p>{turn.text}</p><div className="exchange-tools"><EditedMessage turn={turn}/><span className="spacer"/>{turn.role === 'user' && <button className="icon-button" type="button" aria-label="Edit answer" title="Edit answer" onClick={() => editAnswer(turn)} disabled={editBusy}><Pencil size={14} aria-hidden="true"/></button>}</div></>}
     {turn.delivery !== 'complete' && <p className="hint">Text {readable(turn.delivery)}</p>}
     {turn.speech_delivery && <details className="subtle-details"><summary>Audio delivery</summary><p className="hint">{turn.speech_delivery.status === 'estimated_complete' ? 'Playback was estimated complete; hearing is not verified.' : `Delivery ${readable(turn.speech_delivery.status)}. Generated text may not have been spoken.`}</p></details>}
    </article>)}</div>
   </details></section>
   <section className="section" aria-labelledby="records-title"><div className="section-head"><h2 id="records-title">Sources and method</h2></div><details className="card disclosure rv" id="review-records"><summary>How this report was produced</summary>
    <RecordGroup title="Review method and models"><p>{report.calibration_limitation}</p>{review && <><p className="hint">Generated {date.format(new Date(review.generated_at * 1000))} · session revision {review.source_revision}</p><ul>{review.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></>}<dl className="summary-list"><div><dt>Interview provider</dt><dd>{report.snapshot.provider === 'codex' ? 'OpenAI' : report.snapshot.provider}</dd></div><div><dt>Interview model</dt><dd translate="no">{report.snapshot.config.live_model}</dd></div><div><dt>Review model</dt><dd translate="no">{report.snapshot.config.assessment_model}</dd></div></dl></RecordGroup>
    <RecordGroup title="Topics and resume sources"><h3>Topics practised</h3><p>{report.topics_tested.length ? report.topics_tested.map(readable).join(' · ') : 'No completed answers recorded.'}</p>{report.claims.map((claim, index) => <article key={index}><h3>{claim.project || 'Confirmed experience'}</h3><p>{claim.contribution}</p><p className="hint">Source offset {claim.offset}{claim.page ? ` · page ${claim.page}` : ''}</p><blockquote>{claim.source_bullet}</blockquote><p>Measurement evidence: {claim.measurement || 'Not supplied; no achievement inferred.'}</p></article>)}</RecordGroup>
    <RecordGroup title="Observations and coverage">
     {!report.findings.length && <p>No calibrated criterion observations recorded. The practice review above is separate.</p>}
     {report.findings.map(finding => <article key={finding.id}><h3>{readable(finding.criterion)} · {readable(finding.status)}</h3><blockquote>{finding.quote || finding.evidence}</blockquote><p className="hint">Source version {finding.source_version ?? 'unavailable'} · {readable(finding.support_level)}</p>{!['stale', 'disputed'].includes(finding.status) ? <><p>{finding.inference}</p><p>{finding.coaching}</p></> : <p>Excluded from current conclusions while stale or unresolved.</p>}{challengeId === finding.id ? <form className="answer-editor" onSubmit={saveChallenge}><label htmlFor={`challenge-${finding.id}`}>Explain the missing context</label><textarea id={`challenge-${finding.id}`} name="challenge" autoComplete="off" ref={challengeInput} value={challengeText} onChange={event => setChallengeText(event.target.value)} maxLength={5000} disabled={challengeBusy} aria-invalid={!!challengeError} aria-describedby={challengeError ? 'challenge-error' : undefined}/>{challengeError && <p id="challenge-error" className="form-error" role="alert">{challengeError}</p>}<div><button type="submit" className="btn btn-dark btn-sm" disabled={challengeBusy}>{challengeBusy ? 'Saving…' : 'Save challenge'}</button><button type="button" className="btn btn-ghost btn-sm" disabled={challengeBusy} onClick={() => {if (discardChanges()) {setChallengeId(null); setChallengeText('')}}}>Cancel</button></div></form> : <button type="button" className="link-button" onClick={() => {if (discardChanges()) {setChallengeId(finding.id); setChallengeText(''); setChallengeError(''); setEditingAnswerId(null); setEditingText('')}}}>Challenge observation</button>}</article>)}
     <p>Coverage records evidence against rubric criteria; it does not establish calibrated competency ratings.</p>{report.excluded_findings > 0 && <p>{number.format(report.excluded_findings)} unsupported observation records excluded.</p>}{report.criterion_coverage.map(criterion => <article key={criterion.criterion_id}><h3>{criterion.name}</h3><p className="hint">{readable(criterion.status)} · rubric version {criterion.rubric_version}</p><p>{criterion.explanation}</p>{criterion.source_utterance_ids.length > 0 && <a href="#review-transcript" onClick={() => revealSection('review-transcript')}>Review candidate statements</a>}{criterion.source_event_ids.length > 0 && <p><a href={`#review-event-${criterion.source_event_ids[0]}`} onClick={() => revealSection(`review-event-${criterion.source_event_ids[0]}`)}>Review reasoning action</a></p>}</article>)}
    </RecordGroup>
    <RecordGroup title="Timeline" id="review-timeline">{!report.timeline.length && <p>No reasoning actions recorded.</p>}{report.timeline.map(event => <article id={`review-event-${event.id}`} tabIndex={-1} key={event.id}><h3>{readable(event.kind)}</h3><p className="hint">{readable(event.stage)} · {date.format(new Date(event.created * 1000))}</p><p>{event.text || event.detail || event.card_id || 'Saved session action'}</p></article>)}</RecordGroup>
    <RecordGroup title="Conversation coverage and open questions"><p>Conversation coverage groups recorded questions and quoted replies. It does not establish technical correctness.</p>{report.conversation_memory.status === 'unavailable' ? <p>Conversation grouping is unavailable; the full transcript remains saved.</p> : <>{report.conversation_memory.answered_points.map((point, index) => <article key={index}>{point.question_turn_ids.map(id => <p key={id}>{report.conversation_memory.questions.find(question => question.id === id)?.text}</p>)}{point.answers.map(answer => <blockquote key={`${answer.utterance_id}-${answer.quote}`}>{answer.quote}<small>Source version {answer.source_version}</small></blockquote>)}</article>)}{report.conversation_memory.unresolved_details.length > 0 && <><h3>Details to revisit</h3><ul>{report.conversation_memory.unresolved_details.map((item, index) => <li key={index}>{item.excerpt}</li>)}</ul></>}</>}<h3>Questions to revisit</h3><p className="hint">Unanswered questions and requests for clarification, repetition, help or skipping. Some questions may not have been heard.</p>{report.unresolved_questions.length ? <ul>{report.unresolved_questions.map((question, index) => <li key={index}>{question}</li>)}</ul> : <p>No such questions recorded; this does not establish technical completeness.</p>}</RecordGroup>
    <RecordGroup title="Exercise references"><p>These describe synthetic task facts, not a diagnosed weakness.</p>{report.reference_review.map(reference => <article key={reference.reference_id}><h3>{readable(reference.scenario_id)}</h3><Reference value={reference.causal_reference}/><p className="hint">Reference: {reference.reference_id}</p></article>)}{!report.reference_review.length && <p>Complete or explicitly skip the independent exercise and coding attempt to view references.</p>}</RecordGroup>
   </details></section>
  </>}
 </main>
}
