"""RFID module for Flipper Zero MCP (125 kHz LF).

Wraps the firmware CLI:
    rfid read [normal|indala]                 - read a card
    rfid <write|emulate> <key_type> <key_data>
    rfid raw_read <ask|psk> <filename>         - raw signal capture
    rfid raw_emulate <filename>                - replay raw capture
    rfid raw_analyze <filename>                - decode raw for protocol dev

Plus file management for saved .rfid cards.

Common key_types:
    EM4100      - EM-Micro EM4100 / EM4102 (most common 125 kHz)
    H10301      - HID Prox (26-bit Wiegand)
    Indala26    - Motorola Indala 26-bit
    IoProxXSF   - HID ioProx
    AWID        - AWID 26-bit
    Paradox     - Paradox
"""

from __future__ import annotations

from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


DEFAULT_RFID_DIR = "/ext/lfrfid"


class RFIDModule(FlipperModule):
    @property
    def name(self) -> str:
        return "rfid"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "125 kHz LF RFID: read, write, emulate, raw capture/replay"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="rfid_list_files",
                description=f"List saved RFID cards (.rfid). Defaults to {DEFAULT_RFID_DIR}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": DEFAULT_RFID_DIR},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="rfid_read_file",
                description="Read a saved .rfid file (shows protocol + key data).",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="rfid_delete_file",
                description="Delete a saved .rfid file.",
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
                name="rfid_read",
                description=(
                    "Read a 125 kHz card presented to the LF antenna. Returns protocol + data. "
                    "Hold the card on the back of the Flipper during the read window."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["normal", "indala"],
                            "default": "normal",
                            "description": "'normal' covers most protocols; 'indala' forces Indala decode.",
                        },
                        "read_duration": {"type": "number", "default": 5.0},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="rfid_write",
                description=(
                    "Write a key to a writable card (T5577 blank). WARNING: modifies the card. "
                    "Research/authorized testing only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key_type": {
                            "type": "string",
                            "description": "Protocol name, e.g. EM4100, H10301, Indala26",
                        },
                        "key_data": {
                            "type": "string",
                            "description": "Hex key data (length depends on protocol)",
                        },
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["key_type", "key_data", "confirm"],
                },
            ),
            Tool(
                name="rfid_emulate",
                description=(
                    "Emulate a 125 kHz card for a duration (Flipper pretends to BE the card). "
                    "Research/authorized testing only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key_type": {"type": "string"},
                        "key_data": {"type": "string"},
                        "read_duration": {
                            "type": "number",
                            "description": "How many seconds to emulate.",
                            "default": 10.0,
                        },
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["key_type", "key_data", "confirm"],
                },
            ),
            Tool(
                name="rfid_raw_read",
                description=(
                    "Capture raw LF signal to a file for protocol analysis. "
                    "Useful when `rfid read` can't identify the protocol."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["ask", "psk"],
                            "description": "Modulation: ASK (most common) or PSK (Indala/HID).",
                            "default": "ask",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Filename under /ext/lfrfid (without extension).",
                        },
                        "read_duration": {"type": "number", "default": 5.0},
                    },
                    "required": ["filename"],
                },
            ),
            Tool(
                name="rfid_raw_emulate",
                description="Replay a previously captured raw LF signal from file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "read_duration": {"type": "number", "default": 10.0},
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["filename", "confirm"],
                },
            ),
            Tool(
                name="rfid_raw_analyze",
                description="Decode a raw LF signal file (useful for new-protocol reverse engineering).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                    },
                    "required": ["filename"],
                },
            ),
            Tool(
                name="rfid_launch_app",
                description="Launch the 125 kHz RFID app on the Flipper (UI).",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="rfid_launch_file",
                description="Launch the RFID app with a specific saved .rfid file (enables Emulate from UI).",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Any) -> Sequence[TextContent]:
        args = arguments or {}
        try:
            if tool_name == "rfid_list_files":
                return await self._list_files(args.get("path", DEFAULT_RFID_DIR))
            if tool_name == "rfid_read_file":
                return await self._read_file(args["path"])
            if tool_name == "rfid_delete_file":
                return await self._delete_file(args["path"], bool(args.get("confirm", False)))
            if tool_name == "rfid_read":
                return await self._read(
                    args.get("mode", "normal"),
                    float(args.get("read_duration", 5.0)),
                )
            if tool_name == "rfid_write":
                return await self._write(
                    str(args["key_type"]),
                    str(args["key_data"]),
                    bool(args.get("confirm", False)),
                )
            if tool_name == "rfid_emulate":
                return await self._emulate(
                    str(args["key_type"]),
                    str(args["key_data"]),
                    float(args.get("read_duration", 10.0)),
                    bool(args.get("confirm", False)),
                )
            if tool_name == "rfid_raw_read":
                return await self._raw_read(
                    args.get("mode", "ask"),
                    str(args["filename"]),
                    float(args.get("read_duration", 5.0)),
                )
            if tool_name == "rfid_raw_emulate":
                return await self._raw_emulate(
                    str(args["filename"]),
                    float(args.get("read_duration", 10.0)),
                    bool(args.get("confirm", False)),
                )
            if tool_name == "rfid_raw_analyze":
                return await self._raw_analyze(str(args["filename"]))
            if tool_name == "rfid_launch_app":
                return await self._launch_app(None)
            if tool_name == "rfid_launch_file":
                return await self._launch_app(str(args["path"]))
        except KeyError as e:
            return [TextContent(type="text", text=f"Missing argument: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        return [TextContent(type="text", text=f"Unknown RFID tool '{tool_name}'")]

    # --- helpers ---

    def _require_cli(self) -> tuple[bool, str]:
        if not getattr(self.flipper, "cli", None):
            return False, "❌ CLI bridge not available"
        return True, ""

    async def _list_files(self, path: str) -> Sequence[TextContent]:
        files = await self.flipper.storage.list(path) or []
        return [TextContent(
            type="text", text=f"{path}:\n" + "\n".join(f"  {f}" for f in files) if files else f"{path}: (empty)"
        )]

    async def _read_file(self, path: str) -> Sequence[TextContent]:
        content = await self.flipper.storage.read(path)
        return [TextContent(
            type="text",
            text=f"=== {path} ===\n{content}" if content else f"(empty or failed: {path})",
        )]

    async def _delete_file(self, path: str, confirm: bool) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to delete: confirm=true required")]
        ok = await self.flipper.storage.delete(path)
        return [TextContent(type="text", text=f"{'✅' if ok else '❌'} Delete {path}")]

    async def _read(self, mode: str, duration: float) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        mode_arg = "" if mode == "normal" else " indala"
        out = await self.flipper.cli.send_command(
            f"rfid read{mode_arg}", read_duration=duration, stop_running_app=True,
        )
        return [TextContent(
            type="text",
            text=f"🪪 RFID read ({mode}, {duration}s)\n---\n{out or '(no card detected)'}"
        )]

    async def _write(self, key_type: str, key_data: str, confirm: bool) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to write: confirm=true required")]
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"rfid write {key_type} {key_data}", read_duration=10.0, stop_running_app=True,
        )
        return [TextContent(
            type="text",
            text=f"✍️  Write {key_type}={key_data}\n---\n{out or '(no output)'}"
        )]

    async def _emulate(
        self, key_type: str, key_data: str, duration: float, confirm: bool
    ) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to emulate: confirm=true required")]
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"rfid emulate {key_type} {key_data}",
            read_duration=duration,
            stop_running_app=True,
        )
        return [TextContent(
            type="text",
            text=f"📡 Emulated {key_type}={key_data} for {duration}s\n---\n{out or '(done)'}"
        )]

    async def _raw_read(self, mode: str, filename: str, duration: float) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"rfid raw_read {mode} {filename}",
            read_duration=duration,
            stop_running_app=True,
        )
        return [TextContent(
            type="text",
            text=f"📼 Raw {mode.upper()} capture → {filename} ({duration}s)\n---\n{out or '(no output)'}"
        )]

    async def _raw_emulate(
        self, filename: str, duration: float, confirm: bool
    ) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to emulate: confirm=true required")]
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"rfid raw_emulate {filename}",
            read_duration=duration,
            stop_running_app=True,
        )
        return [TextContent(type="text", text=f"📡 Raw replay {filename} ({duration}s)\n---\n{out or '(done)'}")]

    async def _raw_analyze(self, filename: str) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"rfid raw_analyze {filename}", timeout=15.0, stop_running_app=True,
        )
        return [TextContent(type="text", text=f"🔬 Analyze {filename}\n---\n{out or '(no output)'}")]

    async def _launch_app(self, path: str | None) -> Sequence[TextContent]:
        args = path or ""
        ok = await self.flipper.app.launch("125 kHz RFID", args=args)
        suffix = f" with {path}" if path else ""
        return [TextContent(type="text", text=f"{'✅' if ok else '❌'} Launch 125 kHz RFID{suffix}")]

    def validate_environment(self) -> tuple[bool, str]:
        return True, ""

    def requires_sd_card(self) -> bool:
        return True
