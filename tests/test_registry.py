from __future__ import annotations

from typing import Dict

from core.primitive import CapabilityPrimitive, TypeSignature
from core.registry import CapabilityPrimitiveRegistry, build_default_registry


class _DummyPrimitiveV1(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="DUMMY",
            type_signature=TypeSignature(type_in=["A"], type_out=["B"]),
            semantic_descriptor="Dummy primitive v1",
            version="1.0.0",
        )

    def invoke(self, input_data, session_id=None):
        return {}


class _DummyPrimitiveV2(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="DUMMY",
            type_signature=TypeSignature(type_in=["A"], type_out=["C"]),
            semantic_descriptor="Dummy primitive v2",
            version="2.0.0",
        )

    def invoke(self, input_data, session_id=None):
        return {}


def test_registry_register_get_and_versions() -> None:
    reg = CapabilityPrimitiveRegistry()
    v1 = _DummyPrimitiveV1()
    v2 = _DummyPrimitiveV2()
    reg.register(v1)
    reg.register(v2)

    latest = reg.get("DUMMY")  # default "latest"
    assert isinstance(latest, _DummyPrimitiveV2)

    assert reg.get("DUMMY", "1.0.0") is v1
    assert reg.get("DUMMY", "2.0.0") is v2


def test_registry_access_control_deny_list() -> None:
    deny: Dict[str, list[str]] = {"HTTP_GET": ["alice"]}
    reg = CapabilityPrimitiveRegistry(deny_list=deny)

    assert reg.can_invoke("HTTP_GET", "bob") is True
    assert reg.can_invoke("HTTP_GET", "alice") is False


def test_search_by_semantic() -> None:
    reg = CapabilityPrimitiveRegistry()
    reg.register(
        _DummyPrimitiveV1(),
    )
    results = reg.search_by_semantic("dummy")
    assert any(p.id == "DUMMY" for p in results)


def test_build_default_registry_populates_primitives() -> None:
    reg = build_default_registry()
    all_ids = {p.id for p in reg.list_all()}
    # Expect at least some known primitives to be present.
    assert "HTTP_GET" in all_ids
    assert "SESSION_STORE" in all_ids

