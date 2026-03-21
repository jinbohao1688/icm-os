#!/usr/bin/env python3
"""
ICM-OS intent-driven shell.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

def _format_output(primitive_id: str, output: Dict[str, Any]) -> str:
    if not output or output.get("error"):
        return str(output.get("error", output))
    parts = []
    for k in ("file_id", "bytes_read", "bytes_written", "content", "text",
              "matches", "count", "translated", "title", "status_code", "success",
              "ip", "domain", "body"):
        if k in output:
            v = output[k]
            if isinstance(v, str) and len(v) > 120:
                v = v[:117] + "..."
            parts.append(f"{k}={v!r}" if isinstance(v, str) else f"{k}={v}")
    return "  ".join(parts) if parts else str(output)[:120]


def _extract_context(intent: str) -> Dict[str, Any]:
    """从意图中提取所有参数到 initial_context。"""
    ctx: Dict[str, Any] = {}
    line = intent

    # URL
    url_match = re.search(r"https?://\S+", line)
    if url_match:
        url = url_match.group(0).rstrip(".,;)")
        ctx["url"] = url
        # 从 URL 提取 domain
        domain_match = re.search(r"https?://([^/\s]+)", url)
        if domain_match:
            ctx["domain"] = domain_match.group(1)

    # 裸域名（如 "fetch baidu.com"）
    if "domain" not in ctx:
        domain_match = re.search(
            r"\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b", line
        )
        if domain_match:
            ctx["domain"] = domain_match.group(1)
            if "url" not in ctx:
                ctx["url"] = "https://" + domain_match.group(1)

    # 文件路径
    paths = re.findall(r"/\S+\.\w+", line)
    if paths:
        ctx["path"] = paths[0]
        ctx["text"] = paths[0]

    # 搜索词
    search_match = re.search(r"search\s+for\s+['\"]([^'\"]+)['\"]", line, re.I)
    if search_match:
        ctx["query"] = search_match.group(1)

    # 目标语言
    lang_map = {
        "chinese":    "Chinese",
        "中文":        "Chinese",
        "english":    "English",
        "英文":        "English",
        "french":     "French",
        "法语":        "French",
        "german":     "German",
        "德语":        "German",
        "japanese":   "Japanese",
        "日语":        "Japanese",
        "korean":     "Korean",
        "韩语":        "Korean",
        "spanish":    "Spanish",
        "西班牙语":    "Spanish",
        "russian":    "Russian",
        "俄语":        "Russian",
    }
    for kw, lang in lang_map.items():
        if kw in line.lower():
            ctx["target_lang"] = lang
            break

    # 要翻译的文本（"translate X to Y"）
    trans_match = re.search(
        r"translate\s+['\"]?(.+?)['\"]?\s+(?:to|into)\s+\w+", line, re.I
    )
    if trans_match:
        ctx["text"] = trans_match.group(1).strip()

    # 中文翻译模式：把X翻译成Y / 将X翻译成Y
    cn_match = re.search(r'[把将](.+?)(?:翻译|转)成', line)
    if cn_match:
        ctx['text'] = cn_match.group(1).strip()

    return ctx


def main() -> None:
    session_id = "icm-shell-session"
    registry = None
    decomposer = None
    executor = None
    try:
        from core.registry import build_default_registry
        from core.graph import CapabilityGraph, GraphExecutor
        from security.taint import TaintTracker
        from ams.decomposer import IntentDecomposer, DecompositionError
        registry = build_default_registry()
        try:
            decomposer = IntentDecomposer(registry=registry)
        except Exception as e:
            print(f"[ICM-OS] CDM unavailable: {e}", file=sys.stderr)
        taint_tracker = TaintTracker()
        executor = GraphExecutor(taint_tracker)
    except ImportError as e:
        print(f"[ICM-OS] Import error (run from repo with deps): {e}", file=sys.stderr)
        print("[ICM-OS] Fallback: traditional commands only.", file=sys.stderr)

    n = len(registry.list_all()) if registry is not None else 0
    print(f"ICM-OS shell (intent-driven). Primitives: {n}. CDM: {'yes' if decomposer else 'no (fallback only)'}")
    print("Enter intent or a command. 'exit' to quit.")
    print()

    while True:
        try:
            line = input("icm> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            print("Bye.")
            break

        if decomposer and executor and not line.startswith("!"):
            try:
                graph = decomposer.decompose(intent=line, principal=session_id)
                order = [p.id for p in graph.get_execution_order()]
                print(f"Graph: {' -> '.join(order)}")

                initial_context = _extract_context(line)

                def on_step(primitive_id: str, output: Dict[str, Any]) -> None:
                    print(f"  {primitive_id}: {_format_output(primitive_id, output)}")

                results = executor.execute(
                    graph,
                    session_id=session_id,
                    initial_context=initial_context,
                    on_step=on_step,
                )
                last_id = order[-1] if order else None
                if last_id and last_id in results:
                    out = results[last_id]
                    if isinstance(out, dict) and out.get("error"):
                        print(f"Result error: {out['error']}")
                    else:
                        # 只显示关键字段
                        if isinstance(out, dict):
                            for k in ("translated", "body", "title", "text", "content", "status_code"):
                                if k in out:
                                    v = out[k]
                                    if isinstance(v, str) and len(v) > 200:
                                        v = v[:197] + "..."
                                    print(f"Result [{k}]: {v}")
                                    break
                            else:
                                print(f"Result: {out}")
                        else:
                            print(f"Result: {out}")
                print()
                continue
            except Exception as e:
                print(f"Execution error: {e}")
                continue

        # 传统命令
        if line.startswith("!"):
            line = line[1:].lstrip()
        try:
            rc = subprocess.run(line, shell=True)
            if rc.returncode != 0:
                print(f"[exit {rc.returncode}]")
        except Exception as e:
            print(f"Command error: {e}")

if __name__ == "__main__":
    main()
