"""Live nac.yaml generator (iosxe-devices-configuration-full shape)."""

from __future__ import annotations

from collections.abc import Callable

from app import field_keys as fk
from app.models import (
    CryptoIkev2KeyringPeer,
    CryptoIkev2Profile,
    Device,
    DeviceConfiguration,
    Interface,
    NacYamlResult,
)
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
    def __init__(self, header: str, *, show_hints: bool = False) -> None:
        self.show_hints = show_hints
        self.lines: list[str] = [line for line in header.rstrip().splitlines()]
        self.ranges: dict[str, tuple[int, int]] = {}

    def hint_line(self, line: str) -> None:
        if self.show_hints:
            self.append(line)

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


def _format_id_interface(
    iface: Interface,
    id_value: str,
    indent_entry: str = "        ",
    *,
    show_hints: bool = False,
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = fk.interface_key(iface.name)
    block_start = 1

    lines.append(f"{indent_entry}- id: '{id_value}'")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"{indent_entry}  description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    if iface.ipv4_dhcp or iface.ipv4_address or show_hints:
        ipv4_start = len(lines) + 1
        lines.append(f"{indent_entry}  ipv4:")
        if iface.ipv4_dhcp:
            lines.append(f"{indent_entry}    address: dhcp")
            lines.append(f"{indent_entry}    address_mask: null")
        elif iface.ipv4_address:
            lines.append(f"{indent_entry}    address: {_yaml_str(iface.ipv4_address)}")
            mask = iface.ipv4_address_mask or "255.255.255.255"
            lines.append(f"{indent_entry}    address_mask: {_yaml_str(mask)}")
        else:
            lines.append(f"{indent_entry}    address: {_yaml_null_hint('type: ip address ...')}")
            lines.append(f"{indent_entry}    address_mask: null")
        rel[f"{base}:ipv4"] = (ipv4_start, len(lines))

    ipv6_lines, _ = _format_ipv6_block(iface, f"{indent_entry}  ")
    if ipv6_lines:
        ipv6_start = len(lines) + 1
        lines.extend(ipv6_lines)
        rel[f"{base}:ipv6"] = (ipv6_start, len(lines))

    if not iface.shutdown:
        sd_line = len(lines) + 1
        lines.append(f"{indent_entry}  shutdown: false")
        rel[f"{base}:shutdown"] = (sd_line, sd_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _format_port_channel(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    return _format_id_interface(iface, iface.port_channel_id or "0", show_hints=show_hints)


def _format_port_channel_subinterface(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    pc_id = iface.port_channel_id or "0"
    sub_id = iface.subinterface_id or "0"
    return _format_id_interface(iface, f"{pc_id}.{sub_id}", show_hints=show_hints)


def _format_ethernet_subinterface(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = fk.interface_key(iface.name)
    block_start = 1

    etype = iface.ethernet_type or "GigabitEthernet"
    eid = iface.ethernet_id or "0/0/0"
    sub_id = iface.subinterface_id or "0"
    lines.append(f"        - type: {etype}")
    lines.append(f"          id: {eid}.{sub_id}")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    if iface.ipv4_dhcp or iface.ipv4_address or show_hints:
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

    ipv6_lines, _ = _format_ipv6_block(iface, "          ")
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


def _format_bdi(iface: Interface, *, show_hints: bool = False) -> tuple[list[str], dict[str, tuple[int, int]]]:
    return _format_id_interface(iface, iface.bdi_id or "0", show_hints=show_hints)


def _format_nve(iface: Interface, *, show_hints: bool = False) -> tuple[list[str], dict[str, tuple[int, int]]]:
    return _format_id_interface(iface, iface.nve_id or "0", show_hints=show_hints)


def _format_loopback(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = fk.interface_key(iface.name)
    lines.append(f"        - id: '{iface.loopback_id or '0'}'")
    block_start = 1

    if iface.ipv4_dhcp or iface.ipv4_address or show_hints:
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


def _format_ethernet(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = fk.interface_key(iface.name)
    block_start = 1

    etype = iface.ethernet_type or "GigabitEthernet"
    eid = iface.ethernet_id or "0/0/0"
    lines.append(f"        - type: {etype}")
    lines.append(f"          id: {eid}")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    if iface.vrf_forwarding:
        vrf_line = len(lines) + 1
        lines.append(f"          vrf: {_yaml_str(iface.vrf_forwarding)}")
        rel[f"{base}:vrf"] = (vrf_line, vrf_line)

    if iface.nat_inside:
        nat_line = len(lines) + 1
        lines.append("          nat_inside: true")
        rel[f"{base}:nat_inside"] = (nat_line, nat_line)
    if iface.nat_outside:
        nat_line = len(lines) + 1
        lines.append("          nat_outside: true")
        rel[f"{base}:nat_outside"] = (nat_line, nat_line)

    if iface.ipv4_dhcp or iface.ipv4_address or show_hints:
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

    if iface.port_channel_id:
        cg_line = len(lines) + 1
        lines.append(f"          port_channel_id: '{iface.port_channel_id}'")
        rel[f"{base}:channel_group"] = (cg_line, cg_line)
        if iface.port_channel_mode:
            mode_line = len(lines) + 1
            lines.append(f"          port_channel_mode: {_yaml_str(iface.port_channel_mode)}")
            rel[f"{base}:channel_group"] = (cg_line, mode_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _format_tunnel(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = fk.interface_key(iface.name)
    block_start = 1

    lines.append(f"        - id: '{iface.tunnel_id or '0'}'")
    if iface.tunnel_id and str(iface.tunnel_id).isdigit():
        # Schema key is `name` (integer). `id` is the existing preview key.
        lines.append(f"          name: {int(iface.tunnel_id)}")

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    if iface.ipv4_dhcp or iface.ipv4_address or show_hints:
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

    if iface.tunnel_source:
        src_line = len(lines) + 1
        lines.append(f"          tunnel_source: {_yaml_str(iface.tunnel_source)}")
        rel[f"{base}:tunnel_source"] = (src_line, src_line)
    if iface.tunnel_destination_ipv4:
        dest_line = len(lines) + 1
        lines.append(f"          tunnel_destination_ipv4: {_yaml_str(iface.tunnel_destination_ipv4)}")
        rel[f"{base}:tunnel_destination_ipv4"] = (dest_line, dest_line)
    if iface.tunnel_mode_gre_multipoint is not None:
        mode_line = len(lines) + 1
        mode_val = "true" if iface.tunnel_mode_gre_multipoint else "false"
        lines.append(f"          tunnel_mode_gre_multipoint: {mode_val}")
        rel[f"{base}:tunnel_mode_gre_multipoint"] = (mode_line, mode_line)
    if iface.tunnel_mode_ipsec_ipv4 is not None:
        ipsec_mode_line = len(lines) + 1
        ipsec_mode_val = "true" if iface.tunnel_mode_ipsec_ipv4 else "false"
        lines.append(f"          tunnel_mode_ipsec_ipv4: {ipsec_mode_val}")
        rel[f"{base}:tunnel_mode_ipsec_ipv4"] = (ipsec_mode_line, ipsec_mode_line)
    if iface.tunnel_key is not None:
        key_line = len(lines) + 1
        lines.append(f"          tunnel_key: {iface.tunnel_key}")
        rel[f"{base}:tunnel_key"] = (key_line, key_line)
    if iface.tunnel_protection_ipsec_profile:
        prot_line = len(lines) + 1
        lines.append(
            f"          tunnel_protection_ipsec_profile: {_yaml_str(iface.tunnel_protection_ipsec_profile)}"
        )
        rel[f"{base}:tunnel_protection_ipsec_profile"] = (prot_line, prot_line)
    if iface.ip_nhrp_authentication is not None:
        auth_line = len(lines) + 1
        lines.append(f"          ip_nhrp_authentication: {_yaml_str(iface.ip_nhrp_authentication)}")
        rel[f"{base}:ip_nhrp_authentication"] = (auth_line, auth_line)
    if iface.ip_nhrp_network_id is not None:
        nid_line = len(lines) + 1
        lines.append(f"          ip_nhrp_network_id: {iface.ip_nhrp_network_id}")
        rel[f"{base}:ip_nhrp_network_id"] = (nid_line, nid_line)
    if iface.ip_nhrp_nhs:
        nhs_start = len(lines) + 1
        lines.append("          ip_nhrp_nhs:")
        for nhs in iface.ip_nhrp_nhs:
            lines.append(f"          - ipv4: {_yaml_str(nhs.ipv4)}")
        rel[f"{base}:ip_nhrp_nhs"] = (nhs_start, len(lines))
    if iface.ip_nhrp_maps:
        maps_start = len(lines) + 1
        lines.append("          ip_nhrp_maps:")
        for nhrp_map in iface.ip_nhrp_maps:
            lines.append(f"          - dest_ipv4: {_yaml_str(nhrp_map.dest_ipv4)}")
            lines.append(f"            nbma_ipv4: {_yaml_str(nhrp_map.nbma_ipv4)}")
        rel[f"{base}:ip_nhrp_maps"] = (maps_start, len(lines))
    if iface.ip_nhrp_redirect is not None:
        redir_line = len(lines) + 1
        redir_val = "true" if iface.ip_nhrp_redirect else "false"
        lines.append(f"          ip_nhrp_redirect: {redir_val}")
        rel[f"{base}:ip_nhrp_redirect"] = (redir_line, redir_line)
    if iface.ip_nhrp_shortcut is not None:
        short_line = len(lines) + 1
        short_val = "true" if iface.ip_nhrp_shortcut else "false"
        lines.append(f"          ip_nhrp_shortcut: {short_val}")
        rel[f"{base}:ip_nhrp_shortcut"] = (short_line, short_line)
    if iface.mpls_nhrp is not None:
        mpls_line = len(lines) + 1
        mpls_val = "true" if iface.mpls_nhrp else "false"
        lines.append(f"          mpls_nhrp: {mpls_val}")
        rel[f"{base}:mpls_nhrp"] = (mpls_line, mpls_line)

    rel[base] = (block_start, len(lines))
    return lines, rel


def _format_vlan(
    iface: Interface, *, show_hints: bool = False
) -> tuple[list[str], dict[str, tuple[int, int]]]:
    lines: list[str] = []
    rel: dict[str, tuple[int, int]] = {}
    base = fk.interface_key(iface.name)
    block_start = 1

    lines.append(f"        - id: '{iface.vlan_id or '0'}'")

    if iface.nat_inside:
        nat_line = len(lines) + 1
        lines.append("          nat_inside: true")
        rel[f"{base}:nat_inside"] = (nat_line, nat_line)
    if iface.nat_outside:
        nat_line = len(lines) + 1
        lines.append("          nat_outside: true")
        rel[f"{base}:nat_outside"] = (nat_line, nat_line)

    if iface.description:
        desc_line = len(lines) + 1
        lines.append(f"          description: {_yaml_str(iface.description)}")
        rel[f"{base}:description"] = (desc_line, desc_line)

    if iface.ipv4_dhcp or iface.ipv4_address or show_hints:
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


def _system_has_content(system) -> bool:
    return bool(
        system.hostname
        or system.ipv6_unicast_routing
        or system.mtu is not None
        or system.ip_domain_name
        or system.enable_secret
        or system.enable_password
    )


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
    system = config.system
    if not _system_has_content(system) and not builder.show_hints:
        return
    builder.append("      system:")
    if system.hostname:
        hn_line = builder.append(f"        hostname: {_yaml_str(system.hostname)}")
        builder.mark(fk.system_hostname(), hn_line, hn_line)
    elif builder.show_hints:
        builder.hint_line(f"        hostname: {_yaml_null_hint('type: hostn R1')}")

    if system.ipv6_unicast_routing:
        routing_line = builder.append("        ipv6_unicast_routing: true")
        builder.mark(fk.system_ipv6_unicast_routing(), routing_line, routing_line)

    if system.mtu is not None:
        mtu_line = builder.append(f"        mtu: {system.mtu}")
        builder.mark(fk.system_mtu(), mtu_line, mtu_line)

    if system.ip_domain_name:
        domain_line = builder.append(f"        ip_domain_name: {_yaml_str(system.ip_domain_name)}")
        builder.mark(fk.system_ip_domain_name(), domain_line, domain_line)

    if system.enable_secret:
        secret_line = builder.append(f"        enable_secret: {_yaml_str(system.enable_secret)}")
        if system.enable_secret_type:
            builder.append(f"        enable_secret_type: {_yaml_str(system.enable_secret_type)}")
        builder.mark(fk.system_enable_secret(), secret_line, secret_line)

    if system.enable_password:
        pass_line = builder.append(f"        enable_password: {_yaml_str(system.enable_password)}")
        if system.enable_password_type:
            builder.append(f"        enable_password_type: {_yaml_str(system.enable_password_type)}")
        builder.mark(fk.system_enable_password(), pass_line, pass_line)


def _emit_users(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    if config.users:
        start = builder.append("      users:")
        for user in config.users:
            user_start = len(builder.lines) + 1
            builder.append(f"        - name: {_yaml_str(user.name)}")
            if user.privilege is not None:
                builder.append(f"          privilege: {user.privilege}")
            if user.secret is not None:
                secret_line = builder.append(f"          secret: {_yaml_str(user.secret)}")
                if user.secret_type:
                    builder.append(f"          secret_type: {_yaml_str(user.secret_type)}")
                builder.mark(fk.user_key(user.name), user_start, secret_line)
            elif user.password is not None:
                pass_line = builder.append(f"          password: {_yaml_str(user.password)}")
                if user.password_type:
                    builder.append(f"          password_type: {_yaml_str(user.password_type)}")
                builder.mark(fk.user_key(user.name), user_start, pass_line)
        builder.mark(fk.users_section(), start, len(builder.lines))
    elif config.section_is_empty("users"):
        builder.hint_line(f"      users:{_section_hint('type: username admin secret ...')}")


def _emit_banner(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    banner = config.banner
    if banner and not config.section_is_empty("banner"):
        start = builder.append("      banner:")
        if banner.motd:
            motd_line = builder.append(f"        motd: {_yaml_str(banner.motd)}")
            builder.mark(fk.banner_key("motd"), motd_line, motd_line)
        if banner.login:
            login_line = builder.append(f"        login: {_yaml_str(banner.login)}")
            builder.mark(fk.banner_key("login"), login_line, login_line)
        if banner.exec:
            exec_line = builder.append(f"        exec: {_yaml_str(banner.exec)}")
            builder.mark(fk.banner_key("exec"), exec_line, exec_line)
        builder.mark(fk.banner_section(), start, len(builder.lines))
    elif config.section_is_empty("banner"):
        builder.hint_line(f"      banner:{_section_hint('type: banner motd ^C...^C')}")


def _emit_clock(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    clock = config.clock
    if clock and not config.section_is_empty("clock"):
        start = builder.append("      clock:")
        if clock.timezone:
            tz_line = builder.append(f"        timezone: {_yaml_str(clock.timezone)}")
            builder.mark(fk.clock_timezone(), tz_line, tz_line)
        if clock.timezone_offset_hours is not None:
            builder.append(f"        timezone_offset_hours: {clock.timezone_offset_hours}")
        if clock.summer_time_zone:
            builder.append(f"        summer_time_zone: {_yaml_str(clock.summer_time_zone)}")
        builder.mark(fk.clock_section(), start, len(builder.lines))
    elif config.section_is_empty("clock"):
        builder.hint_line(f"      clock:{_section_hint('type: clock timezone EST -5')}")


def _emit_access_lists(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    acls = config.access_lists
    if acls is None or config.section_is_empty("access_lists"):
        builder.hint_line(f"      access_lists:{_section_hint('type: ip access-list standard ...')}")
        return

    builder.append("      access_lists:")
    if acls.standard:
        builder.append("        standard:")
        for acl in acls.standard:
            acl_start = len(builder.lines) + 1
            builder.append(f"        - name: {_yaml_str(acl.name)}")
            if acl.entries:
                entries_start = builder.append("          entries:")
                for entry in acl.entries:
                    builder.append(f"          - sequence: {entry.sequence}")
                    builder.append(f"            action: {entry.action}")
                    if entry.prefix:
                        builder.append(f"            prefix: {_yaml_str(entry.prefix)}")
                    if entry.prefix_mask:
                        builder.append(f"            prefix_mask: {_yaml_str(entry.prefix_mask)}")
                builder.mark(fk.access_list_standard_key(acl.name, "entries"), entries_start, len(builder.lines))
            builder.mark(fk.access_list_standard_key(acl.name), acl_start, len(builder.lines))
    if acls.extended:
        builder.append("        extended:")
        for acl in acls.extended:
            acl_start = len(builder.lines) + 1
            builder.append(f"        - name: {_yaml_str(acl.name)}")
            if acl.entries:
                entries_start = builder.append("          entries:")
                for entry in acl.entries:
                    builder.append(f"          - sequence: {entry.sequence}")
                    builder.append(f"            action: {entry.action}")
                    if entry.protocol:
                        builder.append(f"            protocol: {entry.protocol}")
                    if entry.source_any:
                        builder.append("            source:")
                        builder.append("              any: true")
                    if entry.destination_any:
                        builder.append("            destination:")
                        builder.append("              any: true")
                builder.mark(fk.access_list_extended_key(acl.name, "entries"), entries_start, len(builder.lines))
            builder.mark(fk.access_list_extended_key(acl.name), acl_start, len(builder.lines))


def _emit_prefix_lists(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    if config.section_is_empty("prefix_lists"):
        builder.hint_line(f"      prefix_lists:{_section_hint('type: ip prefix-list ...')}")
        return

    builder.append("      prefix_lists:")
    for pl in config.prefix_lists:
        pl_start = len(builder.lines) + 1
        builder.append(f"      - name: {_yaml_str(pl.name)}")
        if pl.description:
            builder.append(f"        description: {_yaml_str(pl.description)}")
        if pl.seqs:
            builder.append("        seqs:")
            for seq in pl.seqs:
                builder.append(f"        - seq: {seq.seq}")
                if seq.action:
                    builder.append(f"          action: {seq.action}")
                if seq.prefix:
                    builder.append(f"          prefix: {_yaml_str(seq.prefix)}")
                if seq.greater_equal is not None:
                    builder.append(f"          greater_equal: {seq.greater_equal}")
                if seq.less_equal is not None:
                    builder.append(f"          less_equal: {seq.less_equal}")
        builder.mark(fk.prefix_list_key(pl.name), pl_start, len(builder.lines))


def _emit_route_maps(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    if config.section_is_empty("route_maps"):
        builder.hint_line(f"      route_maps:{_section_hint('type: route-map RM permit 10')}")
        return

    builder.append("      route_maps:")
    for rm in config.route_maps:
        builder.append(f"      - name: {_yaml_str(rm.name)}")
        if rm.entries:
            builder.append("        entries:")
            for entry in rm.entries:
                entry_start = len(builder.lines) + 1
                builder.append(f"        - seq: {entry.seq}")
                if entry.operation:
                    builder.append(f"          operation: {entry.operation}")
                if entry.description:
                    builder.append(f"          description: {_yaml_str(entry.description)}")
                if entry.match and (
                    entry.match.ipv4_address_prefix_lists or entry.match.ipv4_address_access_lists
                ):
                    builder.append("          match:")
                    if entry.match.ipv4_address_prefix_lists:
                        builder.append("            ipv4_address_prefix_lists:")
                        for pl_name in entry.match.ipv4_address_prefix_lists:
                            builder.append(f"            - {_yaml_str(pl_name)}")
                    if entry.match.ipv4_address_access_lists:
                        builder.append("            ipv4_address_access_lists:")
                        for acl_name in entry.match.ipv4_address_access_lists:
                            builder.append(f"            - {_yaml_str(acl_name)}")
                if entry.set and (
                    entry.set.local_preference is not None or entry.set.metric_value is not None
                ):
                    builder.append("          set:")
                    if entry.set.local_preference is not None:
                        builder.append(f"            local_preference: {entry.set.local_preference}")
                    if entry.set.metric_value is not None:
                        builder.append(f"            metric_value: {entry.set.metric_value}")
                builder.mark(fk.route_map_key(rm.name, entry.seq), entry_start, len(builder.lines))


def _emit_vrfs(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    if config.section_is_empty("vrfs"):
        builder.hint_line(f"      vrfs:{_section_hint('type: vrf definition MGMT')}")
        return

    builder.append("      vrfs:")
    for vrf in config.vrfs:
        vrf_start = len(builder.lines) + 1
        builder.append(f"      - name: {_yaml_str(vrf.name)}")
        if vrf.description:
            desc_line = len(builder.lines) + 1
            builder.append(f"        description: {_yaml_str(vrf.description)}")
            builder.mark(fk.vrf_key(vrf.name, "description"), desc_line, desc_line)
        if vrf.route_distinguisher:
            rd_line = len(builder.lines) + 1
            builder.append(f"        route_distinguisher: {_yaml_str(vrf.route_distinguisher)}")
            builder.mark(fk.vrf_key(vrf.name, "rd"), rd_line, rd_line)
        if vrf.address_family_ipv4 and (
            vrf.address_family_ipv4.import_route_targets or vrf.address_family_ipv4.export_route_targets
        ):
            af_start = len(builder.lines) + 1
            builder.append("        address_family_ipv4:")
            if vrf.address_family_ipv4.import_route_targets:
                builder.append("          import_route_targets:")
                for rt in vrf.address_family_ipv4.import_route_targets:
                    builder.append(f"          - {_yaml_str(rt)}")
            if vrf.address_family_ipv4.export_route_targets:
                builder.append("          export_route_targets:")
                for rt in vrf.address_family_ipv4.export_route_targets:
                    builder.append(f"          - {_yaml_str(rt)}")
            builder.mark(fk.vrf_key(vrf.name, "address_family_ipv4"), af_start, len(builder.lines))
        if vrf.address_family_ipv6 and (
            vrf.address_family_ipv6.import_route_targets or vrf.address_family_ipv6.export_route_targets
        ):
            af_start = len(builder.lines) + 1
            builder.append("        address_family_ipv6:")
            if vrf.address_family_ipv6.import_route_targets:
                builder.append("          import_route_targets:")
                for rt in vrf.address_family_ipv6.import_route_targets:
                    builder.append(f"          - {_yaml_str(rt)}")
            if vrf.address_family_ipv6.export_route_targets:
                builder.append("          export_route_targets:")
                for rt in vrf.address_family_ipv6.export_route_targets:
                    builder.append(f"          - {_yaml_str(rt)}")
            builder.mark(fk.vrf_key(vrf.name, "address_family_ipv6"), af_start, len(builder.lines))
        builder.mark(fk.vrf_key(vrf.name), vrf_start, len(builder.lines))


def _emit_routing(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    routing = config.routing
    has_static = bool(routing.static_routes)
    has_other = bool(routing.ospf_processes or routing.bgp or routing.isis or routing.eigrp_processes)

    if not has_static and not has_other:
        if not builder.show_hints:
            return
        builder.append("      routing:")
        for subsection in ROUTING_SUBSECTION_HINTS:
            builder.hint_line(f"        {subsection.key}:{_section_hint(subsection.hint)}")
        return

    builder.append("      routing:")
    if has_static:
        builder.append("        static_routes:")
        for route in routing.static_routes:
            route_start = len(builder.lines) + 1
            plen = route.prefix if "/" in route.prefix else route.prefix
            if route.prefix_length and "/" not in route.prefix:
                plen = f"{route.prefix}/{route.prefix_length}"
            builder.append(f"        - prefix: {_yaml_str(plen)}")
            if route.next_hop:
                builder.append(f"          next_hop: {_yaml_str(route.next_hop)}")
            builder.mark(fk.static_route_key(plen), route_start, len(builder.lines))

    if routing.ospf_processes:
        builder.append("        ospf_processes:")
        for proc in routing.ospf_processes:
            proc_start = len(builder.lines) + 1
            builder.append(f"        - id: {proc.id}")
            if proc.router_id:
                rid_line = len(builder.lines) + 1
                builder.append(f"          router_id: {_yaml_str(proc.router_id)}")
                builder.mark(fk.ospf_process_key(proc.id, "router_id"), rid_line, rid_line)
            if proc.networks:
                nets_start = builder.append("          networks:")
                for net in proc.networks:
                    builder.append(f"          - ip: {_yaml_str(net.ip)}")
                    if net.wildcard:
                        builder.append(f"            wildcard: {_yaml_str(net.wildcard)}")
                    if net.area is not None:
                        builder.append(f"            area: {net.area}")
                builder.mark(fk.ospf_process_key(proc.id, "networks"), nets_start, len(builder.lines))
            if proc.passive_interface_default:
                pid_line = builder.append("          passive_interface_default: true")
                builder.mark(fk.ospf_process_key(proc.id, "passive_interface_default"), pid_line, pid_line)
            if proc.passive_interfaces:
                pass_start = builder.append("          passive_interfaces:")
                for passive in proc.passive_interfaces:
                    builder.append(
                        f"          - interface_type: {_yaml_str(passive.interface_type or 'GigabitEthernet')}"
                    )
                    if passive.interface_id:
                        builder.append(f"            interface_id: {_yaml_str(passive.interface_id)}")
                builder.mark(fk.ospf_process_key(proc.id, "passive_interfaces"), pass_start, len(builder.lines))
            builder.mark(fk.ospf_process_key(proc.id), proc_start, len(builder.lines))

    if routing.bgp and (
        routing.bgp.as_number is not None
        or routing.bgp.neighbors
        or (
            routing.bgp.address_family
            and routing.bgp.address_family.ipv4_unicast
            and routing.bgp.address_family.ipv4_unicast.networks
        )
    ):
        bgp = routing.bgp
        bgp_start = builder.append("        bgp:")
        if bgp.as_number is not None:
            builder.append(f"          as_number: {bgp.as_number}")
        if bgp.neighbors:
            neigh_start = builder.append("          neighbors:")
            for neighbor in bgp.neighbors:
                builder.append(f"          - ip: {_yaml_str(neighbor.ip)}")
                if neighbor.remote_as is not None:
                    builder.append(f"            remote_as: {neighbor.remote_as}")
            builder.mark(fk.bgp_key("neighbors"), neigh_start, len(builder.lines))
        ipv4_nets = (
            bgp.address_family.ipv4_unicast.networks
            if bgp.address_family and bgp.address_family.ipv4_unicast
            else []
        )
        if ipv4_nets:
            nets_start = builder.append("          address_family:")
            builder.append("            ipv4_unicast:")
            builder.append("              networks:")
            for net in ipv4_nets:
                builder.append(f"              - network: {_yaml_str(net.network)}")
                if net.mask:
                    builder.append(f"                mask: {_yaml_str(net.mask)}")
            builder.mark(fk.bgp_key("address_family.ipv4_unicast.networks"), nets_start, len(builder.lines))
        builder.mark(fk.bgp_key(), bgp_start, len(builder.lines))

    if routing.isis and (routing.isis.area_tag or routing.isis.nets or routing.isis.is_type):
        isis = routing.isis
        isis_start = builder.append("        isis:")
        if isis.area_tag:
            builder.append(f"          area_tag: {_yaml_str(isis.area_tag)}")
        if isis.nets:
            nets_start = builder.append("          nets:")
            for net in isis.nets:
                builder.append(f"          - tag: {_yaml_str(net.tag)}")
            builder.mark(fk.isis_key("nets"), nets_start, len(builder.lines))
        if isis.is_type:
            type_line = len(builder.lines) + 1
            builder.append(f"          is_type: {_yaml_str(isis.is_type)}")
            builder.mark(fk.isis_key("is_type"), type_line, type_line)
        builder.mark(fk.isis_key(), isis_start, len(builder.lines))

    if routing.eigrp_processes:
        builder.append("        eigrp_processes:")
        for proc in routing.eigrp_processes:
            proc_key = fk.eigrp_process_key(proc.name, proc.vrf)
            proc_start = len(builder.lines) + 1
            builder.append(f"        - name: {_yaml_str(proc.name)}")
            if proc.autonomous_system is not None:
                builder.append(f"          autonomous_system: {proc.autonomous_system}")
            if proc.vrf:
                builder.append(f"          vrf: {_yaml_str(proc.vrf)}")
            if proc.router_id:
                rid_line = len(builder.lines) + 1
                builder.append(f"          router_id: {_yaml_str(proc.router_id)}")
                builder.mark(fk.eigrp_process_key(proc.name, proc.vrf, "router_id"), rid_line, rid_line)
            if proc.auto_summary is not None:
                summary_line = builder.append(
                    f"          auto_summary: {'true' if proc.auto_summary else 'false'}"
                )
                builder.mark(fk.eigrp_process_key(proc.name, proc.vrf, "auto_summary"), summary_line, summary_line)
            if proc.shutdown is not None:
                shut_line = builder.append(f"          shutdown: {'true' if proc.shutdown else 'false'}")
                builder.mark(fk.eigrp_process_key(proc.name, proc.vrf, "shutdown"), shut_line, shut_line)
            if proc.networks:
                nets_start = builder.append("          networks:")
                for net in proc.networks:
                    builder.append(f"          - ip: {_yaml_str(net.ip)}")
                    builder.append(f"            wildcard: {_yaml_str(net.wildcard)}")
                builder.mark(fk.eigrp_process_key(proc.name, proc.vrf, "networks"), nets_start, len(builder.lines))
            builder.mark(proc_key, proc_start, len(builder.lines))

    for subsection in ROUTING_SUBSECTION_HINTS:
        if subsection.key == "static_routes":
            continue
        if subsection.key == "ospf_processes" and routing.ospf_processes:
            continue
        if subsection.key == "bgp" and routing.bgp:
            continue
        if subsection.key == "isis" and routing.isis:
            continue
        if subsection.key == "eigrp_processes" and routing.eigrp_processes:
            continue
        if not config.section_is_empty("routing") and has_static and not has_other:
            builder.hint_line(f"        {subsection.key}:{_section_hint(subsection.hint)}")


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
    show_hints = builder.show_hints

    builder.append("      interfaces:")

    if not loopbacks and not ethernets and not tunnels and not vlans and not has_extra:
        if show_hints:
            builder.hint_line("        # ← type: int lo0, int g0/0/0, int tun10, int vlan888")
            builder.hint_line("        port_channels:  # ← type: int po1")
            builder.hint_line("        port_channel_subinterfaces:  # ← type: int po1.100")
            builder.hint_line("        ethernet_subinterfaces:  # ← type: int g0/0/0.100")
            builder.hint_line("        bdis:  # ← type: int bdi100")
            builder.hint_line("        nves:  # ← type: int nve1")
        return

    if loopbacks:
        builder.append("        loopbacks:")
        for iface in sorted(loopbacks, key=lambda i: int(i.loopback_id or "0")):
            block, rel = _format_loopback(iface, show_hints=show_hints)
            _add_iface_block(builder, iface, block, rel)

    if ethernets:
        builder.append("        ethernets:")
        for iface in ethernets:
            block, rel = _format_ethernet(iface, show_hints=show_hints)
            _add_iface_block(builder, iface, block, rel)

    if vlans:
        builder.append("        vlans:")
        for iface in sorted(vlans, key=lambda i: int(i.vlan_id or "0")):
            block, rel = _format_vlan(iface, show_hints=show_hints)
            _add_iface_block(builder, iface, block, rel)

    if tunnels:
        builder.append("        tunnels:")
        for iface in sorted(tunnels, key=lambda i: int(i.tunnel_id or "0")):
            block, rel = _format_tunnel(iface, show_hints=show_hints)
            _add_iface_block(builder, iface, block, rel)

    for key, hint, formatter in (
        ("port_channels", "type: int po1", _format_port_channel),
        ("port_channel_subinterfaces", "type: int po1.100", _format_port_channel_subinterface),
        ("ethernet_subinterfaces", "type: int g0/0/0.100", _format_ethernet_subinterface),
        ("bdis", "type: int bdi100", _format_bdi),
        ("nves", "type: int nve1", _format_nve),
    ):
        bucket = getattr(ifaces, key)
        if bucket:
            builder.append(f"        {key}:")
            sort_key = {
                "port_channels": lambda i: int(i.port_channel_id or "0"),
                "port_channel_subinterfaces": lambda i: (
                    int(i.port_channel_id or "0"),
                    int(i.subinterface_id or "0"),
                ),
                "ethernet_subinterfaces": lambda i: i.name,
                "bdis": lambda i: int(i.bdi_id or "0"),
                "nves": lambda i: int(i.nve_id or "0"),
            }.get(key, lambda i: i.name)
            for iface in sorted(bucket, key=sort_key):
                block, rel = formatter(iface, show_hints=show_hints)
                _add_iface_block(builder, iface, block, rel)
        elif not has_extra and show_hints:
            builder.hint_line(f"        {key}:  {_section_hint(hint)}")




def _emit_aaa(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    aaa = config.aaa
    if aaa and not config.section_is_empty("aaa"):
        start = builder.append("      aaa:")
        aaa_rel: dict[str, tuple[int, int]] = {}
        if aaa.new_model:
            nm_line = builder.append("        new_model: true")
            aaa_rel[fk.aaa_new_model()] = (nm_line, nm_line)
        if aaa.authentication and aaa.authentication.logins:
            auth_start = builder.append("        authentication:")
            logins_start = builder.append("          logins:")
            for login in aaa.authentication.logins:
                login_key = fk.aaa_login_key(login.name)
                login_start = builder.append(f"          - name: {_yaml_str(login.name)}")
                if login.methods:
                    methods_start = builder.append("            methods:")
                    for method in login.methods:
                        builder.append(f"            - {_yaml_str(method)}")
                    aaa_rel[f"{login_key}:methods"] = (methods_start, len(builder.lines))
                aaa_rel[login_key] = (login_start, len(builder.lines))
            aaa_rel["aaa.authentication.logins"] = (logins_start, len(builder.lines))
            aaa_rel["aaa.authentication"] = (auth_start, len(builder.lines))
        if aaa.authorization and aaa.authorization.execs:
            authz_start = builder.append("        authorization:")
            execs_start = builder.append("          execs:")
            for authz in aaa.authorization.execs:
                authz_key = fk.aaa_authz_key(authz.name)
                authz_start_line = builder.append(f"          - name: {_yaml_str(authz.name)}")
                if authz.methods:
                    methods_start = builder.append("            methods:")
                    for method in authz.methods:
                        builder.append(f"            - {_yaml_str(method)}")
                    aaa_rel[f"{authz_key}:methods"] = (methods_start, len(builder.lines))
                aaa_rel[authz_key] = (authz_start_line, len(builder.lines))
            aaa_rel["aaa.authorization.execs"] = (execs_start, len(builder.lines))
            aaa_rel["aaa.authorization"] = (authz_start, len(builder.lines))
        if aaa.accounting and aaa.accounting.execs:
            acct_start = builder.append("        accounting:")
            execs_start = builder.append("          execs:")
            for acct in aaa.accounting.execs:
                acct_key = fk.aaa_acct_key(acct.name)
                acct_start_line = builder.append(f"          - name: {_yaml_str(acct.name)}")
                if acct.action_type:
                    action_line = builder.append(f"            action_type: {_yaml_str(acct.action_type)}")
                    aaa_rel[f"{acct_key}:action_type"] = (action_line, action_line)
                if acct.start_stop_groups:
                    groups_start = builder.append("            start_stop_groups:")
                    for grp in acct.start_stop_groups:
                        builder.append(f"            - {_yaml_str(grp)}")
                    aaa_rel[f"{acct_key}:start_stop_groups"] = (groups_start, len(builder.lines))
                aaa_rel[acct_key] = (acct_start_line, len(builder.lines))
            aaa_rel["aaa.accounting.execs"] = (execs_start, len(builder.lines))
            aaa_rel["aaa.accounting"] = (acct_start, len(builder.lines))
        _apply_crypto_marks(builder, aaa_rel)
        builder.mark(fk.aaa_section(), start, len(builder.lines))
    elif config.section_is_empty("aaa"):
        builder.hint_line(f"      aaa:{_section_hint('type: aaa new-model ...')}")


def _emit_snmp_server(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    snmp = config.snmp_server
    if snmp and not config.section_is_empty("snmp_server"):
        start = builder.append("      snmp_server:")
        if snmp.snmp_communities:
            builder.append("        snmp_communities:")
            for comm in snmp.snmp_communities:
                builder.append(f'        - name: {_yaml_str(comm.name)}')
                if comm.permission:
                    builder.append(f'          permission: {_yaml_str(comm.permission)}')
        if snmp.contact:
            contact_line = builder.append(f"        contact: {_yaml_str(snmp.contact)}")
            builder.mark(fk.snmp_server_contact(), contact_line, contact_line)
        if snmp.location:
            builder.append(f"        location: {_yaml_str(snmp.location)}")
        builder.mark(fk.snmp_server_section(), start, len(builder.lines))
    elif config.section_is_empty("snmp_server"):
        builder.hint_line(f"      snmp_server:{_section_hint('type: snmp-server community ...')}")


def _emit_ntp(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    ntp = config.ntp
    if ntp and not config.section_is_empty("ntp"):
        start = builder.append("      ntp:")
        ntp_rel: dict[str, tuple[int, int]] = {}
        if ntp.servers:
            servers_start = builder.append("        servers:")
            for srv in ntp.servers:
                entry_start = builder.append(f'        - ip: {_yaml_str(srv.ip)}')
                if srv.vrf:
                    builder.append(f'          vrf: {_yaml_str(srv.vrf)}')
                if srv.prefer:
                    builder.append("          prefer: true")
                ntp_rel[fk.ntp_endpoint_key("server", srv.ip)] = (entry_start, len(builder.lines))
            ntp_rel["ntp.servers"] = (servers_start, len(builder.lines))
        if ntp.peers:
            peers_start = builder.append("        peers:")
            for peer in ntp.peers:
                entry_start = builder.append(f'        - ip: {_yaml_str(peer.ip)}')
                if peer.vrf:
                    builder.append(f'          vrf: {_yaml_str(peer.vrf)}')
                if peer.prefer:
                    builder.append("          prefer: true")
                ntp_rel[fk.ntp_endpoint_key("peer", peer.ip)] = (entry_start, len(builder.lines))
            ntp_rel["ntp.peers"] = (peers_start, len(builder.lines))
        _apply_crypto_marks(builder, ntp_rel)
        builder.mark(fk.ntp_section(), start, len(builder.lines))
    elif config.section_is_empty("ntp"):
        builder.hint_line(f"      ntp:{_section_hint('type: ntp server 10.0.0.1')}")


def _emit_dhcp(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    dhcp = config.dhcp
    if dhcp and not config.section_is_empty("dhcp"):
        start = builder.append("      dhcp:")
        if dhcp.enabled:
            enabled_line = builder.append("        enabled: true")
            builder.mark(fk.dhcp_enabled(), enabled_line, enabled_line)
        builder.mark(fk.dhcp_section(), start, len(builder.lines))
    elif config.section_is_empty("dhcp"):
        builder.hint_line(f"      dhcp:{_section_hint('type: ip dhcp ...')}")


def _emit_dhcp_pools(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    if config.dhcp_pools:
        start = builder.append("      dhcp_pools:")
        for pool in config.dhcp_pools:
            pool_start = len(builder.lines) + 1
            builder.append(f'      - name: {_yaml_str(pool.name)}')
            if pool.network_number:
                net_start = len(builder.lines) + 1
                builder.append(f'        network_number: {_yaml_str(pool.network_number)}')
                if pool.network_mask:
                    builder.append(f'        network_mask: {_yaml_str(pool.network_mask)}')
                builder.mark(fk.dhcp_pool_key(pool.name, "network"), net_start, len(builder.lines))
            if pool.default_routers:
                builder.append("        default_routers:")
                for router in pool.default_routers:
                    builder.append(f'        - {_yaml_str(router)}')
            if pool.dns_servers:
                builder.append("        dns_servers:")
                for dns in pool.dns_servers:
                    builder.append(f'        - {_yaml_str(dns)}')
            builder.mark(fk.dhcp_pool_key(pool.name), pool_start, len(builder.lines))
        builder.mark(fk.dhcp_pools_section(), start, len(builder.lines))
    elif config.section_is_empty("dhcp_pools"):
        builder.hint_line(f"      dhcp_pools:{_section_hint('type: ip dhcp pool LAN')}")


def _emit_nat(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    nat = config.nat
    if nat and not config.section_is_empty("nat"):
        start = builder.append("      nat:")
        if nat.inside_source_interfaces:
            builder.append("        inside_source_interfaces:")
            for src in nat.inside_source_interfaces:
                builder.append(f"        - id: {src.id}")
                if src.interfaces:
                    builder.append("          interfaces:")
                    for iface in src.interfaces:
                        builder.append(f'          - interface_type: {_yaml_str(iface.interface_type)}')
                        if iface.interface_id:
                            builder.append(f'            interface_id: {_yaml_str(iface.interface_id)}')
                        if iface.overload:
                            builder.append("            overload: true")
        builder.mark(fk.nat_section(), start, len(builder.lines))
    elif config.section_is_empty("nat"):
        builder.hint_line(f"      nat:{_section_hint('type: ip nat inside source ...')}")

def _emit_crypto_bool(builder: _YamlBuilder, indent: str, key: str, value: bool | None) -> int | None:
    if value:
        return builder.append(f"{indent}{key}: true")
    return None


def _emit_crypto_str(builder: _YamlBuilder, indent: str, key: str, value: str | None) -> int | None:
    if value:
        return builder.append(f"{indent}{key}: {_yaml_str(value)}")
    return None


def _emit_ikev2_keyring_peer(builder: _YamlBuilder, peer: CryptoIkev2KeyringPeer) -> None:
    builder.append(f"              - name: {_yaml_str(peer.name)}")
    _emit_crypto_str(builder, "                ", "description", peer.description)
    _emit_crypto_str(builder, "                ", "hostname", peer.hostname)
    _emit_crypto_str(builder, "                ", "ipv4_address", peer.ipv4_address)
    _emit_crypto_str(builder, "                ", "ipv4_mask", peer.ipv4_mask)
    _emit_crypto_str(builder, "                ", "ipv6_prefix", peer.ipv6_prefix)
    _emit_crypto_str(builder, "                ", "identity_fqdn_domain", peer.identity_fqdn_domain)
    _emit_crypto_str(builder, "                ", "identity_key_id", peer.identity_key_id)
    _emit_crypto_str(builder, "                ", "pre_shared_key", peer.pre_shared_key)
    _emit_crypto_str(builder, "                ", "pre_shared_key_local", peer.pre_shared_key_local)
    _emit_crypto_str(builder, "                ", "pre_shared_key_remote", peer.pre_shared_key_remote)


def _emit_ikev2_profile(builder: _YamlBuilder, profile: CryptoIkev2Profile) -> dict[str, tuple[int, int]]:
    rel: dict[str, tuple[int, int]] = {}
    base = fk.crypto_profile_key(profile.name)
    block_start = builder.append(f"            - name: {_yaml_str(profile.name)}")
    desc_line = _emit_crypto_str(builder, "              ", "description", profile.description)
    if desc_line:
        rel[f"{base}:description"] = (desc_line, desc_line)
    auth_local = _emit_crypto_bool(builder, "              ", "authentication_local_pre_share", profile.authentication_local_pre_share)
    if auth_local:
        rel[f"{base}:authentication_local_pre_share"] = (auth_local, auth_local)
    auth_remote = _emit_crypto_bool(builder, "              ", "authentication_remote_pre_share", profile.authentication_remote_pre_share)
    if auth_remote:
        rel[f"{base}:authentication_remote_pre_share"] = (auth_remote, auth_remote)
    _emit_crypto_bool(builder, "              ", "config_exchange_request", profile.config_exchange_request)
    if profile.dpd_interval is not None:
        builder.append(f"              dpd_interval: {profile.dpd_interval}")
    _emit_crypto_str(builder, "              ", "dpd_query", profile.dpd_query)
    if profile.dpd_retry is not None:
        builder.append(f"              dpd_retry: {profile.dpd_retry}")
    _emit_crypto_str(builder, "              ", "identity_local_key_id", profile.identity_local_key_id)
    _emit_crypto_str(builder, "              ", "ivrf", profile.ivrf)
    keyring_line = _emit_crypto_str(builder, "              ", "keyring_local", profile.keyring_local)
    if keyring_line:
        rel[f"{base}:keyring_local"] = (keyring_line, keyring_line)
    if profile.lifetime is not None:
        builder.append(f"              lifetime: {profile.lifetime}")
    _emit_crypto_str(builder, "              ", "match_address_local_ip", profile.match_address_local_ip)
    if profile.match_address_local_interface_loopback_legacy is not None:
        builder.append(
            f"              match_address_local_interface_loopback_legacy: {profile.match_address_local_interface_loopback_legacy}"
        )
    _emit_crypto_str(builder, "              ", "match_fvrf", profile.match_fvrf)
    _emit_crypto_bool(builder, "              ", "match_fvrf_any", profile.match_fvrf_any)
    if profile.match_identity_remote_ipv4_addresses:
        builder.append("              match_identity_remote_ipv4_addresses:")
        for addr in profile.match_identity_remote_ipv4_addresses:
            builder.append(f"                - address: {_yaml_str(addr.address)}")
            _emit_crypto_str(builder, "                  ", "mask", addr.mask)
    if profile.match_identity_remote_ipv6_prefixes:
        builder.append("              match_identity_remote_ipv6_prefixes:")
        for prefix in profile.match_identity_remote_ipv6_prefixes:
            builder.append(f"                - {_yaml_str(prefix)}")
    if profile.match_identity_remote_keys:
        builder.append("              match_identity_remote_keys:")
        for key in profile.match_identity_remote_keys:
            builder.append(f"                - {_yaml_str(key)}")
    _emit_crypto_bool(builder, "              ", "match_inbound_only", profile.match_inbound_only)
    rel[base] = (block_start, len(builder.lines))
    return rel


def _apply_crypto_marks(builder: _YamlBuilder, rel: dict[str, tuple[int, int]]) -> None:
    for key, (start, end) in rel.items():
        builder.mark(key, start, end)


def _emit_crypto(builder: _YamlBuilder, config: DeviceConfiguration) -> None:
    crypto = config.crypto
    if crypto is None or crypto.is_empty():
        if config.section_is_empty("crypto"):
            builder.hint_line(f"      crypto:{_section_hint('type: crypto ikev2 proposal ...')}")
        return

    start = builder.append("      crypto:")
    crypto_rel: dict[str, tuple[int, int]] = {}

    if crypto.ipsec_profiles:
        ipsec_profiles_start = builder.append("        ipsec_profiles:")
        for prof in crypto.ipsec_profiles:
            prof_key = fk.crypto_ipsec_profile_key(prof.name)
            prof_start = builder.append(f"          - name: {_yaml_str(prof.name)}")
            if prof.set_transform_set:
                ts_start = len(builder.lines) + 1
                builder.append("            set_transform_set:")
                for ts in prof.set_transform_set:
                    builder.append(f"              - {_yaml_str(ts)}")
                crypto_rel[f"{prof_key}:set_transform_set"] = (ts_start, len(builder.lines))
            ikev2_line = _emit_crypto_str(builder, "            ", "set_ikev2_profile", prof.set_ikev2_profile)
            if ikev2_line:
                crypto_rel[f"{prof_key}:set_ikev2_profile"] = (ikev2_line, ikev2_line)
            _emit_crypto_str(builder, "            ", "set_isakmp_profile", prof.set_isakmp_profile)
            _emit_crypto_str(builder, "            ", "set_pfs_group", prof.set_pfs_group)
            if prof.set_security_association_lifetime_seconds is not None:
                builder.append(
                    f"            set_security_association_lifetime_seconds: {prof.set_security_association_lifetime_seconds}"
                )
            crypto_rel[prof_key] = (prof_start, len(builder.lines))
        crypto_rel["crypto.ipsec_profiles"] = (ipsec_profiles_start, len(builder.lines))

    if crypto.ipsec_transform_sets:
        transform_sets_start = builder.append("        ipsec_transform_sets:")
        for ts in crypto.ipsec_transform_sets:
            ts_key = fk.crypto_transform_set_key(ts.name)
            ts_start = builder.append(f"          - name: {_yaml_str(ts.name)}")
            esp_line = _emit_crypto_str(builder, "            ", "esp", ts.esp)
            if esp_line:
                crypto_rel[f"{ts_key}:esp"] = (esp_line, esp_line)
            hmac_line = _emit_crypto_str(builder, "            ", "esp_hmac", ts.esp_hmac)
            if hmac_line:
                crypto_rel[f"{ts_key}:esp_hmac"] = (hmac_line, hmac_line)
            mode_line = _emit_crypto_bool(builder, "            ", "mode_tunnel", ts.mode_tunnel)
            if mode_line:
                crypto_rel[f"{ts_key}:mode_tunnel"] = (mode_line, mode_line)
            crypto_rel[ts_key] = (ts_start, len(builder.lines))
        crypto_rel["crypto.ipsec_transform_sets"] = (transform_sets_start, len(builder.lines))

    ikev2 = crypto.ikev2
    if ikev2 and not ikev2.is_empty():
        ikev2_start = builder.append("        ikev2:")
        if ikev2.nat_keepalive is not None:
            nat_line = builder.append(f"          nat_keepalive: {ikev2.nat_keepalive}")
            crypto_rel[fk.crypto_ikev2_global("nat_keepalive")] = (nat_line, nat_line)
        if ikev2.dpd_interval is not None:
            dpd_line = builder.append(f"          dpd_interval: {ikev2.dpd_interval}")
            crypto_rel[fk.crypto_ikev2_global("dpd_interval")] = (dpd_line, dpd_line)
        _emit_crypto_str(builder, "          ", "dpd_query", ikev2.dpd_query)
        if ikev2.dpd_retry is not None:
            builder.append(f"          dpd_retry: {ikev2.dpd_retry}")
        if ikev2.proposals:
            proposals_start = builder.append("          proposals:")
            for prop in ikev2.proposals:
                prop_key = fk.crypto_proposal_key(prop.name)
                prop_start = builder.append(f"            - name: {_yaml_str(prop.name)}")
                if prop.encryption:
                    enc_start = len(builder.lines) + 1
                    builder.append("              encryption:")
                    for enc in prop.encryption:
                        builder.append(f"                - {_yaml_str(enc)}")
                    crypto_rel[f"{prop_key}:encryption"] = (enc_start, len(builder.lines))
                if prop.group:
                    grp_start = len(builder.lines) + 1
                    builder.append("              group:")
                    for grp in prop.group:
                        builder.append(f"                - {_yaml_str(grp)}")
                    crypto_rel[f"{prop_key}:group"] = (grp_start, len(builder.lines))
                if prop.integrity:
                    int_start = len(builder.lines) + 1
                    builder.append("              integrity:")
                    for val in prop.integrity:
                        builder.append(f"                - {_yaml_str(val)}")
                    crypto_rel[f"{prop_key}:integrity"] = (int_start, len(builder.lines))
                if prop.prf:
                    prf_start = len(builder.lines) + 1
                    builder.append("              prf:")
                    for val in prop.prf:
                        builder.append(f"                - {_yaml_str(val)}")
                    crypto_rel[f"{prop_key}:prf"] = (prf_start, len(builder.lines))
                crypto_rel[prop_key] = (prop_start, len(builder.lines))
            crypto_rel["crypto.ikev2.proposals"] = (proposals_start, len(builder.lines))
        if ikev2.policies:
            policies_start = builder.append("          policies:")
            for pol in ikev2.policies:
                pol_key = fk.crypto_policy_key(pol.name)
                pol_start = builder.append(f"            - name: {_yaml_str(pol.name)}")
                if pol.proposals:
                    prop_start = len(builder.lines) + 1
                    builder.append("              proposals:")
                    for prop in pol.proposals:
                        builder.append(f"                - {_yaml_str(prop)}")
                    crypto_rel[f"{pol_key}:proposals"] = (prop_start, len(builder.lines))
                fvrf_line = _emit_crypto_str(builder, "              ", "match_fvrf", pol.match_fvrf)
                if fvrf_line:
                    crypto_rel[f"{pol_key}:match_fvrf"] = (fvrf_line, fvrf_line)
                fvrf_any = _emit_crypto_bool(builder, "              ", "match_fvrf_any", pol.match_fvrf_any)
                if fvrf_any:
                    crypto_rel[f"{pol_key}:match_fvrf_any"] = (fvrf_any, fvrf_any)
                if pol.match_address_local_ip:
                    local_start = len(builder.lines) + 1
                    builder.append("              match_address_local_ip:")
                    for ip in pol.match_address_local_ip:
                        builder.append(f"                - {_yaml_str(ip)}")
                    crypto_rel[f"{pol_key}:match_address_local_ip"] = (local_start, len(builder.lines))
                _emit_crypto_bool(builder, "              ", "match_inbound_only", pol.match_inbound_only)
                crypto_rel[pol_key] = (pol_start, len(builder.lines))
            crypto_rel["crypto.ikev2.policies"] = (policies_start, len(builder.lines))
        if ikev2.keyrings:
            keyrings_start = builder.append("          keyrings:")
            for kr in ikev2.keyrings:
                kr_key = fk.crypto_keyring_key(kr.name)
                kr_start = builder.append(f"            - name: {_yaml_str(kr.name)}")
                if kr.peers:
                    peers_start = builder.append("              peers:")
                    for peer in kr.peers:
                        peer_start = len(builder.lines) + 1
                        _emit_ikev2_keyring_peer(builder, peer)
                        crypto_rel[f"{kr_key}:peers:{peer.name}"] = (peer_start, len(builder.lines))
                    crypto_rel[f"{kr_key}:peers"] = (peers_start, len(builder.lines))
                crypto_rel[kr_key] = (kr_start, len(builder.lines))
            crypto_rel["crypto.ikev2.keyrings"] = (keyrings_start, len(builder.lines))
        if ikev2.profiles:
            profiles_start = builder.append("          profiles:")
            for profile in ikev2.profiles:
                crypto_rel.update(_emit_ikev2_profile(builder, profile))
            crypto_rel["crypto.ikev2.profiles"] = (profiles_start, len(builder.lines))
        crypto_rel["crypto.ikev2"] = (ikev2_start, len(builder.lines))

    pki = crypto.pki
    if pki and not pki.is_empty():
        pki_start = builder.append("        pki:")
        trustpoints_start = builder.append("          trustpoints:")
        for tp in pki.trustpoints:
            tp_key = fk.crypto_trustpoint_key(tp.id)
            tp_start = builder.append(f"            - id: {_yaml_str(tp.id)}")
            enroll_line = _emit_crypto_bool(builder, "              ", "enrollment_terminal", tp.enrollment_terminal)
            if enroll_line:
                crypto_rel[f"{tp_key}:enrollment_terminal"] = (enroll_line, enroll_line)
            _emit_crypto_bool(builder, "              ", "enrollment_selfsigned", tp.enrollment_selfsigned)
            rsa_line = _emit_crypto_str(builder, "              ", "rsakeypair", tp.rsakeypair)
            if rsa_line:
                crypto_rel[f"{tp_key}:rsakeypair"] = (rsa_line, rsa_line)
            _emit_crypto_str(builder, "              ", "subject_name", tp.subject_name)
            usage_line = _emit_crypto_str(builder, "              ", "usage", tp.usage)
            if usage_line:
                crypto_rel[f"{tp_key}:usage"] = (usage_line, usage_line)
            if tp.revocation_check:
                builder.append("              revocation_check:")
                for rc in tp.revocation_check:
                    builder.append(f"                - {_yaml_str(rc)}")
            crypto_rel[tp_key] = (tp_start, len(builder.lines))
        crypto_rel["crypto.pki.trustpoints"] = (trustpoints_start, len(builder.lines))
        crypto_rel["crypto.pki"] = (pki_start, len(builder.lines))

    _apply_crypto_marks(builder, crypto_rel)
    builder.mark(fk.crypto_section(), start, len(builder.lines))


_SECTION_EMITTERS: dict[str, Callable[[_YamlBuilder, DeviceConfiguration], None]] = {
    "system": _emit_system,
    "users": _emit_users,
    "banner": _emit_banner,
    "clock": _emit_clock,
    "aaa": _emit_aaa,
    "access_lists": _emit_access_lists,
    "prefix_lists": _emit_prefix_lists,
    "route_maps": _emit_route_maps,
    "routing": _emit_routing,
    "vrfs": _emit_vrfs,
    "interfaces": _emit_interfaces,
    "snmp_server": _emit_snmp_server,
    "ntp": _emit_ntp,
    "dhcp": _emit_dhcp,
    "dhcp_pools": _emit_dhcp_pools,
    "nat": _emit_nat,
    "crypto": _emit_crypto,
}


def generate_nac_yaml(device: Device, *, show_hints: bool = False) -> NacYamlResult:
    """Generate apply-safe nac.yaml with YAML line ranges for highlighting."""
    header = SCAFFOLD_HEADER
    if show_hints:
        header += "# Scaffold hints: on — empty sections show # ← type: ... placeholders\n\n"
    else:
        header += "# Scaffold hints: off — only typed CLI appears in YAML\n\n"

    builder = _YamlBuilder(header, show_hints=show_hints)
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
            builder.hint_line(f"      {section.key}:{_section_hint(section.hint)}")

    return builder.build()
