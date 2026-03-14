from __future__ import annotations

from typing import Any, Dict, List

from core.primitive import CapabilityPrimitive, TypeSignature


class BookmarkWritePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="BOOKMARK_WRITE",
            type_signature=TypeSignature(
                type_in=["text", "kv_result"], type_out=["bookmark_id"]
            ),
            semantic_descriptor="Write a bookmark entry.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        url = input_data.get("url", "")
        title = input_data.get("title", "")
        tags: List[str] = input_data.get("tags", [])
        bookmark_id = f"bm-{hash((url, title, tuple(tags))) & 0xFFFF}"
        return {
            "bookmark_id": bookmark_id,
            "saved": True,
        }

