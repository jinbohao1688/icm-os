from __future__ import annotations

from core.graph import CapabilityGraph
from core.primitive import CapabilityPrimitive, ResourceRequirements, TypeSignature
from core.registry import CapabilityPrimitiveRegistry
from core.validator import GraphValidator


class _SimplePrim(CapabilityPrimitive):
    def __init__(self, pid: str, type_in, type_out, mem: int = 0) -> None:
        super().__init__(
            id=pid,
            type_signature=TypeSignature(type_in=list(type_in), type_out=list(type_out)),
            semantic_descriptor=f"Simple {pid}",
        )
        if mem:
            self.resource_requirements = ResourceRequirements(
                max_memory_mb=mem,
                max_cpu_percent=10.0,
                max_io_ops=10,
            )

    def invoke(self, input_data, session_id=None):
        return {}


def test_type_compatibility_pass_and_fail() -> None:
    v = GraphValidator()
    g_ok = CapabilityGraph()
    a = _SimplePrim("A", type_in=["X"], type_out=["Y"])
    b = _SimplePrim("B", type_in=["Y"], type_out=["Z"])
    g_ok.add_node(a)
    g_ok.add_node(b)
    g_ok.add_edge("A", "B")
    res_ok = v.check_type_compatibility(g_ok)
    assert res_ok.passed

    g_bad = CapabilityGraph()
    c = _SimplePrim("C", type_in=["X"], type_out=["P"])
    d = _SimplePrim("D", type_in=["Q"], type_out=["R"])
    g_bad.add_node(c)
    g_bad.add_node(d)
    g_bad.add_edge("C", "D")
    res_bad = v.check_type_compatibility(g_bad)
    assert not res_bad.passed
    assert any("Type mismatch" in m for m in res_bad.failed_checks)


def test_cycle_detection() -> None:
    v = GraphValidator()
    g = CapabilityGraph()
    a = _SimplePrim("A", ["X"], ["Y"])
    b = _SimplePrim("B", ["Y"], ["X"])
    g.add_node(a)
    g.add_node(b)
    g.add_edge("A", "B")
    g.add_edge("B", "A")
    res = v.check_acyclicity(g)
    assert not res.passed
    assert "Graph contains cycles" in res.failed_checks[0]


def test_resource_bounds_node_and_memory_limits() -> None:
    v = GraphValidator()
    g = CapabilityGraph()
    # Create 51 nodes each with 100 MB to exceed both node and memory limits.
    for i in range(51):
        p = _SimplePrim(f"P{i}", ["X"], ["Y"], mem=100)
        g.add_node(p)

    res = v.check_resource_bounds(g)
    assert not res.passed
    assert any("Node count" in m for m in res.failed_checks)
    assert any("Total max_memory_mb" in m for m in res.failed_checks)


def test_access_control_rejection() -> None:
    v = GraphValidator()
    g = CapabilityGraph()
    p = _SimplePrim("SENSITIVE", ["X"], ["Y"])
    g.add_node(p)

    reg = CapabilityPrimitiveRegistry(deny_list={"SENSITIVE": ["alice"]})
    res = v.check_access_control(g, principal="alice", registry=reg)
    assert not res.passed
    assert any("Access denied" in m for m in res.failed_checks)

