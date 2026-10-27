"""Compare synthetic session persistence on mounted and native WSL filesystems."""
import json
import statistics
import tempfile
import time
from pathlib import Path

from interviewer.sessions import CreateSession, Sessions
from interviewer.store import Store


root = Path(__file__).resolve().parents[1]
result = {
    'scope': 'Synthetic SQLite sessions only; no provider, speech, runner or candidate execution. Separate temporary databases; no user-data migration.',
    'profiles': [],
}
for label, parent in [('repository_filesystem', root/'data'), ('native_temporary_filesystem', Path(tempfile.gettempdir()))]:
    samples = []
    with tempfile.TemporaryDirectory(prefix='fieldnote-storage-probe-', dir=parent) as directory:
        store = Store(Path(directory)/'interviews.sqlite3')
        session = Sessions(store).create(CreateSession(
            context='Built a synthetic API with explicit cache invalidation.',
            claims=[{'source_bullet': 'Built a synthetic API'}], role='backend',
            experience='junior', cloud_consent=True, idempotency_key='synthetic-storage-profile'),
            'synthetic-owner', {'provider': 'groq', 'config': store.settings()['providers']['groq']})
        session['turns'].append({'id': 'synthetic-turn', 'role': 'assistant', 'text': '',
                                 'version': 1, 'stage': session['stage'], 'delivery': 'generating'})
        with store.transaction() as db:
            store.save(db, session)
        for index in range(60):
            start = time.perf_counter()
            # Match the current streaming path: authoritative read, transactional
            # recheck, persisted growing text before publishing each delta.
            state = store.get(session['id'], 'synthetic-owner')
            with store.transaction() as db:
                state = store.get(session['id'], 'synthetic-owner', db)
                state['turns'][-1]['text'] += ' synthetic delta'
                store.save(db, state)
            samples.append(time.perf_counter()-start)
        result['profiles'].append({
            'filesystem_basis': label, 'parent_directory': str(parent),
            'sample_count': len(samples), 'session_json_bytes': len(json.dumps(state).encode()),
            'median_seconds_per_delta': statistics.median(samples),
            'p95_seconds_per_delta': sorted(samples)[56],
            'p95_method': 'nearest rank: ceil(0.95 * 60), one-based',
            'total_seconds': sum(samples),
        })
(root/'docs/sqlite-storage-profiles.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
