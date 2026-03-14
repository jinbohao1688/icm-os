from __future__ import annotations

from typing import Any, Dict

from core.primitive import CapabilityPrimitive, TypeSignature


class FileOpenPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_OPEN",
            type_signature=TypeSignature(
                type_in=["FileOpenInput"], type_out=["FileOpenOutput"]
            ),
            semantic_descriptor="Open a file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        path = input_data.get("path", "/tmp/mock.txt")
        mode = input_data.get("mode", "r")
        return {
            "file_id": f"file-{hash((path, mode)) & 0xFFFF}",
            "size": 0,
        }


class FileReadPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_READ",
            type_signature=TypeSignature(
                type_in=["FileReadInput"], type_out=["FileReadOutput"]
            ),
            semantic_descriptor="Read from an open file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        file_id = input_data.get("file_id", "file-0")
        content = f"Mock content from {file_id}"
        return {
            "content": content,
            "bytes_read": len(content.encode("utf-8")),
        }


class FileWritePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_WRITE",
            type_signature=TypeSignature(
                type_in=["FileWriteInput"], type_out=["FileWriteOutput"]
            ),
            semantic_descriptor="Write to an open file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        content = input_data.get("content", "")
        return {
            "bytes_written": len(str(content).encode("utf-8")),
        }


class FileClosePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_CLOSE",
            type_signature=TypeSignature(
                type_in=["FileCloseInput"], type_out=["FileCloseOutput"]
            ),
            semantic_descriptor="Close an open file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        return {
            "success": True,
        }

