import {useRef} from 'react'

// Streams text in word by word: words already shown keep their timing, new ones
// rise in with a short stagger. A new `id` (question) restarts the sequence.
export default function Words({text,id}:{text:string;id?:string}){
 const shown=useRef<{id?:string;delays:number[]}>({id,delays:[]})
 if(shown.current.id!==id)shown.current={id,delays:[]}
 const words=text.split(/(\s+)/).filter(Boolean)
 const delays=shown.current.delays,previous=delays.length
 for(let index=previous;index<words.length;index++)delays[index]=Math.min(index-previous,24)*28
 return <>{words.map((word,index)=>/^\s+$/.test(word)?word:<span key={`${id}-${index}`} className="word" style={{animationDelay:`${delays[index]}ms`}}>{word}</span>)}</>
}
