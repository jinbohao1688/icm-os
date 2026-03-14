from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

import angr  # type: ignore[import]

from gbt.sir import BasicBlockSummary, SemanticIR


class SemanticLifter:
    """
    Lift a concrete binary (e.g. ARM64) into a semantic IR (SIR).
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

    # ---- Low-level analyses -------------------------------------------------

    def load_binary(self, path: str, arch: str) -> "angr.Project":
        """
        Load the binary with angr for the given architecture.
        """
        # angr typically infers arch from the binary; `arch` is kept for validation/logging.
        project = angr.Project(path, auto_load_libs=False)
        return project

    def extract_cfg(self, project: "angr.Project") -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        用 capstone 直接反汇编，提取基本块地址（这里按指令地址近似）
        不使用 angr CFGFast（太慢，依赖 z3）。
        """
        import capstone  # type: ignore[import]

        # 获取主要代码段
        main_obj = project.loader.main_object
        text_section = main_obj.sections_map.get(".text")
        if text_section is None:
            # fallback: 用入口点附近的内存
            entry = project.entry
            memory = project.loader.memory.load(entry, 0x500)
            base_addr = entry
        else:
            base_addr = text_section.vaddr
            size = min(text_section.filesize, 0x1000)  # 只分析前 4KB
            memory = project.loader.memory.load(base_addr, size)

        # capstone 反汇编
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        md.detail = True

        cfg_nodes: List[str] = []
        cfg_edges: List[Tuple[str, str]] = []
        prev_addr: str | None = None

        # 保存一份最近一次反汇编结果，供 lift_with_limit 使用。
        disasm_map: Dict[str, str] = {}

        for insn in md.disasm(bytes(memory), base_addr):
            addr_str = hex(insn.address)
            line = f"{addr_str}: {insn.mnemonic} {insn.op_str}".strip()
            disasm_map[addr_str] = line
            if addr_str not in cfg_nodes:
                cfg_nodes.append(addr_str)
            if prev_addr is not None:
                cfg_edges.append((prev_addr, addr_str))
            prev_addr = addr_str
            if len(cfg_nodes) >= 20:  # 最多取 20 个指令地址
                break

        # 缓存本次反汇编文本，lift_with_limit 会使用。
        self._last_disasm_map = disasm_map  # type: ignore[attr-defined]

        return cfg_nodes, cfg_edges

    def extract_dfg(
        self,
        project: "angr.Project",
        cfg_nodes: List[str],
    ) -> List[Tuple[str, str]]:
        """
        Extract a coarse data-flow graph between basic blocks.

        For now this uses a very lightweight approximation: we connect successive
        blocks in the CFG to indicate potential data dependencies.
        """
        # Placeholder: a more precise DFG would use angr's analyses like ReachingDefinitions.
        dfg_edges: List[Tuple[str, str]] = []
        for i in range(len(cfg_nodes) - 1):
            dfg_edges.append((cfg_nodes[i], cfg_nodes[i + 1]))
        return dfg_edges

    def classify_safety(self, block: "angr.block.Block", project: "angr.Project") -> str:
        """
        Legacy API kept for compatibility; delegates to classify_safety_from_text.
        """
        disasm_text = block.capstone.__str__()  # type: ignore[no-untyped-call]
        return self.classify_safety_from_text(disasm_text)

    def classify_safety_from_text(self, disasm_text: str) -> str:
        """
        Classify safety directly from disassembly text, without requiring angr blocks.
        """
        text = disasm_text.lower()
        if any(x in text for x in ["ldr", "str", "ldp", "stp"]):
            return "unsafe-pointer"
        if any(x in text for x in ["sdiv", "udiv", "lsl", "lsr", "asr"]):
            return "unsafe-arithmetic"
        if any(x in text for x in ["svc", "hvc", "smc", "msr", "mrs"]):
            return "privileged"
        return "safe"

    # ---- LLM-based semantic summarization -----------------------------------

    def summarize_block_with_llm(self, block_disasm: str, safety: str) -> BasicBlockSummary:
        """
        Use DeepSeek to produce a BasicBlockSummary from the block's disassembly.
        """
        system_prompt = (
            "You are a binary analysis assistant that summarizes basic blocks "
            "into a structured semantic form for the ICM-OS GBT module.\n"
            "You MUST respond with valid JSON only, matching the following schema:\n"
            '{'
            '"description": str, '
            '"preconditions": str, '
            '"postconditions": str, '
            '"roles": [str, ...], '
            '"safety": str'
            "}\n"
            "Do not include any explanation outside of the JSON."
        )

        user_prompt = (
            "Disassembly of a single basic block:\n\n"
            f"{block_disasm}\n\n"
            f"Pre-classified safety level: {safety}.\n"
            "Summarize this block into the required JSON structure."
        )

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        text = response.choices[0].message.content.strip()  # type: ignore[assignment]

        # Strip optional markdown fences.
        if text.startswith("```"):
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1 :]
            if "```" in text:
                text = text.rsplit("```", 1)[0].strip()

        data = json.loads(text)
        return BasicBlockSummary(
            description=data.get("description", ""),
            preconditions=data.get("preconditions", ""),
            postconditions=data.get("postconditions", ""),
            roles=list(data.get("roles", [])),
            safety=data.get("safety", safety),
        )

    # ---- High-level lifting pipeline ----------------------------------------

    def _cache_path_for_binary(self, binary_path: str) -> str:
        h = hashlib.sha256(os.path.abspath(binary_path).encode("utf-8")).hexdigest()
        base_dir = os.path.expanduser("~/.icm-os/gbt_cache")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, f"{h}.json")

    def lift(self, binary_path: str, arch: str = "arm64") -> SemanticIR:
        """
        Full lifting pipeline: load → CFG → DFG → safety classification →
        LLM semantic summaries → SIR (with caching).
        """
        cache_path = self._cache_path_for_binary(binary_path)
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Reconstruct SIR from JSON.
            block_summaries = {
                bid: BasicBlockSummary(**bs) for bid, bs in raw["block_summaries"].items()
            }
            return SemanticIR(
                source_binary=raw["source_binary"],
                source_isa=raw["source_isa"],
                cfg_nodes=raw["cfg_nodes"],
                cfg_edges=[tuple(e) for e in raw["cfg_edges"]],
                dfg_edges=[tuple(e) for e in raw["dfg_edges"]],
                block_summaries=block_summaries,
                patterns=list(raw.get("patterns", [])),
                cached_at=raw.get("cached_at", ""),
            )

        project = self.load_binary(binary_path, arch)
        cfg_nodes, cfg_edges = self.extract_cfg(project)
        dfg_edges = self.extract_dfg(project, cfg_nodes)

        block_summaries: Dict[str, BasicBlockSummary] = {}
        for addr_str in cfg_nodes:
            addr = int(addr_str, 16)
            block = project.factory.block(addr)  # type: ignore[attr-defined]
            safety = self.classify_safety(block, project)
            disasm = block.capstone.__str__()  # type: ignore[no-untyped-call]
            summary = self.summarize_block_with_llm(disasm, safety)
            block_summaries[addr_str] = summary

        # Simple pattern extraction heuristic.
        patterns: List[str] = []
        if any("loop" in (s.description or "").lower() for s in block_summaries.values()):
            patterns.append("LOOP")

        sir = SemanticIR(
            source_binary=binary_path,
            source_isa=arch,
            cfg_nodes=cfg_nodes,
            cfg_edges=cfg_edges,
            dfg_edges=dfg_edges,
            block_summaries=block_summaries,
            patterns=patterns,
            cached_at=datetime.utcnow().isoformat() + "Z",
        )

        # Cache to disk.
        serializable = asdict(sir)
        # Convert BasicBlockSummary objects to plain dicts.
        serializable["block_summaries"] = {
            bid: asdict(bs) for bid, bs in sir.block_summaries.items()
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2, sort_keys=True)

        return sir

    def lift_with_limit(
        self,
        binary_path: str,
        arch: str = "arm64",
        max_blocks: int = 10,
    ) -> SemanticIR:
        """
        只处理前 max_blocks 个“基本块”（这里近似为前若干条指令），
        用于快速测试真实二进制，避免大型二进制全量分析超时。
        不使用或更新缓存。
        """
        project = self.load_binary(binary_path, arch)
        cfg_nodes, cfg_edges = self.extract_cfg(project)
        if max_blocks > 0:
            cfg_nodes = cfg_nodes[:max_blocks]
            cfg_edges = [e for e in cfg_edges if e[0] in cfg_nodes and e[1] in cfg_nodes]
        dfg_edges = self.extract_dfg(project, cfg_nodes)

        # 从最近一次 extract_cfg 的 capstone 结果中取反汇编文本。
        disasm_map: Dict[str, str] = getattr(self, "_last_disasm_map", {})  # type: ignore[assignment]

        block_summaries: Dict[str, BasicBlockSummary] = {}
        for addr_str in cfg_nodes:
            disasm_text = disasm_map.get(addr_str, addr_str)
            safety = self.classify_safety_from_text(disasm_text)
            summary = self.summarize_block_with_llm(disasm_text, safety)
            block_summaries[addr_str] = summary

        patterns: List[str] = []
        if any("loop" in (s.description or "").lower() for s in block_summaries.values()):
            patterns.append("LOOP")

        return SemanticIR(
            source_binary=binary_path,
            source_isa=arch,
            cfg_nodes=cfg_nodes,
            cfg_edges=cfg_edges,
            dfg_edges=dfg_edges,
            block_summaries=block_summaries,
            patterns=patterns,
            cached_at=datetime.utcnow().isoformat() + "Z",
        )

