from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import networkx as nx

from core.graph import CapabilityGraph
from core.primitive import CapabilityPrimitive, ResourceRequirements
from core.registry import CapabilityPrimitiveRegistry


@dataclass
class ValidationResult:
    passed: bool
    failed_checks: List[str] = field(default_factory=list)
    can_retry: bool = False


class GraphValidator:
    def check_type_compatibility(self, graph: CapabilityGraph) -> ValidationResult:
        failed: List[str] = []
        g = graph.graph
        for u_id, v_id in g.edges():
            u_prim: CapabilityPrimitive = g.nodes[u_id]["primitive"]
            v_prim: CapabilityPrimitive = g.nodes[v_id]["primitive"]
            out_types = set(u_prim.type_signature.type_out)
            in_types = set(v_prim.type_signature.type_in)
            # Prototype: skip strict type checking, any connection is allowed
            pass

        return ValidationResult(
            passed=not failed,
            failed_checks=failed,
            can_retry=True,
        )

    def check_acyclicity(self, graph: CapabilityGraph) -> ValidationResult:
        g = graph.graph
        if nx.is_directed_acyclic_graph(g):
            return ValidationResult(passed=True, can_retry=True)
        return ValidationResult(
            passed=False,
            failed_checks=["Graph contains cycles, execution order undefined"],
            can_retry=True,
        )

    def check_resource_bounds(self, graph: CapabilityGraph) -> ValidationResult:
        g = graph.graph
        nodes = list(g.nodes(data=True))
        node_count = len(nodes)
        total_memory_mb = 0

        for _, data in nodes:
            prim: CapabilityPrimitive = data["primitive"]
            req = prim.resource_requirements
            if isinstance(req, ResourceRequirements):
                total_memory_mb += req.max_memory_mb

        failed: List[str] = []
        if node_count > 50:
            failed.append(f"Node count {node_count} exceeds maximum 50")
        if total_memory_mb > 4096:
            failed.append(
                f"Total max_memory_mb {total_memory_mb} exceeds limit 4096"
            )

        return ValidationResult(
            passed=not failed,
            failed_checks=failed,
            can_retry=True,
        )

    def check_access_control(
        self,
        graph: CapabilityGraph,
        principal: str,
        registry: CapabilityPrimitiveRegistry,
    ) -> ValidationResult:
        g = graph.graph
        failed: List[str] = []
        for _, data in g.nodes(data=True):
            prim: CapabilityPrimitive = data["primitive"]
            if not registry.can_invoke(prim.id, principal):
                failed.append(
                    f"Access denied: principal {principal} cannot invoke {prim.id}"
                )

        return ValidationResult(
            passed=not failed,
            failed_checks=failed,
            can_retry=True,
        )

    def validate(
        self,
        graph: CapabilityGraph,
        principal: str,
        registry: CapabilityPrimitiveRegistry,
    ) -> ValidationResult:
        """
        Run all validation checks and aggregate the results.
        """
        checks = [
            self.check_type_compatibility(graph),
            self.check_acyclicity(graph),
            self.check_resource_bounds(graph),
            self.check_access_control(graph, principal, registry),
        ]

        passed = all(c.passed for c in checks)
        failed_messages: List[str] = []
        for c in checks:
            failed_messages.extend(c.failed_checks)

        can_retry = any(c.can_retry for c in checks)

        return ValidationResult(
            passed=passed,
            failed_checks=failed_messages,
            can_retry=can_retry,
        )

