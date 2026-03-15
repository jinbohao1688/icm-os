from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import networkx as nx

from core.primitive import CapabilityPrimitive
from core.registry import CapabilityPrimitiveRegistry
from security.taint import TaintLabel, TaintTracker


@dataclass
class CapabilityGraph:
    """
    Directed capability graph (Definition 3 in the paper).
    Nodes are capability primitives; edges represent data/control flow.
    """

    graph: nx.DiGraph

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_node(self, primitive: CapabilityPrimitive) -> None:
        """
        Add a primitive node keyed by its id.
        """
        self.graph.add_node(primitive.id, primitive=primitive)

    def add_edge(self, from_id: str, to_id: str) -> None:
        """
        Add a directed edge from one primitive id to another.
        """
        self.graph.add_edge(from_id, to_id)

    def get_execution_order(self) -> List[CapabilityPrimitive]:
        """
        Return primitives in a topologically sorted execution order.
        Raises NetworkXUnfeasible if the graph is cyclic.
        """
        order: List[CapabilityPrimitive] = []
        for node_id in nx.topological_sort(self.graph):
            data = self.graph.nodes[node_id]
            primitive: CapabilityPrimitive = data["primitive"]
            order.append(primitive)
        return order

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize graph to a dict:
        {
          "nodes": [{"id": ..., "version": ...}, ...],
          "edges": [{"from": ..., "to": ...}, ...]
        }
        """
        nodes: List[Dict[str, Any]] = []
        for node_id, data in self.graph.nodes(data=True):
            primitive: CapabilityPrimitive = data["primitive"]
            nodes.append(
                {
                    "id": primitive.id,
                    "version": getattr(primitive, "version", "1.0.0"),
                }
            )

        edges: List[Dict[str, str]] = [
            {"from": u, "to": v} for u, v in self.graph.edges()
        ]
        return {"nodes": nodes, "edges": edges}

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], registry: CapabilityPrimitiveRegistry
    ) -> "CapabilityGraph":
        """
        Deserialize a CapabilityGraph from dict representation using a registry
        to look up concrete primitive instances.
        """
        graph = cls()
        for node in data.get("nodes", []):
            pid = node if isinstance(node, str) else node.get("id")
            version = "latest" if isinstance(node, str) else node.get("version", "latest")
            if not pid:
                continue
            primitive = registry.get(pid, version)
            graph.add_node(primitive)

        for edge in data.get("edges", []):
            from_id = edge[0] if isinstance(edge, list) else edge.get("from")
            to_id = edge[1] if isinstance(edge, list) else edge.get("to")
            if from_id and to_id:
                graph.add_edge(from_id, to_id)

        return graph


class GraphExecutor:
    """
    Execute a capability graph in topological order while performing
    session-scoped taint tracking.
    """

    def __init__(self, taint_tracker: TaintTracker) -> None:
        self.taint_tracker = taint_tracker

    def execute(
        self,
        graph: CapabilityGraph,
        session_id: str,
        initial_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        results: Dict[str, Dict[str, Any]] = {}
        if initial_context:
            results["__init__"] = initial_context

        for primitive in graph.get_execution_order():
            predecessors = list(graph.graph.predecessors(primitive.id))
            input_data: Dict[str, Any] = {}

            # 合并所有上游输出
            for pred_id in predecessors:
                input_data.update(results.get(pred_id, {}))

            # 如果是起始节点（无上游），注入初始上下文
            if not predecessors and initial_context:
                input_data.update(initial_context)

            output = primitive.invoke(input_data, session_id)
            results[primitive.id] = output

            # High-risk primitives: tag outputs with appropriate taint labels.
            data_id = f"{primitive.id}_out"
            if primitive.id in ("HTTP_GET", "HTTP_POST", "TCP_CONNECT"):
                self.taint_tracker.tag(data_id, TaintLabel.NETWORK)
            elif primitive.id == "FILE_READ":
                self.taint_tracker.tag(data_id, TaintLabel.FILE_UNTRUSTED)
            else:
                self.taint_tracker.tag(data_id, TaintLabel.CLEAN)

            # Propagate taint from all predecessors to current output.
            for pred_id in predecessors:
                self.taint_tracker.propagate(f"{pred_id}_out", data_id)

        # Flatten results for caller.
        flat: Dict[str, Any] = {}
        for pid, out in results.items():
            flat[pid] = out
        return flat

