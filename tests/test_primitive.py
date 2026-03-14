from __future__ import annotations

import os
from typing import Any, Dict

import pytest

from primitives.stateless.network import (
    DNSResolvePrimitive,
    HTTPGetPrimitive,
    HTTPPostPrimitive,
    TCPConnectPrimitive,
    TLSHandshakePrimitive,
)
from primitives.stateless.rendering import (
    CSSLayoutPrimitive,
    HTMLParsePrimitive,
    JSExecutePrimitive,
    WindowRenderPrimitive,
)
from primitives.stateless.text import (
    SearchIndexPrimitive,
    TextLayoutPrimitive,
    UTF8DecodePrimitive,
    ScrollInputPrimitive,
)
from primitives.stateless.file import (
    FileClosePrimitive,
    FileOpenPrimitive,
    FileReadPrimitive,
    FileWritePrimitive,
)
from primitives.stateless.nlp import NLPEncodePrimitive, NLPTranslatePrimitive
from primitives.stateless.misc import BookmarkWritePrimitive
from primitives.stateful.session_store import SessionStore
from primitives.stateful.cache_layer import CacheLayer
from primitives.stateful.file_state import FileState


@pytest.mark.parametrize(
    "primitive_cls,input_data,expected_keys",
    [
        (DNSResolvePrimitive, {"domain": "example.com"}, {"ip", "ttl", "domain"}),
        (TCPConnectPrimitive, {"ip": "127.0.0.1", "port": 80}, {"connection_id", "status"}),
        (TLSHandshakePrimitive, {"connection_id": "conn-1"}, {"session_key", "cert_valid"}),
        (
            HTTPGetPrimitive,
            {"url": "https://example.com", "headers": {}},
            {"status_code", "body", "headers"},
        ),
        (
            HTTPPostPrimitive,
            {"url": "https://example.com", "body": {}, "headers": {}},
            {"status_code", "response"},
        ),
        (HTMLParsePrimitive, {"html": "<html><title>X</title></html>"}, {"dom_tree", "title"}),
        (CSSLayoutPrimitive, {"dom_tree": {"children": []}}, {"layout"}),
        (JSExecutePrimitive, {"dom_tree": {}, "scripts": ["console.log(1)"]}, {"dom_tree", "console_output"}),
        (WindowRenderPrimitive, {"layout": {}}, {"rendered", "frame_id"}),
        (UTF8DecodePrimitive, {"raw_bytes": "hello"}, {"text", "encoding"}),
        (TextLayoutPrimitive, {"text": "hello world"}, {"lines", "word_count"}),
        (ScrollInputPrimitive, {"frame_id": "f1", "delta": 10}, {"position"}),
        (SearchIndexPrimitive, {"text": "abcabc", "query": "ab"}, {"matches", "count"}),
        (FileOpenPrimitive, {"path": "/tmp/x", "mode": "r"}, {"file_id", "size"}),
        (FileReadPrimitive, {"file_id": "file-1"}, {"content", "bytes_read"}),
        (FileWritePrimitive, {"file_id": "file-1", "content": "x"}, {"bytes_written"}),
        (FileClosePrimitive, {"file_id": "file-1"}, {"success"}),
        (NLPTranslatePrimitive, {"text": "hi", "target_lang": "fr"}, {"translated", "confidence"}),
        (NLPEncodePrimitive, {"text": "hello"}, {"embedding", "dim"}),
        (
            BookmarkWritePrimitive,
            {"url": "https://example.com", "title": "Example", "tags": ["a"]},
            {"bookmark_id", "saved"},
        ),
    ],
)
def test_stateless_primitives_return_structure(primitive_cls, input_data: Dict[str, Any], expected_keys: set[str]) -> None:
    prim = primitive_cls()
    out = prim.invoke(input_data, session_id=None)
    assert expected_keys.issubset(out.keys())


def test_session_store_persistence_and_isolation(tmp_path, monkeypatch) -> None:
    # Redirect state directory to a temp location by patching HOME.
    monkeypatch.setenv("HOME", str(tmp_path))

    store1 = SessionStore()
    store2 = SessionStore()

    # Same session_id: data should persist across instances.
    sid = "s1"
    store1.invoke({"operation": "set", "key": "k", "value": 42}, session_id=sid)
    res = store2.invoke({"operation": "get", "key": "k"}, session_id=sid)
    assert res["found"] is True
    assert res["value"] == 42

    # Different session_id: isolation.
    res_other = store2.invoke({"operation": "get", "key": "k"}, session_id="s2")
    assert res_other["found"] is False


def test_cache_layer_persistence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    cache1 = CacheLayer()
    cache2 = CacheLayer()
    sid = "s3"

    cache1.invoke({"operation": "set", "key": "k", "value": "v", "ttl_seconds": 60}, session_id=sid)
    res = cache2.invoke({"operation": "get", "key": "k"}, session_id=sid)
    assert res["hit"] is True
    assert res["expired"] is False
    assert res["value"] == "v"


def test_file_state_read_write_and_isolation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    fs1 = FileState()
    fs2 = FileState()

    content = {"a": 1}
    sid = "sx"
    path = "/virtual/file.json"

    write_res = fs1.invoke({"operation": "write", "path": path, "content": content}, session_id=sid)
    assert write_res["success"] is True
    assert write_res["bytes_written"] > 0

    read_res = fs2.invoke({"operation": "read", "path": path}, session_id=sid)
    assert read_res["exists"] is True
    assert read_res["content"] == content

    # Another session should not see this file.
    read_other = fs2.invoke({"operation": "read", "path": path}, session_id="other")
    assert read_other["exists"] is False

