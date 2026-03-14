from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class BasicBlockSummary:
    """
    High-level semantic summary of a single basic block.
    """

    description: str          # Natural language description of the block's computation
    preconditions: str        # Preconditions on inputs / machine state
    postconditions: str       # Postconditions on outputs / machine state
    roles: List[str]          # Abstract roles, e.g. SIMD_ARITHMETIC, BOUNDS_CHECK
    safety: str               # safe / unsafe-pointer / unsafe-arithmetic / privileged


@dataclass
class SemanticIR:
    """
    Semantic Intermediate Representation (SIR) for a binary, as in Section 4.3.
    """

    source_binary: str                      # Original binary path
    source_isa: str                         # Source ISA, e.g. "arm64"
    cfg_nodes: List[str]                    # Basic block IDs from the CFG
    cfg_edges: List[Tuple[str, str]]        # Control flow edges (u, v)
    dfg_edges: List[Tuple[str, str]]        # Data-flow dependency edges (u, v)
    block_summaries: Dict[str, BasicBlockSummary]  # block_id -> summary
    patterns: List[str]                     # High-level patterns: LOOP, FUNCTION_CALL, SIMD, etc.
    cached_at: str                          # Timestamp when this SIR was cached

