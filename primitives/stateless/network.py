from __future__ import annotations

from typing import Any, Dict, List

import requests
import urllib3

from core.primitive import CapabilityPrimitive, TypeSignature

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DNSResolvePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="DNS_RESOLVE",
            type_signature=TypeSignature(
                type_in=["text", "domain"], type_out=["ip"]
            ),
            semantic_descriptor="Resolve a domain name to an IP address.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        import socket
        domain = input_data.get("domain", "example.com")
        try:
            ip = socket.gethostbyname(domain)
        except Exception:
            ip = "0.0.0.0"
        return {
            "ip": ip,
            "ttl": 300,
            "domain": domain,
        }


class TCPConnectPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="TCP_CONNECT",
            type_signature=TypeSignature(
                type_in=["ip", "text"], type_out=["connection_id"]
            ),
            semantic_descriptor="Establish a TCP connection to an IP and port.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        ip = input_data.get("ip", "127.0.0.1")
        port = input_data.get("port", 80)
        return {
            "connection_id": f"conn-{ip}-{port}",
            "status": "CONNECTED",
        }


class TLSHandshakePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="TLS_HANDSHAKE",
            type_signature=TypeSignature(
                type_in=["connection_id"], type_out=["session_key"]
            ),
            semantic_descriptor="Perform a TLS handshake on an existing TCP connection.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        connection_id = input_data.get("connection_id", "conn-unknown")
        return {
            "session_key": f"session-key-for-{connection_id}",
            "cert_valid": True,
        }


class HTTPGetPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="HTTP_GET",
            type_signature=TypeSignature(
                type_in=["session_key", "text"], type_out=["http_response", "text"]
            ),
            semantic_descriptor="Perform an HTTP GET request.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        url = input_data.get("url", "https://example.com")
        headers = input_data.get("headers") or {}
        try:
            resp = requests.get(url, headers=headers, timeout=30, verify=False)
            body = (resp.text or "")[:2000]
            return {
                "status_code": resp.status_code,
                "body": body,
                "headers": dict(resp.headers),
            }
        except Exception as e:
            return {"status_code": 0, "error": str(e)}


class HTTPPostPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="HTTP_POST",
            type_signature=TypeSignature(
                type_in=["session_key", "text", "http_response", "dom_tree", "kv_result", "position"],
                type_out=["http_response", "text"],
            ),
            semantic_descriptor="Perform an HTTP POST request.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        url = input_data.get("url", "https://example.com")
        body = input_data.get("body")
        try:
            resp = requests.post(url, json=body, timeout=30, verify=False)
            return {
                "status_code": resp.status_code,
                "response": resp.text[:2000] if resp.text else "",
            }
        except Exception as e:
            return {"status_code": 0, "response": "", "error": str(e)}

