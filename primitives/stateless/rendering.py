from __future__ import annotations

from typing import Any, Dict, List

from core.primitive import CapabilityPrimitive, TypeSignature


class HTMLParsePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="HTML_PARSE",
            type_signature=TypeSignature(
                type_in=["HTMLParseInput"], type_out=["HTMLParseOutput"]
            ),
            semantic_descriptor="Parse HTML into a DOM-like tree.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        html = input_data.get("html", "")
        title = "Mock Title"
        return {
            "dom_tree": {"type": "document", "children": [], "length": len(html)},
            "title": title,
        }


class CSSLayoutPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="CSS_LAYOUT",
            type_signature=TypeSignature(
                type_in=["CSSLayoutInput"], type_out=["CSSLayoutOutput"]
            ),
            semantic_descriptor="Compute layout information from a DOM tree and styles.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        dom_tree = input_data.get("dom_tree", {})
        return {
            "layout": {
                "root": {
                    "x": 0,
                    "y": 0,
                    "width": 800,
                    "height": 600,
                    "node_count": len(dom_tree.get("children", [])),
                }
            }
        }


class JSExecutePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="JS_EXECUTE",
            type_signature=TypeSignature(
                type_in=["JSExecuteInput"], type_out=["JSExecuteOutput"]
            ),
            semantic_descriptor="Execute JavaScript against a DOM tree.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        dom_tree = input_data.get("dom_tree", {})
        scripts: List[str] = input_data.get("scripts", [])
        console_output = [f"Executed script: {s[:20]}..." for s in scripts]
        return {
            "dom_tree": dom_tree,
            "console_output": console_output,
        }


class WindowRenderPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="WINDOW_RENDER",
            type_signature=TypeSignature(
                type_in=["WindowRenderInput"], type_out=["WindowRenderOutput"]
            ),
            semantic_descriptor="Render a layout tree into a window/frame.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        return {
            "rendered": True,
            "frame_id": "frame-1",
        }

