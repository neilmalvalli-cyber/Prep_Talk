import asyncio
import json

import pytest

from interviewer import body_limit


@pytest.mark.asyncio
@pytest.mark.parametrize('declared',[None,b'1'])
async def test_actual_chunked_bytes_are_bounded_before_parser_runs(monkeypatch,declared):
    monkeypatch.setattr(body_limit,'REQUEST_LIMIT',8)
    called=[]
    async def downstream(*args):called.append(True)
    messages=iter([{'type':'http.request','body':b'12345','more_body':True},
                   {'type':'http.request','body':b'6789','more_body':False}])
    async def receive():return next(messages)
    sent=[]
    async def send(message):sent.append(message)
    headers=[] if declared is None else [(b'content-length',declared)]
    await body_limit.BodyLimit(downstream)({'type':'http','method':'POST','path':'/api/resumes','headers':headers},receive,send)
    assert called==[]
    assert sent[0]['status']==413
    assert json.loads(sent[1]['body'])=={'detail':'Request exceeds upload limit'}


@pytest.mark.asyncio
async def test_valid_chunked_body_is_replayed_exactly_once(monkeypatch):
    monkeypatch.setattr(body_limit,'REQUEST_LIMIT',8)
    messages=iter([{'type':'http.request','body':b'1234','more_body':True},
                   {'type':'http.request','body':b'5678','more_body':False},
                   {'type':'http.disconnect'}])
    async def receive():return next(messages)
    async def downstream(scope,read,send):
        assert await read()=={'type':'http.request','body':b'12345678','more_body':False}
        assert await read()=={'type':'http.disconnect'}
    await body_limit.BodyLimit(downstream)({'type':'http','method':'POST','path':'/api/resumes'},receive,None)


@pytest.mark.asyncio
async def test_timeout_and_abandoned_body_never_reach_parser(monkeypatch):
    monkeypatch.setattr(body_limit,'RECEIVE_TIMEOUT',0.01)
    called=[]
    async def downstream(*args):called.append(True)
    sent=[]
    async def send(message):sent.append(message)
    async def slow():await asyncio.Event().wait()
    scope={'type':'http','method':'PATCH','path':'/api/settings'}
    await body_limit.BodyLimit(downstream)(scope,slow,send)
    assert sent[0]['status']==408 and called==[]
    async def disconnected():return {'type':'http.disconnect'}
    sent.clear()
    await body_limit.BodyLimit(downstream)(scope,disconnected,send)
    assert sent==[] and called==[]
