"""RESTCONF JSON generator (OpenConfig interfaces subset)."""

from __future__ import annotations

import json

from app.models import Device, Interface


def _iface_json(iface: Interface) -> dict[str, object]:
    name = iface.name.replace("GigabitEthernet", "GigabitEthernet=")
    if not name.startswith("GigabitEthernet=") and iface.kind == "ethernet":
        name = f"GigabitEthernet={iface.ethernet_id or iface.name}"

    entry: dict[str, object] = {
        "name": iface.name,
        "config": {
            "name": iface.name,
            "enabled": not iface.shutdown,
        },
    }
    if iface.description:
        entry["config"]["description"] = iface.description  # type: ignore[index]

    addresses: list[dict[str, str]] = []
    if iface.ipv4_address and not iface.ipv4_dhcp:
        addresses.append({"ip": iface.ipv4_address, "prefix-length": "32"})
    elif iface.ipv4_dhcp:
        addresses.append({"origin": "dhcp"})

    if addresses:
        entry["subinterfaces"] = {
            "subinterface": [
                {
                    "index": 0,
                    "config": {"index": 0},
                    "openconfig-if-ip:ipv4": {"addresses": {"address": addresses}},
                }
            ]
        }

    if iface.has_ipv6:
        v6_addrs = [{"ip": a.prefix, "config": {"ip": a.prefix}} for a in iface.ipv6_addresses]
        if v6_addrs:
            if "subinterfaces" not in entry:
                entry["subinterfaces"] = {"subinterface": [{"index": 0, "config": {"index": 0}}]}
            sub = entry["subinterfaces"]["subinterface"][0]  # type: ignore[index]
            sub["openconfig-if-ip:ipv6"] = {"config": {"enabled": True}, "addresses": {"address": v6_addrs}}

    return entry


def generate_restconf_json(device: Device) -> str:
    hostname = device.system.hostname or device.name
    payload = {
        "ietf-interfaces:interfaces": {
            "interface": [_iface_json(i) for i in device.interfaces]
        },
        "Cisco-IOS-XE-native:native": {
            "hostname": hostname,
            "ipv6": {"unicast-routing": device.system.ipv6_unicast_routing},
        },
    }
    return json.dumps(payload, indent=2) + "\n"
