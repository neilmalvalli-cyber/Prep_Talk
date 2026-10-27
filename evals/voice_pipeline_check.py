"""Real local voice pipeline downlink check; no cloud, physical microphone or runner."""
import asyncio,json,time
from pathlib import Path
import numpy as np
from fractions import Fraction
from av import AudioFrame
from scipy.signal import resample_poly
from math import gcd
from aiortc import RTCPeerConnection,RTCConfiguration,RTCSessionDescription,AudioStreamTrack
from interviewer.voice import VoiceManager

class SyntheticMicrophone(AudioStreamTrack):
 def __init__(self):
  super().__init__();self.samples=np.zeros(0,dtype=np.int16);self.offset=0;self.timestamp=0;self.started=None
 async def recv(self):
  if self.started is None:self.started=time.monotonic()
  await asyncio.sleep(max(0,self.started+self.timestamp/16000-time.monotonic()))
  chunk=np.zeros(320,dtype=np.int16)
  if self.offset<len(self.samples):
   available=self.samples[self.offset:self.offset+320];chunk[:len(available)]=available;self.offset+=len(available)
  frame=AudioFrame.from_ndarray(chunk.reshape(1,-1),format='s16',layout='mono');frame.sample_rate=16000;frame.pts=self.timestamp;frame.time_base=Fraction(1,16000);self.timestamp+=320
  return frame

async def main():
 root=Path(__file__).resolve().parents[1]
 state={'id':'a'*32,'generation_id':'test-generation','created':time.time(),'duration_minutes':5,'record_audio':False}
 manager=VoiceManager(model_dir=root/'data/models',data_dir=root/'data')
 client=RTCPeerConnection(RTCConfiguration(iceServers=[]))
 channel=client.createDataChannel('pipecat');opened=asyncio.Event();audible=asyncio.Event();messages=[];audio_frames=0;played_ms=0;receiver=None
 @channel.on('open')
 def on_open():opened.set()
 @channel.on('message')
 def on_message(message):messages.append(json.loads(message))
 @client.on('track')
 def on_track(track):
  nonlocal receiver
  async def receive():
   nonlocal audio_frames,played_ms
   while True:
    frame=await track.recv();audio_frames+=1;played_ms+=frame.samples/frame.sample_rate*1000
    if np.max(np.abs(frame.to_ndarray().astype(np.float32)))>100:audible.set()
    if channel.readyState=='open':channel.send(json.dumps({'type':'playback_ack','generation_id':state['generation_id'],'played_ms':int(played_ms)}))
  receiver=asyncio.create_task(receive())
 microphone=SyntheticMicrophone();client.addTrack(microphone)
 transcribed=asyncio.Event();transcripts=[]
 async def on_answer(sid,text,metadata):
  transcripts.append({'text':text,'metadata':metadata});transcribed.set()
 try:
  await client.setLocalDescription(await client.createOffer())
  answer=await manager.offer(state['id'],client.localDescription.sdp,'offer',on_answer,lambda sid:state)
  await client.setRemoteDescription(RTCSessionDescription(sdp=answer['sdp'],type=answer['type']))
  await asyncio.wait_for(opened.wait(),15)
  await asyncio.sleep(.5)
  started=time.monotonic()
  await manager.send_text(state['id'],'What did you change in the cache? ',state['generation_id'])
  await asyncio.wait_for(audible.wait(),20)
  first_audio_seconds=time.monotonic()-started
  # No finish_text call has occurred: complete clauses must play while the
  # provider could still be producing later content.
  later_clause_at=time.monotonic()-started
  await manager.send_text(state['id'],'How did you verify that decision? ',state['generation_id'])
  await manager.finish_text(state['id'],state['generation_id'])
  await asyncio.sleep(4)
  result={'real_voice_pipeline':True,'cloud_used':False,'physical_microphone':False,'audio_frames_received':audio_frames,'first_audible_after_text_seconds':first_audio_seconds,'server_audio_pending_ms':manager._sessions[state['id']].pending_audio_ms,'server_playback_acked_ms':manager._sessions[state['id']].playback_acked_ms,'text_received':any(m.get('type')=='assistant_text' for m in messages)}
  result['first_audio_before_stream_completion']=first_audio_seconds<=later_clause_at
  result['later_clause_sent_seconds']=later_clause_at
  spoken,rate=await asyncio.to_thread(manager._kokoro_model.create,'I invalidated the cache after the write.',voice='af_heart',speed=1.0,lang='en-us')
  divisor=gcd(int(rate),16000)
  microphone.samples=(np.clip(resample_poly(np.asarray(spoken),16000//divisor,int(rate)//divisor),-1,1)*32767).astype(np.int16)
  await asyncio.wait_for(transcribed.wait(),20)
  result['real_uplink_transcripts']=transcripts
  state['generation_id']='replacement-generation';await manager.interrupt(state['id']);await asyncio.sleep(.1)
  result['interrupt_message_received']=any(m.get('type')=='interrupt' for m in messages)
  (root/'docs/voice-pipeline-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 finally:
  await manager.close(state['id']);await client.close()
  if receiver:receiver.cancel()
asyncio.run(main())
