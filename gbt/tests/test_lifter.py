from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from gbt.lifter import SemanticLifter
from gbt.sir import BasicBlockSummary, SemanticIR


class _DummyBlock:
    def __init__(self) -> None:
        class _Capstone:
            @property
            def insns(self) -> list[Any]:
                return []

            def __str__(self) -> str:
                return "nop"

        self.capstone = _Capstone()


class _DummyProject:
    def __init__(self) -> None:
        class _Factory:
            def block(self, addr: int) -> _DummyBlock:
                return _DummyBlock()

        self.factory = _Factory()


@pytest.fixture
def tmp_binary(tmp_path: Path) -> str:
    bin_path = tmp_path / "dummy.bin"
    bin_path.write_bytes(b"\x00\x00")
    return str(bin_path)


def test_lift_uses_cache_and_produces_sir(tmp_path: Path, monkeypatch: Any, tmp_binary: str) -> None:
    # Force cache directory into tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    lifter = SemanticLifter()

    # Stub out heavy analyses and LLM calls.
    monkeypatch.setattr(lifter, "load_binary", lambda path, arch: _DummyProject())
    monkeypatch.setattr(
        lifter,
        "extract_cfg",
        lambda project: (["0x1000"], [("0x1000", "0x1000")]),
    )
    monkeypatch.setattr(
        lifter,
        "extract_dfg",
        lambda project, nodes: [("0x1000", "0x1000")],
    )
    monkeypatch.setattr(
        lifter,
        "classify_safety",
        lambda block, project: "safe",
    )

    def fake_summary(disasm: str, safety: str) -> BasicBlockSummary:
        return BasicBlockSummary(
            description="do nothing",
            preconditions="none",
            postconditions="none",
            roles=["NO_OP"],
            safety=safety,
        )

    monkeypatch.setattr(lifter, "summarize_block_with_llm", fake_summary)

    sir = lifter.lift(tmp_binary, arch="arm64")
    assert isinstance(sir, SemanticIR)
    assert sir.cfg_nodes == ["0x1000"]
    assert "0x1000" in sir.block_summaries

    # Ensure cache file is created.
    cache_dir = os.path.expanduser("~/.icm-os/gbt_cache")
    assert any(p.suffix == ".json" for p in Path(cache_dir).glob("*.json"))

