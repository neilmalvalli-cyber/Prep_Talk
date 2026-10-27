"""Unit/HTTP tests must not inherit locally configured integration credentials."""
import pytest


@pytest.fixture(autouse=True)
def isolate_external_configuration(monkeypatch):
    for name in ('GROQ_API_KEY', 'OPENROUTER_API_KEY', 'RUNNER_URL', 'RUNNER_BEARER_TOKEN'):
        monkeypatch.delenv(name, raising=False)
