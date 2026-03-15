# Run: python3 cli.py
"""
ICM-OS interactive CLI: enter natural-language intents, get capability graph
execution with real primitives. Session state persists within the same run.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel

from ams.decomposer import DecompositionError, IntentDecomposer
from core.graph import CapabilityGraph, GraphExecutor
from core.registry import build_default_registry
from security.taint import TaintTracker

SESSION_ID = "cli-session"


def _format_step_output(primitive_id: str, output: Dict[str, Any]) -> str:
    """Format a single primitive's output for display."""
    if not output or output.get("error"):
        return str(output.get("error", output))
    parts = []
    if "file_id" in output:
        parts.append(f"file_id: {output['file_id']}")
    if "bytes_read" in output:
        parts.append(f"bytes_read: {output['bytes_read']}")
    if "bytes_written" in output:
        parts.append(f"bytes_written: {output['bytes_written']}")
    if "content" in output:
        c = output["content"]
        if isinstance(c, str) and len(c) > 50:
            c = c[:47] + "..."
        parts.append(f"content: {c!r}")
    if "text" in output and primitive_id == "UTF8_DECODE":
        t = output["text"]
        if isinstance(t, str) and len(t) > 40:
            t = t[:37] + "..."
        parts.append(f"text: {t!r}")
    if "matches" in output:
        parts.append(f"matches: {output['matches']}")
    if "count" in output:
        parts.append(f"count: {output['count']}")
    if "translated" in output:
        t = output["translated"]
        if isinstance(t, str) and len(t) > 50:
            t = t[:47] + "..."
        parts.append(f"translated: {t!r}")
    if "title" in output:
        parts.append(f"title: {output['title']!r}")
    if "status_code" in output:
        parts.append(f"status_code: {output['status_code']}")
    if "rendered" in output:
        parts.append("rendered")
    if "success" in output:
        parts.append("success")
    if "frame_id" in output:
        parts.append(f"frame_id: {output['frame_id']}")
    if not parts:
        parts.append(str(output)[:60])
    return "  ".join(parts)


def main() -> None:
    console = Console()
    registry = build_default_registry()
    n = len(registry.list_all())
    decomposer = IntentDecomposer(registry=registry)
    taint_tracker = TaintTracker()
    executor = GraphExecutor(taint_tracker)

    console.print(
        Panel(
            f"[bold]ICM-OS CLI v1.0[/bold]\n[dim]{n} primitives loaded[/dim]",
            title="",
            border_style="cyan",
        )
    )
    console.print()

    while True:
        try:
            intent = console.input("[bold cyan]Enter intent (or 'exit' to quit):[/bold cyan]\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break
        if not intent:
            continue
        if intent.lower() in ("exit", "quit"):
            console.print("[dim]Bye.[/dim]")
            break

        try:
            console.print("[dim][AMS] Decomposing...[/dim]")
            graph: CapabilityGraph = decomposer.decompose(intent=intent, principal=SESSION_ID)
        except DecompositionError as e:
            console.print(f"[red]Decomposition failed: {e}[/red]")
            console.print()
            continue

        order = [p.id for p in graph.get_execution_order()]
        console.print(f"[green]✓ Graph:[/green] {' → '.join(order)}")
        console.print()

        paths = re.findall(r"/\S+\.\w+", intent)
        initial_context: Dict[str, Any] = {}
        if paths:
            initial_context["path"] = paths[0]
            initial_context["text"] = paths[0]
        search_match = re.search(r"search\s+for\s+['\"]([^'\"]+)['\"]", intent, re.I)
        if search_match:
            initial_context["query"] = search_match.group(1)

        def on_step(primitive_id: str, output: Dict[str, Any]) -> None:
            line = _format_step_output(primitive_id, output)
            console.print(f"  [green]✓[/green] [bold]{primitive_id:14}[/bold] → {line}")

        console.print("[bold][EXECUTING][/bold]")
        results = executor.execute(
            graph,
            session_id=SESSION_ID,
            initial_context=initial_context,
            on_step=on_step,
        )
        console.print()

        console.print("[bold][RESULT][/bold]")
        last_id = order[-1] if order else None
        if last_id and last_id in results:
            out = results[last_id]
            if isinstance(out, dict) and out.get("error"):
                console.print(f"  [red]error: {out['error']}[/red]")
            else:
                for k, v in out.items():
                    if k in ("error",):
                        continue
                    if isinstance(v, str) and len(v) > 80:
                        v = v[:77] + "..."
                    console.print(f"  [cyan]{k}:[/cyan] {v}")
        console.print()

    return None


if __name__ == "__main__":
    main()
