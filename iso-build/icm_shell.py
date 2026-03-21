#!/usr/bin/env python3
"""
ICM-OS intent-driven shell.
- Input: natural language intent.
- CDM decomposes intent into capability graph; executor runs the graph.
- Fallback: run line as traditional shell command.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Any, Dict

# Run from repo root so imports resolve
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

def _format_output(primitive_id: str, output: Dict[str, Any]) -> str:
    if not output or output.get("error"):
        return str(output.get("error", output))
    parts = []
    for k in ("file_id", "bytes_read", "bytes_written", "content", "text", "matches", "count", "translated", "title", "status_code", "success"):
        if k in output:
            v = output[k]
            if isinstance(v, str) and len(v) > 60:
                v = v[:57] + "..."
            parts.append(f"{k}={v!r}" if isinstance(v, str) else f"{k}={v}")
    return "  ".join(parts) if parts else str(output)[:80]

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
            print(f"[ICM-OS] CDM unavailable (e.g. DEEPSEEK_API_KEY): {e}", file=sys.stderr)
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

        # Try CDM decomposition first (if available and looks like intent)
        if decomposer and executor and not line.startswith("!"):
            try:
                graph: CapabilityGraph = decomposer.decompose(intent=line, principal=session_id)
                order = [p.id for p in graph.get_execution_order()]
                print(f"Graph: {' -> '.join(order)}")

                initial_context: Dict[str, Any] = {}
                paths = re.findall(r"/\S+\.\w+", line)
                if paths:
                    initial_context["path"] = paths[0]
                    initial_context["text"] = paths[0]
                search_match = re.search(r"search\s+for\s+['\"]([^'\"]+)['\"]", line, re.I)
                if search_match:
                    initial_context["query"] = search_match.group(1)

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
                        print("Result:", out)
                print()
                continue
            except DecompositionError as e:
                print(f"Decomposition failed: {e}")
                print("Run as command? (y/n or run with ! prefix next time)")
                try:
                    if input().strip().lower() != "y":
                        continue
                except (EOFError, KeyboardInterrupt):
                    continue
            except Exception as e:
                print(f"Execution error: {e}")
                continue

        # Fallback: traditional command
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
