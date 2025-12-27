# ESP32 WiFi Dev Board: TCP ↔ UART Bridge (Scaffold)

Goal: make the WiFi devboard expose a **raw TCP socket** that forwards bytes to/from the Flipper over **UART**, so this repo’s `WiFiTransport` can speak Protobuf RPC over Wi‑Fi.

## What it should do

- Connect to your **home Wi‑Fi** (STA mode)
- Listen on **TCP port 8080**
- When a client connects:
  - forward bytes from TCP → UART (to Flipper)
  - forward bytes from UART → TCP (to client)

## Why this exists

The stock “Blackmagic” firmware typically exposes a web UI but does not provide the raw TCP bridge this repo expects.

## Notes / things you must verify

- **UART pins / wiring**: confirm which UART pins on the devboard connect to the Flipper header.
- **Baud rate**: pick the baud rate that the Flipper side expects.
- **Does the Flipper speak Protobuf RPC on that UART?**  
  This project’s WiFi model assumes you can carry the Protobuf RPC byte stream over the UART path. If your Flipper firmware does not expose Protobuf RPC on that UART, you’ll need either:
  - a Flipper-side app/service that exposes RPC over UART, or
  - a different bridging strategy.

## How to use with this repo

Once flashed and on your LAN:

```bash
export FLIPPER_TRANSPORT=wifi
export FLIPPER_WIFI_HOST=<DEVBOARD_IP>
export FLIPPER_WIFI_PORT=8080
python3 check_wifi_bridge.py
```

## Scaffold contents

This directory includes placeholder source that shows the structure of:

- Wi‑Fi STA connect
- TCP server accept loop
- UART init
- two forwarder tasks

You’ll need to fill in:

- SSID/password provisioning
- UART pin numbers / baud rate
- build system specifics (ESP-IDF / Arduino / PlatformIO)


