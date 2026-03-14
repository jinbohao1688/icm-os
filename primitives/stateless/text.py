from __future__ import annotations

from typing import Any, Dict, List

from core.primitive import CapabilityPrimitive, TypeSignature


class UTF8DecodePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="UTF8_DECODE",
            type_signature=TypeSignature(
                type_in=["UTF8DecodeInput"], type_out=["UTF8DecodeOutput"]
            ),
            semantic_descriptor="Decode UTF-8 encoded bytes into text.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        raw_bytes = input_data.get("raw_bytes", "")
        text = raw_bytes  # mock: treat as already-decoded
        return {
            "text": text,
            "encoding": "utf-8",
        }


class TextLayoutPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="TEXT_LAYOUT",
            type_signature=TypeSignature(
                type_in=["TextLayoutInput"], type_out=["TextLayoutOutput"]
            ),
            semantic_descriptor="Layout text into lines.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        text = input_data.get("text", "")
        words = text.split()
        return {
            "lines": text.splitlines() or [text],
            "word_count": len(words),
        }


class ScrollInputPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="SCROLL_INPUT",
            type_signature=TypeSignature(
                type_in=["ScrollInput"], type_out=["ScrollOutput"]
            ),
            semantic_descriptor="Scroll within a rendered frame.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        delta = int(input_data.get("delta", 0))
        base_position = 0
        return {
            "position": base_position + delta,
        }


class SearchIndexPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="SEARCH_INDEX",
            type_signature=TypeSignature(
                type_in=["SearchIndexInput"], type_out=["SearchIndexOutput"]
            ),
            semantic_descriptor="Search within text and return match positions.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        text = input_data.get("text", "")
        query = input_data.get("query", "")
        matches: List[int] = []
        if query:
            start = 0
            while True:
                idx = text.find(query, start)
                if idx == -1:
                    break
                matches.append(idx)
                start = idx + len(query)
        return {
            "matches": matches,
            "count": len(matches),
        }

