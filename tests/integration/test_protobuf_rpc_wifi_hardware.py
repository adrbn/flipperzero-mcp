import os

import pytest

from flipper_mcp.core.transport.wifi import WiFiTransport
from flipper_mcp.core.protobuf_rpc import ProtobufRPC


def _wifi_host_port() -> tuple[str, int] | None:
    host = os.environ.get("FLIPPER_WIFI_HOST", "").strip()
    port_s = os.environ.get("FLIPPER_WIFI_PORT", "").strip()
    if not host:
        return None
    try:
        port = int(port_s) if port_s else 8080
    except ValueError:
        return None
    return host, port


@pytest.mark.integration
@pytest.mark.asyncio
async def test_protobuf_ping_over_wifi_bridge():
    """
    Hardware-gated smoke test for the ESP32 WiFi bridge.

    Requirements:
    - FLIPPER_WIFI_HOST set (and optionally FLIPPER_WIFI_PORT).
    - Bridge firmware exposing raw Protobuf RPC byte stream over TCP.
    """
    hp = _wifi_host_port()
    if not hp:
        pytest.skip("Set FLIPPER_WIFI_HOST (and optionally FLIPPER_WIFI_PORT) to run WiFi bridge test")
    host, port = hp

    transport = WiFiTransport({"host": host, "port": port, "connect_timeout": 3.0})
    if not await transport.connect():
        pytest.skip(f"Could not connect to WiFi bridge at {host}:{port}")

    try:
        rpc = ProtobufRPC(transport)
        echoed = await rpc.ping(b"mcp")
        assert echoed == b"mcp"
    finally:
        await transport.disconnect()


