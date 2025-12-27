# Flipper Zero MCP Server

Modular Model Context Protocol (MCP) server for interacting with a Flipper Zero from MCP-capable clients (including Claude Desktop).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Features

- Modular architecture: functionality is provided by modules under `src/flipper_mcp/modules/`
- Multiple transports: USB and WiFi are implemented; Bluetooth is present as a stub transport
- Protobuf RPC support (nanopb-delimited framing) with generated protobuf code committed in `src/flipper_mcp/core/protobuf_gen/`
- Built-in modules:
  - `systeminfo`: connection/device/SD-card status
  - `badusb`: generate, validate, store, and execute BadUSB scripts (requires SD card for file operations)
  - `music`: save/play songs using Flipper Music Format (FMF) (requires SD card)

## Documentation

- `docs/index.md`: documentation hub
- `docs/claude_setup.md`: Claude Desktop setup (kept up to date)
- `docs/modules/`: built-in module documentation
- `docs/core/`: core server documentation

## Quick start

```bash
pip install -e .
flipper-mcp
```

The server communicates over stdio (MCP) and will auto-discover built-in modules at startup.

## Configuration

The CLI currently uses environment variables for configuration:

- `FLIPPER_TRANSPORT`: `usb` (default), `wifi`, `bluetooth`/`ble`
- `FLIPPER_PORT`: override the USB serial device path (only used for `usb`)
- `FLIPPER_WIFI_HOST`: Flipper WiFi dev board host/IP (only used for `wifi`)
- `FLIPPER_WIFI_PORT`: Flipper WiFi dev board TCP port (only used for `wifi`)
- `FLIPPER_DEBUG`: enable protobuf RPC debug logging (`1`, `true`, `yes`, `on`)
- `FLIPPER_FORCE_START_RPC_SESSION`: force sending `start_rpc_session` on connect (`1`, `true`, `yes`, `on`)
- `FLIPPER_MCP_ALLOW_STUB_MODE`: **DEV ONLY**. If enabled (`1`, `true`, `yes`, `on`), the server will run in stub mode when it cannot connect to hardware. Default: disabled.

Examples:

```bash
# Use a specific USB port
export FLIPPER_TRANSPORT=usb
export FLIPPER_PORT=/dev/ttyACM0
flipper-mcp

# Use WiFi transport
export FLIPPER_TRANSPORT=wifi
export FLIPPER_WIFI_HOST=192.168.1.1
export FLIPPER_WIFI_PORT=8080
flipper-mcp
```

### WiFi transport note (important)

The `wifi` transport in this repo expects a **raw TCP socket bridge** that carries Flipper **Protobuf RPC** bytes over the network.
If your WiFi devboard firmware only provides a **web UI** (often the stock “Blackmagic” firmware), you may be able to browse it at `blackmagic.local`,
but this repo will **not** be able to run Protobuf RPC over WiFi until you flash (or build) bridge firmware that exposes the TCP byte-stream (e.g. on port 8080).

See `docs/wifi_remote_control.md`.

## Using with Claude Desktop

See `docs/claude_setup.md`.

## Available tools (built-in)

### connection (health/recovery)

- `flipper_connection_health` (authoritative transport + protobuf-RPC health)
- `flipper_connection_reconnect` (disconnect/connect, then health)

### systeminfo

- `systeminfo_get`

### badusb

- `badusb_list`
- `badusb_read`
- `badusb_generate`
- `badusb_validate`
- `badusb_write`
- `badusb_delete`
- `badusb_diff`
- `badusb_rename`
- `badusb_execute` (requires `confirm=true`)
- `badusb_workflow`

### music

- `music_get_format`
- `music_play`

## Contributing

See `CONTRIBUTING.md` and `docs/module_development.md`.

## License

MIT License - see `LICENSE`.
