from __future__ import annotations

import os
from typing import Any, Dict
from uuid import uuid4

from core.primitive import CapabilityPrimitive, TypeSignature

# 模块级文件句柄存储：file_id -> 打开的文件对象
_FILE_HANDLES: Dict[str, Any] = {}


class FileOpenPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_OPEN",
            type_signature=TypeSignature(
                type_in=["text"], type_out=["file_id"]
            ),
            semantic_descriptor="Open a file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        path = input_data.get("path") or input_data.get("text") or input_data.get("file_path") or ""
        mode = input_data.get("mode", "r")
        # 如果文件不存在且是写模式，自动创建
        if not path:
            return {"error": "no path provided"}
        if not os.path.exists(path) and mode == "r":
            # 尝试写模式（write intent）
            mode = "w"
        try:
            f = open(path, mode)
            file_id = f"fh-{uuid4().hex[:8]}"
            _FILE_HANDLES[file_id] = f
            return {
                "file_id": file_id,
                "size": os.path.getsize(path),
            }
        except OSError as e:
            return {"error": str(e)}


class FileReadPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_READ",
            type_signature=TypeSignature(
                type_in=["file_id"], type_out=["text", "file_content"]
            ),
            semantic_descriptor="Read from an open file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        file_id = input_data.get("file_id", "")
        if file_id not in _FILE_HANDLES:
            return {"content": "", "bytes_read": 0, "error": "file handle not found"}
        f = _FILE_HANDLES[file_id]
        try:
            content = f.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            return {
                "content": content,
                "bytes_read": len(content.encode("utf-8")),
            }
        except Exception as e:
            return {"content": "", "bytes_read": 0, "error": str(e)}


class FileWritePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_WRITE",
            type_signature=TypeSignature(
                type_in=["file_id", "text"], type_out=["bytes_count"]
            ),
            semantic_descriptor="Write to an open file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        file_id = input_data.get("file_id", "")
        content = input_data.get("content") or input_data.get("write_content") or input_data.get("body") or ""
        if file_id not in _FILE_HANDLES:
            return {"bytes_written": 0, "error": "file handle not found"}
        f = _FILE_HANDLES[file_id]
        try:
            text = content if isinstance(content, str) else str(content)
            f.write(text)
            return {"bytes_written": len(text.encode("utf-8"))}
        except Exception as e:
            return {"bytes_written": 0, "error": str(e)}


class FileClosePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_CLOSE",
            type_signature=TypeSignature(
                type_in=["file_id", "bytes_count", "text"], type_out=["bytes_count"]
            ),
            semantic_descriptor="Close an open file handle.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        file_id = input_data.get("file_id", "")
        if file_id not in _FILE_HANDLES:
            return {"success": True}
        f = _FILE_HANDLES.pop(file_id)
        try:
            f.close()
        except Exception:
            pass
        return {"success": True}

