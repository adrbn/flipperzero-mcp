"""IR (Infrared) module for Flipper Zero MCP.

Wraps the firmware CLI:
    ir rx [raw]                              - capture IR signals
    ir tx <protocol> <address> <command>     - transmit a known-protocol signal
    ir tx RAW F:<freq> DC:<duty> <samples>   - transmit raw samples
    ir decode <input_file> [<output_file>]   - decode a .ir file
    ir universal <remote_name> <signal>      - send a universal remote signal
    ir universal list <remote_name>          - list signals in a universal remote

Protocols: NEC, NECext, NEC42, NEC42ext, Samsung32, RC6, RC5, RC5X,
           SIRC, SIRC15, SIRC20, Kaseikyo, RCA, Pioneer
Universal remotes: ac audio bluray_dvd digital_sign fans leds monitor projectors tv
"""

from __future__ import annotations

from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


DEFAULT_IR_DIR = "/ext/infrared"

IR_PROTOCOLS = [
    "NEC", "NECext", "NEC42", "NEC42ext", "Samsung32",
    "RC6", "RC5", "RC5X", "SIRC", "SIRC15", "SIRC20",
    "Kaseikyo", "RCA", "Pioneer",
]

UNIVERSAL_REMOTES = [
    "ac", "audio", "bluray_dvd", "digital_sign", "fans",
    "leds", "monitor", "projectors", "tv",
]


class IRModule(FlipperModule):
    @property
    def name(self) -> str:
        return "ir"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Infrared: capture, transmit, decode, universal remotes"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="ir_list_files",
                description=f"List .ir files (saved remotes). Defaults to {DEFAULT_IR_DIR}.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": DEFAULT_IR_DIR},
                        "recursive": {"type": "boolean", "default": False},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="ir_read_file",
                description="Read a saved .ir file (contains one or more named signals).",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="ir_delete_file",
                description="Delete a .ir file.",
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
                name="ir_rx",
                description=(
                    "Capture incoming IR signals. Point an IR remote at the Flipper's IR receiver. "
                    "Returns any signals received during the listen window."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "raw": {
                            "type": "boolean",
                            "description": "Capture raw timings instead of protocol-decoded.",
                            "default": False,
                        },
                        "read_duration": {"type": "number", "default": 5.0},
                    },
                    "required": [],
                },
            ),
            Tool(
                name="ir_tx",
                description=(
                    "Transmit a known-protocol IR signal. "
                    f"Protocols: {', '.join(IR_PROTOCOLS)}. "
                    "address and command are hex (e.g. address='0x04', command='0x08')."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "protocol": {
                            "type": "string",
                            "enum": IR_PROTOCOLS,
                        },
                        "address": {
                            "type": "string",
                            "description": "Hex address (e.g. '0x04' or '04')",
                        },
                        "command": {
                            "type": "string",
                            "description": "Hex command (e.g. '0x08' or '08')",
                        },
                    },
                    "required": ["protocol", "address", "command"],
                },
            ),
            Tool(
                name="ir_tx_raw",
                description=(
                    "Transmit a raw IR waveform. "
                    "frequency: 10000-1000000 Hz, duty_cycle: 0-100, samples: up to 512 integers."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "frequency": {"type": "integer", "default": 38000},
                        "duty_cycle": {"type": "integer", "default": 33},
                        "samples": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Alternating on/off microsecond durations",
                        },
                    },
                    "required": ["samples"],
                },
            ),
            Tool(
                name="ir_decode",
                description="Decode a raw .ir file to text (shows protocol/address/command).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "input_file": {"type": "string"},
                        "output_file": {
                            "type": "string",
                            "description": "Optional: write decoded result to this path",
                            "default": "",
                        },
                    },
                    "required": ["input_file"],
                },
            ),
            Tool(
                name="ir_universal_list",
                description=(
                    f"List signals available in a universal remote. "
                    f"Remotes: {', '.join(UNIVERSAL_REMOTES)}."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "remote": {
                            "type": "string",
                            "enum": UNIVERSAL_REMOTES,
                        },
                    },
                    "required": ["remote"],
                },
            ),
            Tool(
                name="ir_universal_send",
                description=(
                    "Send a signal via the built-in universal remote database. "
                    "Will try every known code for that function (e.g. every TV's 'power' code) "
                    "until a device responds."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "remote": {
                            "type": "string",
                            "enum": UNIVERSAL_REMOTES,
                        },
                        "signal": {
                            "type": "string",
                            "description": "Signal name (e.g. 'power', 'vol_up', 'ch_up'). Use ir_universal_list to discover.",
                        },
                    },
                    "required": ["remote", "signal"],
                },
            ),
            Tool(
                name="ir_launch_app",
                description="Launch the Infrared app UI on the Flipper.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="ir_launch_file",
                description="Launch the Infrared app with a specific .ir file (enables button send from UI).",
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
            if tool_name == "ir_list_files":
                return await self._list_files(
                    args.get("path", DEFAULT_IR_DIR),
                    bool(args.get("recursive", False)),
                )
            if tool_name == "ir_read_file":
                return await self._read_file(args["path"])
            if tool_name == "ir_delete_file":
                return await self._delete_file(args["path"], bool(args.get("confirm", False)))
            if tool_name == "ir_rx":
                return await self._rx(
                    bool(args.get("raw", False)),
                    float(args.get("read_duration", 5.0)),
                )
            if tool_name == "ir_tx":
                return await self._tx(
                    str(args["protocol"]),
                    str(args["address"]),
                    str(args["command"]),
                )
            if tool_name == "ir_tx_raw":
                return await self._tx_raw(
                    int(args.get("frequency", 38000)),
                    int(args.get("duty_cycle", 33)),
                    list(args["samples"]),
                )
            if tool_name == "ir_decode":
                return await self._decode(str(args["input_file"]), str(args.get("output_file", "")))
            if tool_name == "ir_universal_list":
                return await self._universal_list(str(args["remote"]))
            if tool_name == "ir_universal_send":
                return await self._universal_send(str(args["remote"]), str(args["signal"]))
            if tool_name == "ir_launch_app":
                return await self._launch_app(None)
            if tool_name == "ir_launch_file":
                return await self._launch_app(str(args["path"]))
        except KeyError as e:
            return [TextContent(type="text", text=f"Missing argument: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        return [TextContent(type="text", text=f"Unknown IR tool '{tool_name}'")]

    # --- helpers ---

    def _require_cli(self) -> tuple[bool, str]:
        if not getattr(self.flipper, "cli", None):
            return False, "❌ CLI bridge not available"
        return True, ""

    @staticmethod
    def _normalize_hex(v: str) -> str:
        v = v.strip().lower()
        if v.startswith("0x"):
            v = v[2:]
        return v

    async def _list_files(self, path: str, recursive: bool) -> Sequence[TextContent]:
        files = await self.flipper.storage.list(path) or []
        lines = [f"{path}:"] + [f"  {f}" for f in files]
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

    async def _delete_file(self, path: str, confirm: bool) -> Sequence[TextContent]:
        if not confirm:
            return [TextContent(type="text", text="Refusing to delete: confirm=true required")]
        ok = await self.flipper.storage.delete(path)
        return [TextContent(type="text", text=f"{'✅' if ok else '❌'} Delete {path}")]

    async def _rx(self, raw: bool, duration: float) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        cmd = "ir rx raw" if raw else "ir rx"
        out = await self.flipper.cli.send_command(
            cmd, read_duration=duration, stop_running_app=True,
        )
        return [TextContent(
            type="text",
            text=f"🔴 IR listen {'(raw)' if raw else ''} for {duration}s\n---\n{out or '(no signals received)'}"
        )]

    async def _tx(self, protocol: str, address: str, command: str) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        addr = self._normalize_hex(address)
        cmd = self._normalize_hex(command)
        cli_cmd = f"ir tx {protocol} 0x{addr} 0x{cmd}"
        out = await self.flipper.cli.send_command(cli_cmd, timeout=5.0, stop_running_app=True)
        return [TextContent(
            type="text",
            text=f"📤 IR {protocol} addr=0x{addr} cmd=0x{cmd}\n---\n{out or '(sent)'}"
        )]

    async def _tx_raw(
        self, frequency: int, duty_cycle: int, samples: list[int]
    ) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        if len(samples) > 512:
            return [TextContent(type="text", text="❌ max 512 samples")]
        sample_str = " ".join(str(int(s)) for s in samples)
        cli_cmd = f"ir tx RAW F:{frequency} DC:{duty_cycle} {sample_str}"
        out = await self.flipper.cli.send_command(cli_cmd, timeout=5.0, stop_running_app=True)
        return [TextContent(
            type="text",
            text=f"📤 IR RAW F:{frequency}Hz DC:{duty_cycle}% ({len(samples)} samples)\n---\n{out or '(sent)'}"
        )]

    async def _decode(self, input_file: str, output_file: str) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        cli_cmd = f"ir decode {input_file}"
        if output_file:
            cli_cmd += f" {output_file}"
        out = await self.flipper.cli.send_command(cli_cmd, timeout=10.0, stop_running_app=True)
        return [TextContent(type="text", text=f"🔬 Decode {input_file}\n---\n{out or '(no output)'}")]

    async def _universal_list(self, remote: str) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"ir universal list {remote}", timeout=8.0, stop_running_app=True,
        )
        return [TextContent(type="text", text=f"🎛 Universal '{remote}' signals\n---\n{out or '(no output)'}")]

    async def _universal_send(self, remote: str, signal: str) -> Sequence[TextContent]:
        ok, err = self._require_cli()
        if not ok:
            return [TextContent(type="text", text=err)]
        out = await self.flipper.cli.send_command(
            f"ir universal {remote} {signal}", read_duration=8.0, stop_running_app=True,
        )
        return [TextContent(
            type="text",
            text=f"📡 Universal {remote}/{signal}\n---\n{out or '(sent; cycles through all known codes)'}"
        )]

    async def _launch_app(self, path: str | None) -> Sequence[TextContent]:
        args = path or ""
        ok = await self.flipper.app.launch("Infrared", args=args)
        suffix = f" with {path}" if path else ""
        return [TextContent(type="text", text=f"{'✅' if ok else '❌'} Launch Infrared{suffix}")]

    def validate_environment(self) -> tuple[bool, str]:
        return True, ""

    def requires_sd_card(self) -> bool:
        return True
