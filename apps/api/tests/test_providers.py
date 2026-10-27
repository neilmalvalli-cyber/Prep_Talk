import json

import httpx
import pytest

from interviewer.providers import ProviderConfig, ProviderFailure, Providers


def snapshot(provider='groq'):
    return {'provider': provider, 'config': {'live_model': 'openai/gpt-oss-20b', 'assessment_model': 'openai/gpt-oss-120b', 'live_route': 'approved-route', 'assessment_route': 'approved-route', 'paid_opt_in': True}}


@pytest.mark.asyncio
async def test_stream_content_only_and_no_reasoning(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-test-secret')
    seen = []
    def handle(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, text=': ping\n\ndata: {"choices":[{"delta":{"reasoning":"private"}}]}\n\ndata: {"choices":[{"delta":{"content":"What "}}]}\n\ndata: {"choices":[{"delta":{"content":"changed?"}}]}\n\ndata: [DONE]\n\n')
    p = Providers()
    await p.client.aclose()
    p.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    pieces = [c['text'] async for c in p.stream(snapshot(), [{'role': 'user', 'content': 'TTL only'}])]
    assert ''.join(pieces) == 'What changed?'
    assert seen[0]['include_reasoning'] is False
    assert seen[0]['reasoning_effort'] == 'low'
    await p.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('status,code', [(401,'authentication'),(402,'insufficient_credits'),(404,'unavailable_model'),(429,'rate_limit'),(413,'context_overflow')])
async def test_distinct_provider_errors(monkeypatch, status, code):
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-test-secret')
    p = Providers()
    await p.client.aclose()
    p.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status, headers={'Retry-After': '5'})))
    with pytest.raises(ProviderFailure) as exc:
        _ = [c async for c in p.stream(snapshot(), [])]
    assert exc.value.code == code
    assert exc.value.retry_after == '5'
    await p.client.aclose()


@pytest.mark.asyncio
async def test_partial_stream_not_retried(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'synthetic-test-secret')
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Partial"}}]}\n\ndata: {"error":{"message":"upstream died"}}\n\n')
    p = Providers()
    await p.client.aclose()
    p.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    chunks = []
    with pytest.raises(ProviderFailure) as exc:
        async for c in p.stream(snapshot('openrouter'), []):
            chunks.append(c['text'])
    assert chunks == ['Partial']
    assert exc.value.code == 'partial_stream'
    assert len(calls) == 1
    body = json.loads(calls[0].content)
    assert body['provider'] == {'only': ['approved-route'], 'allow_fallbacks': False, 'require_parameters': True}
    assert 'reasoning_effort' not in body
    await p.client.aclose()


def test_provider_structured_uses_selected_assessment_model():
    p = Providers()
    body = p.body(snapshot('openrouter'), [], 'assessment', {'type': 'object'})
    assert body['model'] == 'openai/gpt-oss-120b'
    assert body['stream'] is False
    assert body['response_format']['json_schema']['strict'] is True


READY_SCHEMA = {'type':'object','properties':{'ready':{'type':'boolean'}},
                'required':['ready'],'additionalProperties':False}


def test_live_budgets_are_provider_specific_without_relaxing_routing():
    p = Providers()
    groq = p.body(snapshot('groq'), [])
    routed = p.body(snapshot('openrouter'), [])
    assert groq['max_tokens'] == 300 and groq['reasoning_effort'] == 'low'
    assert groq['include_reasoning'] is False
    assert routed['max_tokens'] == 1200
    assert 'reasoning_effort' not in routed and 'include_reasoning' not in routed
    assert routed['provider'] == {'only': ['approved-route'], 'allow_fallbacks': False, 'require_parameters': True}


@pytest.mark.asyncio
@pytest.mark.parametrize('provider',['groq','openrouter'])
@pytest.mark.parametrize('content',[
    '{"ready":1}', '{"ready":"true"}', '{}', '{"ready":true,"extra":"instruction"}',
    '[]', '{"ready":NaN}', 'not JSON',
])
async def test_structured_output_is_locally_validated_without_retry(monkeypatch,provider,content):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    monkeypatch.setenv('OPENROUTER_API_KEY','synthetic-test-secret')
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':content}}]})
    p=Providers()
    await p.client.aclose()
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(ProviderFailure) as error:
            await p.structured(snapshot(provider),[],READY_SCHEMA)
        assert error.value.code=='malformed_output'
        assert len(calls)==1
        assert 'synthetic-test-secret' not in error.value.message
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('choice',[
    {'finish_reason':'length','message':{'content':'{"ready":true}'}},
    {'finish_reason':'stop','message':{'content':'{"ready":true}','refusal':'Cannot comply'}},
    {'message':{'content':None}},
    {'message':[]},
])
async def test_structured_refusal_truncation_and_malformed_envelope_are_unavailable(monkeypatch,choice):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers()
    await p.client.aclose()
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'choices':[choice]})))
    try:
        with pytest.raises(ProviderFailure,match='factual review remains available'):
            await p.structured(snapshot(),[],READY_SCHEMA)
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
async def test_structured_local_schema_references_work_and_remote_references_do_not_fetch(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers()
    await p.client.aclose()
    calls=[]
    def handle(request):
        calls.append(str(request.url))
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ready":true}'}}]})
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    try:
        local={'$defs':{'result':READY_SCHEMA},'$ref':'#/$defs/result'}
        assert await p.structured(snapshot(),[],local)=={'ready':True}
        with pytest.raises(ProviderFailure):
            await p.structured(snapshot(),[],{'$ref':'https://untrusted.invalid/schema'})
        assert len(calls)==2
        assert all(url.startswith('https://api.groq.com/') for url in calls)
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('event',[[],None,{'choices':{}},{'choices':[None]},
    {'choices':[{'delta':'wrong'}]},{'choices':[{'delta':[]}]},
    {'choices':[{'delta':{'content':{'text':'wrong'}}}]}, {'choices':[{'finish_reason':{}}]}])
async def test_malformed_live_event_is_a_typed_failure(monkeypatch,event):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers()
    await p.client.aclose()
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,text='data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n')))
    try:
        with pytest.raises(ProviderFailure) as error:
            _=[chunk async for chunk in p.stream(snapshot(),[])]
        assert error.value.code=='malformed_output'
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
async def test_live_usage_only_event_is_retained(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers()
    await p.client.aclose()
    events=[{'choices':[{'delta':{'content':'A question?'}}]},
            {'choices':[],'usage':{'total_tokens':12}}]
    stream=''.join('data: '+json.dumps(event)+'\n\n' for event in events)
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,text=stream+'data: [DONE]\n\n')))
    try:
        chunks=[chunk async for chunk in p.stream(snapshot(),[])]
        assert chunks[-1]['text']=='' and chunks[-1]['usage']=={'total_tokens':12}
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
async def test_empty_completed_stream_is_not_a_completed_question(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers()
    await p.client.aclose()
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,text='data: {"choices":[]}\n\ndata: [DONE]\n\n')))
    try:
        with pytest.raises(ProviderFailure) as error:
            _=[chunk async for chunk in p.stream(snapshot(),[])]
        assert error.value.code=='empty_response'
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
async def test_live_truncated_response_preserves_text_and_reports_incomplete(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers()
    await p.client.aclose()
    truncated={'choices':[{'delta':{'content':'Partial'},'finish_reason':'length'}]}
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,text='data: '+json.dumps(truncated)+'\n\ndata: [DONE]\n\n')))
    delivered=[]
    try:
        with pytest.raises(ProviderFailure) as error:
            async for chunk in p.stream(snapshot(),[]):
                delivered.append(chunk['text'])
        assert error.value.code=='incomplete_response' and delivered==['Partial']
    finally:
        await p.client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize('body',[None,[],{}, {'data':None},{'data':[None]}, {'data':[{'id':[]}]}])
async def test_malformed_model_catalog_is_typed_and_does_not_replace_cached_catalog(monkeypatch,body):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-secret')
    p=Providers();await p.client.aclose()
    p.catalogs['groq']=(1,{'known/model':{'id':'known/model'}})
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json=body)))
    try:
        with pytest.raises(ProviderFailure) as error:await p.catalog('groq')
        assert error.value.code=='malformed_output'
        assert p.catalogs['groq'][0]==1
    finally:await p.client.aclose()


@pytest.mark.asyncio
async def test_openrouter_catalog_keeps_explicit_models_beside_dynamic_aliases(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'synthetic-test-secret')
    rows = [{'id': value, 'supported_parameters': ['structured_outputs']} for value in (
        'openai/gpt-oss-20b', '~openai/gpt-sol-latest', 'openrouter/auto',
        'openrouter/free', 'openrouter/fusion', 'vendor/model:free')]
    p = Providers()
    await p.client.aclose()
    p.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={'data': rows})))
    try:
        catalog = await p.catalog('openrouter')
        assert [row['id'] for row in catalog['models']] == ['openai/gpt-oss-20b', 'vendor/model:free']
        assert set(p.catalogs['openrouter'][1]) == {'openai/gpt-oss-20b', 'vendor/model:free'}
    finally:
        await p.client.aclose()


@pytest.mark.parametrize('model', ['~openai/gpt-sol-latest', 'openrouter/auto', 'openrouter/free', 'openrouter/fusion'])
def test_dynamic_model_selection_is_rejected(model):
    with pytest.raises(ValueError, match='explicit valid model'):
        ProviderConfig(live_model=model, assessment_model='vendor/model')


@pytest.mark.asyncio
@pytest.mark.parametrize('failure,code',[(httpx.ReadTimeout,'timeout'),(httpx.ConnectError,'network')])
async def test_endpoint_catalog_network_failures_are_typed(monkeypatch,failure,code):
    monkeypatch.setenv('OPENROUTER_API_KEY','synthetic-test-secret')
    def broken(request):raise failure('synthetic',request=request)
    p=Providers();await p.client.aclose()
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(broken))
    try:
        with pytest.raises(ProviderFailure) as error:await p.endpoints('vendor/model')
        assert error.value.code==code
    finally:await p.client.aclose()


@pytest.mark.asyncio
async def test_structured_rate_limit_also_blocks_live_without_retry(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic')
    p=Providers()
    await p.client.aclose()
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(429,headers={'Retry-After':'18'},json={'error':{'message':'private provider details'}})
    p.client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    with pytest.raises(ProviderFailure) as exc:
        await p.structured(snapshot(),[],READY_SCHEMA)
    assert '18 seconds' in exc.value.message
    assert 'private' not in exc.value.message
    with pytest.raises(ProviderFailure):
        _=[chunk async for chunk in p.stream(snapshot(),[])]
    assert len(calls)==1
    await p.client.aclose()
