"""Offer lifecycle faults with fake transport primitives; no speech/runner calls."""
import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from interviewer.voice import VoiceManager

SDP = 'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'

@pytest.fixture
def runtime(monkeypatch):
    state = {'generation_id': 'g1', 'created': 0, 'paused': False, 'stage': 'RESUME_ROLE_DIALOGUE'}
    control = SimpleNamespace(fail=None, hold_initialize=False, hold_workers=False,
        entered=asyncio.Event(), release=asyncio.Event(), workers_entered=asyncio.Event(),
        workers_release=asyncio.Event(), connections=[], recordings=[], events=[], run_count=0)
    class Connection:
        def __init__(self):
            self.number = len(control.connections)+1
            self.fail_disconnect = False
            self.disconnect_entered = asyncio.Event()
            self.disconnect_release = None
            self.closed = False
            control.connections.append(self)
            control.events.append(f'allocate-{self.number}')
        async def initialize(self, **kwargs):
            control.entered.set()
            if control.hold_initialize: await control.release.wait()
            if control.fail == 'initialize': raise RuntimeError('synthetic initialize failure')
        def get_answer(self):
            if control.fail == 'answer': raise RuntimeError('synthetic answer failure')
            return {'sdp': 'synthetic-answer', 'type': 'answer'}
        async def disconnect(self):
            self.disconnect_entered.set()
            if self.disconnect_release: await self.disconnect_release.wait()
            if self.fail_disconnect:
                self.fail_disconnect = False
                raise OSError('synthetic disconnect failure')
            control.events.append(f'close-{self.number}')
            self.closed = True
    class Processor:
        def __init__(self, *args, **kwargs): pass
        async def process_frame(self, *args): pass
    class Transport:
        def __init__(self, **kwargs):
            if control.fail == 'transport': raise RuntimeError('synthetic transport failure')
        def input(self): return Processor()
        def output(self): return Processor()
        def event_handler(self, name): return lambda handler: handler
    class Runner:
        def __init__(self, *, handle_sigint, handle_sigterm):
            control.signal_handlers = (handle_sigint, handle_sigterm)
        async def add_workers(self, *args):
            control.workers_entered.set()
            if control.hold_workers: await control.workers_release.wait()
            if control.fail == 'workers': raise RuntimeError('synthetic worker failure')
        async def run(self):
            control.run_count += 1
            await asyncio.Event().wait()
    def pipeline(*args):
        if control.fail == 'pipeline': raise RuntimeError('synthetic pipeline failure')
        return object()
    libs = {'SmallWebRTCTransport': Transport, 'FrameProcessor': Processor,
            'Pipeline': pipeline, 'WorkerRunner': Runner}
    for name in ('TransportParams', 'PipelineWorker', 'PipelineParams', 'VADProcessor', 'SileroVADAnalyzer', 'VADParams'):
        libs[name] = Processor
    monkeypatch.setitem(sys.modules, 'pipecat.transports.smallwebrtc.connection', SimpleNamespace(SmallWebRTCConnection=Connection))
    manager = VoiceManager(get_session=lambda sid: state)
    monkeypatch.setattr(manager, 'warmup', AsyncMock(return_value={'ready': True}))
    monkeypatch.setattr(manager, '_load_runtime', lambda: libs)
    monkeypatch.setattr(manager, '_emit_delivery', AsyncMock())
    def record(session, source):
        recording = SimpleNamespace(close=Mock())
        control.recordings.append(recording)
        session.recording = recording
        if control.fail == 'recording': raise OSError('synthetic recording failure')
    monkeypatch.setattr(manager, '_start_recording', record)
    control.manager, control.state = manager, state
    return control


async def offer(runtime):
    return await runtime.manager.offer('session', SDP, 'offer')


@pytest.mark.asyncio
async def test_interview_runner_leaves_shutdown_signals_to_server(runtime):
    await offer(runtime)
    assert runtime.signal_handlers == (False, False)
    await runtime.manager.close_all()
    assert not runtime.manager._sessions


@pytest.mark.asyncio
async def test_replacement_closes_prior_before_allocating_and_keeps_one_owner(runtime):
    await offer(runtime)
    prior = runtime.manager._sessions['session']
    await offer(runtime)
    assert runtime.events.index('close-1') < runtime.events.index('allocate-2')
    assert prior.cleanup_complete and prior.pipeline_task.done() and prior.sender_task.done()
    runtime.recordings[0].close.assert_called_once()
    assert runtime.manager._sessions['session'].offer_task is None
    await runtime.manager.close_all()
    assert not runtime.manager._sessions and all(c.closed for c in runtime.connections)


@pytest.mark.asyncio
async def test_failed_prior_cleanup_retains_owner_and_prevents_new_allocation(runtime):
    await offer(runtime)
    prior = runtime.manager._sessions['session']
    runtime.connections[0].fail_disconnect = True
    with pytest.raises(OSError): await offer(runtime)
    assert runtime.manager._sessions['session'] is prior
    assert len(runtime.connections) == 1 and not prior.cleanup_complete
    await offer(runtime)
    assert prior.cleanup_complete and len(runtime.connections) == 2
    await runtime.manager.close_all()


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['initialize', 'answer', 'transport', 'recording', 'pipeline', 'workers'])
async def test_failed_offer_releases_every_allocated_resource(runtime, failure):
    runtime.fail = failure
    with pytest.raises((RuntimeError, OSError)): await offer(runtime)
    assert not runtime.manager._sessions
    assert len(runtime.connections) == 1 and runtime.connections[0].closed
    assert runtime.run_count == 0
    for recording in runtime.recordings: recording.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('external_close', [False, True])
async def test_cancelled_initialization_is_owned_until_disconnect(runtime, external_close):
    runtime.hold_initialize = True
    task = asyncio.create_task(offer(runtime))
    await runtime.entered.wait()
    assert runtime.manager._sessions['session'].offer_task is task
    if external_close: await runtime.manager.close('session')
    else: task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert runtime.connections[0].closed and not runtime.manager._sessions
    assert runtime.run_count == 0


@pytest.mark.asyncio
async def test_cancelled_cleanup_waiter_leaves_shielded_cleanup_owned(runtime):
    runtime.hold_initialize = True
    task = asyncio.create_task(offer(runtime))
    await runtime.entered.wait()
    connection = runtime.connections[0]
    connection.disconnect_release = asyncio.Event()
    runtime.fail = 'initialize'
    runtime.release.set()
    await connection.disconnect_entered.wait()
    session = runtime.manager._sessions['session']
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert runtime.manager._sessions['session'] is session and not session.cleanup_task.done()
    connection.disconnect_release.set()
    await runtime.manager.close('session')
    assert connection.closed and not runtime.manager._sessions


@pytest.mark.asyncio
async def test_overlapping_offers_serialize_allocation_and_prior_cleanup(runtime):
    runtime.hold_initialize = True
    first = asyncio.create_task(offer(runtime))
    await runtime.entered.wait()
    second = asyncio.create_task(offer(runtime))
    await asyncio.sleep(0)
    assert len(runtime.connections) == 1
    runtime.release.set()
    await asyncio.gather(first, second)
    assert len(runtime.connections) == 2
    assert runtime.events.index('close-1') < runtime.events.index('allocate-2')
    assert len(runtime.manager._sessions) == 1
    await runtime.manager.close_all()


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['pause', 'complete', 'generation', 'delete'])
async def test_changed_state_during_initialization_cannot_publish_connection(runtime, change):
    runtime.hold_initialize = True
    task = asyncio.create_task(offer(runtime))
    await runtime.entered.wait()
    if change == 'pause': runtime.state['paused'] = True
    elif change == 'complete': runtime.state['stage'] = 'COMPLETED'
    elif change == 'delete': runtime.state.clear()
    else: runtime.state['generation_id'] = 'new-generation'
    runtime.release.set()
    with pytest.raises(RuntimeError, match='Session changed'): await task
    assert not runtime.manager._sessions and runtime.connections[0].closed
    assert runtime.run_count == 0


@pytest.mark.asyncio
async def test_state_change_while_workers_register_prevents_pipeline_start(runtime):
    runtime.hold_workers = True
    task = asyncio.create_task(offer(runtime))
    await runtime.workers_entered.wait()
    runtime.state['paused'] = True
    runtime.workers_release.set()
    with pytest.raises(RuntimeError): await task
    assert runtime.run_count == 0 and not runtime.manager._sessions
    runtime.recordings[0].close.assert_called_once()


@pytest.mark.asyncio
async def test_unauthorized_or_paused_offer_does_not_close_existing_voice(runtime):
    await offer(runtime)
    for lookup, error in ((lambda sid: None, PermissionError), (lambda sid: {**runtime.state, 'paused': True}, RuntimeError)):
        with pytest.raises(error):
            await runtime.manager.offer('session', SDP, 'offer', get_session=lookup)
        assert not runtime.connections[0].closed and len(runtime.connections) == 1
    await runtime.manager.close_all()


@pytest.mark.asyncio
@pytest.mark.parametrize('sdp', ['not-an-sdp', 'v=0\r\n', 'v=0\r\nm=audio bogus RTP/AVP 111\r\n',
    'v=0\r\nm=audio 0 UDP/TLS/RTP/SAVPF 111\r\n', 'v=0\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\n',
    'v=0\r\nm=audio 99999 UDP/TLS/RTP/SAVPF 111\r\n'])
async def test_invalid_or_audio_free_offer_cannot_allocate_or_replace_voice(runtime, sdp):
    await offer(runtime)
    prior = runtime.manager._sessions['session']
    with pytest.raises(ValueError, match='active audio'):
        await runtime.manager.offer('session', sdp, 'offer')
    assert runtime.manager._sessions['session'] is prior
    assert not runtime.connections[0].closed and len(runtime.connections) == 1
    await runtime.manager.close_all()
