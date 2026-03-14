from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TaintLabel(str, Enum):
    CLEAN = "clean"
    USER_INPUT = "user_input"
    NETWORK = "network"
    FILE_UNTRUSTED = "file_untrusted"


def _combine_labels(a: TaintLabel, b: TaintLabel) -> TaintLabel:
    """
    Combine two taint labels according to the propagation rules:
    - CLEAN + CLEAN = CLEAN
    - any taint + CLEAN = that taint
    - NETWORK + FILE_UNTRUSTED = NETWORK (NETWORK has higher precedence)
    - other mixed taints: prefer the first non-clean label.
    """
    if a == TaintLabel.CLEAN and b == TaintLabel.CLEAN:
        return TaintLabel.CLEAN
    if a == TaintLabel.CLEAN:
        return b
    if b == TaintLabel.CLEAN:
        return a
    # Both non-clean
    if {a, b} == {TaintLabel.NETWORK, TaintLabel.FILE_UNTRUSTED}:
        return TaintLabel.NETWORK
    # Fallback: prefer first label.
    return a


@dataclass
class TaintTracker:
    """
    Session-scoped taint tracker keyed by logical data identifiers.
    """

    _labels: Dict[str, TaintLabel] = field(default_factory=dict)
    _parents: Dict[str, str] = field(default_factory=dict)

    def tag(self, data_id: str, label: TaintLabel) -> None:
        self._labels[data_id] = label
        # Root tag: clear any previous parent chain.
        if data_id in self._parents:
            del self._parents[data_id]

    def propagate(self, from_id: str, to_id: str) -> None:
        """
        Propagate taint from one data item to another.
        """
        from_label = self._labels.get(from_id, TaintLabel.CLEAN)
        to_label = self._labels.get(to_id, TaintLabel.CLEAN)
        combined = _combine_labels(from_label, to_label)
        self._labels[to_id] = combined
        if combined != TaintLabel.CLEAN:
            self._parents[to_id] = from_id

    def get_label(self, data_id: str) -> TaintLabel:
        return self._labels.get(data_id, TaintLabel.CLEAN)

    def is_tainted(self, data_id: str) -> bool:
        return self.get_label(data_id) != TaintLabel.CLEAN

    def get_taint_path(self, data_id: str) -> List[str]:
        """
        Return the chain of data_ids from original source to the given id.
        """
        path: List[str] = []
        current: Optional[str] = data_id
        while current is not None and current not in path:
            path.append(current)
            current = self._parents.get(current)
        path.reverse()
        return path

    # ----- Helpers for high-risk primitives -----

    def tag_primitive_output(self, primitive_id: str, output_id: str) -> None:
        """
        Convenience helper: tag outputs of high-risk primitives with
        appropriate taint labels.

        By convention we often use the primitive id itself as data_id for
        its primary output, but callers can pass any logical output_id.
        """
        if primitive_id in {"HTTP_GET", "HTTP_POST", "TCP_CONNECT"}:
            self.tag(output_id, TaintLabel.NETWORK)
        elif primitive_id == "FILE_READ":
            self.tag(output_id, TaintLabel.FILE_UNTRUSTED)

    def record_window_render_input(self, frame_id: str, source_data_id: str) -> None:
        """
        WINDOW_RENDER: if input comes from NETWORK, record / propagate
        that into the rendered frame.
        """
        source_label = self.get_label(source_data_id)
        if source_label == TaintLabel.NETWORK:
            self.tag(frame_id, TaintLabel.NETWORK)

