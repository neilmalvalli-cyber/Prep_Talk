import {useEffect, useRef, useState} from 'react'
import {api, ApiError, errorMessage, type Session} from './api'

export type VoiceState='ready'|'listening'|'muted'|'processing'|'speaking'|'thinking'|'paused'|'reconnecting'|'error'|'completed'
export function useVoice(session:Session,refresh:()=>Promise<void>,onError:(message:string)=>void){
 const [connected,setConnected]=useState(false),[disconnecting,setDisconnecting]=useState(false),[state,setState]=useState<VoiceState>('ready'),[level,setLevel]=useState(0),[playbackLevel,setPlaybackLevel]=useState(0)
 const [starting,setStarting]=useState(false),[playbackBlocked,setPlaybackBlocked]=useState(false)
 const peer=useRef<RTCPeerConnection|null>(null),stream=useRef<MediaStream|null>(null),channel=useRef<RTCDataChannel|null>(null)
 const output=useRef<HTMLAudioElement|null>(null),context=useRef<AudioContext|null>(null),frame=useRef(0),generation=useRef(session.generation_id)
 const sessionRef=useRef(session),lastSound=useRef(0),onErrorRef=useRef(onError),refreshRef=useRef(refresh)
 const attempt=useRef(0),connecting=useRef(false)
 const ackTimer=useRef<ReturnType<typeof setInterval>|null>(null)
 const releaseVisuals=useRef<(()=>void)|null>(null)
 const pendingPause=useRef<Promise<void>|null>(null)
 const suppressedGeneration=useRef<string|null>(null)
 // Shared with the orb so it can read live frequency bands.
 const analysers=useRef<{mic:AnalyserNode|null;playback:AnalyserNode|null}>({mic:null,playback:null})
 sessionRef.current=session;onErrorRef.current=onError;refreshRef.current=refresh
 function stopPlayback(){setPlaybackLevel(0);setPlaybackBlocked(false);suppressedGeneration.current=generation.current;if(output.current){output.current.pause();output.current.muted=true}setState(sessionRef.current.paused?'paused':'ready')}
 function disconnect(){attempt.current++;connecting.current=false;setStarting(false);setPlaybackBlocked(false);if(ackTimer.current!==null)clearInterval(ackTimer.current);ackTimer.current=null;releaseVisuals.current?.();releaseVisuals.current=null;cancelAnimationFrame(frame.current);frame.current=0;const prior=peer.current;peer.current=null;prior?.close();channel.current=null;stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(output.current){output.current.pause();output.current.srcObject=null};context.current?.close().catch(()=>{});context.current=null;analysers.current={mic:null,playback:null};setConnected(false);setLevel(0);setPlaybackLevel(0);setState('ready')}
 async function resumePlayback(){
  if(sessionRef.current.paused||suppressedGeneration.current===generation.current)return
  try{await context.current?.resume();if(output.current){output.current.muted=false;await output.current.play();setPlaybackBlocked(false)}}
  catch{setPlaybackBlocked(true)}
 }
 function send(type:string,fields:Record<string,unknown>={}){if(channel.current?.readyState==='open')channel.current.send(JSON.stringify({type,...fields}))}
 function pauseDisconnectedSession(){
  if(pendingPause.current)return
  setDisconnecting(true)
  pendingPause.current=(async()=>{
   try{
    for(let retry=0;retry<2;retry++){
     const current=await api.session(session.id)
     if(current.stage==='COMPLETED')return
     try{await api.action(current.id,current.revision,'disconnect');return}
     catch(error){if(error instanceof ApiError&&error.status===409&&retry===0)continue;throw error}
    }
   }catch{onErrorRef.current('Voice disconnected locally, but the interview pause could not be confirmed. Select Pause interview or reload before continuing.')}
   finally{await refreshRef.current().catch(()=>{});pendingPause.current=null;setDisconnecting(false)}
  })()
  pendingPause.current.catch(()=>{})
 }
 async function connect(){
  if(pendingPause.current){await pendingPause.current;return}
  if(connected&&peer.current)return
  if(connecting.current)return
  if(peer.current)disconnect()
  const ticket=++attempt.current;connecting.current=true;setStarting(true);suppressedGeneration.current=null
  try{
   setState('processing')
   const ready=await api.warmVoice()
   if(ticket!==attempt.current)return
   if(!ready.ready)throw new Error(ready.detail)
   const outputOnly=sessionRef.current.stage==='COMPLETED'
   let media:MediaStream|null=null
   if(!outputOnly){
    try{media=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false})}
    catch{onErrorRef.current('Microphone unavailable. Interviewer audio is still enabled; type your answers below.')}
   }
   if(ticket!==attempt.current){media?.getTracks().forEach(track=>track.stop());return}
   stream.current=media
   const pc=new RTCPeerConnection({iceServers:[]});peer.current=pc
   const audio=new Audio();audio.autoplay=true;output.current=audio
   const ac=new AudioContext();context.current=ac;await ac.resume()
   if(ticket!==attempt.current)return
   const mic=media?ac.createAnalyser():null
   if(mic&&media){mic.fftSize=256;ac.createMediaStreamSource(media).connect(mic);analysers.current.mic=mic}
   let playback:AnalyserNode|null=null
   let ackGeneration='',generatedMs=0,playedMs=0,lastMediaTime=0,playbackStarted=false
   let textReceiptGeneration='',playbackMetricGeneration=''
   function trackGeneration(id:string){
    if(ackGeneration===id)return
    ackGeneration=id;generatedMs=0;playedMs=0;lastMediaTime=audio.currentTime;playbackStarted=false
   }
   async function acceptsGeneration(id:string){
    if(peer.current!==pc||sessionRef.current.paused||id===suppressedGeneration.current)return false
    if(id===sessionRef.current.generation_id)return true
    const authoritative=await api.session(session.id)
    return peer.current===pc&&!authoritative.paused&&authoritative.generation_id===id&&authoritative.revision>=sessionRef.current.revision
   }
   const bindChannel=(dc:RTCDataChannel)=>{
    channel.current=dc
    dc.onmessage=async event=>{
     if(peer.current!==pc)return
     const receivedAt=performance.timeOrigin+performance.now()
     try{
      const envelope=JSON.parse(event.data)
      // A direct voice_error has a text message, not a nested packet.
      const packet=typeof envelope.data==='object'&&envelope.data!==null?envelope.data:
       typeof envelope.message==='object'&&envelope.message!==null?envelope.message:envelope
      if(packet.type==='interrupt'){
       stopPlayback();generation.current=packet.authoritative_generation_id||sessionRef.current.generation_id
      }else if(packet.type==='voice_error'){
       stopPlayback();onErrorRef.current(packet.message||'Local speech failed. Continue by typing.');setState('error')
      }else if(packet.type==='state'){
       if(packet.state!=='speaking')setState(packet.state)
      }else if(packet.type==='assistant_text'){
       if(!await acceptsGeneration(packet.generation_id))return
       if(output.current){
        trackGeneration(packet.generation_id)
        generation.current=packet.generation_id;output.current.muted=false
        void resumePlayback()
        if(textReceiptGeneration!==packet.generation_id){
         textReceiptGeneration=packet.generation_id
         send('text_received',{generation_id:packet.generation_id,client_time_ms:receivedAt})
        }
       }
      }else if(packet.type==='audio_progress'){
       if(!await acceptsGeneration(packet.generation_id))return
       if(typeof packet.generated_ms!=='number'||!Number.isFinite(packet.generated_ms)||packet.generated_ms<0)return
       trackGeneration(packet.generation_id);generatedMs=Math.max(generatedMs,packet.generated_ms)
      }else if(packet.type==='complete'){
       if(packet.generation_id===generation.current)setState('ready')
       refreshRef.current()
      }else if(packet.type==='resync'||packet.type==='execution')refreshRef.current()
     }catch{onErrorRef.current('Voice status message was unreadable. Reconnect voice or type.')}
    }
   }
   bindChannel(pc.createDataChannel('pipecat'))
   pc.ondatachannel=e=>bindChannel(e.channel)
   if(media)media.getTracks().forEach(track=>pc.addTrack(track,media))
   else pc.addTransceiver('audio',{direction:'recvonly'})
   pc.ontrack=event=>{if(peer.current!==pc)return;const incoming=event.streams[0]||new MediaStream([event.track]);audio.srcObject=incoming;playback=ac.createAnalyser();playback.fftSize=256;ac.createMediaStreamSource(incoming).connect(playback);analysers.current.playback=playback;void resumePlayback()}
   pc.onconnectionstatechange=()=>{if(peer.current!==pc)return;if(['disconnected','failed','closed'].includes(pc.connectionState)){const reconnect=pc.connectionState!=='closed';disconnect();if(!outputOnly)pauseDisconnectedSession();if(reconnect){setState('reconnecting');onErrorRef.current(outputOnly?'Feedback audio disconnected. Select Read feedback aloud to retry.':'Voice disconnected and the interview was paused. Select Resume interview to reconnect; old audio will not replay.')}}}
   await pc.setLocalDescription(await pc.createOffer())
   await Promise.race([new Promise<void>(resolve=>{if(pc.iceGatheringState==='complete')resolve();pc.addEventListener('icegatheringstatechange',()=>{if(pc.iceGatheringState==='complete')resolve()})}),new Promise<never>((_,reject)=>setTimeout(()=>reject(new Error('Microphone connection timed out. Continue by typing.')),10000))])
   const answer=await api.offer({session_id:session.id,sdp:pc.localDescription?.sdp||'',type:'offer'})
   if(ticket!==attempt.current)return
   generation.current=answer.generation_id;await pc.setRemoteDescription({type:answer.type,sdp:answer.sdp})
   if(ticket!==attempt.current||peer.current!==pc)return
   setConnected(true);setState(outputOnly?'ready':media?'listening':'muted')
   const samples=new Uint8Array(256)
   const rms=(analyser:AnalyserNode)=>{analyser.getByteTimeDomainData(samples);return Math.sqrt(samples.reduce((sum,n)=>sum+((n-128)/128)**2,0)/samples.length)}
   function markPlayback(){
    if(playbackMetricGeneration!==generation.current){
     playbackMetricGeneration=generation.current
     send('playback_started',{generation_id:generation.current,client_time_ms:performance.timeOrigin+performance.now()})
    }
    playbackStarted=true
   }
   // Audio delivery uses the media clock and available generated frames. Idle
   // time and a prior generation cannot prepay a later utterance's backpressure.
   ackTimer.current=setInterval(()=>{
    if(peer.current!==pc)return
    trackGeneration(generation.current)
    const mediaTime=audio.currentTime,elapsed=Math.max(0,mediaTime-lastMediaTime)*1000
    lastMediaTime=mediaTime
    if(audio.paused||audio.muted||sessionRef.current.paused||generation.current!==sessionRef.current.generation_id){playbackStarted=false;return}
    if(!playbackStarted&&playback&&rms(playback)>.005)markPlayback()
    if(playbackStarted){
     playedMs=Math.min(generatedMs,playedMs+elapsed)
     send('playback_ack',{generation_id:generation.current,played_ms:Math.floor(playedMs)})
    }
   },100)
   function update(now:number){
    frame.current=0
    if(peer.current!==pc||document.hidden)return
     const active=sessionRef.current
     const microphoneActive=Boolean(media?.getAudioTracks().some(t=>t.enabled&&!t.muted&&t.readyState==='live'))
     const micLevel=microphoneActive&&mic?rms(mic):0
     const audible=playback&&!audio.paused&&!audio.muted?rms(playback):0
     setLevel(Math.min(1,micLevel*5))
     setPlaybackLevel(active.paused?0:Math.min(1,audible*7))
     if(active.paused)setState('paused')
     else if(audible>.005){markPlayback();lastSound.current=now;setState('speaking')}
     else if(active.stage==='COMPLETED')setState('completed')
     else if(!microphoneActive)setState('muted')
     else if(now-lastSound.current>300)setState(current=>['processing','thinking','error'].includes(current)?current:'listening')
    frame.current=requestAnimationFrame(update)
   }
   function visibilityChanged(){
    if(document.hidden){cancelAnimationFrame(frame.current);frame.current=0;setLevel(0);setPlaybackLevel(0)}
    else if(peer.current===pc&&!frame.current)frame.current=requestAnimationFrame(update)
   }
   document.addEventListener('visibilitychange',visibilityChanged)
   releaseVisuals.current=()=>document.removeEventListener('visibilitychange',visibilityChanged)
   visibilityChanged()
  }catch(error){if(ticket===attempt.current){disconnect();setState('error');onErrorRef.current(errorMessage(error))}}
  finally{if(ticket===attempt.current){connecting.current=false;setStarting(false)}}
 }
 function disconnectAndPause(){disconnect();if(sessionRef.current.stage!=='COMPLETED')pauseDisconnectedSession()}
 useEffect(()=>{if(session.generation_id!==generation.current){stopPlayback();generation.current=session.generation_id}},[session.generation_id])
 useEffect(()=>{stream.current?.getAudioTracks().forEach(t=>t.enabled=!session.paused);if(session.paused){stopPlayback();setState('paused')}},[session.paused])
 useEffect(()=>()=>disconnect(),[])
 return {analysers,connected,starting,disconnecting,playbackBlocked,resumePlayback,state,setState,level,playbackLevel,connect,disconnect,disconnectAndPause,stopPlayback,send}
}

