from __future__ import annotations

from statistics import mean
from typing import List, Set

from rich.console import Console
from rich.table import Table

from ams.decomposer import DecompositionError, IntentDecomposer
from benchmarks.intents import TEST_INTENTS
from core.graph import CapabilityGraph
from core.registry import build_default_registry
from core.validator import GraphValidator
from security.policy import PolicyEngine
from security.taint import TaintTracker


def run_benchmarks() -> None:
    console = Console()

    registry = build_default_registry()
    decomposer = IntentDecomposer(registry=registry)
    policy_engine = PolicyEngine()
    taint_tracker = TaintTracker()

    table = Table(title="ICM-OS Intent Decomposition Benchmarks")
    table.add_column("Intent", style="cyan", overflow="fold", max_width=40)
    table.add_column("Session", style="magenta")
    table.add_column("Nodes", justify="right")
    table.add_column("Validated", justify="center")
    table.add_column("Policy", justify="center")
    table.add_column("Execution Order", overflow="fold", max_width=60)

    total_intents = len(TEST_INTENTS)
    successful = 0
    policy_blocked = 0
    node_counts: List[int] = []
    used_primitives: Set[str] = set()

    for item in TEST_INTENTS:
        intent = item["intent"]
        session_id = item["session_id"]

        try:
            graph: CapabilityGraph = decomposer.decompose(intent=intent, principal=session_id)
        except DecompositionError as e:
            table.add_row(intent, session_id, "-", "FAIL", "-", f"DecompositionError: {e}")
            continue

        # Graph is already validated inside decomposer.
        validated = "OK"
        node_count = graph.graph.number_of_nodes()
        edge_count = graph.graph.number_of_edges()
        node_counts.append(node_count)

        # Update primitive usage stats.
        for node_id in graph.graph.nodes():
            used_primitives.add(node_id)

        # Evaluate security policies (taint tracking can be extended when executor is added).
        violations = policy_engine.evaluate(graph, taint_tracker)
        if violations:
            policy_status = f"BLOCK ({len(violations)})"
            policy_blocked += 1
        else:
            policy_status = "OK"

        successful += 1

        # Compute execution order (topological).
        try:
            execution_order = [p.id for p in graph.get_execution_order()]
        except Exception:
            execution_order = list(graph.graph.nodes())

        table.add_row(
            intent,
            session_id,
            str(node_count),
            validated,
            policy_status,
            " -> ".join(execution_order),
        )

    console.print(table)

    # Summary statistics.
    avg_nodes = mean(node_counts) if node_counts else 0.0
    total_nodes = sum(node_counts)
    unique_primitive_count = len(used_primitives) if used_primitives else 1
    reuse_rate = total_nodes / unique_primitive_count

    console.rule("Summary")
    console.print(f"Total intents: {total_intents}")
    console.print(f"Successfully decomposed: {successful}")
    console.print(f"Policy blocked: {policy_blocked}")
    console.print(f"Average node count: {avg_nodes:.2f}")
    console.print(f"Primitive reuse rate: {reuse_rate:.2f} (total nodes / unique primitives)")


if __name__ == "__main__":
    run_benchmarks()

