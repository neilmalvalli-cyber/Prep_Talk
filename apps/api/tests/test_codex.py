import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from interviewer import codex_provider, practice_review
from interviewer.providers import Providers, ProviderFailure
from interviewer.sessions import interview_plan


@pytest.mark.asyncio
@pytest.mark.parametrize('item,completed,exit_code,ok', [
    ('agent_message', True, 0, True), ('agent_message', False, 0, False),
    ('agent_message', True, 1, False), ('command_execution', True, 0, False),
])
async def test_cli_isolated_and_requires_success(monkeypatch, tmp_path, item, completed, exit_code, ok):
    monkeypatch.setenv('FIELDNOTE_DATA', str(tmp_path))
    monkeypatch.setenv('OPENROUTER_API_KEY', 'must-not-inherit')
    monkeypatch.setattr(codex_provider, 'executable', lambda: 'codex')
    seen = {}
    class Input:
        def write(self, value): seen['prompt'] = value
        async def drain(self): pass
        def close(self): pass
    events = [{'type':'item.completed','item':{'type':'error','message':'diagnostic'}},
              {'type':'item.completed','item':{'type':item,'text':'Ready'}}]
    if completed: events.append({'type':'turn.completed'})
    reader = asyncio.StreamReader()
    reader.feed_data(('\n'.join(json.dumps(e) for e in events)).encode())
    reader.feed_eof()
    class Process:
        stdin = Input()
        stdout = reader
        returncode = exit_code
        async def wait(self): return self.returncode
    async def spawn(*args, **kwargs):
        seen.update(args=args, **kwargs)
        return Process()
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    client = codex_provider.CodexClient()
    if ok:
        assert await client.complete([{'role':'user','content':'synthetic candidate'}]) == 'Ready'
    else:
        with pytest.raises(ProviderFailure):
            await client.complete([{'role':'user','content':'synthetic candidate'}])
    assert 'OPENROUTER_API_KEY' not in seen['env']
    assert 'synthetic candidate' not in str(seen['args'])
    assert b'synthetic candidate' in seen['prompt']
    assert seen['args'][seen['args'].index('--model')+1] == 'gpt-6-luna'
    assert '--ignore-user-config' in seen['args']
    assert 'features.shell_tool=false' in seen['args']
    assert not list((tmp_path/'codex-jobs').iterdir())
    assert not client.slot.locked()


@pytest.mark.asyncio
async def test_codex_provider_never_uses_http_or_fallback(monkeypatch):
    provider = Providers()
    monkeypatch.setattr(provider.client, 'post', AsyncMock(side_effect=AssertionError('HTTP forbidden')))
    monkeypatch.setattr(provider.codex, 'complete', AsyncMock(return_value='A question?'))
    snapshot = {'provider':'codex','config':{'live_model':'gpt-6-luna','assessment_model':'gpt-6-luna'}}
    chunks = [part async for part in provider.stream(snapshot, [])]
    assert ''.join(part['text'] for part in chunks) == 'A question?'
    monkeypatch.setattr(provider.codex, 'complete', AsyncMock(side_effect=ProviderFailure('codex_failure','Failed')))
    with pytest.raises(ProviderFailure):
        _ = [part async for part in provider.stream(snapshot, [])]
    await provider.client.aclose()


def test_practice_review_quote_version_and_score_invariants():
    expected = [{'utterance_id':'answer','source_version':2,'answer':'A cache can return stale data.'}]
    session = {'turns':[], 'stage':'CODING','revision':4,'snapshot':{'config':{'assessment_model':'gpt-6-luna'}}}
    value = {'summary':'Practice only','answers':[{'utterance_id':'answer','source_version':2,'quote':'stale data','score':3,'verdict':'correct','reason':'Explanation','improvement':'Example'}],'limitations':[]}
    result = practice_review.validate(value, expected, session, [])
    assert result['overall_score'] == 75
    for field, invalid in [('quote','invented quote'),('source_version',1),('score',None),('verdict','incorrect')]:
        broken = json.loads(json.dumps(value))
        broken['answers'][0][field] = invalid
        with pytest.raises(ValueError): practice_review.validate(broken, expected, session, [])
    value['answers'][0].update(score=None,verdict='not_assessable')
    assert practice_review.validate(value, expected, session, [])['overall_score'] is None
    value['answers'] *= 2
    with pytest.raises(ValueError): practice_review.validate(value, expected, session, [])


def test_practice_signature_changes_with_corrections_and_execution():
    session = {'turns':[{'id':'a','text':'first','version':1}], 'stage':'CODING'}
    initial = practice_review.signature(session, [])
    session['turns'][0].update(text='corrected',version=2)
    assert practice_review.signature(session, []) != initial
    assert practice_review.signature(session, [{'status':'complete'}]) != practice_review.signature(session, [])


@pytest.mark.parametrize('score,phrase', [(0, '0 out of 100'), (None, 'not enough assessable evidence')])
def test_spoken_feedback_preserves_zero_and_unassessable_scores(score, phrase):
    text = practice_review.spoken_feedback({'overall_score': score, 'summary': 'Recorded feedback.', 'answers': []})
    assert phrase in text and 'Recorded feedback.' in text
    assert ('out of 100' in text) is (score is not None)


@pytest.mark.asyncio
async def test_cli_cancellation_stops_process_before_removing_scratch(monkeypatch, tmp_path):
    monkeypatch.setenv('FIELDNOTE_DATA', str(tmp_path))
    monkeypatch.setattr(codex_provider, 'executable', lambda: 'codex')
    started = asyncio.Event()
    seen = {}
    class Input:
        def write(self, value): pass
        async def drain(self): pass
        def close(self): pass
    class Output:
        async def read(self, size):
            started.set()
            await asyncio.Event().wait()
    class Process:
        stdin = Input()
        stdout = Output()
        returncode = None
        pid = 123456789
        async def wait(self):
            self.returncode = -9
            return -9
    process = Process()
    class Killer:
        async def wait(self): return 0
    async def spawn(*args, **kwargs):
        if args[0] == 'taskkill':
            assert seen['cwd'].exists()
            seen['killed'] = True
            return Killer()
        seen['cwd'] = kwargs['cwd']
        return process
    def killpg(*args):
        assert seen['cwd'].exists()
        seen['killed'] = True
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    monkeypatch.setattr(codex_provider.os, 'killpg', killpg, raising=False)
    client = codex_provider.CodexClient()
    task = asyncio.create_task(client.complete([]))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert seen['killed']
    assert not seen['cwd'].exists()
    assert not client.slot.locked()
