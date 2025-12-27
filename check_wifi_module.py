#!/usr/bin/env python3
"""Check for WiFi module on Flipper Zero device."""

import asyncio
import sys
import os
from pathlib import Path

# Try to import directly - if package is installed, this will work
try:
    from flipper_mcp.core.transport.usb import USBTransport
    from flipper_mcp.core.flipper_client import FlipperClient
except ImportError:
    # Fallback: add src to path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    from flipper_mcp.core.transport.usb import USBTransport
    from flipper_mcp.core.flipper_client import FlipperClient


async def check_wifi_module():
    """Check for WiFi module on Flipper Zero."""
    
    print("=" * 60)
    print("Checking for WiFi Module on Flipper Zero")
    print("=" * 60)
    print()
    
    # Configuration
    port_override = os.environ.get("FLIPPER_PORT")
    config = {
        "transport": {
            "type": "usb",
            "usb": {
                **({"port": port_override} if port_override else {}),
                "baudrate": 115200,
                "timeout": 2.0
            }
        }
    }
    
    # Step 1: Create transport and connect
    print("Step 1: Connecting to Flipper Zero...")
    try:
        usb_config = config.get("transport", {}).get("usb", {})
        transport = USBTransport(usb_config)
        client = FlipperClient(transport)
        
        connected = await client.connect()
        if not connected:
            print("   ❌ Failed to connect to Flipper Zero")
            return False
        
        print("   ✓ Connected to Flipper Zero")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    # Step 2: Check connection health
    print("\nStep 2: Checking connection health...")
    try:
        health = await client.get_connection_health(probe_rpc=True)
        print(f"   Transport: {health.get('transport', {}).get('type', 'Unknown')}")
        print(f"   Transport Connected: {health.get('transport_connected', False)}")
        print(f"   RPC Responsive: {health.get('rpc_responsive', False)}")
        print(f"   Overall Connected: {health.get('connected', False)}")
    except Exception as e:
        print(f"   ⚠️  Error checking health: {e}")
    
    # Step 3: Get device info
    print("\nStep 3: Reading device information...")
    try:
        device_info = await client.get_device_info()
        print(f"   Device: {device_info.get('name', 'Unknown')}")
        print(f"   Firmware: {device_info.get('firmware', 'Unknown')}")
    except Exception as e:
        print(f"   ⚠️  Could not read device info: {e}")
    
    # Step 4: Check for WiFi-related files/directories
    print("\nStep 4: Searching for WiFi module...")
    
    # Common paths where WiFi apps might be stored
    search_paths = [
        "/ext/apps",
        "/ext/apps/Tools",
        "/ext/apps/wifi",
        "/ext/apps/wifi_marauder",
        "/ext/apps/wifi_deauther",
        "/ext/apps/wifi_scanner",
        "/ext/apps_data",
        "/ext",
        "/ext/wifi",
    ]
    
    wifi_found = False
    
    for path in search_paths:
        try:
            print(f"   Checking: {path}")
            entries = await client.storage.list(path)
            if entries:
                print(f"   ✓ Found {len(entries)} items in {path}:")
                for entry in entries[:20]:  # Show first 20
                    print(f"     - {entry}")
                    # Check if entry name contains "wifi" (case-insensitive)
                    if "wifi" in entry.lower():
                        wifi_found = True
                        print(f"       ⭐ WiFi-related item found!")
                if len(entries) > 20:
                    print(f"     ... and {len(entries) - 20} more")
            else:
                print(f"   (empty or not found)")
        except Exception as e:
            print(f"   ⚠️  Error accessing {path}: {e}")
    
    # Step 5: Check Tools directory in detail (WiFi apps often go here)
    print("\nStep 5: Checking Tools directory...")
    try:
        tools_list = await client.storage.list("/ext/apps/Tools")
        if tools_list:
            print(f"   ✓ Found {len(tools_list)} items in Tools:")
            for item in tools_list:
                print(f"     - {item}")
                if "wifi" in item.lower() or "marauder" in item.lower() or "esp32" in item.lower():
                    wifi_found = True
                    print(f"       ⭐ WiFi-related item found!")
        else:
            print("   (Tools directory is empty or doesn't exist)")
    except Exception as e:
        print(f"   ⚠️  Error checking Tools directory: {e}")
    
    # Step 5b: Check apps_manifests for app metadata
    print("\nStep 5b: Checking apps_manifests for app metadata...")
    try:
        manifests = await client.storage.list("/ext/apps_manifests")
        if manifests:
            print(f"   ✓ Found {len(manifests)} manifest files:")
            for manifest in manifests:
                print(f"     - {manifest}")
                if "wifi" in manifest.lower() or "marauder" in manifest.lower():
                    wifi_found = True
                    print(f"       ⭐ WiFi-related manifest found!")
    except Exception as e:
        print(f"   ⚠️  Error checking apps_manifests: {e}")
    
    # Step 6: Check apps_data for WiFi-related data
    print("\nStep 6: Checking apps_data directory...")
    try:
        apps_data = await client.storage.list("/ext/apps_data")
        if apps_data:
            print(f"   ✓ Found {len(apps_data)} items in apps_data:")
            for item in apps_data:
                print(f"     - {item}")
                if "wifi" in item.lower() or "marauder" in item.lower() or "esp32" in item.lower():
                    wifi_found = True
                    print(f"       ⭐ WiFi-related item found!")
    except Exception as e:
        print(f"   ⚠️  Error checking apps_data: {e}")
    
    # Step 7: Summary
    print("\n" + "=" * 60)
    if wifi_found:
        print("✓ WiFi module/app appears to be installed!")
    else:
        print("⚠️  No WiFi module/app found in common locations")
        print("   (It might be installed in a different location)")
    print("=" * 60)
    
    # Cleanup
    try:
        await client.disconnect()
    except Exception:
        pass
    
    return wifi_found


if __name__ == "__main__":
    try:
        found = asyncio.run(check_wifi_module())
        sys.exit(0 if found else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

