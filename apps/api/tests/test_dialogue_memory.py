import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from interviewer import main
from interviewer.dialogue_memory import Coverage, current_memory, memory_context, memory_input, transcript_signature, validate_coverage
from interviewer.providers import ProviderFailure
from interviewer.sessions import CreateSession, Sessions, dialogue_request_kind
from interviewer.store import Store


@pytest.fixture
def state(tmp_path, monkeypatch):
    store = Store(tmp_path/'memory.sqlite3')
    service = Sessions(store)
    config = store.settings()['providers']['groq']
    session = service.create(CreateSession(context='A confirmed cache project.', claims=[{'source_bullet': 'Built a cache.'}],
        role='backend', experience='junior', cloud_consent=True, idempotency_key='memory-create'), main.LEGACY_OWNER,
        {'provider': 'groq', 'config': config})
    turns = [dict(id='q1', role='assistant', text='What expiration did you use?', version=1, delivery='complete', stage=session['stage']),
             dict(id='a1', role='user', text='TTL only, sixty seconds.', version=1, delivery='complete', stage=session['stage']),
             dict(id='q2', role='assistant', text='How long did cached values live?', version=1, delivery='complete', stage=session['stage']),
             dict(id='a2', role='user', text='The same sixty seconds.', version=1, delivery='complete', stage=session['stage']),
             dict(id='q3', role='assistant', text='What about writes before expiration?', version=1, delivery='complete', stage=session['stage'])]
    session['turns'] = turns
    for turn in turns:
        if turn['role'] == 'user':
            turn.update(support_level='independent', versions=[{'version': 1, 'text': turn['text'], 'kind': 'original'}])
    with store.transaction() as db:
        for turn in turns:
            if turn['role'] == 'user':
                store.event(db, session, 'answer', {'utterance_id': turn['id'], 'version': 1, 'text': turn['text']})
        store.save(db,session,main.LEGACY_OWNER)
    monkeypatch.setattr(main, 'store', store)
    monkeypatch.setattr(main, 'sessions', service)
    monkeypatch.setattr(main, 'memory_tasks', {})
    monkeypatch.setattr(main, 'generations', {})
    monkeypatch.setattr(main.providers, 'structured', AsyncMock())
    inputs = memory_input(session, store.events(session['id']), dialogue_request_kind)
    source = next(t for t in inputs['transcript'] if t['id'] == 'a1')
    value = {'answered_points': [{'question_turn_ids': ['q1', 'q2'], 'answers': [
        {'utterance_id': 'a1', 'source_version': 1, 'event_id': source['event_id'], 'quote': 'TTL only, sixty seconds.'}]}],
        'unresolved_details': [{'question_turn_id': 'q3', 'excerpt': 'writes before expiration'}]}
    main.providers.structured.return_value = value
    return session, inputs, value


@pytest.mark.asyncio
async def test_memory_groups_paraphrases_with_exact_evidence_and_enters_live_context(state):
    session, inputs, value = state
    await main.refresh_dialogue_memory(session['id'], session, inputs, 2)
    stored = main.store.get(session['id'], main.LEGACY_OWNER)
    assert current_memory(stored)['coverage'] == value
    assert stored['revision'] == session['revision']  # No action revision race.
    prompt = main.sessions.prompt(stored)
    assert 'grounded_dialogue_memory' in prompt[1]['content']
    assert 'TTL only, sixty seconds.' in prompt[1]['content']
    assert 'writes before expiration' in prompt[1]['content']
    assert main.providers.structured.call_args.args[0] == session['snapshot']
    assert 'hidden' not in main.providers.structured.call_args.args[1][1]['content']
    assert '_dialogue_memory' not in main.sessions.view(stored)
    assert main.store.events(session['id'])[-1]['kind'] == 'dialogue_memory_finished'
    assert 'coverage' not in main.store.events(session['id'])[-1]


@pytest.mark.parametrize('change', ['foreign_answer', 'foreign_question', 'wrong_version', 'wrong_event', 'invented_quote', 'invented_detail', 'extra', 'request_only', 'cross_stage', 'future_question'])
def test_memory_rejects_unowned_or_unverifiable_selection(state, change):
    session, inputs, value = deepcopy(state)
    answer = value['answered_points'][0]['answers'][0]
    if change == 'foreign_answer': answer['utterance_id'] = 'foreign'
    elif change == 'foreign_question': value['answered_points'][0]['question_turn_ids'] = ['foreign']
    elif change == 'wrong_version': answer['source_version'] = 2
    elif change == 'wrong_event': answer['event_id'] = 'foreign'
    elif change == 'invented_quote': answer['quote'] = 'I verified every write.'
    elif change == 'invented_detail': value['unresolved_details'][0]['excerpt'] = 'unasked detail'
    elif change == 'extra': answer['rating'] = 0
    elif change == 'request_only': next(t for t in inputs['transcript'] if t['id']=='a1')['request_kind'] = 'uncertainty'
    elif change == 'cross_stage': next(t for t in inputs['transcript'] if t['id']=='a1')['stage'] = 'COACHED_RETRY'
    elif change == 'future_question': value['answered_points'][0]['question_turn_ids'] = ['q3']
    with pytest.raises(ValueError): validate_coverage(value, inputs)


@pytest.mark.asyncio
async def test_correction_invalidates_cache_read_only_and_late_result_cannot_publish(state):
    session, inputs, value = state
    await main.refresh_dialogue_memory(session['id'], session, inputs, 2)
    with main.store.transaction() as db:
        changed = main.store.get(session['id'], main.LEGACY_OWNER, db)
        changed['turns'][1].update(text='Explicit invalidation, not TTL.', version=2)
        main.store.save(db,changed,main.LEGACY_OWNER)
    before = main.store.events(session['id'])
    assert current_memory(changed) is None
    assert memory_context(changed)['status'] == 'unavailable'
    await main.refresh_dialogue_memory(session['id'], session, inputs, 2)
    assert main.store.events(session['id']) == before
    assert current_memory(main.store.get(session['id'], main.LEGACY_OWNER)) is None


@pytest.mark.asyncio
@pytest.mark.parametrize('retire', ['delete', 'pause', 'generation', 'answer'])
async def test_late_memory_never_mutates_retired_or_changed_work(state, retire):
    session, inputs, value = state
    with main.store.transaction() as db:
        changed = main.store.get(session['id'], main.LEGACY_OWNER, db)
        if retire == 'delete': db.execute('DELETE FROM sessions WHERE id=?', (session['id'],))
        else:
            if retire == 'pause': changed['paused'] = True
            elif retire == 'generation': changed['generation_id'] = 'new-generation'
            else: changed['turns'].append(dict(id='new', role='user', text='Another answer.', version=1, stage=changed['stage'], delivery='complete'))
            main.store.save(db,changed,main.LEGACY_OWNER)
    before = main.store.events(session['id'])
    await main.refresh_dialogue_memory(session['id'], session, inputs, 2)
    assert main.store.events(session['id']) == before
    if retire != 'delete': assert '_dialogue_memory' not in main.store.get(session['id'], main.LEGACY_OWNER)


@pytest.mark.asyncio
async def test_optional_memory_failure_keeps_dialogue_available_and_no_findings(state):
    session, inputs, value = state
    main.providers.structured.side_effect = ProviderFailure('network', 'Unavailable')
    await main.refresh_dialogue_memory(session['id'], session, inputs, 2)
    stored = main.store.get(session['id'], main.LEGACY_OWNER)
    assert not stored['paused'] and stored['last_error'] is None and stored['findings'] == []
    assert current_memory(stored) is None
    assert main.store.events(session['id'])[-1]['status'] == 'unavailable'


@pytest.mark.asyncio
async def test_background_memory_is_bounded_and_yields_to_cancellation(state):
    session, inputs, value = state
    entered, released = asyncio.Event(), asyncio.Event()
    async def held(*args):
        entered.set()
        try: await asyncio.Event().wait()
        finally: released.set()
    main.providers.structured.side_effect = held
    main.schedule_dialogue_memory(session['id'])
    task = main.memory_tasks[session['id']]
    await entered.wait()
    main.schedule_dialogue_memory(session['id'])
    assert main.memory_tasks[session['id']] is task
    await main.cancel_generation(session['id'], interrupt_voice=False)
    assert released.is_set() and task.cancelled() and not main.memory_tasks
    assert '_dialogue_memory' not in main.store.get(session['id'], main.LEGACY_OWNER)


def test_memory_schema_is_closed_and_all_fields_required():
    schema = Coverage.model_json_schema()
    for model in [schema, *schema['$defs'].values()]:
        assert model['additionalProperties'] is False
        assert set(model['required']) == set(model['properties'])


@pytest.mark.asyncio
async def test_live_response_preempts_background_memory_without_waiting(state, monkeypatch):
    session, inputs, value = state
    entered = asyncio.Event()
    async def held(*args):
        entered.set()
        await asyncio.Event().wait()
    main.providers.structured.side_effect = held
    main.schedule_dialogue_memory(session['id'])
    memory_task = main.memory_tasks[session['id']]
    await entered.wait()
    live = AsyncMock()
    monkeypatch.setattr(main, 'generate', live)
    main.start_generation(session['id'])
    await main.generations[session['id']]
    await asyncio.gather(memory_task, return_exceptions=True)
    live.assert_awaited_once_with(session['id'], repeated_text=None)
    assert memory_task.cancelled()
