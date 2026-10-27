// The PrepTalk mark: a speech bubble whose three dots stand in for the P.
export default function Logo({onClick}:{onClick?:()=>void}){
 return <button type="button" className="logo" onClick={onClick} aria-label="PrepTalk home">
  <svg width="26" height="29" viewBox="0 0 34 38" aria-hidden="true"><path d="M9 1h16a9 9 0 0 1 9 9v8a9 9 0 0 1-9 9H14l-7.5 9.2A1.4 1.4 0 0 1 4 35.3V27.4A9 9 0 0 1 0 20V10a9 9 0 0 1 9-9z" fill="none" stroke="currentColor" strokeWidth="2.17" strokeLinejoin="round"/><circle cx="8.667" cy="14" r="2.917" fill="currentColor"/><circle cx="17" cy="14" r="2.917" fill="currentColor"/><circle cx="25.333" cy="14" r="2.917" fill="currentColor"/></svg>
  <span className="wordmark">rep<em>Talk</em></span>
 </button>
}
