from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from core.primitive import CapabilityPrimitive, TypeSignature


def _state_file_path(session_id: str, primitive_id: str) -> str:
    base_dir = os.path.expanduser("~/.icm-os/state")
    return os.path.join(base_dir, session_id, f"{primitive_id}.json")


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _write_json_atomic(path: str, payload: Dict[str, Any]) -> None:
    _ensure_parent_dir(path)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _assert_serializable_dict(content: Any) -> Dict[str, Any]:
    if not isinstance(content, dict):
        raise TypeError("content must be a dict")
    # Ensure JSON-serializable
    json.dumps(content)
    return content


class FileState(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="FILE_STATE",
            type_signature=TypeSignature(type_in=["text"], type_out=["text", "file_state_result"]),
            semantic_descriptor="Per-session virtual file state with read/write operations.",
            is_stateful=True,
        )

    def invoke(self, input_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or "default"
        operation = str(input_data.get("operation", ""))
        print(f"[STATEFUL: {self.id}] session={sid} op={operation}")

        path = _state_file_path(sid, self.id)
        state = _read_json(path)
        files = state.get("files")
        if not isinstance(files, dict):
            files = {}

        now = time.time()

        try:
            if operation == "read":
                p = str(input_data.get("path", ""))
                exists = p in files
                content = files.get(p) if exists else {}
                if not isinstance(content, dict):
                    content = {}
                return {"content": content, "exists": exists}

            if operation == "write":
                p = str(input_data.get("path", ""))
                content = _assert_serializable_dict(input_data.get("content"))
                files[p] = content
                payload = {"files": files, "updated_at": now}
                serialized = json.dumps(payload, ensure_ascii=False)
                _write_json_atomic(path, payload)
                return {"success": True, "bytes_written": len(serialized.encode("utf-8"))}

            return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}

