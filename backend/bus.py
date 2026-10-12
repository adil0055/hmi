"""Opening a CAN bus by name.

``INTERFACE[:CHANNEL][@BITRATE]``, anything python-can opens:
``udp_multicast`` (python-can's virtual bus over the network, no hardware;
alone it means the IPv4 group, which crosses an ordinary network where the
IPv6 default may not), ``socketcan:vcan0``, ``pcan:PCAN_USBBUS1@500000``,
``kvaser:0@500000``, ``virtual:name`` (in one process only).
"""

from __future__ import annotations

UDP_GROUP = "239.74.163.2"


def parse_bus(spec: str) -> dict:
    """``INTERFACE[:CHANNEL][@BITRATE]`` as keyword arguments for ``can.Bus``."""
    spec = (spec or "").strip()
    bitrate = None
    if "@" in spec:
        spec, rate = spec.rsplit("@", 1)
        bitrate = int(rate)
    interface, _, channel = spec.partition(":")
    interface = interface.strip() or "udp_multicast"
    if not channel and interface == "udp_multicast":
        channel = UDP_GROUP
    kwargs: dict = {"interface": interface}
    if channel:
        kwargs["channel"] = channel
    if bitrate:
        kwargs["bitrate"] = bitrate
    return kwargs


def open_bus(spec: str):
    import can

    return can.Bus(**parse_bus(spec))
