from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import networkx as nx

from core.graph import CapabilityGraph
from security.taint import TaintTracker


@dataclass
class PolicyViolation:
    policy_name: str
    message: str
    path: Optional[List[str]] = None


@dataclass
class GraphPolicy:
    name: str
    description: str

    def check(
        self, graph: CapabilityGraph, taint_tracker: TaintTracker
    ) -> Optional[PolicyViolation]:
        raise NotImplementedError


class NoTaintToAMS(GraphPolicy):
    """
    Tainted data must not flow into AMS intent parsing.
    """

    AMS_PRIMITIVE_IDS = {"AMS_INTENT", "AMS_INTENT_PARSE", "INTENT_PARSER"}

    def __init__(self) -> None:
        super().__init__(
            name="NoTaintToAMS",
            description="Prevent tainted data from flowing into AMS intent parsing primitives.",
        )

    def check(
        self, graph: CapabilityGraph, taint_tracker: TaintTracker
    ) -> Optional[PolicyViolation]:
        g = graph.graph

        for node_id in g.nodes():
            if node_id not in self.AMS_PRIMITIVE_IDS:
                continue

            # If the AMS node itself is tainted, this is a violation.
            if taint_tracker.is_tainted(node_id):
                path = taint_tracker.get_taint_path(node_id)
                return PolicyViolation(
                    policy_name=self.name,
                    message=f"Tainted data flows into AMS node {node_id}",
                    path=path,
                )

            # Additionally, if any predecessor is tainted, flag it.
            for pred in g.predecessors(node_id):
                if taint_tracker.is_tainted(pred):
                    path = taint_tracker.get_taint_path(pred)
                    # Ensure the AMS node is included at the end of the path.
                    if not path or path[-1] != node_id:
                        path = path + [node_id]
                    return PolicyViolation(
                        policy_name=self.name,
                        message=f"Tainted data from {pred} flows into AMS node {node_id}",
                        path=path,
                    )

        return None


class NoSensitiveDataExfiltration(GraphPolicy):
    """
    Detect data exfiltration of file content towards network outputs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="NoSensitiveDataExfiltration",
            description="Detect potential exfiltration of sensitive file content to network outputs.",
        )

    def check(
        self, graph: CapabilityGraph, taint_tracker: TaintTracker
    ) -> Optional[PolicyViolation]:
        g = graph.graph
        file_read_nodes = [n for n in g.nodes() if n == "FILE_READ"]
        http_post_nodes = [n for n in g.nodes() if n == "HTTP_POST"]

        if not (file_read_nodes and http_post_nodes):
            return None

        for fr in file_read_nodes:
            for hp in http_post_nodes:
                if nx.has_path(g, fr, hp):
                    path = nx.shortest_path(g, fr, hp)
                    return PolicyViolation(
                        policy_name=self.name,
                        message="Potential data exfiltration: file content flows to network output",
                        path=path,
                    )

        return None


class PolicyEngine:
    def __init__(self) -> None:
        self._policies: List[GraphPolicy] = [
            NoTaintToAMS(),
            NoSensitiveDataExfiltration(),
        ]

    def evaluate(
        self, graph: CapabilityGraph, taint_tracker: TaintTracker
    ) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        for policy in self._policies:
            violation = policy.check(graph, taint_tracker)
            if violation is not None:
                violations.append(violation)
        return violations

