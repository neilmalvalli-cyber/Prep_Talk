import {useEffect,useRef,useState} from 'react'
import {flushSync} from 'react-dom'

export const reducedMotion=()=>matchMedia('(prefers-reduced-motion: reduce)').matches

// Runs a state change inside a view transition where the browser supports it.
export function transition(update:()=>void){
 const doc=document as Document&{startViewTransition?:(callback:()=>void)=>unknown}
 if(!doc.startViewTransition||reducedMotion()){update();return}
 doc.startViewTransition(()=>flushSync(update))
}

// Global, markup-driven motion: .rv elements reveal on scroll (marked with a
// data attribute, which React leaves alone when it rewrites className), .spot surfaces
// follow the pointer, and .segmented groups get a sliding selection indicator.
export function initMotion(){
 const reveal=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){(entry.target as HTMLElement).dataset.in='';reveal.unobserve(entry.target)}},{rootMargin:'0px 0px -8% 0px',threshold:.06})
 const segments=new Set<HTMLElement>()
 const place=(group:HTMLElement)=>{
  const active=group.querySelector<HTMLElement>(':scope>button[aria-pressed=true]')
  if(!active){group.style.setProperty('--seg-o','0');return}
  group.style.setProperty('--seg-x',`${active.offsetLeft}px`);group.style.setProperty('--seg-y',`${active.offsetTop}px`)
  group.style.setProperty('--seg-w',`${active.offsetWidth}px`);group.style.setProperty('--seg-h',`${active.offsetHeight}px`);group.style.setProperty('--seg-o','1')
  // Skip the slide on first placement so the indicator does not fly in from 0.
  if(!group.classList.contains('seg-ready'))requestAnimationFrame(()=>group.classList.add('seg-ready'))
 }
 const resize=new ResizeObserver(entries=>{for(const entry of entries)place(entry.target as HTMLElement)})
 const scan=(root:ParentNode)=>{
  root.querySelectorAll<HTMLElement>('.rv:not([data-in])').forEach(el=>reveal.observe(el))
  root.querySelectorAll<HTMLElement>('.segmented').forEach(group=>{if(!segments.has(group)){segments.add(group);resize.observe(group)}place(group)})
 }
 const mutations=new MutationObserver(records=>{
  for(const record of records){
   if(record.type==='attributes'){const group=(record.target as HTMLElement).closest<HTMLElement>('.segmented');if(group)place(group);continue}
   record.addedNodes.forEach(node=>{if(node instanceof HTMLElement){if(node.matches('.rv:not([data-in])'))reveal.observe(node);if(node.matches('.segmented')){segments.add(node);resize.observe(node);place(node)}scan(node)}})
   record.removedNodes.forEach(node=>{if(node instanceof HTMLElement)for(const group of segments)if(node===group||node.contains(group)){segments.delete(group);resize.unobserve(group)}})
  }
 })
 mutations.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['aria-pressed']})
 scan(document)
 const pointer=(event:PointerEvent)=>{
  if(event.pointerType!=='mouse')return
  const surface=(event.target as Element|null)?.closest?.<HTMLElement>('.spot')
  if(!surface)return
  const rect=surface.getBoundingClientRect()
  surface.style.setProperty('--mx',`${event.clientX-rect.left}px`);surface.style.setProperty('--my',`${event.clientY-rect.top}px`)
 }
 document.addEventListener('pointermove',pointer,{passive:true})
 document.fonts?.ready.then(()=>segments.forEach(place))
}

// Eases a number from its previous value to the target.
export function useCountUp(target:number|null|undefined,duration=1200){
 const [value,setValue]=useState(target==null?0:reducedMotion()?target:0)
 const from=useRef(0)
 useEffect(()=>{
  if(target==null)return
  if(reducedMotion()){setValue(target);from.current=target;return}
  const start=performance.now(),origin=from.current
  let frame=0
  const tick=(now:number)=>{const t=Math.min(1,(now-start)/duration),eased=1-Math.pow(1-t,4);const next=origin+(target-origin)*eased;setValue(next);if(t<1)frame=requestAnimationFrame(tick);else from.current=target}
  frame=requestAnimationFrame(tick)
  return()=>cancelAnimationFrame(frame)
 },[target,duration])
 return value
}
