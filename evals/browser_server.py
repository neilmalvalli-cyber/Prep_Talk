"""Browser acceptance harness. Synthetic provider only; never used by normal startup.

Run from repository root with PYTHONPATH=apps/api and uvicorn evals.browser_server:app.
Real provider and hardware acceptance must be recorded separately.
"""
import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault('FIELDNOTE_DATA', str(Path(__file__).resolve().parents[1] / 'data' / 'browser-acceptance'))
os.environ['FIELDNOTE_OWNER_KEY'] = 'synthetic-browser-acceptance-owner-key'
os.environ.setdefault('FIELDNOTE_ORIGIN', 'http://127.0.0.1:8000')
from interviewer import main


class SyntheticProvider(main.Providers):
    def key(self, provider):
        return 'synthetic-test-credential-not-a-real-key'

    async def catalog(self, provider):
        rows = [{'id': 'openai/gpt-oss-20b', 'supported_parameters': ['structured_outputs']}, {'id': 'openai/gpt-oss-120b', 'supported_parameters': ['structured_outputs']}]
        self.catalogs[provider] = (__import__('time').time(), {r['id']: r for r in rows})
        return {'models': rows, 'fetched_at': __import__('time').time(), 'pricing_note': 'Synthetic browser test catalog; no pricing claim.'}

    async def validate(self, provider, config):
        if not config['paid_opt_in']:
            raise main.ProviderFailure('paid_consent_required', 'Approve synthetic test configuration')
        return config

    async def stream(self, snapshot, messages):
        recent = next((m['content'].lower() for m in reversed(messages) if m['role'] == 'user'), '')
        if 'ttl only' in recent:
            question = 'What happens if the record changes before the TTL expires?'
        elif 'invalidat' in recent:
            question = 'How did you handle a successful write followed by failed invalidation?'
        else:
            question = 'Which confirmed project decision would you like to explain, and what did you contribute?'
        for word in question.split(' '):
            await asyncio.sleep(.04)
            yield {'text': word+' ', 'usage': None, 'route': 'synthetic-test'}

    async def structured(self, snapshot, messages, schema):
        if 'answered_points' in schema.get('properties', {}):
            # Synthetic extractive fixture only; not a semantic-model result.
            transcript = json.loads(messages[-1]['content'].split('\n', 1)[1])['transcript']
            points = []
            question = None
            for turn in transcript:
                if turn['role'] == 'assistant':
                    question = turn
                elif question and not turn['request_kind']:
                    points.append({'question_turn_ids': [question['id']], 'answers': [{
                        'utterance_id': turn['id'], 'source_version': turn['version'],
                        'event_id': turn['event_id'], 'quote': turn['text'][:240]}]})
            last = transcript[-1]
            return {'answered_points': points[-6:], 'unresolved_details': [
                {'question_turn_id': last['id'], 'excerpt': last['text'][:240]}] if last['role'] == 'assistant' else []}
        return {'ready': True}


main.providers = SyntheticProvider()
if os.getenv('ACCEPTANCE_HOLD_RUNNER') == '1':
    async def hold_submission(submission):
        """Hold an app task only; never dispatch or execute candidate source."""
        await asyncio.Event().wait()
    main.run_submission = hold_submission
app = main.app


@app.get('/api/acceptance/voice/{sid}')
async def acceptance_voice_state(sid: str):
    """Authenticated diagnostics in this synthetic harness only, never production."""
    state = main.store.get(sid, main.OWNER)
    channel = main.voice._sessions.get(sid) if main.voice else None
    def task_state(task):
        if task is None:
            return 'missing'
        if not task.done():
            return 'running'
        if task.cancelled():
            return 'cancelled'
        error = task.exception()
        return type(error).__name__ if error else 'completed'
    return {'session_generation': state['generation_id'], 'paused': state['paused'],
            'connected': main.voice.is_connected(sid) if main.voice else False,
            'voice_generation': channel.generation_id if channel else None,
            'interrupted': channel.interrupted if channel else None,
            'queued_clauses': channel.text_queue.qsize() if channel else None,
            'pending_audio_ms': channel.pending_audio_ms if channel else None,
            'generated_audio_ms': channel.generated_audio_ms if channel else None,
            'offered_audio_ms': channel.offered_audio_ms if channel else None,
            'peak_pending_audio_ms': channel.peak_pending_audio_ms if channel else None,
            'sender': task_state(channel.sender_task) if channel else 'missing',
            'pipeline': task_state(channel.pipeline_task) if channel else 'missing'}


# main's built-site mount is a catch-all; keep this test-only API before it.
app.router.routes.insert(0, app.router.routes.pop())


@app.post('/api/acceptance/voice/{sid}/fill-held-draft')
async def acceptance_fill_held_draft(sid: str):
    """Place a near-limit synthetic draft before the next real STT segment."""
    main.store.get(sid, main.OWNER)
    channel = main.voice._sessions[sid]
    channel.defer_answers = True
    channel.held_answers = [(('Draft thought. ' * 900)[:11990], {})]
    return {'synthetic_draft_characters': 11990}


app.router.routes.insert(0, app.router.routes.pop())


@app.post('/api/acceptance/voice/{sid}/fail-tts')
async def acceptance_fail_tts(sid: str):
    """Inject one model outage through the real pipeline in this harness only."""
    main.store.get(sid, main.OWNER)
    class FailedSynthesis:
        def create(self, *args, **kwargs):
            raise RuntimeError('Synthetic TTS outage for recovery acceptance')
    if not hasattr(main.voice, '_acceptance_original_kokoro'):
        main.voice._acceptance_original_kokoro = main.voice._kokoro_model
    main.voice._kokoro_model = FailedSynthesis()
    return {'fault': 'synthetic_tts_failure'}


app.router.routes.insert(0, app.router.routes.pop())


@app.post('/api/acceptance/voice/{sid}/restore-tts')
async def acceptance_restore_tts(sid: str):
    main.store.get(sid, main.OWNER)
    main.voice._kokoro_model = main.voice._acceptance_original_kokoro
    return {'restored': True}


app.router.routes.insert(0, app.router.routes.pop())

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('ACCEPTANCE_PORT', '8001')), workers=1)
