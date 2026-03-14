from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TypeSignature:
    """
    Describes the input and output type signatures of a capability primitive.
    """

    type_in: List[str]
    type_out: List[str]


@dataclass(frozen=True)
class ResourceRequirements:
    """
    Describes coarse resource bounds required to execute a primitive.
    """

    max_memory_mb: int
    max_cpu_percent: float
    max_io_ops: int


@dataclass
class CapabilityPrimitive(ABC):
    """
    Abstract base class for all capability primitives (Definition 1 in the paper).
    """

    id: str
    type_signature: TypeSignature
    semantic_descriptor: str
    is_stateful: bool = False
    resource_requirements: Optional[ResourceRequirements] = None
    version: str = "1.0.0"

    @abstractmethod
    def invoke(self, input_data: Dict, session_id: Optional[str] = None) -> Dict:
        """
        Execute the primitive.
        Implementations should be pure or stateful depending on `is_stateful`.
        """
        raise NotImplementedError


@dataclass
class PrimitiveResult:
    """
    Standardized result wrapper for primitive invocations.
    """

    success: bool
    output: Dict
    error: Optional[str] = None
    taint_label: str = "CLEAN"

