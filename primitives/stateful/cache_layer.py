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


class CacheLayer(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="CACHE_LAYER",
            type_signature=TypeSignature(
                type_in=["CacheLayerInput"], type_out=["CacheLayerOutput"]
            ),
            semantic_descriptor="Per-session TTL cache with get/set operations.",
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

        now = time.time()

        try:
            if operation == "get":
                key = str(input_data.get("key", ""))
                entry = data.get(key)
                if not isinstance(entry, dict):
                    return {"value": None, "hit": False, "expired": False}
                expires_at = entry.get("expires_at")
                if isinstance(expires_at, (int, float)) and now >= float(expires_at):
                    # expired: treat as miss and optionally delete
                    try:
                        del data[key]
                        _write_json_atomic(path, {"data": data, "updated_at": now})
                    except Exception:
                        pass
                    return {"value": None, "hit": False, "expired": True}
                return {"value": entry.get("value"), "hit": True, "expired": False}

            if operation == "set":
                key = str(input_data.get("key", ""))
                value = input_data.get("value")
                ttl_seconds = int(input_data.get("ttl_seconds", 0))
                expires_at = now + max(ttl_seconds, 0)
                data[key] = {"value": value, "expires_at": expires_at}
                _write_json_atomic(path, {"data": data, "updated_at": now})
                return {"success": True}

            return {"error": f"Unknown operation: {operation}"}
        except Exception as e:
            return {"error": str(e)}

