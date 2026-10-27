import asyncio
from types import SimpleNamespace
from interviewer.voice.manager import VoiceManager

delivered=[]
m=VoiceManager(on_answer=lambda *a: delivered.append(a))
s=SimpleNamespace(session_id='s1',on_control=None,on_answer=m._on_answer,defer_answers=False,held_answers=None,force_endpoint=None)
async def exercise():
 print('before keep', flush=True)
 await m._dispatch_control(s,'keep_thinking',{})
 print('after keep', flush=True)
 await m._accept_transcript(s,'First part.',{'final':True})
 print('after accept', flush=True)
 await m._dispatch_control(s,'done_speaking',{})
 print('after done', flush=True)
asyncio.run(exercise())
