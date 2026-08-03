"""Terraform HCL scaffold generator (CiscoDevNet/iosxe shape)."""

from __future__ import annotations

from app.models import Device, Interface, Ipv6Address, OspfProcess

SCAFFOLD_HEADER = """# Network Lens — Terraform preview
# Generated · Not applied
# Provider: CiscoDevNet/iosxe (scaffold only)
# NaC path → TF resource:
#   iosxe.devices[].configuration.system.*     → iosxe_system
#   iosxe.devices[].configuration.users[]      → iosxe_username
#   iosxe.devices[].configuration.banner       → iosxe_banner
#   iosxe.devices[].configuration.clock        → iosxe_clock
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
    if device.system.mtu is not None:
        lines.append(f"  mtu = {device.system.mtu}")
    if device.system.ip_domain_name:
        lines.append(f'  ip_domain_name = "{device.system.ip_domain_name}"')
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


def _format_ospf_block(proc: OspfProcess) -> str:
    safe_id = str(proc.id).replace("-", "_")
    lines = [f'resource "iosxe_ospf" "ospf_{safe_id}" {{', f"  process_id = {proc.id}"]
    if proc.router_id:
        lines.append(f'  router_id = "{proc.router_id}"')
    if proc.passive_interface_default:
        lines.append("  passive_interface_default = true")
    if proc.networks:
        lines.append("  networks = [")
        for net in proc.networks:
            area_val = f'"{net.area}"' if isinstance(net.area, str) else str(net.area)
            wildcard = net.wildcard or "0.0.0.0"
            lines.append(
                f'    {{ ip = "{net.ip}", wildcard = "{wildcard}", area = {area_val} }},'
            )
        lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_bgp_block(device: Device) -> str:
    bgp = device.configuration.routing.bgp
    if bgp is None:
        return ""
    lines = ['resource "iosxe_bgp" "bgp" {']
    if bgp.as_number is not None:
        lines.append(f"  as_number = {bgp.as_number}")
    if bgp.neighbors:
        lines.append("  neighbors = [")
        for neighbor in bgp.neighbors:
            remote_as = neighbor.remote_as if neighbor.remote_as is not None else "null"
            lines.append(f'    {{ ip = "{neighbor.ip}", remote_as = {remote_as} }},')
        lines.append("  ]")
    ipv4_nets = (
        bgp.address_family.ipv4_unicast.networks
        if bgp.address_family and bgp.address_family.ipv4_unicast
        else []
    )
    if ipv4_nets:
        lines.append("  address_family_ipv4_unicast_networks = [")
        for net in ipv4_nets:
            mask = net.mask or "255.255.255.255"
            lines.append(f'    {{ network = "{net.network}", mask = "{mask}" }},')
        lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_isis_block(device: Device) -> str:
    isis = device.configuration.routing.isis
    if isis is None:
        return ""
    safe_tag = (isis.area_tag or "default").lower().replace("-", "_")
    lines = [f'resource "iosxe_isis" "isis_{safe_tag}" {{']
    if isis.area_tag:
        lines.append(f'  area_tag = "{isis.area_tag}"')
    if isis.is_type:
        lines.append(f'  is_type = "{isis.is_type}"')
    if isis.nets:
        tags = ", ".join(f'"{net.tag}"' for net in isis.nets)
        lines.append(f"  nets = [{tags}]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_id_interface_block(
    resource_type: str, resource_id: str, name_value: str | int, iface: Interface
) -> str:
    shutdown_val = "true" if iface.shutdown else "false"
    body_lines = [
        f'resource "{resource_type}" "{resource_id}" {{',
        f"  name              = {name_value}",
        f"  shutdown          = {shutdown_val}",
    ]
    if iface.description:
        body_lines.append(f'  description       = "{iface.description}"')
    if iface.ipv4_address and not iface.ipv4_dhcp:
        body_lines.append(f'  ipv4_address      = "{iface.ipv4_address}"')
        body_lines.append(f'  ipv4_address_mask = "{iface.ipv4_address_mask or "255.255.255.255"}"')
    elif iface.ipv4_dhcp:
        body_lines.append("  ipv4_address      = dhcp")
        body_lines.append("  ipv4_address_mask = null")
    if iface.has_ipv6:
        body_lines.append("  ipv6_enable       = true")
    body_lines.append("}")
    return "\n".join(body_lines) + "\n"


def _format_port_channel_block(iface: Interface) -> str:
    pc_id = iface.port_channel_id or "0"
    return _format_id_interface_block("iosxe_interface_port_channel", f"po{pc_id}", int(pc_id), iface)


def _format_port_channel_subinterface_block(iface: Interface) -> str:
    pc_id = iface.port_channel_id or "0"
    sub_id = iface.subinterface_id or "0"
    return _format_id_interface_block(
        "iosxe_interface_port_channel_subinterface",
        f"po{pc_id}_{sub_id}",
        f'"{pc_id}.{sub_id}"',
        iface,
    )


def _format_ethernet_subinterface_block(iface: Interface) -> str:
    etype = iface.ethernet_type or "GigabitEthernet"
    eid = iface.ethernet_id or "0/0/0"
    sub_id = iface.subinterface_id or "0"
    safe_id = f"{eid.replace('/', '_')}_{sub_id}"
    name = f"{eid}.{sub_id}"
    shutdown_val = "true" if iface.shutdown else "false"
    body_lines = [
        f'resource "iosxe_interface_ethernet" "gi_{safe_id}" {{',
        f'  type              = "{etype}"',
        f'  name              = "{name}"',
        f"  shutdown          = {shutdown_val}",
    ]
    if iface.ipv4_address and not iface.ipv4_dhcp:
        body_lines.append(f'  ipv4_address      = "{iface.ipv4_address}"')
        body_lines.append(f'  ipv4_address_mask = "{iface.ipv4_address_mask or "255.255.255.255"}"')
    body_lines.append("}")
    return "\n".join(body_lines) + "\n"


def _format_bdi_block(iface: Interface) -> str:
    bdi_id = iface.bdi_id or "0"
    return _format_id_interface_block("iosxe_interface_bdi", f"bdi{bdi_id}", int(bdi_id), iface)


def _format_nve_block(iface: Interface) -> str:
    nve_id = iface.nve_id or "0"
    return _format_id_interface_block("iosxe_interface_nve", f"nve{nve_id}", int(nve_id), iface)




def _format_aaa_block(device: Device) -> str:
    aaa = device.configuration.aaa
    if aaa is None or device.configuration.section_is_empty("aaa"):
        return ""
    lines = ['resource "iosxe_aaa" "aaa" {', "  new_model = true"]
    if aaa.authentication and aaa.authentication.logins:
        lines.append("  authentication_logins = [")
        for login in aaa.authentication.logins:
            methods = ", ".join(f'"{m}"' for m in login.methods)
            lines.append(f'    {{ name = "{login.name}", methods = [{methods}] }},')
        lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_snmp_block(device: Device) -> str:
    snmp = device.configuration.snmp_server
    if snmp is None or device.configuration.section_is_empty("snmp_server"):
        return ""
    lines = ['resource "iosxe_snmp_server" "snmp" {']
    if snmp.contact:
        lines.append(f'  contact = "{snmp.contact}"')
    if snmp.snmp_communities:
        lines.append("  communities = [")
        for comm in snmp.snmp_communities:
            perm = f', permission = "{comm.permission}"' if comm.permission else ""
            lines.append(f'    {{ name = "{comm.name}"{perm} }},')
        lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_ntp_block(device: Device) -> str:
    ntp = device.configuration.ntp
    if ntp is None or device.configuration.section_is_empty("ntp"):
        return ""
    lines = ['resource "iosxe_ntp" "ntp" {', "  servers = ["]
    for srv in ntp.servers:
        prefer = ", prefer = true" if srv.prefer else ""
        lines.append(f'    {{ ip = "{srv.ip}"{prefer} }},')
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _format_dhcp_block(device: Device) -> str:
    config = device.configuration
    parts: list[str] = []
    if config.dhcp and config.dhcp.enabled:
        parts.append('resource "iosxe_dhcp" "dhcp" {\n  enabled = true\n}\n')
    if config.dhcp_pools:
        parts.append("# iosxe.devices[].configuration.dhcp_pools[] → iosxe_dhcp_pool")
        for pool in config.dhcp_pools:
            safe = pool.name.replace("-", "_")
            parts.append(f'resource "iosxe_dhcp_pool" "{safe}" {{\n  name = "{pool.name}"\n}}\n')
    return "".join(parts)


def _format_nat_block(device: Device) -> str:
    nat = device.configuration.nat
    if nat is None or device.configuration.section_is_empty("nat"):
        return ""
    lines = ['resource "iosxe_nat" "nat" {', "  inside_source_interfaces = ["]
    for src in nat.inside_source_interfaces:
        lines.append(f"    {{ id = {src.id} }},")
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


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

    routing = device.configuration.routing
    if routing.ospf_processes:
        parts.append("# iosxe.devices[].configuration.routing.ospf_processes[] → iosxe_ospf")
        for proc in routing.ospf_processes:
            parts.append(_format_ospf_block(proc))
    if routing.bgp:
        parts.append("# iosxe.devices[].configuration.routing.bgp → iosxe_bgp")
        parts.append(_format_bgp_block(device))
    if routing.isis:
        parts.append("# iosxe.devices[].configuration.routing.isis → iosxe_isis")
        parts.append(_format_isis_block(device))

    port_channels = [i for i in device.interfaces if i.kind == "port_channel"]
    for iface in sorted(port_channels, key=lambda i: int(i.port_channel_id or "0")):
        parts.append(_format_port_channel_block(iface))
    po_subifs = [i for i in device.interfaces if i.kind == "port_channel_subinterface"]
    for iface in sorted(
        po_subifs, key=lambda i: (int(i.port_channel_id or "0"), int(i.subinterface_id or "0"))
    ):
        parts.append(_format_port_channel_subinterface_block(iface))
    eth_subifs = [i for i in device.interfaces if i.kind == "ethernet_subinterface"]
    for iface in eth_subifs:
        parts.append(_format_ethernet_subinterface_block(iface))
    bdis = [i for i in device.interfaces if i.kind == "bdi"]
    for iface in sorted(bdis, key=lambda i: int(i.bdi_id or "0")):
        parts.append(_format_bdi_block(iface))
    nves = [i for i in device.interfaces if i.kind == "nve"]
    for iface in sorted(nves, key=lambda i: int(i.nve_id or "0")):
        parts.append(_format_nve_block(iface))

    config = device.configuration
    if config.vrfs:
        parts.append("# iosxe.devices[].configuration.vrfs[] → iosxe_vrf")
        for vrf in config.vrfs:
            safe = vrf.name.replace("-", "_")
            parts.append(f'resource "iosxe_vrf" "{safe}" {{')
            parts.append(f'  name = "{vrf.name}"')
            if vrf.route_distinguisher:
                parts.append(f'  rd = "{vrf.route_distinguisher}"')
            parts.append("}")
    if config.access_lists and not config.section_is_empty("access_lists"):
        parts.append("# iosxe.devices[].configuration.access_lists → iosxe_access_list_*")
        for acl in config.access_lists.standard:
            safe = acl.name.replace("-", "_")
            parts.append(f'resource "iosxe_access_list_standard" "{safe}" {{')
            parts.append(f'  name = "{acl.name}"')
            parts.append("}")
        for acl in config.access_lists.extended:
            safe = acl.name.replace("-", "_")
            parts.append(f'resource "iosxe_access_list_extended" "{safe}" {{')
            parts.append(f'  name = "{acl.name}"')
            parts.append("}")
    if config.prefix_lists:
        parts.append("# iosxe.devices[].configuration.prefix_lists[] → iosxe_prefix_list")
        for pl in config.prefix_lists:
            safe = pl.name.replace("-", "_")
            parts.append(f'resource "iosxe_prefix_list" "{safe}" {{')
            parts.append(f'  name = "{pl.name}"')
            parts.append("}")
    if config.route_maps:
        parts.append("# iosxe.devices[].configuration.route_maps[] → iosxe_route_map")
        for rm in config.route_maps:
            safe = rm.name.replace("-", "_")
            parts.append(f'resource "iosxe_route_map" "{safe}" {{')
            parts.append(f'  name = "{rm.name}"')
            parts.append("}")

    svc = _format_aaa_block(device)
    if svc:
        parts.append("# iosxe.devices[].configuration.aaa → iosxe_aaa")
        parts.append(svc)
    svc = _format_snmp_block(device)
    if svc:
        parts.append("# iosxe.devices[].configuration.snmp_server → iosxe_snmp_server")
        parts.append(svc)
    svc = _format_ntp_block(device)
    if svc:
        parts.append("# iosxe.devices[].configuration.ntp → iosxe_ntp")
        parts.append(svc)
    svc = _format_dhcp_block(device)
    if svc:
        parts.append(svc)
    svc = _format_nat_block(device)
    if svc:
        parts.append("# iosxe.devices[].configuration.nat → iosxe_nat")
        parts.append(svc)

    return "\n".join(parts).rstrip() + "\n"
