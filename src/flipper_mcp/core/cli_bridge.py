"""CLI bridge for sending text CLI commands to Flipper Zero.

The Flipper's USB CDC serial supports two modes on the same port:
    - CLI mode: text commands terminated by CR, prompt shown as `>: `
    - RPC mode: nanopb-delimited protobuf messages, entered via `start_rpc_session`

The MCP server normally runs in RPC mode. For radio-protocol features
(subghz, rfid) the firmware only exposes text CLI commands, not RPC.

CLIBridge handles switching from RPC→CLI, executing a text command,
reading its response (until prompt or fixed duration), and leaving the
session flagged so the next RPC call re-negotiates mode automatically.

Typical usage:
    out = await flipper.cli.send_command("subghz rx 433920000 0", read_duration=5.0)
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Optional

from .transport.base import FlipperTransport
from .protobuf_gen import flipper_pb2


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _encode_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


class CLIBridge:
    """Execute CLI text commands on the Flipper with RPC mode-switching."""

    def __init__(self, transport: FlipperTransport, protobuf_rpc) -> None:
        self.transport = transport
        self.protobuf_rpc = protobuf_rpc
        self._lock = asyncio.Lock()

    async def send_command(
        self,
        command: str,
        timeout: float = 5.0,
        read_duration: Optional[float] = None,
        stop_running_app: bool = False,
    ) -> str:
        """Execute a CLI command and return the response text.

        Args:
            command: CLI command without trailing newline.
            timeout: Max time to wait for the prompt to reappear.
            read_duration: If set, read for this fixed duration instead of
                waiting for the prompt. Used for streaming commands like
                `subghz rx` that don't return until Ctrl+C.
            stop_running_app: If True, send `loader close` first to release
                hardware held by a running app (subghz/rfid/nfc CLI refuse
                to run while their app is open).
        """
        async with self._lock:
            await self._exit_rpc_to_cli()
            if stop_running_app:
                await self._send_raw_cli("loader close", timeout=2.5)
            return await self._send_raw_cli(
                command, timeout=timeout, read_duration=read_duration
            )

    async def send_commands(
        self,
        commands: list[str],
        per_command_timeout: float = 5.0,
    ) -> list[str]:
        """Execute a batch of CLI commands atomically (single mode switch)."""
        async with self._lock:
            await self._exit_rpc_to_cli()
            results: list[str] = []
            for cmd in commands:
                results.append(await self._send_raw_cli(cmd, timeout=per_command_timeout))
            return results

    async def interrupt(self) -> None:
        """Send Ctrl+C to interrupt a streaming command."""
        try:
            await self.transport.send(b"\x03")
        except Exception:
            pass

    async def _exit_rpc_to_cli(self) -> None:
        """Leave RPC mode (if active) and land at a fresh CLI prompt."""
        if getattr(self.protobuf_rpc, "_rpc_session_started", False):
            try:
                main = flipper_pb2.Main()
                main.command_id = 0xDEAD
                main.has_next = False
                main.stop_session.SetInParent()
                payload = main.SerializeToString()
                await self.transport.send(_encode_varint(len(payload)) + payload)
            except Exception:
                pass
            self.protobuf_rpc._rpc_session_started = False
            await asyncio.sleep(0.25)

        try:
            self.transport.clear_receive_buffer()
        except Exception:
            pass

        try:
            await self.transport.send(b"\x03\r")
        except Exception:
            pass
        await asyncio.sleep(0.15)
        await self._drain(max_seconds=0.3)

    async def _send_raw_cli(
        self,
        command: str,
        timeout: float = 5.0,
        read_duration: Optional[float] = None,
    ) -> str:
        try:
            self.transport.clear_receive_buffer()
        except Exception:
            pass

        await self.transport.send((command + "\r\n").encode())

        if read_duration is not None:
            raw = await self._read_for_duration(read_duration)
            try:
                await self.transport.send(b"\x03")
            except Exception:
                pass
            await asyncio.sleep(0.15)
            raw += await self._drain_to_string(max_seconds=0.3)
        else:
            raw = await self._read_until_prompt(timeout=timeout)

        return self._clean_output(command, raw)

    async def _read_until_prompt(self, timeout: float) -> str:
        end = time.monotonic() + timeout
        buf = bytearray()
        while time.monotonic() < end:
            remaining = max(0.05, min(0.3, end - time.monotonic()))
            chunk = await self.transport.receive(timeout=remaining)
            if not chunk:
                continue
            buf.extend(chunk)
            stripped = _ANSI_RE.sub("", buf.decode("utf-8", errors="replace")).rstrip()
            if stripped.endswith(">:"):
                tail_end = time.monotonic() + 0.15
                while time.monotonic() < tail_end:
                    more = await self.transport.receive(timeout=0.05)
                    if more:
                        buf.extend(more)
                        tail_end = time.monotonic() + 0.1
                break
        return buf.decode("utf-8", errors="replace")

    async def _read_for_duration(self, duration: float) -> str:
        end = time.monotonic() + duration
        buf = bytearray()
        while time.monotonic() < end:
            remaining = max(0.05, min(0.5, end - time.monotonic()))
            try:
                chunk = await self.transport.receive(timeout=remaining)
            except Exception:
                break
            if chunk:
                buf.extend(chunk)
        return buf.decode("utf-8", errors="replace")

    async def _drain(self, max_seconds: float = 0.3) -> None:
        end = time.monotonic() + max_seconds
        while time.monotonic() < end:
            chunk = await self.transport.receive(timeout=0.05)
            if not chunk:
                if time.monotonic() + 0.05 >= end:
                    break

    async def _drain_to_string(self, max_seconds: float = 0.3) -> str:
        end = time.monotonic() + max_seconds
        buf = bytearray()
        while time.monotonic() < end:
            chunk = await self.transport.receive(timeout=0.05)
            if chunk:
                buf.extend(chunk)
        return buf.decode("utf-8", errors="replace")

    @staticmethod
    def _clean_output(command: str, raw: str) -> str:
        text = _ANSI_RE.sub("", raw)
        lines = text.splitlines()
        # Drop command echo (it's always the first non-empty line)
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and lines[0].strip() == command.strip():
            lines.pop(0)
        # Drop trailing prompt/blank lines
        while lines and lines[-1].strip() in ("", ">:", ">"):
            lines.pop()
        return "\n".join(lines).strip()
