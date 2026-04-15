"""SubGHz module for Flipper Zero MCP.

Provides access to the Flipper's 300-928 MHz radio via the firmware CLI:
    subghz rx <freq_hz> <device>              - listen
    subghz rx_raw <freq_hz>                   - capture raw waveform
    subghz tx <3-byte-hex> <freq_hz> <te> <repeat> <device>  - transmit key
    subghz tx_from_file <path> <repeat> <device>             - replay .sub file
    subghz decode_raw <path>                  - decode a raw capture
    subghz chat <freq_hz> <device>            - Flipper-to-Flipper chat

Plus file management (list/read/write/delete .sub files) and app launchers.

device: 0 = internal CC1101, 1 = external CC1101 module
"""

from __future__ import annotations

from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


DEFAULT_SUBGHZ_DIR = "/ext/subghz"


class SubGHzModule(FlipperModule):
    @property
    def name(self) -> str:
        return "subghz"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "300-928 MHz radio: capture, replay, transmit, analyze (CC1101)"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="subghz_list_files",
                description=(
                    "List .sub files (saved captures/keys) in a directory. "
                    f"Defaults to {DEFAULT_SUBGHZ_DIR}."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory on the Flipper SD card",
                            "default": DEFAULT_SUBGHZ_DIR,
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Recurse one level into subdirectories",
                            "default": False,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="subghz_read_file",
                description="Read the contents of a .sub file (frequency, preset, protocol, key).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full path to the .sub file",
                        }
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="subghz_delete_file",
                description="Delete a .sub file from the Flipper SD card.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "confirm": {
                            "type": "boolean",
                            "description": "Must be true (safety).",
                            "default": False,
                        },
                    },
                    "required": ["path", "confirm"],
                },
            ),
            Tool(
                name="subghz_rx",
                description=(
                    "Listen on a frequency and report any signals the CC1101 decodes. "
                    "Returns the text output after `read_duration` seconds. "
                    "Common frequencies: 433920000 (EU/garage), 315000000 (US), 868350000 (EU LPD), "
                    "915000000 (US ISM)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "frequency": {
                            "type": "integer",
                            "description": "Frequency in Hz (e.g. 433920000)",
                        },
                        "read_duration": {
                            "type": "number",
                            "description": "Seconds to listen before returning.",
                            "default": 5.0,
                        },
                        "external_module": {
                            "type": "boolean",
                            "description": "Use external CC1101 module instead of internal.",
                            "default": False,
                        },
                    },
                    "required": ["frequency"],
                },
            ),
            Tool(
                name="subghz_rx_raw",
                description=(
                    "Capture a raw waveform on a frequency for protocol analysis. "
                    "Useful when the protocol isn't auto-decoded."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "frequency": {"type": "integer"},
                        "read_duration": {"type": "number", "default": 5.0},
                    },
                    "required": ["frequency"],
                },
            ),
            Tool(
                name="subghz_tx",
                description=(
                    "Transmit a 3-byte key. WARNING: transmitting on regulated frequencies may be illegal "
                    "in your jurisdiction and can interfere with licensed services. Research use only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key_hex": {
                            "type": "string",
                            "description": "3-byte hex key, e.g. 'AABBCC'",
                        },
                        "frequency": {"type": "integer"},
                        "te": {
                            "type": "integer",
                            "description": "Bit timing in microseconds (typical: 250-500)",
                            "default": 400,
                        },
                        "repeat": {
                            "type": "integer",
                            "description": "Number of repetitions",
                            "default": 5,
                        },
                        "external_module": {"type": "boolean", "default": False},
                        "confirm": {
                            "type": "boolean",
                            "description": "Must be true (authorizes RF transmission).",
                            "default": False,
                        },
                    },
                    "required": ["key_hex", "frequency", "confirm"],
                },
            ),
            Tool(
                name="subghz_tx_from_file",
                description=(
                    "Replay a previously captured .sub file. WARNING: may be illegal depending on content. "
                    "Research/authorized testing only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to .sub file"},
                        "repeat": {"type": "integer", "default": 1},
                        "external_module": {"type": "boolean", "default": False},
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["path", "confirm"],
                },
            ),
            Tool(
                name="subghz_decode_raw",
                description="Decode a raw waveform capture (.sub raw file) into a protocol+key if recognized.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="subghz_chat",
                description=(
                    "Open SubGHz chat on a frequency (other Flippers on the same frequency will see your text). "
                    "Returns initial state; chatting requires UI input."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "frequency": {"type": "integer", "default": 433920000},
                        "external_module": {"type": "boolean", "default": False},
                        "read_duration": {"type": "number", "default": 3.0},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="subghz_launch_app",
                description="Launch the SubGHz app UI on the Flipper (for manual interaction).",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="subghz_launch_frequency_analyzer",
                description="Launch the Frequency Analyzer (locates the strongest ambient frequency).",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="subghz_launch_read",
                description=(
                    "Launch the SubGHz 'Read' feature on a given .sub file (plays it on tap on Flipper). "
                    "Opens the file in the SubGHz app; user confirms playback on-device."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to a .sub file to open"}
                    },
                    "required": ["path"],
                },
            ),
        ]

    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        args = arguments or {}
        try:
            if tool_name == "subghz_list_files":
                return await self._list_files(
                    args.get("path", DEFAULT_SUBGHZ_DIR),
                    bool(args.get("recursive", False)),
                )
            if tool_name == "subghz_read_file":
                return await self._read_file(args["path"])
            if tool_name == "subghz_delete_file":
                return await self._delete_file(args["path"], bool(args.get("confirm", False)))
            if tool_name == "subghz_rx":
                return await self._rx(
                    int(args["frequency"]),
                    float(args.get("read_duration", 5.0)),
                    bool(args.get("external_module", False)),
                )
            if tool_name == "subghz_rx_raw":
                return await self._rx_raw(
                    int(args["frequency"]),
                    float(args.get("read_duration", 5.0)),
                )
            if tool_name == "subghz_tx":
                return await self._tx(
                    str(args["key_hex"]),
                    int(args["frequency"]),
                    int(args.get("te", 400)),
                    int(args.get("repeat", 5)),
                    bool(args.get("external_module", False)),
                    bool(args.get("confirm", False)),
                )
            if tool_name == "subghz_tx_from_file":
                return await self._tx_from_file(
                    str(args["path"]),
                    int(args.get("repeat", 1)),
                    bool(args.get("external_module", False)),
                    bool(args.get("confirm", False)),
                )
            if tool_name == "subghz_decode_raw":
                return await self._decode_raw(str(args["path"]))
            if tool_name == "subghz_chat":
                return await self._chat(
                    int(args.get("frequency", 433920000)),
                    bool(args.get("external_module", False)),
                    float(args.get("read_duration", 3.0)),
                )
            if tool_name == "subghz_launch_app":
                return await self._launch_app(None)
            if tool_name == "subghz_launch_frequency_analyzer":
                return await self._launch_frequency_analyzer()
            if tool_name == "subghz_launch_read":
                return await self._launch_app(str(args["path"]))
        except KeyError as e:
            return [TextContent(type="text", text=f"Missing argument: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        return [TextContent(type="text", text=f"Unknown SubGHz tool '{tool_name}'")]

    # --- helpers ---

    def _require_cli(self) -> tuple[bool, str]:
        if not getattr(self.flipper, "cli", None):
            return False, "❌ CLI bridge not available (device not connected or RPC init failed)"
        return True, ""

    async def _list_files(self, path: str, recursive: bool) -> Sequence[TextContent]:
        files = await self.flipper.storage.list(path) or []
        if not files:
            return [TextContent(type="text", text=f"{path}: (empty)")]
        lines = [f"{path}:"]
        for f in files:
            lines.append(f"  {f}")
        if recursive:
            for f in files:
                # entries like "[D] foo" or "[F] bar.sub"
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
        if not content:
            return [TextContent(type="text", text=f"(empty or failed to read {path})")]
        return [TextContent(type="text", text=f"=== {path} ===\n{content}")]

    async def _delete_file(self, path: str, confirm: bool) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to delete: confirm=true required")]
        ok = await self.flipper.storage.delete(path)
        return [TextContent(type="text", text=f"{'✅ Deleted' if ok else '❌ Failed to delete'} {path}")]

    async def _rx(self, freq: int, duration: float, external: bool) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        device = 1 if external else 0
        cmd = f"subghz rx {freq} {device}"
        out = await self.flipper.cli.send_command(
            cmd, read_duration=duration, stop_running_app=True
        )
        return [TextContent(
            type="text",
            text=f"📡 Listened on {freq/1e6:.3f} MHz for {duration}s (device={device})\n---\n{out or '(no output)'}"
        )]

    async def _rx_raw(self, freq: int, duration: float) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        cmd = f"subghz rx_raw {freq}"
        out = await self.flipper.cli.send_command(
            cmd, read_duration=duration, stop_running_app=True
        )
        return [TextContent(
            type="text",
            text=f"📡 Raw capture on {freq/1e6:.3f} MHz for {duration}s\n---\n{out or '(no output)'}"
        )]

    async def _tx(
        self,
        key_hex: str,
        freq: int,
        te: int,
        repeat: int,
        external: bool,
        confirm: bool,
    ) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(
                type="text",
                text="Refusing to transmit: confirm=true required. "
                     "RF transmission may be regulated in your jurisdiction.",
            )]
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        key_hex = key_hex.strip().replace(" ", "").upper()
        if not all(c in "0123456789ABCDEF" for c in key_hex) or len(key_hex) != 6:
            return [TextContent(type="text", text="❌ key_hex must be exactly 6 hex chars (3 bytes)")]
        device = 1 if external else 0
        cmd = f"subghz tx {key_hex} {freq} {te} {repeat} {device}"
        out = await self.flipper.cli.send_command(cmd, timeout=15.0, stop_running_app=True)
        return [TextContent(
            type="text",
            text=f"📤 Transmitted key {key_hex} on {freq/1e6:.3f} MHz, te={te}µs, repeat={repeat}, device={device}\n---\n{out or '(done)'}"
        )]

    async def _tx_from_file(
        self, path: str, repeat: int, external: bool, confirm: bool
    ) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to transmit: confirm=true required")]
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        device = 1 if external else 0
        cmd = f"subghz tx_from_file {path} {repeat} {device}"
        out = await self.flipper.cli.send_command(cmd, timeout=20.0, stop_running_app=True)
        return [TextContent(
            type="text",
            text=f"📤 Replayed {path} (repeat={repeat}, device={device})\n---\n{out or '(done)'}"
        )]

    async def _decode_raw(self, path: str) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        cmd = f"subghz decode_raw {path}"
        out = await self.flipper.cli.send_command(cmd, timeout=10.0, stop_running_app=True)
        return [TextContent(type="text", text=f"🔍 Decoded {path}:\n---\n{out or '(no output)'}")]

    async def _chat(self, freq: int, external: bool, duration: float) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        device = 1 if external else 0
        cmd = f"subghz chat {freq} {device}"
        out = await self.flipper.cli.send_command(
            cmd, read_duration=duration, stop_running_app=True
        )
        return [TextContent(
            type="text",
            text=f"💬 Chat on {freq/1e6:.3f} MHz (device={device})\n---\n{out or '(no traffic)'}"
        )]

    async def _launch_app(self, path: str | None) -> Sequence[TextContent]:
        args = path or ""
        ok = await self.flipper.app.launch("Sub-GHz", args=args)
        suffix = f" with {path}" if path else ""
        return [TextContent(
            type="text",
            text=f"{'✅' if ok else '❌'} Launch Sub-GHz app{suffix}",
        )]

    async def _launch_frequency_analyzer(self) -> Sequence[TextContent]:
        # Momentum/Unleashed expose this as a separate app; fall back to main SubGHz app.
        for app_name in ("Frequency Analyzer", "Sub-GHz FreqAnalyzer", "SubGhz Freq Analyzer"):
            if await self.flipper.app.launch(app_name):
                return [TextContent(type="text", text=f"✅ Launched '{app_name}'")]
        return [TextContent(
            type="text",
            text="ℹ️ Couldn't find a dedicated Frequency Analyzer app. Launch Sub-GHz and navigate to it manually."
        )]

    def validate_environment(self) -> tuple[bool, str]:
        return True, ""

    def requires_sd_card(self) -> bool:
        return True
