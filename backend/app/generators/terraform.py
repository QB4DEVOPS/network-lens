"""Terraform HCL scaffold generator (CiscoDevNet/iosxe shape)."""

from __future__ import annotations

from app.models import Device, Interface, Ipv6Address

SCAFFOLD_HEADER = """# Network Lens — Terraform preview
# Generated · Not applied
# Provider: CiscoDevNet/iosxe (scaffold only)
# NaC path → TF resource:
#   iosxe.devices[].configuration.system.*     → iosxe_system
#   iosxe.devices[].configuration.interfaces.loopbacks[] → iosxe_interface_loopback

"""


def _ipv6_prefix(addr: Ipv6Address) -> str:
    if addr.prefix_length is not None and "/" not in addr.prefix:
        return f"{addr.prefix}/{addr.prefix_length}"
    return addr.prefix


def _loopback_number(name: str) -> int:
    """Extract loopback index from name like Loopback0."""
    return int(name.replace("Loopback", "").replace("loopback", ""))


def _format_system_block(device: Device) -> str:
    hostname = device.system.hostname
    lines = ['resource "iosxe_system" "r1" {']
    if hostname:
        lines.append(f'  hostname = "{hostname}"')
    else:
        lines.append("  hostname = null # ← type: hostn R1")
    if device.system.ipv6_unicast_routing:
        lines.append("  ipv6_unicast_routing = true")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_loopback_block(iface: Interface) -> str:
    num = _loopback_number(iface.name)
    lo_id = f"lo{num}"

    shutdown_val = "true" if iface.shutdown else "false"
    body_lines = [
        f'resource "iosxe_interface_loopback" "{lo_id}" {{',
        f"  name              = {num}",
        f"  shutdown          = {shutdown_val}",
    ]

    if iface.ipv4_address and iface.ipv4_address.lower() != "dhcp":
        body_lines.append(f'  ipv4_address      = "{iface.ipv4_address}"')
        body_lines.append(f'  ipv4_address_mask = "{iface.ipv4_address_mask or "255.255.255.255"}"')
    elif iface.ipv4_address and iface.ipv4_address.lower() == "dhcp":
        body_lines.append('  ipv4_address      = "dhcp" # ⚠ semantic: DHCP on loopback is unusual')
        body_lines.append("  ipv4_address_mask = null")
    else:
        body_lines.append("  ipv4_address      = null # ← type: ip address ...")
        body_lines.append("  ipv4_address_mask = null")

    if iface.has_ipv6:
        body_lines.append("  ipv6_enable       = true")
        if iface.ipv6_addresses:
            prefixes = ", ".join(f'"{_ipv6_prefix(a)}"' for a in iface.ipv6_addresses)
            body_lines.append(f"  ipv6_addresses    = [{prefixes}]")

    body_lines.append("}")
    return "\n".join(body_lines) + "\n"


def generate_terraform(device: Device) -> str:
    """Generate Terraform HCL scaffold. Never returns blank — always shows structure."""
    parts = [SCAFFOLD_HEADER, _format_system_block(device)]

    loopbacks = [i for i in device.interfaces if i.kind == "loopback"]
    if loopbacks:
        for iface in sorted(loopbacks, key=lambda i: _loopback_number(i.name)):
            parts.append(_format_loopback_block(iface))
    else:
        parts.append(
            '''resource "iosxe_interface_loopback" "lo0" {
  name              = 0
  shutdown          = true
  ipv4_address      = null # ← type: interface lo0, no shutdown, ip address ...
  ipv4_address_mask = null
}
'''
        )

    return "\n".join(parts).rstrip() + "\n"
