from __future__ import annotations

from typing import Any

import pytest

from ams.decomposer import DecompositionError, IntentDecomposer
from core.registry import build_default_registry


@pytest.fixture
def registry() -> Any:
    return build_default_registry()


def _make_decomposer(monkeypatch, registry) -> IntentDecomposer:
    # Ensure API key is present so constructor passes, but we'll mock network calls.
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    decomposer = IntentDecomposer(registry=registry)
    return decomposer


def test_decompose_success_single_attempt(monkeypatch, registry) -> None:
    decomposer = _make_decomposer(monkeypatch, registry)

    # Return a minimal valid DAG with a single existing primitive and no edges.
    response_json = '{"nodes": ["UTF8_DECODE"], "edges": []}'

    def fake_call(system_prompt: str, user_prompt: str) -> str:
        return response_json

    monkeypatch.setattr(decomposer, "_call_model", fake_call)

    graph = decomposer.decompose("decode some text", principal="u", max_retries=1)
    assert "UTF8_DECODE" in graph.graph.nodes()


def test_decompose_retries_on_validation_failure(monkeypatch, registry) -> None:
    decomposer = _make_decomposer(monkeypatch, registry)

    # First response: introduce a simple cycle using two known primitives.
    bad_resp = '{"nodes": ["UTF8_DECODE", "TEXT_LAYOUT"], "edges": [["UTF8_DECODE", "TEXT_LAYOUT"], ["TEXT_LAYOUT", "UTF8_DECODE"]]}'
    # Second response: valid single-node graph.
    good_resp = '{"nodes": ["UTF8_DECODE"], "edges": []}'

    calls = {"count": 0}

    def fake_call(system_prompt: str, user_prompt: str) -> str:
        calls["count"] += 1
        return bad_resp if calls["count"] == 1 else good_resp

    monkeypatch.setattr(decomposer, "_call_model", fake_call)

    graph = decomposer.decompose("some intent", principal="u", max_retries=3)
    assert calls["count"] >= 2
    assert "UTF8_DECODE" in graph.graph.nodes()


def test_decompose_raises_after_max_retries(monkeypatch, registry) -> None:
    decomposer = _make_decomposer(monkeypatch, registry)

    def fake_call(system_prompt: str, user_prompt: str) -> str:
        # Always return invalid JSON.
        return "not-json"

    monkeypatch.setattr(decomposer, "_call_model", fake_call)

    with pytest.raises(DecompositionError):
        decomposer.decompose("will fail", principal="u", max_retries=2)

