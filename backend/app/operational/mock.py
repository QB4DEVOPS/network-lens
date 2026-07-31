"""Mock operational state engine."""

from __future__ import annotations

from app.models import Device


def compute_operational_state(device: Device) -> dict[str, object]:
    interfaces: list[dict[str, object]] = []
    for iface in device.interfaces:
        admin = "down" if iface.shutdown else "up"
        oper = "down" if iface.shutdown else "up"
        if not iface.ipv4_address and not iface.ipv4_dhcp and not iface.has_ipv6:
            oper = "down"
        interfaces.append(
            {
                "name": iface.name,
                "admin_status": admin,
                "oper_status": oper,
                "ipv4": iface.ipv4_address,
            }
        )

    routes = len(device.static_routes)
    return {
        "mode": "mock",
        "hostname": device.system.hostname or device.name,
        "interfaces": interfaces,
        "route_count": routes,
    }


def mock_ping(device: Device, destination: str) -> dict[str, object]:
    """Deterministic mock ping — fails when all interfaces are down."""
    any_up = any(not i.shutdown and (i.ipv4_address or i.ipv4_dhcp or i.has_ipv6) for i in device.interfaces)
    if not any_up:
        return {"success": False, "destination": destination, "message": "No usable interfaces — ping failed"}
    if destination.startswith("169.254."):
        return {"success": False, "destination": destination, "message": "Destination unreachable (mock)"}
    return {"success": True, "destination": destination, "rtt_ms": 12, "message": "Success rate is 100 percent (mock)"}
