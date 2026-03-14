from __future__ import annotations

import os

import pytest

from gbt.lifter import SemanticLifter
from gbt.translator import GBT


SAMPLE_ELF = os.path.join(os.path.dirname(__file__), "sample_arm64.elf")


@pytest.mark.skipif(not os.path.exists(SAMPLE_ELF), reason="需要先运行 compile_test.sh 编译 ELF")
def test_lift_real_arm64_binary(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", "test-key"))

    lifter = SemanticLifter()
    sir = lifter.lift_with_limit(SAMPLE_ELF, arch="arm64", max_blocks=5)

    assert sir.source_isa == "arm64"
    assert len(sir.cfg_nodes) > 0
    assert len(sir.block_summaries) > 0
    print(f"\n提取到 {len(sir.cfg_nodes)} 个基本块")
    for addr, summary in list(sir.block_summaries.items())[:3]:
        print(f"  {addr}: [{summary.safety}] {summary.description[:60]}")


@pytest.mark.skipif(not os.path.exists(SAMPLE_ELF), reason="需要先运行 compile_test.sh 编译 ELF")
def test_full_gbt_pipeline(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", "test-key"))

    result = GBT(SAMPLE_ELF, src_isa="arm64", dst_isa="x86-64")

    assert result.sir is not None
    assert result.synthesized_code is not None
    assert result.verification.equivalent is True
    print(f"\n合成代码片段：\n{result.synthesized_code[:300]}")

