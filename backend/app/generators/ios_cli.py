"""Regenerate IOS CLI from canonical device model."""

from __future__ import annotations

from app.models import Device, Interface


def _iface_lines(iface: Interface) -> list[str]:
    lines = [f"interface {iface.name}"]
    if iface.description:
        lines.append(f" description {iface.description}")
    if not iface.shutdown:
        lines.append(" no shutdown")
    if iface.ipv4_dhcp:
        lines.append(" ip address dhcp")
    elif iface.ipv4_address:
        mask = iface.ipv4_address_mask or "255.255.255.255"
        lines.append(f" ip address {iface.ipv4_address} {mask}")
    if iface.ipv6_enable or iface.has_ipv6:
        lines.append(" ipv6 enable")
    for addr in iface.ipv6_addresses:
        plen = f"/{addr.prefix_length}" if addr.prefix_length and "/" not in addr.prefix else ""
        suffix = " eui-64" if addr.eui_64 else ""
        lines.append(f" ipv6 address {addr.prefix}{plen}{suffix}")
    for ll in iface.ipv6_link_local_addresses:
        lines.append(f" ipv6 address {ll} link-local")
    return lines


def generate_ios_cli(device: Device) -> str:
    lines: list[str] = []
    if device.system.hostname:
        lines.append(f"hostname {device.system.hostname}")
    if device.system.ipv6_unicast_routing:
        lines.append("ipv6 unicast-routing")
    for route in device.static_routes:
        plen = f"/{route.prefix_length}" if route.prefix_length else ""
        if route.next_hop:
            lines.append(f"ip route {route.prefix}{plen} {route.next_hop}")
        elif route.interface:
            lines.append(f"ip route {route.prefix}{plen} {route.interface}")
    for iface in device.interfaces:
        lines.extend(_iface_lines(iface))
    return "\n".join(lines) + ("\n" if lines else "")
