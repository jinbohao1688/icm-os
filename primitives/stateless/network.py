from __future__ import annotations

from typing import Any, Dict, List

from core.primitive import CapabilityPrimitive, TypeSignature


class DNSResolvePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="DNS_RESOLVE",
            type_signature=TypeSignature(
                type_in=["DNSResolveInput"], type_out=["DNSResolveOutput"]
            ),
            semantic_descriptor="Resolve a domain name to an IP address.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        domain = input_data.get("domain", "example.com")
        return {
            "ip": "93.184.216.34",
            "ttl": 300,
            "domain": domain,
        }


class TCPConnectPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="TCP_CONNECT",
            type_signature=TypeSignature(
                type_in=["TCPConnectInput"], type_out=["TCPConnectOutput"]
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
                type_in=["TLSHandshakeInput"], type_out=["TLSHandshakeOutput"]
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
                type_in=["HTTPGetInput"], type_out=["HTTPGetOutput"]
            ),
            semantic_descriptor="Perform an HTTP GET request.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        url = input_data.get("url", "https://example.com")
        headers = input_data.get("headers", {})
        return {
            "status_code": 200,
            "body": f"Mock response body for {url}",
            "headers": {"Content-Type": "text/html", **headers},
        }


class HTTPPostPrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="HTTP_POST",
            type_signature=TypeSignature(
                type_in=["HTTPPostInput"], type_out=["HTTPPostOutput"]
            ),
            semantic_descriptor="Perform an HTTP POST request.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        url = input_data.get("url", "https://example.com")
        body = input_data.get("body", {})
        return {
            "status_code": 201,
            "response": f"Mock response for POST to {url} with body keys {list(body.keys())}",
        }

