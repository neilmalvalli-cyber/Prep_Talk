"""Inspect the production web artifact without printing credential values."""
import json
import os
import re
from pathlib import Path

from dotenv import dotenv_values


root = Path(__file__).resolve().parents[1]
files = [path for path in (root/'apps/web/dist').rglob('*') if path.is_file()]
if not files:
    raise SystemExit('Build the web application before checking its artifact.')
patterns = {
    'groq_key': re.compile(rb'gsk_[A-Za-z0-9]{20,}'),
    'openrouter_key': re.compile(rb'sk-or-v1-[A-Za-z0-9]{20,}'),
    'private_key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
}
values = dotenv_values(root/'.env') if (root/'.env').exists() else {}
configured = []
for name in ('GROQ_API_KEY', 'OPENROUTER_API_KEY', 'RUNNER_BEARER_TOKEN', 'FIELDNOTE_OWNER_KEY'):
    value = os.environ.get(name) or values.get(name)
    if value and len(value) >= 16:
        configured.append((name, value.encode()))
findings, sanitizer_files = [], []
for path in files:
    raw = path.read_bytes()
    for name, pattern in patterns.items():
        if pattern.search(raw):
            findings.append({'file': str(path.relative_to(root)), 'category': name})
    for name, value in configured:
        if value in raw:
            findings.append({'file': str(path.relative_to(root)), 'category': 'configured_'+name})
    if path.suffix == '.js' and b'3.4.17' in raw:
        sanitizer_files.append(path.name)
    if path.suffix == '.js' and b'3.4.15' in raw:
        findings.append({'file': str(path.relative_to(root)), 'category': 'old_vendored_sanitizer'})
result = {'scope': 'current production frontend artifact only', 'files_scanned': len(files),
          'configured_secret_values_checked': len(configured), 'findings': findings,
          'secret_values_printed': False, 'patched_sanitizer_files': sanitizer_files}
(root/'docs/public-artifact-secret-scan.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
raise SystemExit(0 if not findings and sanitizer_files else 1)
