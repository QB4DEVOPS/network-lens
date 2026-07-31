"""Terraform HCL scaffold generator (CiscoDevNet/iosxe shape)."""

from __future__ import annotations

from app.models import Device, Interface

SCAFFOLD_HEADER = """# Network Lens — Terraform preview
# Generated · Not applied
# Provider: CiscoDevNet/iosxe (scaffold only)

"""


def _loopback_number(name: str) -> int:
    """Extract loopback index from name like Loopback0."""
    return int(name.replace("Loopback", "").replace("loopback", ""))


def _format_system_block(device: Device) -> str:
    hostname = device.system.hostname
    if hostname:
        return f'''resource "iosxe_system" "r1" {{
  hostname = "{hostname}"
}}
'''
    return '''resource "iosxe_system" "r1" {
  hostname = null # ← type: hostname R1
}
'''


def _format_loopback_block(iface: Interface) -> str:
    num = _loopback_number(iface.name)
    lo_id = f"lo{num}"

    shutdown_val = "true" if iface.shutdown else "false"

    if iface.ipv4_address and iface.ipv4_address.lower() != "dhcp":
        addr = iface.ipv4_address
        mask = iface.ipv4_address_mask or "255.255.255.255"
        return f'''resource "iosxe_interface_loopback" "{lo_id}" {{
  name              = {num}
  shutdown          = {shutdown_val}
  ipv4_address      = "{addr}"
  ipv4_address_mask = "{mask}"
}}
'''
    if iface.ipv4_address and iface.ipv4_address.lower() == "dhcp":
        return f'''resource "iosxe_interface_loopback" "{lo_id}" {{
  name              = {num}
  shutdown          = {shutdown_val}
  ipv4_address      = "dhcp" # ⚠ semantic: DHCP on loopback is unusual
  ipv4_address_mask = null
}}
'''

    # Partial scaffold — interface known, address not yet set
    return f'''resource "iosxe_interface_loopback" "{lo_id}" {{
  name              = {num}
  shutdown          = {shutdown_val}
  ipv4_address      = null # ← type: ip address ...
  ipv4_address_mask = null
}}
'''


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
