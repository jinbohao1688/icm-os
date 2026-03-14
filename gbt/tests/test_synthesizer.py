from __future__ import annotations

from gbt.sir import BasicBlockSummary, SemanticIR
from gbt.synthesizer import CodeSynthesizer


def test_synthesizer_produces_pseudo_assembly() -> None:
    sir = SemanticIR(
        source_binary="dummy.bin",
        source_isa="arm64",
        cfg_nodes=["0x1000"],
        cfg_edges=[],
        dfg_edges=[],
        block_summaries={
            "0x1000": BasicBlockSummary(
                description="increment a counter",
                preconditions="counter in x0",
                postconditions="counter+1 in x0",
                roles=["ARITHMETIC"],
                safety="safe",
            )
        },
        patterns=["LOOP"],
        cached_at="2026-01-01T00:00:00Z",
    )
    synth = CodeSynthesizer()
    asm = synth.synthesize(sir, dst_isa="x86-64")
    assert "Synthesized from dummy.bin" in asm
    assert "increment a counter" in asm
    assert "L1000:" in asm or "0x1000" in asm

