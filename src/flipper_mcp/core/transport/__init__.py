"""Transport layer initialization and factory.

Important:
- `USBTransport` depends on `pyserial` (import name: `serial`).
- Some users (and scripts) only want WiFi transport and should not be forced to
  have `pyserial` installed.

So we keep this module importable with *lazy imports*.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Type

from .base import FlipperTransport

__all__ = ["FlipperTransport", "USBTransport", "WiFiTransport", "BluetoothTransport", "get_transport"]


def __getattr__(name: str) -> Any:
    # Lazy-export transport classes.
    if name == "USBTransport":
        return import_module(".usb", __name__).USBTransport
    if name == "WiFiTransport":
        return import_module(".wifi", __name__).WiFiTransport
    if name == "BluetoothTransport":
        return import_module(".bluetooth", __name__).BluetoothTransport
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _transport_registry() -> Dict[str, Type[FlipperTransport]]:
    # Construct lazily so importing this module doesn't import pyserial.
    USBTransport = __getattr__("USBTransport")
    WiFiTransport = __getattr__("WiFiTransport")
    BluetoothTransport = __getattr__("BluetoothTransport")
    return {
        "usb": USBTransport,
        "wifi": WiFiTransport,
        "bluetooth": BluetoothTransport,
        "ble": BluetoothTransport,  # Alias
    }


def get_transport(transport_type: str, config: dict) -> FlipperTransport:
    """
    Factory function to create transport instances.
    
    Args:
        transport_type: Type of transport ("usb", "wifi", "bluetooth")
        config: Full configuration dict
        
    Returns:
        Transport instance
        
    Raises:
        ValueError: If transport type is unknown
    """
    transport_type = transport_type.lower()
    
    TRANSPORTS = _transport_registry()
    if transport_type not in TRANSPORTS:
        raise ValueError(
            f"Unknown transport type: {transport_type}. "
            f"Available: {', '.join(TRANSPORTS.keys())}"
        )
    
    # Get transport-specific config
    transport_config = config.get("transport", {}).get(transport_type, {})
    
    # Create and return transport
    transport_class = TRANSPORTS[transport_type]
    return transport_class(transport_config)
