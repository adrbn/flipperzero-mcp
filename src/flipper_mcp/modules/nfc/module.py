"""NFC module for Flipper Zero MCP (13.56 MHz HF).

The Flipper firmware does not expose NFC as a CLI command set (the `nfc` CLI
command just opens the UI app). This module works by:

    - managing .nfc files on the SD card (list, read, write, delete)
    - launching the NFC app with or without a specific file argument
    - parsing the key fields (UID, ATQA, SAK, card type, block data) from .nfc files

Typical workflow for research:
    1. Use `nfc_launch_app` + read on the Flipper UI to capture a card → saves .nfc
    2. `nfc_list_files` / `nfc_read_file` to inspect the dump
    3. `nfc_launch_file` to emulate the saved card
    4. `nfc_write_file` to side-load a dump from another source
"""

from __future__ import annotations

import re
from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


DEFAULT_NFC_DIR = "/ext/nfc"


class NFCModule(FlipperModule):
    @property
    def name(self) -> str:
        return "nfc"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "13.56 MHz HF NFC: manage dumps, launch read/emulate app, parse MIFARE Classic data"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="nfc_list_files",
                description=f"List .nfc files (saved dumps). Defaults to {DEFAULT_NFC_DIR}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": DEFAULT_NFC_DIR},
                        "recursive": {"type": "boolean", "default": False},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="nfc_read_file",
                description="Read a .nfc file and return its raw text contents.",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="nfc_parse_file",
                description=(
                    "Parse a .nfc file and return structured info: UID, ATQA, SAK, card type, "
                    "MIFARE Classic blocks if present."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="nfc_write_file",
                description=(
                    "Write a .nfc file to the SD card (side-load a dump from outside). "
                    "Overwrites if the file exists. Research/authorized testing only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "confirm_overwrite": {"type": "boolean", "default": False},
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="nfc_delete_file",
                description="Delete a .nfc file from the Flipper.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["path", "confirm"],
                },
            ),
            Tool(
                name="nfc_launch_app",
                description="Launch the NFC app on the Flipper (UI for Read/Emulate/Save).",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="nfc_launch_file",
                description=(
                    "Launch the NFC app with a specific .nfc file (enables Emulate/Write from UI). "
                    "User must confirm emulation on-device."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="nfc_detect_reader",
                description="Launch 'NFC Detect Reader' (if available) - scans for nearby NFC readers.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Any) -> Sequence[TextContent]:
        args = arguments or {}
        try:
            if tool_name == "nfc_list_files":
                return await self._list_files(
                    args.get("path", DEFAULT_NFC_DIR),
                    bool(args.get("recursive", False)),
                )
            if tool_name == "nfc_read_file":
                return await self._read_file(args["path"])
            if tool_name == "nfc_parse_file":
                return await self._parse_file(args["path"])
            if tool_name == "nfc_write_file":
                return await self._write_file(
                    str(args["path"]),
                    str(args["content"]),
                    bool(args.get("confirm_overwrite", False)),
                )
            if tool_name == "nfc_delete_file":
                return await self._delete_file(args["path"], bool(args.get("confirm", False)))
            if tool_name == "nfc_launch_app":
                return await self._launch_app(None)
            if tool_name == "nfc_launch_file":
                return await self._launch_app(str(args["path"]))
            if tool_name == "nfc_detect_reader":
                return await self._detect_reader()
        except KeyError as e:
            return [TextContent(type="text", text=f"Missing argument: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        return [TextContent(type="text", text=f"Unknown NFC tool '{tool_name}'")]

    async def _list_files(self, path: str, recursive: bool) -> Sequence[TextContent]:
        files = await self.flipper.storage.list(path) or []
        if not files:
            return [TextContent(type="text", text=f"{path}: (empty)")]
        lines = [f"{path}:"]
        for f in files:
            lines.append(f"  {f}")
        if recursive:
            for f in files:
                if f.startswith("[D] "):
                    subdir = f[4:].strip()
                    sub_path = f"{path.rstrip('/')}/{subdir}"
                    sub = await self.flipper.storage.list(sub_path) or []
                    if sub:
                        lines.append(f"{sub_path}:")
                        for sf in sub:
                            lines.append(f"  {sf}")
        return [TextContent(type="text", text="\n".join(lines))]

    async def _read_file(self, path: str) -> Sequence[TextContent]:
        content = await self.flipper.storage.read(path)
        return [TextContent(
            type="text",
            text=f"=== {path} ===\n{content}" if content else f"(empty or failed: {path})",
        )]

    async def _parse_file(self, path: str) -> Sequence[TextContent]:
        content = await self.flipper.storage.read(path)
        if not content:
            return [TextContent(type="text", text=f"(empty or failed: {path})")]

        info: dict[str, str] = {}
        blocks: dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if ":" not in line or line.startswith("#"):
                continue
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            m = re.match(r"Block\s+(\d+)$", k)
            if m:
                blocks[m.group(1)] = v
            else:
                info[k] = v

        out_lines = [f"=== {path} ==="]
        for k in ("Filetype", "Version", "Device type", "UID", "ATQA", "SAK",
                  "Mifare Classic type", "Data format version"):
            if k in info:
                out_lines.append(f"{k}: {info[k]}")

        if blocks:
            out_lines.append("")
            out_lines.append(f"Sectors decoded: {len(blocks)} blocks")
            # Only show first few blocks to avoid huge output
            for i in sorted(blocks.keys(), key=int)[:8]:
                out_lines.append(f"  Block {i}: {blocks[i]}")
            if len(blocks) > 8:
                out_lines.append(f"  ... ({len(blocks) - 8} more blocks)")

        unknown = {k: v for k, v in info.items()
                   if k not in {"Filetype", "Version", "Device type", "UID", "ATQA", "SAK",
                                "Mifare Classic type", "Data format version"}}
        if unknown:
            out_lines.append("")
            out_lines.append("Other fields:")
            for k, v in unknown.items():
                out_lines.append(f"  {k}: {v}")

        return [TextContent(type="text", text="\n".join(out_lines))]

    async def _write_file(self, path: str, content: str, confirm: bool) -> Sequence[TextContent]:
        existing = await self.flipper.storage.read(path)
        if existing and not confirm:
            return [TextContent(
                type="text",
                text=f"Refusing to overwrite {path} (set confirm_overwrite=true).",
            )]
        ok = await self.flipper.storage.write(path, content)
        return [TextContent(type="text", text=f"{'✅ Wrote' if ok else '❌ Failed to write'} {path}")]

    async def _delete_file(self, path: str, confirm: bool) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to delete: confirm=true required")]
        ok = await self.flipper.storage.delete(path)
        return [TextContent(type="text", text=f"{'✅' if ok else '❌'} Delete {path}")]

    async def _launch_app(self, path: str | None) -> Sequence[TextContent]:
        args = path or ""
        ok = await self.flipper.app.launch("NFC", args=args)
        suffix = f" with {path}" if path else ""
        return [TextContent(type="text", text=f"{'✅' if ok else '❌'} Launch NFC{suffix}")]

    async def _detect_reader(self) -> Sequence[TextContent]:
        for app_name in ("Detect Reader", "NFC Detect Reader", "Detect NFC"):
            if await self.flipper.app.launch(app_name):
                return [TextContent(type="text", text=f"✅ Launched '{app_name}'")]
        return [TextContent(
            type="text",
            text="ℹ️ Couldn't find 'Detect Reader' app. On Momentum, launch NFC → Extra Actions → Detect Reader.",
        )]

    def validate_environment(self) -> tuple[bool, str]:
        return True, ""

    def requires_sd_card(self) -> bool:
        return True
