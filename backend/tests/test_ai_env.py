import os
import pytest
from app.core.settings import get_settings, reset_settings_cache
from app.ai.agent import FiveWhysAI


def test_agent_uses_settings_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "dummy-key")
    reset_settings_cache()
    settings = get_settings()
    assert getattr(settings, "GROQ_API_KEY", None) == "dummy-key"
    agent = FiveWhysAI(model_name="test-model")
    internal_agent = agent._resolve_model()
    assert internal_agent is not None


@pytest.mark.parametrize("missing", ["", None])
def test_agent_missing_key_raises(monkeypatch, missing):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    if missing:
        monkeypatch.setenv("GROQ_API_KEY", missing)
    reset_settings_cache()
    agent = FiveWhysAI(model_name="test-model")
    with pytest.raises(Exception) as exc:
        agent._resolve_model()
    assert "Missing GROQ_API_KEY" in str(exc.value)
