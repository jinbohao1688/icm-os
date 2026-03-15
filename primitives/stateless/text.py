from __future__ import annotations

from typing import Any, Dict, List

from core.primitive import CapabilityPrimitive, TypeSignature


class UTF8DecodePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="UTF8_DECODE",
            type_signature=TypeSignature(
                type_in=["text", "file_content", "raw_bytes"], type_out=["text"]
            ),
            semantic_descriptor="Decode UTF-8 encoded bytes into text.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        raw = input_data.get("content") or input_data.get("body") or input_data.get("raw_bytes") or ""
        if not isinstance(raw, str):
            raw = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        return {"text": raw, "encoding": "utf-8"}


class TextLayoutPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="TEXT_LAYOUT",
            type_signature=TypeSignature(
                type_in=["text", "translated_text"], type_out=["text", "lines"]
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
                type_in=["frame_id", "position"], type_out=["position"]
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
                type_in=["text", "lines"], type_out=["text", "matches"]
            ),
            semantic_descriptor="Search within text and return match positions.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        text = input_data.get("text") or input_data.get("content") or ""
        if not isinstance(text, str):
            text = str(text)
        q = input_data.get("query") or input_data.get("matches") or input_data.get("content") or ""
        if isinstance(q, list) and q:
            query = str(q[0]) if q else ""
        else:
            query = str(q) if q else ""
        lines = text.split("\n")
        if query:
            matches = [line for line in lines if query.lower() in line.lower()]
        else:
            matches = [line for line in lines if line.strip()]
        return {"matches": matches, "count": len(matches)}

