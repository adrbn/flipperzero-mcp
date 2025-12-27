#!/usr/bin/env python3
"""
Check whether the Flipper WiFi devboard is reachable as a TCP bridge for Protobuf RPC.

This repo's WiFi transport expects a raw TCP socket bridge (byte stream) at host:port.
We attempt to connect and then do a protobuf RPC ping + a small storage listing.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _get_candidates() -> list[tuple[str, int]]:
    """
    Build host/port candidates to try.

    Priority:
    - FLIPPER_WIFI_HOST / FLIPPER_WIFI_PORT
    - Common devboard defaults: 192.168.4.1 (AP), blackmagic.local, 192.168.1.1
    """
    host = os.environ.get("FLIPPER_WIFI_HOST")
    port_s = os.environ.get("FLIPPER_WIFI_PORT")
    port = int(port_s) if port_s else 8080

    candidates: list[tuple[str, int]] = []
    if host:
        candidates.append((host, port))

    # Common defaults
    common_hosts = ["blackmagic.local", "192.168.4.1", "192.168.1.1"]
    common_ports = [port]
    # If user didn't specify a port, try a few plausible alternates too.
    if not port_s:
        common_ports.extend([80, 8081, 1337])

    for h in common_hosts:
        for p in common_ports:
            candidates.append((h, p))

    # De-dupe preserving order
    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, int]] = []
    for c in candidates:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


async def _try_one(host: str, port: int) -> bool:
    # IMPORTANT:
    # Importing `flipper_mcp` triggers `flipper_mcp/__init__.py`, which imports the MCP server
    # (and therefore requires the optional `mcp` dependency). For this connectivity check we
    # only need core transport/client, so we force-import from local `src/` to avoid that.
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from flipper_mcp.core.transport.wifi import WiFiTransport
    from flipper_mcp.core.flipper_client import FlipperClient

    print(f"\nTrying {host}:{port} ...")
    transport = WiFiTransport({"host": host, "port": port, "connect_timeout": 2.5})
    client = FlipperClient(transport)

    try:
        if not await client.connect():
            print("  ✗ connect() failed")
            return False

        health = await client.get_connection_health(probe_rpc=True)
        print(f"  transport_connected={health.get('transport_connected')}")
        print(f"  rpc_responsive={health.get('rpc_responsive')}")
        print(f"  connected={health.get('connected')}")

        if not health.get("connected"):
            return False

        # Quick proof we can do useful work over the bridge.
        try:
            items = await client.storage.list("/ext/apps_manifests")
            print(f"  /ext/apps_manifests: {len(items)} item(s)")
            for it in items[:10]:
                print(f"    - {it}")
        except Exception as e:
            print(f"  (storage list failed: {e})")

        return True
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def main() -> int:
    print("=" * 60)
    print("Flipper WiFi devboard bridge check (TCP -> Protobuf RPC)")
    print("=" * 60)

    ok_any = False
    http_only_hosts: set[str] = set()
    for host, port in _get_candidates():
        try:
            ok = await _try_one(host, port)
        except Exception as e:
            print(f"\nTrying {host}:{port} ...")
            print(f"  ✗ error: {e}")
            # Heuristic: if importing succeeded and connect fails for all non-80 ports,
            # later we’ll emit a hint when HTTP (80) is reachable but bridge ports are not.
            ok = False
        if ok:
            ok_any = True
            break

    print("\n" + "=" * 60)
    if ok_any:
        print("✓ WiFi bridge is reachable and Protobuf RPC responds.")
        return 0
    print("✗ Could not reach a working WiFi TCP bridge for Protobuf RPC.")
    print("  If you’re in AP mode, connect your computer to the devboard WiFi and retry.")
    print("  If you’re in home-WiFi (STA) mode, set FLIPPER_WIFI_HOST to the devboard IP and retry.")
    print("  If you can browse a web UI (HTTP/80) but no bridge port is open, you likely have HTTP-only firmware (e.g. stock Blackmagic).")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))


