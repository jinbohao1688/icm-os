from __future__ import annotations

from core.graph import CapabilityGraph
from core.registry import build_default_registry, CapabilityPrimitiveRegistry


def _make_small_graph(registry: CapabilityPrimitiveRegistry) -> CapabilityGraph:
    g = CapabilityGraph()
    # Pick two arbitrary primitives that exist.
    p1 = registry.get("UTF8_DECODE")
    p2 = registry.get("TEXT_LAYOUT")
    g.add_node(p1)
    g.add_node(p2)
    g.add_edge(p1.id, p2.id)
    return g


def test_add_node_edge_and_execution_order() -> None:
    reg = build_default_registry()
    g = _make_small_graph(reg)

    order = [p.id for p in g.get_execution_order()]
    assert order[0] == "UTF8_DECODE"
    assert order[-1] == "TEXT_LAYOUT"


def test_to_dict_from_dict_roundtrip() -> None:
    reg = build_default_registry()
    g = _make_small_graph(reg)

    data = g.to_dict()
    g2 = CapabilityGraph.from_dict(data, registry=reg)

    assert set(g.graph.nodes()) == set(g2.graph.nodes())
    assert set(g.graph.edges()) == set(g2.graph.edges())

