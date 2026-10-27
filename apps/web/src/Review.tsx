import {useEffect, useRef, useState, type ReactNode} from 'react'
import {ArrowLeft, LoaderCircle, Pencil, RefreshCw, Square, Volume2} from 'lucide-react'
import {api, errorMessage, type Report as ReportData, type Session, type Turn} from './api'
import './review.css'
import {useVoice} from './useVoice'

const number = new Intl.NumberFormat(undefined, {maximumFractionDigits: 1})
const date = new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'})
const stageNames: Record<string, string> = {RESUME_ROLE_DIALOGUE: 'Experience & role', CODING: 'Coding discussion', REVIEW: 'Reflection', BASELINE_INCIDENT: 'Independent exercise', COACHED_RETRY: 'Guided practice', TRANSFER: 'Transfer exercise', REPORT: 'Report', COMPLETED: 'Completed'}
const readable = (value: string) => stageNames[value] || value.replaceAll('_', ' ').toLowerCase()
const verdicts = {correct: 'Correct', partial: 'Partly correct', incorrect: 'Incorrect', not_assessable: 'Not scored'}

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

 return <main className="page-content report-page" id="report-content">
  <div className="review-toolbar">
   <button className="review-text-button" type="button" onClick={() => {if (discardChanges()) onBack()}}><ArrowLeft size={16} aria-hidden="true"/>My interviews</button>
   <button className="review-text-button" type="button" onClick={load} disabled={loading || editBusy || challengeBusy}><RefreshCw size={15} aria-hidden="true"/>{loading ? 'Refreshing…' : 'Refresh report'}</button>
  </div>
  <header className="review-title"><h1>Interview report</h1><p>{readable(session.role)} · {readable(session.experience)} · {date.format(new Date(session.created * 1000))}</p></header>
  <p className="review-save-notice" role="status">{notice}</p>
  {error && <div className="review-error" role="alert"><p>{error}</p><button className="review-text-button" type="button" onClick={load} disabled={loading}>Retry loading report</button></div>}
  {!report ? <section className="review-sheet review-loading" aria-busy={loading}><h2>Practice review</h2><p role="status">{loading ? 'Loading your saved report…' : 'Your report could not be loaded. Retry above.'}</p></section> : <div className="review-sheet">
   <section className={`review-overview${stale ? ' review-is-stale' : ''}`} aria-labelledby="practice-score-title" aria-busy={practiceBusy}>
    <div className="review-score">
     <h2 id="practice-score-title">{stale ? 'Previous practice score' : 'Practice score'}</h2>
      {score != null ? <><p className="review-score-value">{number.format(score)}<span> / 100</span></p><meter min={0} max={100} value={score} aria-label={stale ? 'Previous practice score, needs updating' : 'Provisional practice score'} aria-valuetext={`${number.format(score)} out of 100${stale ? ', from an earlier answer version' : ''}`}/><div className="review-scale" aria-hidden="true"><span>0</span><span>100</span></div></> : <><p className="review-no-score">{review ? 'Not assessable yet' : hasAnswers && practiceBusy ? 'In progress' : hasAnswers ? 'Not scored yet' : 'Not assessable'}</p><div className="review-empty-track" aria-hidden="true"/></>}
     <p className="review-score-note">{review ? `${number.format(review.assessed_answers)} ${review.assessed_answers === 1 ? 'answer' : 'answers'} assessed` : 'No score has been generated.'}</p>
    </div>
    <div className="review-overview-copy">
     <h2>Your review</h2>
     {stale && <p className="review-freshness" role="status">Answers changed. Refresh the review before relying on this score.</p>}
     <div className="review-summary-text">{summary.split(/\n\s*\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
      {hasAnswers && <button className={review && !stale ? 'review-text-button review-regenerate' : 'review-primary'} type="button" onClick={generatePracticeReview} disabled={practiceBusy}>{practiceBusy ? <LoaderCircle size={16} aria-hidden="true"/> : review && !stale ? <RefreshCw size={14} aria-hidden="true"/> : null}{practiceBusy ? 'Reviewing answers…' : stale ? 'Update practice review' : review ? 'Review answers again' : 'Generate practice review'}</button>}
      {!hasAnswers && <p className="review-meta">Answer an interview question after your introduction to request a review.</p>}
      {practiceBusy && <p className="review-meta" role="status">The selected review model is rating your answers and preparing feedback. This can take a few minutes.</p>}
     {practiceError && <p className="review-error" role="alert">{practiceError}</p>}
      {session.stage === 'COMPLETED' && review && !stale && <div className="review-audio">
       <div className="review-audio-controls"><button className="review-text-button" type="button" onClick={readFeedback} disabled={voice.starting || practiceBusy}><Volume2 size={16} aria-hidden="true"/>{voice.starting ? 'Starting feedback audio…' : 'Read feedback aloud'}</button>
       <button className="review-text-button" type="button" onClick={voice.disconnect} disabled={!voice.connected && !voice.starting}><Square size={13} aria-hidden="true"/>Stop audio</button>
       {voice.playbackBlocked && <button className="review-text-button" type="button" onClick={voice.resumePlayback}>Play audio</button>}
       </div><p className="review-meta" role="status">{voice.state === 'speaking' ? 'Reading your feedback aloud.' : 'Feedback plays automatically. Your microphone stays off.'}</p>
      </div>}
      {speechError && <p className="review-error" role="alert">{speechError}</p>}
     <p className="review-meta">Provisional learning feedback · Not a hiring assessment{session.stage !== 'COMPLETED' ? ' · Interview in progress' : ''}</p>
    </div>
   </section>
   {(nextFocus?.improvement || report.next_practice_action) && <aside className="review-next-focus"><div><h2>{stale ? 'Previous practice focus' : 'Next practice'}</h2><p>{nextFocus?.improvement || report.next_practice_action}</p></div>{nextFocus && <a href={`#review-feedback-${nextFocus.utterance_id}`}>See related answer</a>}</aside>}
   <nav className="review-jumps" aria-label="Report sections"><a href="#review-feedback">Answer feedback</a><a href="#review-coding">Coding</a><a href="#review-transcript" onClick={() => revealSection('review-transcript')}>Transcript</a><a href="#review-records" onClick={() => revealSection('review-records')}>Report details</a></nav>
   <section className="review-section" id="review-feedback" aria-labelledby="feedback-title">
    <div className="review-section-heading"><h2 id="feedback-title">Answer feedback</h2>{review && <span>{number.format(answers.length)} reviewed</span>}</div>
    {stale && <p className="review-meta">Feedback below refers to the answer versions reviewed previously.</p>}
     {!answers.length && <p className="review-empty">Your answer-by-answer feedback will appear here after the practice review finishes. Your saved transcript remains available below.</p>}
    <div className="review-answer-list">{answers.map(answer => {
     const turn = session.turns.find(item => item.id === answer.utterance_id)
     const question = questionFor(turn, session.turns)
     const reviewedText = turn?.versions?.find(version => version.version === answer.source_version)?.text || (turn?.version === answer.source_version ? turn.text : null)
     return <article className="review-answer" id={`review-feedback-${answer.utterance_id}`} key={answer.utterance_id}>
      <div className="review-agent"><header><div><h3>Agent review</h3><p className="review-answer-stage">{turn ? readable(turn.stage) : 'Recorded answer'}</p></div><span className="review-answer-score">{answer.score === null ? 'Not scored' : `${number.format(answer.score)} / 4`}<small>{verdicts[answer.verdict]}</small></span></header><p>{answer.reason}</p></div>
      <div className="review-chat" aria-label="Reviewed exchange">
       <div className="review-message review-message-interviewer"><h3>Interviewer</h3><p>{question?.text || 'Question unavailable in the saved transcript.'}</p></div>
       <div className="review-message review-message-user"><h3>You</h3><p>{reviewedText || answer.quote}</p>{!reviewedText && <small>Only the saved excerpt is available</small>}<div className="review-message-footer">{turn && <EditedMessage turn={turn} version={answer.source_version}/>}<span className="review-message-spacer"/>{turn && <button className="review-edit-button" type="button" aria-label="Edit answer" title="Edit answer" onClick={() => editAnswer(turn)} disabled={editBusy}><Pencil size={15} aria-hidden="true"/></button>}</div>{turn && turn.version > answer.source_version && <small>This review refers to your earlier answer. Update the review to include your edits.</small>}</div>
      </div>
      {answer.improvement && <p className="review-improvement"><strong>Try next</strong> {answer.improvement}</p>}
      <div className="review-answer-tools"><details><summary>Review evidence</summary><blockquote>{answer.quote}</blockquote></details></div>
     </article>
    })}</div>
   </section>
   <section className="review-section" id="review-coding" aria-labelledby="coding-title">
    <div className="review-section-heading"><h2 id="coding-title">Coding</h2><span>{number.format(report.coding_outcomes.length)} {report.coding_outcomes.length === 1 ? 'attempt' : 'attempts'}</span></div>
    {!report.coding_outcomes.length && <p className="review-empty">No code execution was recorded. Skipped or unavailable execution is not scored as a failure.</p>}
    {report.coding_outcomes.map(job => <article className="review-code-attempt" key={job.id}><h3>{job.language === 'cpp' ? 'C++' : 'Python'} · {readable(job.mode)} · {readable(job.status)}</h3>{job.detail && <p>{job.detail}</p>}{job.execution?.result?.public_summary && <p>{number.format(job.execution.result.public_summary.passed)} / {number.format(job.execution.result.public_summary.total)} public checks passed</p>}<details><summary>Code & execution record</summary><p className="review-meta">Execution records cover only the tests actually run. Any AI code feedback is static reasoning unless a recorded result supports it.</p><pre><code>{job.source}</code></pre>{job.execution && <pre>{JSON.stringify(job.execution, null, 2)}</pre>}</details></article>)}
   </section>
   <section className="review-section" aria-labelledby="transcript-title"><h2 id="transcript-title">Conversation</h2><details className="review-transcript" id="review-transcript"><summary>Read or edit transcript <span>{number.format(session.turns.length)} messages</span></summary>
    {!session.turns.length && <p className="review-empty">No conversation was recorded.</p>}
    <div className="review-chat review-conversation">{session.turns.map(turn => <article className={`review-transcript-turn review-message ${turn.role === 'assistant' ? 'review-message-interviewer' : 'review-message-user'}`} id={`review-answer-${turn.id}`} key={turn.id}><header><h3>{turn.role === 'assistant' ? 'Interviewer' : 'You'}</h3><small>{date.format(new Date(turn.created * 1000))}</small></header>
     {editingAnswerId === turn.id ? <form className="answer-editor" onSubmit={saveAnswerEdit}><label htmlFor={`answer-edit-${turn.id}`}>Edit your answer</label><textarea id={`answer-edit-${turn.id}`} name="answer" autoComplete="off" ref={answerInput} maxLength={12000} value={editingText} onChange={event => setEditingText(event.target.value)} disabled={editBusy} aria-invalid={!!editError} aria-describedby={editError ? 'answer-edit-error' : undefined}/>{editError && <p id="answer-edit-error" role="alert" className="review-error">{editError}</p>}<div><button className="review-primary" type="submit" disabled={editBusy}>{editBusy ? 'Saving…' : 'Save answer'}</button><button className="review-text-button" type="button" disabled={editBusy} onClick={() => {if (discardChanges()) {setEditingAnswerId(null); setEditingText('')}}}>Cancel</button></div></form> : <><p>{turn.text}</p><div className="review-message-footer"><EditedMessage turn={turn}/><span className="review-message-spacer"/>{turn.role === 'user' && <button className="review-edit-button" type="button" aria-label="Edit answer" title="Edit answer" onClick={() => editAnswer(turn)} disabled={editBusy}><Pencil size={15} aria-hidden="true"/></button>}</div></>}
     {turn.delivery !== 'complete' && <p className="review-meta">Text {readable(turn.delivery)}</p>}
     {turn.speech_delivery && <details><summary>Audio delivery</summary><p className="review-meta">{turn.speech_delivery.status === 'estimated_complete' ? 'Playback was estimated complete; hearing is not verified.' : `Delivery ${readable(turn.speech_delivery.status)}. Generated text may not have been spoken.`}</p></details>}
    </article>)}</div>
   </details></section>
   <section className="review-section review-supporting" aria-labelledby="records-title"><h2 id="records-title">Supporting records</h2><details id="review-records"><summary>Sources & report details</summary>
    <RecordGroup title="Review method & models"><p>{report.calibration_limitation}</p>{review && <><p className="review-meta">Generated {date.format(new Date(review.generated_at * 1000))} · Session revision {review.source_revision}</p><ul>{review.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul></>}<dl><dt>Interview provider</dt><dd>{report.snapshot.provider === 'codex' ? 'OpenAI' : report.snapshot.provider}</dd><dt>Interview model</dt><dd translate="no">{report.snapshot.config.live_model}</dd><dt>Review model</dt><dd translate="no">{report.snapshot.config.assessment_model}</dd></dl></RecordGroup>
    <RecordGroup title="Topics & resume sources"><h3>Topics practiced</h3><p>{report.topics_tested.length ? report.topics_tested.map(readable).join(' · ') : 'No completed answers recorded.'}</p>{report.claims.map((claim, index) => <article key={index}><h3>{claim.project || 'Confirmed experience'}</h3><p>{claim.contribution}</p><p className="review-meta">Source offset {claim.offset}{claim.page ? ` · Page ${claim.page}` : ''}</p><blockquote>{claim.source_bullet}</blockquote><p>Measurement evidence: {claim.measurement || 'Not supplied; no achievement inferred.'}</p></article>)}</RecordGroup>
    <RecordGroup title="Observations & coverage">
     {!report.findings.length && <p>No calibrated criterion observations recorded. The practice review above is separate.</p>}
     {report.findings.map(finding => <article key={finding.id}><h3>{readable(finding.criterion)} · {readable(finding.status)}</h3><blockquote>{finding.quote || finding.evidence}</blockquote><p className="review-meta">Source version {finding.source_version ?? 'unavailable'} · {readable(finding.support_level)}</p>{!['stale', 'disputed'].includes(finding.status) ? <><p>{finding.inference}</p><p>{finding.coaching}</p></> : <p>Excluded from current conclusions while stale or unresolved.</p>}{challengeId === finding.id ? <form className="answer-editor" onSubmit={saveChallenge}><label htmlFor={`challenge-${finding.id}`}>Explain the missing context</label><textarea id={`challenge-${finding.id}`} name="challenge" autoComplete="off" ref={challengeInput} value={challengeText} onChange={event => setChallengeText(event.target.value)} maxLength={5000} disabled={challengeBusy} aria-invalid={!!challengeError} aria-describedby={challengeError ? 'challenge-error' : undefined}/>{challengeError && <p id="challenge-error" className="review-error" role="alert">{challengeError}</p>}<div><button type="submit" className="review-primary" disabled={challengeBusy}>{challengeBusy ? 'Saving…' : 'Save challenge'}</button><button type="button" className="review-text-button" disabled={challengeBusy} onClick={() => {if (discardChanges()) {setChallengeId(null); setChallengeText('')}}}>Cancel</button></div></form> : <button type="button" className="review-text-button" onClick={() => {if (discardChanges()) {setChallengeId(finding.id); setChallengeText(''); setChallengeError(''); setEditingAnswerId(null); setEditingText('')}}}>Challenge observation</button>}</article>)}
     <p>Coverage records evidence against rubric criteria; it does not establish calibrated competency ratings.</p>{report.excluded_findings > 0 && <p>{number.format(report.excluded_findings)} unsupported observation records excluded.</p>}{report.criterion_coverage.map(criterion => <article key={criterion.criterion_id}><h3>{criterion.name}</h3><p className="review-meta">{readable(criterion.status)} · Rubric version {criterion.rubric_version}</p><p>{criterion.explanation}</p>{criterion.source_utterance_ids.length > 0 && <a href="#review-transcript" onClick={() => revealSection('review-transcript')}>Review candidate statements</a>}{criterion.source_event_ids.length > 0 && <p><a href={`#review-event-${criterion.source_event_ids[0]}`} onClick={() => revealSection(`review-event-${criterion.source_event_ids[0]}`)}>Review reasoning action</a></p>}</article>)}
    </RecordGroup>
    <RecordGroup title="Timeline" id="review-timeline">{!report.timeline.length && <p>No reasoning actions recorded.</p>}{report.timeline.map(event => <article id={`review-event-${event.id}`} tabIndex={-1} key={event.id}><h3>{readable(event.kind)}</h3><p className="review-meta">{readable(event.stage)} · {date.format(new Date(event.created * 1000))}</p><p>{event.text || event.detail || event.card_id || 'Saved session action'}</p></article>)}</RecordGroup>
    <RecordGroup title="Conversation coverage & open questions"><p>Conversation coverage groups recorded questions and quoted replies. It does not establish technical correctness.</p>{report.conversation_memory.status === 'unavailable' ? <p>Conversation grouping is unavailable; the full transcript remains saved.</p> : <>{report.conversation_memory.answered_points.map((point, index) => <article key={index}>{point.question_turn_ids.map(id => <p key={id}>{report.conversation_memory.questions.find(question => question.id === id)?.text}</p>)}{point.answers.map(answer => <blockquote key={`${answer.utterance_id}-${answer.quote}`}>{answer.quote}<small>Source version {answer.source_version}</small></blockquote>)}</article>)}{report.conversation_memory.unresolved_details.length > 0 && <><h3>Details to revisit</h3><ul>{report.conversation_memory.unresolved_details.map((item, index) => <li key={index}>{item.excerpt}</li>)}</ul></>}</>}<h3>Questions to revisit</h3><p className="review-meta">Unanswered questions and requests for clarification, repetition, help or skipping. Some questions may not have been heard.</p>{report.unresolved_questions.length ? <ul>{report.unresolved_questions.map((question, index) => <li key={index}>{question}</li>)}</ul> : <p>No such questions recorded; this does not establish technical completeness.</p>}</RecordGroup>
    <RecordGroup title="Exercise references"><p>These describe synthetic task facts, not a diagnosed weakness.</p>{report.reference_review.map(reference => <article key={reference.reference_id}><h3>{readable(reference.scenario_id)}</h3><Reference value={reference.causal_reference}/><p className="review-meta">Reference: {reference.reference_id}</p></article>)}{!report.reference_review.length && <p>Complete or explicitly skip the independent exercise and coding attempt to view references.</p>}</RecordGroup>
   </details></section>
  </div>}
 </main>
}
