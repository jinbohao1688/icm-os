from __future__ import annotations

import os
import subprocess
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from gbt.sir import BasicBlockSummary, SemanticIR


class CodeSynthesizer:
    """
    Synthesize x86-64 AT&T assembly from SIR by calling DeepSeek per basic block.
    """

    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set in environment or .env")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    def _label_for_addr(self, addr: str) -> str:
        """Turn block id like '0x400740' into .L400740."""
        a = addr.replace("0x", "").replace("0X", "")
        return f".L{a}"

    def _synthesize_block(self, addr: str, summary: BasicBlockSummary) -> str:
        system_prompt = """You are an expert x86-64 assembly programmer.
Given a semantic description of an ARM64 basic block, generate equivalent x86-64 AT&T syntax assembly.
Rules:
- Use AT&T syntax (source, destination order)
- Use proper registers (%rax, %rbx, %rdi, %rsi, etc.)
- Include the block label (e.g. .L{addr}:)
- Only output assembly code, no explanation
- Make the code actually compilable with gcc/as"""

        user_prompt = f"""Block address: {addr}
Safety class: {summary.safety}
Description: {summary.description}
Preconditions: {summary.preconditions}
Postconditions: {summary.postconditions}
Roles: {', '.join(summary.roles)}

Generate x86-64 AT&T assembly for this block:"""

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        text = (response.choices[0].message.content or "").strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def synthesize(self, sir: SemanticIR, dst_isa: str = "x86-64") -> str:
        lines: List[str] = []
        lines.append(".text")
        lines.append(".globl _start")
        lines.append("")

        block_order = sir.cfg_nodes if sir.cfg_nodes else list(sir.block_summaries.keys())
        first_addr = block_order[0] if block_order else None
        first_label = self._label_for_addr(first_addr) if first_addr else ".L0"

        if not block_order:
            lines.append(".L0:")
            lines.append("    nop")
            lines.append("")

        for addr in block_order:
            summary = sir.block_summaries.get(addr)
            if not summary:
                lines.append(f"; block {addr} (no summary)")
                continue
            try:
                block_asm = self._synthesize_block(addr, summary)
                if block_asm.strip():
                    lines.append(block_asm)
                else:
                    lines.append(f"{self._label_for_addr(addr)}:")
                    lines.append("    nop")
                lines.append("")
            except Exception as e:
                lines.append(f"; block {addr} synthesis failed: {e}")
                lines.append(f"{self._label_for_addr(addr)}:")
                lines.append("    nop")
                lines.append("")

        lines.append("_start:")
        lines.append(f"    call {first_label}")
        lines.append("    mov $60, %rax")
        lines.append("    xor %rdi, %rdi")
        lines.append("    syscall")

        full_asm = "\n".join(lines)

        out_path = "/tmp/synthesized.s"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_asm)

        try:
            result = subprocess.run(
                ["as", "--64", "-o", "/tmp/gbt_test.o", out_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                print("✓ Assembly validated successfully")
            else:
                print(f"Assembly validation failed:\n{result.stderr or result.stdout}")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            print(f"Assembly validation skipped: {e}")

        return full_asm
