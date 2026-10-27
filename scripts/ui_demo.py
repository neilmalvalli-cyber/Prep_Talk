"""Run the API with a synthetic interviewer so the UI can be explored without a provider key.

Usage, from the repository root (instead of the normal API command):
    Windows:  apps\\api\\.venv\\Scripts\\python.exe scripts\\ui_demo.py
    Linux:    apps/api/.venv/bin/python scripts/ui_demo.py

Questions and practice reviews are canned text, not AI output. Demo interviews are
stored separately under data/browser-acceptance, never with real interviews.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'apps' / 'api'), str(ROOT)]
os.environ.setdefault('FIELDNOTE_ORIGIN', 'http://localhost:5173')

from evals import browser_server as harness  # noqa: E402

Synthetic = harness.SyntheticProvider
base_catalog, base_structured = Synthetic.catalog, Synthetic.structured


async def catalog(self, provider):
    result = await base_catalog(self, provider)
    if provider == 'codex':
        row = {'id': 'gpt-6-luna', 'name': 'Luna', 'supported_parameters': ['structured_outputs']}
        result['models'].append(row)
        self.catalogs[provider][1][row['id']] = row
    # The settings screen lists review models by this flag, as the real catalogue sets it.
    for row in result['models']:
        row['structured_outputs'] = True
    return result


async def structured(self, snapshot, messages, schema):
    properties = schema.get('properties', {})
    if 'summary' not in properties or 'answers' not in properties:
        return await base_structured(self, snapshot, messages, schema)
    data = json.loads(messages[-1]['content'].split('\n', 1)[1])
    answers = []
    for index, answer in enumerate(data['answers']):
        score = [3, 2, 4, 1][index % 4]
        answers.append({'utterance_id': answer['utterance_id'], 'source_version': answer['source_version'],
                        'quote': answer['answer'][:80], 'score': score, 'verdict': 'correct' if score >= 3 else 'partial',
                        'reason': 'Demo review: you named the mechanism but did not connect it to the failure the question asked about.',
                        'improvement': 'Walk through one request end to end, then say how you would measure the result.'})
    return {'summary': 'Demo review. You explained the main decision clearly and named a trade-off.\n\n'
                       'The main gap is what a user sees while the system is in an intermediate state.\n\n'
                       'Practise one answer that walks a single request through the change, end to end.',
            'answers': answers, 'limitations': ['Synthetic demo review; not produced by an AI model.']}


Synthetic.catalog, Synthetic.structured = catalog, structured

if __name__ == '__main__':
    import uvicorn
    print('PrepTalk UI demo: synthetic interviewer, no provider key needed.')
    uvicorn.run(harness.app, host='127.0.0.1', port=8000, workers=1)
