from interviewer.voice.manager import VoiceManager
from types import SimpleNamespace
import pytest


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration:
        return
    raise AssertionError("coroutine unexpectedly awaited in this synchronous test")


def test_clause_extraction_waits_for_complete_punctuation():
    clauses, pending = VoiceManager._take_complete_clauses("Use Redis. Then verify the key")

    assert clauses == ["Use Redis."]
    assert pending == "Then verify the key"


def test_clause_extraction_preserves_spacing_after_an_emitted_sentence():
    clauses, pending = VoiceManager._take_complete_clauses("Use Redis. Then ")
    assert clauses == ["Use Redis."]
    assert pending == "Then "
    clauses, pending = VoiceManager._take_complete_clauses(pending + "verify the key. Next")
    assert clauses == ["Then verify the key."]
    assert pending == "Next"


def test_clause_extraction_preserves_provider_delta_spacing():
    first, pending = VoiceManager._take_complete_clauses("Redis ")
    second, pending = VoiceManager._take_complete_clauses(pending + "cache hit. Next")

    assert first == []
    assert second == ["Redis cache hit."]
    assert pending == "Next"


def test_voice_readiness_is_fail_closed_until_models_are_warmed():
    manager = VoiceManager(model_dir="__definitely_missing_voice_assets__")

    assert manager.readiness()["ready"] is False
    assert manager.readiness()["status"] == "unavailable"
    assert manager.is_connected("missing-session") is False


@pytest.mark.asyncio
async def test_completed_voice_requires_saved_review_and_does_not_allow_paused_sessions():
    manager = VoiceManager()
    state = {'stage': 'COMPLETED', 'paused': False, 'generation_id': 'g'}
    with pytest.raises(RuntimeError):
        await manager._active_voice_state('s', lambda sid: state)
    state['_practice_review'] = {'summary': 'Saved feedback'}
    assert await manager._active_voice_state('s', lambda sid: state) is state
    state['paused'] = True
    with pytest.raises(RuntimeError):
        await manager._active_voice_state('s', lambda sid: state)


@pytest.mark.asyncio
async def test_saved_speech_catchup_never_duplicates_streamed_text(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    manager = VoiceManager()
    session = SimpleNamespace(closed=False, interrupted=False, generated_text_chars=0, generation_id='g', text_lock=asyncio.Lock())
    manager._sessions['s'] = session
    async def sent(*args):
        session.generated_text_chars += len(args[1])
    send = AsyncMock(side_effect=sent)
    finish = AsyncMock()
    monkeypatch.setattr(manager, '_send_text_delta', send)
    monkeypatch.setattr(manager, '_finish_text', finish)
    await manager.speak_saved_text('s', 'Saved greeting.', 'g')
    await manager.speak_saved_text('s', 'Saved greeting.', 'g')
    send.assert_awaited_once_with('s', 'Saved greeting.', 'g')
    finish.assert_awaited_once_with('s', 'g')
    session.generated_text_chars = 0
    await manager.speak_saved_text('s', 'Obsolete greeting.', 'old')
    assert send.await_count == 1


@pytest.mark.asyncio
async def test_live_text_catches_up_after_a_prefix_persisted_before_publication():
    import asyncio
    from interviewer.voice.manager import _Session
    messages = []
    manager = VoiceManager(get_session=lambda sid: {'generation_id': 'g'})
    session = _Session('s', 'g', None, None, SimpleNamespace(send_app_message=messages.append),
        asyncio.Lock(), asyncio.Queue(maxsize=2), asyncio.Condition(), tts_done=asyncio.Event())
    manager._sessions['s'] = session
    await manager.speak_saved_text('s', 'Hello. ', 'g', finished=False)
    # This prefix was saved before connect, but its live publication arrives later.
    await manager.send_text('s', 'Hello. ', 'g')
    await manager.send_text('s', 'Hello. How are you?', 'g')
    await manager.finish_text('s', 'g')
    assert [packet['text'] for packet in messages] == ['Hello. ', 'How are you?']
    assert session.generated_text_chars == len('Hello. How are you?')
    assert [session.text_queue.get_nowait()[1] for _ in range(2)] == ['Hello.', 'How are you?']


@pytest.mark.asyncio
async def test_voice_becomes_available_only_when_browser_connects(monkeypatch):
    from unittest.mock import AsyncMock
    handlers, pending = {}, []
    class Transport:
        def event_handler(self, name):
            def register(callback):
                handlers[name] = callback
                return callback
            return register
    manager = VoiceManager()
    session = SimpleNamespace(session_id='s', transport=Transport(), closed=False,
        client_ready=False, pipeline_task=SimpleNamespace(done=lambda: False))
    manager._sessions['s'] = session
    monkeypatch.setattr(manager, '_schedule_callback', lambda s, callback: pending.append(callback))
    dispatch = AsyncMock()
    monkeypatch.setattr(manager, '_dispatch_control', dispatch)
    manager._bind_data_channel(session)
    assert not manager.is_connected('s')
    await handlers['on_client_connected'](session.transport, None)
    assert not manager.is_connected('s')
    await pending[0]()
    assert manager.is_connected('s')
    dispatch.assert_awaited_once_with(session, 'ready', {})


def test_whisper_uses_local_streaming_profile_and_consumes_lazy_segments():
    class Model:
        def transcribe(self, samples, **kwargs):
            self.options = kwargs
            return iter([SimpleNamespace(text=" local answer ", words=[])]), object()

    manager = VoiceManager()
    manager._whisper_model = Model()

    text, words = manager._transcribe([0.0, 0.0])

    assert text == "local answer"
    assert words == []
    assert manager._whisper_model.options == {
        "language": "en",
        "beam_size": 1,
        "word_timestamps": True,
        "condition_on_previous_text": False,
    }


def test_keep_thinking_holds_final_transcript_until_done_speaking():
    delivered = []
    manager = VoiceManager(on_answer=lambda sid, text, metadata: delivered.append((sid, text, metadata)))
    session = SimpleNamespace(
        session_id="s1", on_control=None, on_answer=manager._on_answer,
        defer_answers=False, held_answers=None,
        force_endpoint=None,
        input_failed=False,
    )

    run_immediate(manager._dispatch_control(session, "keep_thinking", {}))
    run_immediate(manager._accept_transcript(session, "First part.", {"final": True}))
    assert delivered == []
    run_immediate(manager._dispatch_control(session, "done_speaking", {}))

    assert delivered == [("s1", "First part.", {"final": True})]
    assert session.defer_answers is False
    assert session.held_answers == []


def test_app_message_uses_smallwebrtc_connection_and_fails_if_missing():
    sent = []
    manager = VoiceManager()
    session = SimpleNamespace(connection=SimpleNamespace(send_app_message=sent.append))

    run_immediate(manager._send_message(session, {"type": "assistant_text", "text": "Hi"}))

    assert sent == [{"type": "assistant_text", "text": "Hi"}]
    try:
        run_immediate(manager._send_message(SimpleNamespace(connection=object()), {"type": "x"}))
    except RuntimeError as exc:
        assert "does not support app messages" in str(exc)
    else:
        raise AssertionError("missing data-channel support must fail loudly")


@pytest.mark.asyncio
async def test_transport_disconnect_during_owned_close_does_not_schedule_recursive_cleanup():
    from unittest.mock import Mock
    handlers = {}
    class Transport:
        def event_handler(self, name):
            def register(handler):
                handlers[name] = handler
                return handler
            return register
    manager = VoiceManager()
    session = SimpleNamespace(session_id='session', closed=True, transport=Transport())
    manager._sessions['session'] = session
    manager._schedule_callback = Mock()
    manager._bind_data_channel(session)
    await handlers['on_client_disconnected'](session.transport, None)
    manager._schedule_callback.assert_not_called()
    session.closed = False
    await handlers['on_client_disconnected'](session.transport, None)
    manager._schedule_callback.assert_called_once()


@pytest.mark.asyncio
async def test_keep_thinking_delivers_one_turn_across_multiple_vad_segments():
    import asyncio
    received=[]
    async def answer(sid,text,metadata):
        received.append((sid,text,metadata))
    manager=VoiceManager()
    session=SimpleNamespace(session_id='session',on_control=None,force_endpoint=None,input_failed=False,defer_answers=True,held_answers=[('First thought.',{'audio_duration_seconds':1.2}),('Revised explanation.',{'audio_duration_seconds':2.3})],on_answer=answer)
    await manager._dispatch_control(session,'done_speaking',{})
    assert len(received)==1
    assert received[0][1]=='First thought. Revised explanation.'
    assert received[0][2]['audio_duration_seconds']==3.5
    assert len(received[0][2]['held_segments'])==2
    assert session.held_answers==[]
    assert session.defer_answers is False

def test_segment_alignment_preserves_relative_words_and_marks_clock_basis():
    words=[{'text':'cache','start':0.25,'end':0.75}]
    result=VoiceManager._align_segment(words,12.0,2.0)
    assert result['audio_interval']=={'start':12.0,'end':14.0}
    assert result['session_words']==[{'text':'cache','start':12.25,'end':12.75}]
    assert words[0]['start']==0.25
    assert result['session_timestamp_basis']=='seconds_since_session_creation'
    assert 'transport delay is not measured' in result['clock_note']

@pytest.mark.asyncio
async def test_close_uses_installed_smallwebrtc_disconnect_api():
    import asyncio
    calls=[]
    async def disconnect():calls.append('disconnect')
    manager=VoiceManager()
    session=SimpleNamespace(closed=False,audio_condition=asyncio.Condition(),pending_audio_ms=500,sender_task=None,pipeline_task=None,connection=SimpleNamespace(disconnect=disconnect),recording=None)
    await manager._close(session)
    await manager._close(session)
    assert calls==['disconnect']
    assert session.closed and session.pending_audio_ms==0


@pytest.mark.asyncio
async def test_failed_disconnect_remains_owned_for_retry_and_releases_recording():
    import asyncio
    from unittest.mock import Mock
    calls=[]
    async def disconnect():
        calls.append('disconnect')
        if len(calls)==1:raise OSError('Transient disconnect failure')
    recording=Mock()
    session=SimpleNamespace(closed=False,audio_condition=asyncio.Condition(),pending_audio_ms=500,
        sender_task=None,pipeline_task=None,connection=SimpleNamespace(disconnect=disconnect),recording=recording)
    manager=VoiceManager();manager._sessions['s1']=session
    with pytest.raises(OSError):await manager.close('s1')
    assert manager._sessions['s1'] is session and session.closed
    assert session.recording is None and recording.close.call_count==1
    await manager.close('s1')
    assert manager._sessions=={} and session.cleanup_complete
    assert calls==['disconnect','disconnect']


@pytest.mark.asyncio
async def test_delivery_diagnostic_failure_does_not_prevent_media_release():
    import asyncio
    from unittest.mock import AsyncMock, Mock
    manager=VoiceManager()
    manager._emit_delivery=AsyncMock(side_effect=RuntimeError('Diagnostic store unavailable'))
    connection=SimpleNamespace(disconnect=AsyncMock())
    recording=Mock()
    session=SimpleNamespace(closed=False,audio_condition=asyncio.Condition(),pending_audio_ms=10,
        sender_task=None,pipeline_task=None,connection=connection,recording=recording)
    await manager._close(session)
    connection.disconnect.assert_awaited_once()
    recording.close.assert_called_once()
    assert session.cleanup_complete and session.recording is None


@pytest.mark.asyncio
async def test_cancelled_close_waiter_does_not_abandon_owned_media_cleanup():
    import asyncio
    from unittest.mock import Mock
    entered,released=asyncio.Event(),asyncio.Event()
    async def disconnect():
        entered.set()
        await released.wait()
    recording=Mock()
    session=SimpleNamespace(closed=False,audio_condition=asyncio.Condition(),pending_audio_ms=10,
        sender_task=None,pipeline_task=None,connection=SimpleNamespace(disconnect=disconnect),recording=recording)
    manager=VoiceManager();manager._sessions['s1']=session
    waiter=asyncio.create_task(manager.close('s1'))
    await entered.wait()
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):await waiter
    assert not session.cleanup_task.done() and manager._sessions['s1'] is session
    released.set()
    await session.cleanup_task
    await asyncio.sleep(0)
    recording.close.assert_called_once()
    assert session.cleanup_complete and manager._sessions=={}


@pytest.mark.asyncio
async def test_shutdown_closes_every_voice_connection_without_active_cloud_generation():
    from unittest.mock import AsyncMock
    manager=VoiceManager()
    first,second=SimpleNamespace(cleanup_task=None),SimpleNamespace(cleanup_task=None)
    manager._sessions={'first':first,'second':second}
    manager._close=AsyncMock()
    await manager.close_all()
    assert manager._sessions=={}
    assert [call.args[0] for call in manager._close.call_args_list]==[first,second]


@pytest.mark.asyncio
async def test_application_callback_does_not_block_frame_loop_and_close_cancels_it():
    import asyncio
    started = asyncio.Event()
    interruption_traversed = asyncio.Event()
    completed = []
    async def application_callback():
        started.set()
        await interruption_traversed.wait()
        completed.append('committed')
    manager = VoiceManager()
    session = SimpleNamespace(session_id='s1', closed=False, callback_tasks=None,
        audio_condition=asyncio.Condition(), pending_audio_ms=0,
        sender_task=None, pipeline_task=None, connection=object(), recording=None)
    manager._schedule_callback(session, application_callback)
    await started.wait()
    # The caller can continue processing the interruption that the callback awaits.
    interruption_traversed.set()
    await asyncio.gather(*session.callback_tasks)
    assert completed == ['committed']
    interruption_traversed.clear()
    manager._schedule_callback(session, application_callback)
    pending = tuple(session.callback_tasks)
    await manager._close(session)
    assert all(task.done() for task in pending)
    assert completed == ['committed']


@pytest.mark.asyncio
async def test_tts_failure_releases_sender_and_requires_reconnect_without_hiding_text():
    import asyncio
    from interviewer.voice.manager import _Session
    class Processor:
        def __init__(self):
            self.frames=[]
        async def process_frame(self,frame,direction):
            pass
        async def push_frame(self,frame,direction):
            self.frames.append(frame)
    class Speak:
        text='A complete question.'
        metadata={'generation_id':'g1'}
    class Started:
        def __init__(self,**kwargs):pass
    class Stopped:
        def __init__(self,**kwargs):pass
    class WorkerInterruption:
        pass
    class FailingModel:
        def create(self,*args,**kwargs):
            raise RuntimeError('synthetic inference failure')
    messages=[]
    manager=VoiceManager(get_session=lambda sid:{'generation_id':'g1'})
    session=_Session('s1','g1',None,None,SimpleNamespace(send_app_message=messages.append),
        asyncio.Lock(),asyncio.Queue(maxsize=2),asyncio.Condition(),
        synth_generation='g1',tts_done=asyncio.Event())
    manager._sessions['s1']=session
    manager._kokoro_model=FailingModel()
    async def interrupt(sid):
        session.interrupted=True
    manager.interrupt=interrupt
    processor=manager._tts_processor({'FrameProcessor':Processor,'TTSSpeakFrame':Speak,
        'TTSStartedFrame':Started,'TTSStoppedFrame':Stopped,'InterruptionWorkerFrame':WorkerInterruption},session)
    await processor.process_frame(Speak(),None)
    await asyncio.gather(*session.callback_tasks)
    assert session.speech_failed and session.tts_done.is_set()
    assert isinstance(processor.frames[-1],Stopped)
    assert messages[-1]['type']=='voice_error'
    assert 'displayed text' in messages[-1]['message']
    await manager.send_text('s1','Text remains available from the session stream.','g1')
    assert session.text_queue.empty()


@pytest.mark.asyncio
async def test_playback_ack_is_monotonic_generation_bound_and_cannot_credit_future_audio():
    import asyncio
    from interviewer.voice.manager import _Session
    manager=VoiceManager()
    session=_Session('s1','g1',None,None,None,asyncio.Lock(),asyncio.Queue(),asyncio.Condition(),
        pending_audio_ms=500,generated_audio_ms=500)
    for invalid in (None,False,True,-1,'100',float('inf'),{},100.5):
        await manager.acknowledge_playback(session,'g1',invalid)
    await manager.acknowledge_playback(session,'old-generation',500)
    assert session.pending_audio_ms==500 and session.playback_acked_ms==0
    await manager.acknowledge_playback(session,'g1',200)
    await manager.acknowledge_playback(session,'g1',200)
    await manager.acknowledge_playback(session,'g1',100)
    assert session.pending_audio_ms==300 and session.playback_acked_ms==200
    await manager.acknowledge_playback(session,'g1',10**30)
    assert session.pending_audio_ms==0 and session.playback_acked_ms==500
    session.generated_audio_ms=800
    session.pending_audio_ms=300
    await manager.acknowledge_playback(session,'g1',500)
    assert session.pending_audio_ms==300  # No stored future credit from the oversized ack.
    session.interrupted=True
    await manager.acknowledge_playback(session,'g1',800)
    assert session.pending_audio_ms==300


def test_active_utterance_buffer_clears_at_limit_without_silently_submitting_partial_audio():
    from interviewer.voice.manager import _UtteranceAudio
    audio=_UtteranceAudio(max_samples=6)
    assert audio.append([1,2,3]) and audio.append([4,5,6])
    assert audio.num_samples==6
    assert audio.append([7]) is False
    assert audio.num_samples==0 and audio.chunks==[]
    assert audio.append([8])
    assert audio.take()==[[8]]
    assert audio.num_samples==0


@pytest.mark.asyncio
async def test_keep_thinking_limit_pauses_with_bounded_draft_and_no_submitted_answer():
    import asyncio
    from interviewer.voice.manager import _Session
    messages,controls,answers=[],[],[]
    manager=VoiceManager()
    async def control(sid,name,payload):controls.append((name,payload))
    async def answer(*args):answers.append(args)
    async def interrupt(sid):pass
    manager.interrupt=interrupt
    session=_Session('s1','g1',None,None,SimpleNamespace(send_app_message=messages.append),
        asyncio.Lock(),asyncio.Queue(),asyncio.Condition(),on_control=control,on_answer=answer,
        defer_answers=True,held_answers=[('a'*11990,{})])
    manager._sessions['s1']=session
    await manager._accept_transcript(session,'A new segment that exceeds the limit.',{})
    assert session.input_failed and session.closed
    assert answers==[] and session.held_answers is None
    assert controls[0][0]=='input_limit'
    assert len(controls[0][1]['draft_text'])==12000
    assert 'not submitted' in messages[-1]['message']


@pytest.mark.asyncio
async def test_done_speaking_collects_forced_endpoint_before_committing_one_answer():
    received=[]
    manager=VoiceManager()
    async def answer(sid,text,metadata):received.append(text)
    session=SimpleNamespace(session_id='s1',on_control=None,on_answer=answer,input_failed=False,
        closed=False,defer_answers=False,held_answers=[('Earlier thought.',{})])
    async def endpoint():
        assert session.defer_answers is True
        await manager._accept_transcript(session,'Final thought.',{})
    session.force_endpoint=endpoint
    await manager._dispatch_control(session,'done_speaking',{})
    assert received==['Earlier thought. Final thought.']
    assert session.held_answers==[] and not session.defer_answers


@pytest.mark.asyncio
async def test_cancelled_stt_keeps_the_actual_worker_owned_until_completion(monkeypatch):
    import asyncio
    import threading
    started,release=threading.Event(),threading.Event()
    manager=VoiceManager()
    def inference(samples):
        started.set()
        release.wait(3)
        return ('Late transcript',[])
    monkeypatch.setattr(manager,'_transcribe',inference)
    pending=asyncio.create_task(manager._transcribe_async([]))
    try:
        await asyncio.to_thread(started.wait,1)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):await pending
        with pytest.raises(RuntimeError,match='still running'):
            await manager._transcribe_async([])
        assert not manager._stt_task.done()
    finally:
        release.set()
        await manager._stt_task


@pytest.mark.asyncio
async def test_readiness_blocks_reconnect_while_prior_inference_is_still_running(tmp_path,monkeypatch):
    import asyncio
    monkeypatch.setattr('interviewer.voice.manager.importlib.util.find_spec',lambda name:object())
    model=tmp_path/'faster-whisper-large-v3-turbo'
    model.mkdir()
    for path in (model/'model.bin',model/'config.json',tmp_path/'kokoro-v1.0.onnx',tmp_path/'voices-v1.0.bin'):
        path.write_bytes(b'synthetic provisioning fixture')
    manager=VoiceManager(model_dir=tmp_path)
    manager._whisper_model=manager._kokoro_model=object()
    release=asyncio.Event()
    manager._stt_task=asyncio.create_task(release.wait())
    assert manager.readiness()['status']=='busy' and not manager.readiness()['ready']
    release.set()
    await manager._stt_task
    assert manager.readiness()['ready']


@pytest.mark.asyncio
async def test_delivery_milestones_are_generation_bound_and_completion_is_an_estimate():
    import asyncio
    from interviewer.voice.manager import _Session
    records=[]
    manager=VoiceManager(on_event=lambda sid,kind,payload:records.append((kind,payload)))
    session=_Session('s1','g1',None,None,None,asyncio.Lock(),asyncio.Queue(),asyncio.Condition(),
        generated_text_chars=20,generated_audio_ms=500,pending_audio_ms=500,text_finished=True,tts_done=asyncio.Event())
    session.tts_done.set()
    for invalid in (False,None,-1,float('nan'),float('inf'),10**1000,'123'):
        await manager._browser_milestone(session,{'type':'text_received','generation_id':'g1','client_time_ms':invalid})
    assert records==[]
    await manager._browser_milestone(session,{'type':'text_received','generation_id':'g1','client_time_ms':1000})
    await manager._browser_milestone(session,{'type':'text_displayed','generation_id':'g1','client_time_ms':1001,'characters':10000})
    await manager._browser_milestone(session,{'type':'playback_started','generation_id':'g1','client_time_ms':1002})
    await manager.acknowledge_playback(session,'g1',500)
    assert records[-1][1]['status']=='estimated_complete'
    assert records[-1][1]['displayed_text_chars']==20
    assert records[-1][1]['estimated_played_ms']==500
    assert records[-1][1]['timing']['first_playback_client_ms']==1002
    assert 'do not prove hearing' in records[-1][1]['delivery_note']
    count=len(records)
    await manager.acknowledge_playback(session,'g1',500)
    await manager._browser_milestone(session,{'type':'playback_started','generation_id':'old','client_time_ms':1003})
    assert len(records)==count


@pytest.mark.asyncio
async def test_cancelled_tts_retains_native_task_and_serializes_the_next_clause():
    import asyncio
    import threading
    entered,release=threading.Event(),threading.Event()
    calls=[]
    active=0
    peak=0
    lock=threading.Lock()
    class Model:
        def create(self,text,**kwargs):
            nonlocal active,peak
            with lock:
                calls.append(text);active+=1;peak=max(peak,active)
            try:
                if text=='first':
                    entered.set();release.wait(3)
                return ([0.1],24000)
            finally:
                with lock:active-=1
    manager=VoiceManager()
    manager._kokoro_model=Model()
    first=asyncio.create_task(manager._synthesize_clause('first'))
    second=None
    try:
        assert await asyncio.to_thread(entered.wait,1)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):await first
        second=asyncio.create_task(manager._synthesize_clause('second'))
        await asyncio.sleep(.01)
        assert calls==['first'] and not manager._tts_task.done()
        release.set()
        assert await second==([0.1],24000)
        assert calls==['first','second'] and peak==1
    finally:
        release.set()
        await asyncio.gather(first,*([second] if second else []),return_exceptions=True)
        if manager._tts_task:await manager._tts_task


@pytest.mark.asyncio
@pytest.mark.parametrize('fail_whisper', [False, True])
async def test_warmup_owns_both_native_loaders_after_waiter_cancellation(monkeypatch, fail_whisper):
    import asyncio
    import sys
    import threading
    entered, release = threading.Event(), threading.Event()
    calls = []

    class Whisper:
        def __init__(self, *args, **kwargs):
            calls.append('whisper')
            if fail_whisper:
                raise RuntimeError('synthetic model failure')

        def transcribe(self, *args, **kwargs):
            return iter([]), None

    class Kokoro:
        def __init__(self, *args, **kwargs):
            calls.append('kokoro')
            entered.set()
            assert release.wait(3), 'test did not release native loader'

        def create(self, *args, **kwargs):
            return [0.1], 24000

    monkeypatch.setitem(sys.modules, 'numpy', SimpleNamespace(zeros=lambda *a, **kw: [], float32='float32'))
    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=Whisper))
    monkeypatch.setitem(sys.modules, 'kokoro_onnx', SimpleNamespace(Kokoro=Kokoro))
    manager = VoiceManager()
    monkeypatch.setattr(manager, '_load_runtime', lambda: {})
    monkeypatch.setattr(manager, 'readiness', lambda: {
        'ready': manager._whisper_model is not None and manager._kokoro_model is not None,
        'status': 'warming'})
    first = asyncio.create_task(manager.warmup())
    second = None
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        owned = manager._warmup_task
        second = asyncio.create_task(manager.warmup())
        await asyncio.sleep(.01)
        assert manager._warmup_task is owned and not owned.done()
        assert sorted(calls) == ['kokoro', 'whisper']
        assert manager._whisper_model is manager._kokoro_model is None
        release.set()
        result = await second
        assert result['ready'] is not fail_whisper
        if fail_whisper:
            assert manager._whisper_model is manager._kokoro_model is None
            assert 'synthetic model failure' in manager._warmup_error
        else:
            assert isinstance(manager._whisper_model, Whisper)
            assert isinstance(manager._kokoro_model, Kokoro)
        assert sorted(calls) == ['kokoro', 'whisper']
        if fail_whisper:
            fail_whisper = False
            assert (await manager.warmup())['ready'] is True
            assert calls.count('whisper') == calls.count('kokoro') == 2
        else:
            assert (await manager.warmup())['ready'] is True
            assert sorted(calls) == ['kokoro', 'whisper']
    finally:
        release.set()
        await asyncio.gather(first, *([second] if second else []), return_exceptions=True)
        if manager._warmup_task:
            await manager._warmup_task
