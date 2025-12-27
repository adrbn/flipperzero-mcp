# WiFi Remote Control (MCP over Wi‑Fi)

This repository supports a `wifi` transport (`WiFiTransport`) that connects to a host/port via TCP and then speaks **Flipper Protobuf RPC framing** over that socket.

## Important: stock "Blackmagic" firmware is not enough

The stock Flipper WiFi Dev Board firmware commonly called **Blackmagic** exposes a **web UI** (HTTP) and various internal tasks (e.g. `httpd`, `mdns`, etc.). In typical default configurations it does **not** expose a **raw TCP byte-stream bridge** suitable for Protobuf RPC.

If you can reach `blackmagic.local` in your browser but this repo’s WiFi probe cannot get an RPC ping, that usually means:

- HTTP works (port 80)
- but the **TCP bridge port** (e.g. 8080) is not open, or it speaks a different protocol than this repo expects.

## What this repo needs

To use `FLIPPER_TRANSPORT=wifi`, you need a network endpoint that behaves like:

- **TCP server** on `<host>:<port>`
- forwards bytes **bidirectionally** to/from the Flipper’s RPC channel
- does not transform framing (it should be a clean byte stream)

This repo defaults to `FLIPPER_WIFI_PORT=8080`.

## Quick verification

If you know the devboard IP on your LAN:

```bash
export FLIPPER_WIFI_HOST=<DEVBOARD_IP>
export FLIPPER_WIFI_PORT=8080
python3 check_wifi_bridge.py
```

- If it prints `rpc_responsive=True`, WiFi remote control is working.
- If it prints `transport_connected=True` but `rpc_responsive=False`, a TCP server is reachable but it’s **not** the Protobuf RPC bridge.
- If it can only connect to port 80, you likely only have the web UI and need bridge firmware.

## Bridge firmware option (recommended)

If you’re willing to flash the devboard, the simplest approach is a tiny ESP32 firmware that provides:

- a TCP listener on `0.0.0.0:8080`
- a UART connection to the Flipper devboard pins
- a bidirectional forwarder between TCP and UART

This repo includes a scaffold under `firmware/tcp_uart_bridge/` you can use as a starting point.


