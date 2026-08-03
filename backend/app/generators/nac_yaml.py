"""Live nac.yaml generator (iosxe-devices-configuration-full shape)."""

from __future__ import annotations

from collections.abc import Callable

from app.models import Device, DeviceConfiguration, Interface, NacYamlResult
from app.nac_sections import NAC_CONFIGURATION_SECTIONS, ROUTING_SUBSECTION_HINTS

SCHEMA_NAME = "iosxe-devices-configuration-full"
SCHEMA_VERSION = "4.0.0"
CANONICAL_ROOT = "iosxe.devices[]"
CONTRACT = "iosxe.devices[].configuration.*"
NETASCODE_DOCS = "https://netascode.cisco.com/docs/data_models/iosxe/overview/"
NAC_MODULE = "netascode/nac-iosxe/iosxe 0.1.0"

SCAFFOLD_HEADER = f"""# Network Lens — Live NaC preview
# Schema: {SCHEMA_NAME}
# Schema version: {SCHEMA_VERSION}
# Canonical root: {CANONICAL_ROOT}
# Contract: {CONTRACT}
# Model docs: {NETASCODE_DOCS}
# Module: {NAC_MODULE}
# Generated · Not applied
# Apply-safe: only resources you typed in CLI — no placeholder values

"""


class _YamlBuilder:
    def __init__(self, header: str) -> None:
        self.lines: list[str] = [line for line in header.rstrip().splitlines()]
        self.ranges: dict[str, tuple[int, int]] = {}

    def append(self, line: str) -> int:
        self.lines.append(line)
        return len(self.lines)

    def extend(self, block: list[str]) -> tuple[int, int]:
        start = len(self.lines) + 1
        self.lines.extend(block)
        return start, len(self.lines)

    def mark(self, key: str, start: int, end: int) -> None:
        self.ranges[key] = (start, end)

    def build(self) -> NacYamlResult:
        return NacYamlResult(content="\n".join(self.lines) + "\n", ranges=self.ranges)


def _yaml_str(value: str) -> str:
    return f'"{value}"'


def _yaml_null_hint(hint: str) -> str:
    return f"null  # ← {hint}"


def _section_hint(hint: str) -> str:
    return f"  # ← {hint}"


def _iface_key(name: str, suffix: str | None = None) -> str:
    if suffix:
        return f"interface:{name}:{suffix}"
    return f"interface:{name}"


def _format_ipv6_block(iface: Interface, indent: str) -> tuple[list[str], tuple[int, int] | None]:
    if not iface.has_ipv6:
        return [], None

    lines: list[str] = [f"{indent}ipv6:"]
    start = 1

    if iface.ipv6_enable or iface.ipv6_addresses or iface.ipv6_dhcp or iface.ipv6_autoconfig:
        lines.append(f"{indent}  enable: true")

    if iface.ipv6_dhcp:
        lines.append(f"{indent}  address_dhcp: true")

    if iface.ipv6_autoconfig:
        lines.append(f"{indent}  address_autoconfig_default: true")

    if iface.ipv6_addresses:
        lines.append(f"{indent}  addresses:")
        for addr in iface.ipv6_addresses:
            if addr.prefix_length is not None and "/" not in addr.prefix:
                prefix_value = f"{addr.prefix}/{addr.prefix_length}"
            else:
                prefix_value = addr.prefix
            lines.append(f"{indent}    - prefix: {_yaml_str(prefix_value)}")
            if addr.eui_64:
                lines.append(f"{indent}      eui_64: true")

    if iface.ipv6_link_local_addresses:
        lines.append(f"{indent}  link_local_addresses:")
        for ll_addr in iface.ipv6_link_local_addresses:
            lines.append(f"{indent}    - {_yaml_str(ll_addr)}")

    return lines, (start, len(lines))


def _format_loopback(iface: Interface) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = _iface_key(iface.name)
    lines.append(f"        - id: '{iface.loopback_id or '0'}'")
    block_start = 1

    ipv4_start = len(lines) + 1
    lines.append("          ipv4:")
    if iface.ipv4_dhcp:
        lines.append("            address: dhcp  # ⚠ semantic: unusual for loopback")
        lines.append("            address_mask: null")
    elif iface.ipv4_address:
        lines.append(f"            address: {_yaml_str(iface.ipv4_address)}")
        mask = iface.ipv4_address_mask or "255.255.255.255"
        lines.append(f"            address_mask: {_yaml_str(mask)}")
    else:
        lines.append(f"            address: {_yaml_null_hint('type: ip address ...')}")
        lines.append("            address_mask: null")
    rel[f"{base}:ipv4"] = (ipv4_start, len(lines))

    ipv6_lines, _ipv6_rel = _format_ipv6_block(iface, "          ")
    if ipv6_lines:
        ipv6_start = len(lines) + 1
        lines.extend(ipv6_lines)
        rel[f"{base}:ipv6"] = (ipv6_start, len(lines))

    if not iface.shutdown:
        sd_line = len(lines) + 1
        lines.append("          shutdown: false")
        rel[f"{base}:shutdown"] = (sd_line, sd_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _format_ethernet(iface: Interface) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = _iface_key(iface.name)
    block_start = 1

    etype = iface.ethernet_type or "GigabitEthernet"
    eid = iface.ethernet_id or "0/0/0"
    lines.append(f"        - type: {etype}")
    lines.append(f"          id: {eid}")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    ipv4_start = len(lines) + 1
    lines.append("          ipv4:")
    if iface.ipv4_dhcp:
        lines.append("            address: dhcp")
        lines.append("            address_mask: null")
    elif iface.ipv4_address:
        lines.append(f"            address: {_yaml_str(iface.ipv4_address)}")
        mask = iface.ipv4_address_mask or "255.255.255.255"
        lines.append(f"            address_mask: {_yaml_str(mask)}")
    else:
        lines.append(f"            address: {_yaml_null_hint('type: ip address ...')}")
        lines.append("            address_mask: null")
    rel[f"{base}:ipv4"] = (ipv4_start, len(lines))

    ipv6_lines, _ipv6_rel = _format_ipv6_block(iface, "          ")
    if ipv6_lines:
        ipv6_start = len(lines) + 1
        lines.extend(ipv6_lines)
        rel[f"{base}:ipv6"] = (ipv6_start, len(lines))

    if not iface.shutdown:
        sd_line = len(lines) + 1
        lines.append("          shutdown: false")
        rel[f"{base}:shutdown"] = (sd_line, sd_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _format_tunnel(iface: Interface) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = _iface_key(iface.name)
    block_start = 1

    lines.append(f"        - id: '{iface.tunnel_id or '0'}'")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    ipv4_start = len(lines) + 1
    lines.append("          ipv4:")
    if iface.ipv4_dhcp:
        lines.append("            address: dhcp")
        lines.append("            address_mask: null")
    elif iface.ipv4_address:
        lines.append(f"            address: {_yaml_str(iface.ipv4_address)}")
        mask = iface.ipv4_address_mask or "255.255.255.255"
        lines.append(f"            address_mask: {_yaml_str(mask)}")
    else:
        lines.append(f"            address: {_yaml_null_hint('type: ip address ...')}")
        lines.append("            address_mask: null")
    rel[f"{base}:ipv4"] = (ipv4_start, len(lines))

    ipv6_lines, _ipv6_rel = _format_ipv6_block(iface, "          ")
    if ipv6_lines:
        ipv6_start = len(lines) + 1
        lines.extend(ipv6_lines)
        rel[f"{base}:ipv6"] = (ipv6_start, len(lines))

    if not iface.shutdown:
        sd_line = len(lines) + 1
        lines.append("          shutdown: false")
        rel[f"{base}:shutdown"] = (sd_line, sd_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _format_vlan(iface: Interface) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = _iface_key(iface.name)
    block_start = 1

    lines.append(f"        - id: '{iface.vlan_id or '0'}'")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    ipv4_start = len(lines) + 1
    lines.append("          ipv4:")
    if iface.ipv4_dhcp:
        lines.append("            address: dhcp")
        lines.append("            address_mask: null")
    elif iface.ipv4_address:
        lines.append(f"            address: {_yaml_str(iface.ipv4_address)}")
        mask = iface.ipv4_address_mask or "255.255.255.255"
        lines.append(f"            address_mask: {_yaml_str(mask)}")
    else:
        lines.append(f"            address: {_yaml_null_hint('type: ip address ...')}")
        lines.append("            address_mask: null")
    rel[f"{base}:ipv4"] = (ipv4_start, len(lines))

    ipv6_lines, _ipv6_rel = _format_ipv6_block(iface, "          ")
    if ipv6_lines:
        ipv6_start = len(lines) + 1
        lines.extend(ipv6_lines)
        rel[f"{base}:ipv6"] = (ipv6_start, len(lines))

    if not iface.shutdown:
        sd_line = len(lines) + 1
        lines.append("          shutdown: false")
        rel[f"{base}:shutdown"] = (sd_line, sd_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _add_iface_block(
    builder: _YamlBuilder,
    iface: Interface,
    block_lines: list[str],
    rel_ranges: dict[str, tuple[int, int]],
) -> None:
    start, end = builder.extend(block_lines)
    for key, (rs, re) in rel_ranges.items():
        builder.mark(key, start + rs - 1, start + re - 1)


def _emit_system(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    builder.append("      system:")
    system = config.system
    if system.hostname:
        hn_line = builder.append(f"        hostname: {_yaml_str(system.hostname)}")
        builder.mark("system.hostname", hn_line, hn_line)
    else:
        builder.append(f"        hostname: {_yaml_null_hint('type: hostn R1')}")

    if system.ipv6_unicast_routing:
        routing_line = builder.append("        ipv6_unicast_routing: true")
        builder.mark("system.ipv6_unicast_routing", routing_line, routing_line)

    if system.mtu is not None:
        builder.append(f"        mtu: {system.mtu}")


def _emit_routing(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    routing = config.routing
    has_static = bool(routing.static_routes)
    has_other = bool(routing.ospf_processes or routing.bgp or routing.isis)

    if not has_static and not has_other:
        builder.append("      routing:")
        for subsection in ROUTING_SUBSECTION_HINTS:
            builder.append(f"        {subsection.key}:{_section_hint(subsection.hint)}")
        return

    builder.append("      routing:")
    if has_static:
        builder.append("        static_routes:")
        for route in routing.static_routes:
            plen = route.prefix if "/" in route.prefix else route.prefix
            if route.prefix_length and "/" not in route.prefix:
                plen = f"{route.prefix}/{route.prefix_length}"
            builder.append(f"        - prefix: {_yaml_str(plen)}")
            if route.next_hop:
                builder.append(f"          next_hop: {_yaml_str(route.next_hop)}")

    for subsection in ROUTING_SUBSECTION_HINTS:
        if subsection.key == "static_routes":
            continue
        if subsection.key == "ospf_processes" and routing.ospf_processes:
            continue
        if subsection.key == "bgp" and routing.bgp:
            continue
        if subsection.key == "isis" and routing.isis:
            continue
        if not config.section_is_empty("routing") and has_static and not has_other:
            builder.append(f"        {subsection.key}:{_section_hint(subsection.hint)}")


def _emit_interfaces(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    ifaces = config.interfaces
    loopbacks = ifaces.loopbacks
    ethernets = ifaces.ethernets
    tunnels = ifaces.tunnels
    vlans = ifaces.vlans
    has_extra = bool(
        ifaces.port_channels
        or ifaces.port_channel_subinterfaces
        or ifaces.ethernet_subinterfaces
        or ifaces.bdis
        or ifaces.nves
    )

    builder.append("      interfaces:")

    if not loopbacks and not ethernets and not tunnels and not vlans and not has_extra:
        builder.append("        # ← type: int lo0, int g0/0/0, int tun10, int vlan888")
        builder.append("        port_channels:  # ← type: int po1")
        builder.append("        port_channel_subinterfaces:  # ← type: int po1.100")
        builder.append("        ethernet_subinterfaces:  # ← type: int g0/0/0.100")
        builder.append("        bdis:  # ← type: int bdi100")
        builder.append("        nves:  # ← type: int nve1")
        return

    if loopbacks:
        builder.append("        loopbacks:")
        for iface in sorted(loopbacks, key=lambda i: int(i.loopback_id or "0")):
            block, rel = _format_loopback(iface)
            _add_iface_block(builder, iface, block, rel)

    if ethernets:
        builder.append("        ethernets:")
        for iface in ethernets:
            block, rel = _format_ethernet(iface)
            _add_iface_block(builder, iface, block, rel)

    if vlans:
        builder.append("        vlans:")
        for iface in sorted(vlans, key=lambda i: int(i.vlan_id or "0")):
            block, rel = _format_vlan(iface)
            _add_iface_block(builder, iface, block, rel)

    if tunnels:
        builder.append("        tunnels:")
        for iface in sorted(tunnels, key=lambda i: int(i.tunnel_id or "0")):
            block, rel = _format_tunnel(iface)
            _add_iface_block(builder, iface, block, rel)

    for key, hint in (
        ("port_channels", "type: int po1"),
        ("port_channel_subinterfaces", "type: int po1.100"),
        ("ethernet_subinterfaces", "type: int g0/0/0.100"),
        ("bdis", "type: int bdi100"),
        ("nves", "type: int nve1"),
    ):
        bucket = getattr(ifaces, key)
        if bucket:
            builder.append(f"        {key}:")
            for iface in bucket:
                block, rel = _format_ethernet(iface)
                _add_iface_block(builder, iface, block, rel)
        elif not has_extra:
            builder.append(f"        {key}:  {_section_hint(hint)}")


_SECTION_EMITTERS: dict[str, Callable[[_YamlBuilder, DeviceConfiguration], None]] = {
    "system": _emit_system,
    "routing": _emit_routing,
    "interfaces": _emit_interfaces,
}


def generate_nac_yaml(device: Device) -> NacYamlResult:
    """Generate apply-safe nac.yaml with YAML line ranges for highlighting."""
    builder = _YamlBuilder(SCAFFOLD_HEADER)
    config = device.configuration

    builder.append("iosxe:")
    builder.append("  devices:")
    builder.append(f"  - name: {device.name}")

    if device.host:
        builder.append(f"    host: {device.host}")

    builder.append("    configuration:")

    for section in NAC_CONFIGURATION_SECTIONS:
        emitter = _SECTION_EMITTERS.get(section.key)
        if emitter is not None:
            emitter(builder, config)
        elif config.section_is_empty(section.key):
            builder.append(f"      {section.key}:{_section_hint(section.hint)}")

    return builder.build()
