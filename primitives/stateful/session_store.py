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
        # Corrupt / partial file / permission issues: treat as empty state.
        return {}


def _write_json_atomic(path: str, payload: Dict[str, Any]) -> None:
    _ensure_parent_dir(path)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


class SessionStore(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="SESSION_STORE",
            type_signature=TypeSignature(
                type_in=["SessionStoreInput"], type_out=["SessionStoreOutput"]
            ),
            semantic_descriptor="Per-session key-value store with get/set/delete operations.",
            is_stateful=True,
        )

    def invoke(self, input_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or "default"
        operation = str(input_data.get("operation", ""))
        print(f"[STATEFUL: {self.id}] session={sid} op={operation}")

        path = _state_file_path(sid, self.id)
        state = _read_json(path)
        data = state.get("data")
        if not isinstance(data, dict):
            data = {}

        try:
            if operation == "get":
                key = str(input_data.get("key", ""))
                found = key in data
                return {"value": data.get(key), "found": found}

            if operation == "set":
                key = str(input_data.get("key", ""))
                value = input_data.get("value")
                data[key] = value
                _write_json_atomic(
                    path,
                    {"data": data, "updated_at": time.time()},
                )
                return {"success": True}

            if operation == "delete":
                key = str(input_data.get("key", ""))
                deleted = key in data
                if deleted:
                    del data[key]
                _write_json_atomic(
                    path,
                    {"data": data, "updated_at": time.time()},
                )
                return {"deleted": deleted}

            return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}

