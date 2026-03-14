from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.primitive import CapabilityPrimitive


def _parse_version(v: str) -> tuple:
    """
    Best-effort semver-ish parsing for ordering.
    Unknown formats fall back to string comparison.
    """
    try:
        parts = v.split(".")
        nums: List[int] = []
        for p in parts:
            if p.isdigit():
                nums.append(int(p))
            else:
                # stop at first non-numeric segment (e.g., "1.2.3-beta")
                break
        return tuple(nums) if nums else (v,)
    except Exception:
        return (v,)


@dataclass
class CapabilityPrimitiveRegistry:
    """
    Capability Primitive Registry (CPR), corresponding to Definition 2.

    - Stores capability primitives keyed by (id, version).
    - Provides access control and simple semantic search.
    """

    deny_list: Dict[str, List[str]] = field(default_factory=dict)
    _store: Dict[str, Dict[str, CapabilityPrimitive]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        # Auto-discover and register all implemented primitives under `primitives/`.
        self._auto_register_primitives()

    def can_invoke(self, primitive_id: str, principal: str) -> bool:
        denied = self.deny_list.get(primitive_id, [])
        return principal not in denied

    def register(self, primitive: CapabilityPrimitive) -> None:
        pid = primitive.id
        ver = getattr(primitive, "version", "1.0.0")
        if pid not in self._store:
            self._store[pid] = {}
        self._store[pid][ver] = primitive

    def get(self, primitive_id: str, version: str = "latest") -> CapabilityPrimitive:
        if primitive_id not in self._store or not self._store[primitive_id]:
            raise KeyError(f"Primitive not found: {primitive_id}")

        versions = self._store[primitive_id]
        if version == "latest":
            latest_ver = max(versions.keys(), key=_parse_version)
            return versions[latest_ver]

        if version not in versions:
            raise KeyError(f"Primitive {primitive_id} version not found: {version}")
        return versions[version]

    def list_all(self) -> List[CapabilityPrimitive]:
        out: List[CapabilityPrimitive] = []
        for _, by_ver in self._store.items():
            out.extend(by_ver.values())
        return out

    def search_by_semantic(self, query: str) -> List[CapabilityPrimitive]:
        q = (query or "").strip().lower()
        if not q:
            return []
        tokens = [t for t in q.split() if t]
        results: List[CapabilityPrimitive] = []
        for prim in self.list_all():
            desc = (prim.semantic_descriptor or "").lower()
            if any(tok in desc for tok in tokens):
                results.append(prim)
        return results

    def get_all_descriptors(self) -> List[dict]:
        descriptors: List[dict] = []
        for prim in self.list_all():
            descriptors.append(
                {
                    "id": prim.id,
                    "semantic_descriptor": prim.semantic_descriptor,
                    "version": getattr(prim, "version", "1.0.0"),
                }
            )
        return descriptors

    def _auto_register_primitives(self) -> None:
        """
        Import all modules under `primitives` and register any CapabilityPrimitive
        subclasses that can be instantiated with a no-arg constructor.
        """
        try:
            import primitives  # type: ignore
        except Exception:
            return

        pkg_path = getattr(primitives, "__path__", None)
        if not pkg_path:
            return

        for mod in pkgutil.walk_packages(pkg_path, prefix="primitives."):
            try:
                module = importlib.import_module(mod.name)
            except Exception:
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                try:
                    if not issubclass(obj, CapabilityPrimitive):
                        continue
                    if obj is CapabilityPrimitive:
                        continue
                except Exception:
                    continue

                # Instantiate only if it has a no-arg constructor.
                try:
                    sig = inspect.signature(obj)
                    # __init__(self) is represented by signature() on class
                    # excluding 'self' already, so we just require all params optional.
                    if any(
                        p.default is inspect._empty
                        and p.kind
                        not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                        for p in sig.parameters.values()
                    ):
                        continue
                    instance = obj()  # type: ignore[call-arg]
                    self.register(instance)
                except Exception:
                    continue


def build_default_registry(deny_list: Optional[Dict[str, List[str]]] = None) -> CapabilityPrimitiveRegistry:
    """
    Build a default CPR instance with all primitives under `primitives/` registered.
    """
    return CapabilityPrimitiveRegistry(deny_list=deny_list or {})

