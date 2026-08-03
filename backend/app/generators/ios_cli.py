"""Regenerate IOS CLI from canonical device model."""

from __future__ import annotations

from app.models import Device, Interface


def _iface_lines(iface: Interface) -> list[str]:
    lines = [f"interface {iface.name}"]
    if iface.description:
        lines.append(f" description {iface.description}")
    if iface.vrf_forwarding:
        lines.append(f" vrf forwarding {iface.vrf_forwarding}")
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
    if iface.nat_inside:
        lines.append(" ip nat inside")
    if iface.nat_outside:
        lines.append(" ip nat outside")
    return lines


def _vrf_lines(device: Device) -> list[str]:
    lines: list[str] = []
    for vrf in device.configuration.vrfs:
        lines.append(f"vrf definition {vrf.name}")
        if vrf.description:
            lines.append(f" description {vrf.description}")
        if vrf.route_distinguisher:
            lines.append(f" rd {vrf.route_distinguisher}")
        for family, af in (("ipv4", vrf.address_family_ipv4), ("ipv6", vrf.address_family_ipv6)):
            if af is None:
                continue
            lines.append(f" address-family {family}")
            for rt in af.import_route_targets:
                lines.append(f"  route-target import {rt}")
            for rt in af.export_route_targets:
                lines.append(f"  route-target export {rt}")
            lines.append(" exit-address-family")
    return lines


def _access_list_lines(device: Device) -> list[str]:
    lines: list[str] = []
    acls = device.configuration.access_lists
    if acls is None:
        return lines
    for acl in acls.standard:
        lines.append(f"ip access-list standard {acl.name}")
        for entry in acl.entries:
            if entry.prefix == "any":
                lines.append(f" {entry.sequence} {entry.action} any")
            elif entry.prefix_mask:
                lines.append(f" {entry.sequence} {entry.action} {entry.prefix} {entry.prefix_mask}")
            else:
                lines.append(f" {entry.sequence} {entry.action} {entry.prefix}")
    for acl in acls.extended:
        lines.append(f"ip access-list extended {acl.name}")
        for entry in acl.entries:
            if entry.source_any and entry.destination_any and entry.protocol:
                lines.append(f" {entry.sequence} {entry.action} {entry.protocol} any any")
            else:
                lines.append(f" {entry.sequence} {entry.action}")
    return lines


def _prefix_list_lines(device: Device) -> list[str]:
    lines: list[str] = []
    for pl in device.configuration.prefix_lists:
        for seq in pl.seqs:
            line = f"ip prefix-list {pl.name} seq {seq.seq} {seq.action} {seq.prefix}"
            if seq.greater_equal is not None:
                line += f" ge {seq.greater_equal}"
            if seq.less_equal is not None:
                line += f" le {seq.less_equal}"
            lines.append(line)
    return lines


def _route_map_lines(device: Device) -> list[str]:
    lines: list[str] = []
    for rm in device.configuration.route_maps:
        for entry in rm.entries:
            operation = entry.operation or "permit"
            lines.append(f"route-map {rm.name} {operation} {entry.seq}")
            if entry.description:
                lines.append(f" description {entry.description}")
            if entry.match:
                for pl_name in entry.match.ipv4_address_prefix_lists:
                    lines.append(f" match ip address prefix-list {pl_name}")
                for acl_name in entry.match.ipv4_address_access_lists:
                    lines.append(f" match ip address {acl_name}")
            if entry.set:
                if entry.set.local_preference is not None:
                    lines.append(f" set local-preference {entry.set.local_preference}")
                if entry.set.metric_value is not None:
                    lines.append(f" set metric {entry.set.metric_value}")
    return lines


def _passive_iface_cli(passive: object) -> str:
    interface_type = getattr(passive, "interface_type", None)
    interface_id = getattr(passive, "interface_id", None)
    if interface_id:
        return f"{interface_type}{interface_id}"
    return interface_type or ""


def _routing_lines(device: Device) -> list[str]:
    lines: list[str] = []
    routing = device.configuration.routing
    for proc in routing.ospf_processes:
        lines.append(f"router ospf {proc.id}")
        router_id = getattr(proc, "router_id", None)
        if router_id:
            lines.append(f" router-id {router_id}")
        for net in getattr(proc, "networks", []) or []:
            wildcard = getattr(net, "wildcard", None) or "0.0.0.0"
            area = getattr(net, "area", None)
            area = area if area is not None else "0"
            lines.append(f" network {net.ip} {wildcard} area {area}")
        if getattr(proc, "passive_interface_default", None):
            lines.append(" passive-interface default")
        for passive in getattr(proc, "passive_interfaces", []) or []:
            iface_name = _passive_iface_cli(passive)
            if iface_name:
                lines.append(f" passive-interface {iface_name}")
    if routing.bgp:
        bgp = routing.bgp
        if bgp.as_number is not None:
            lines.append(f"router bgp {bgp.as_number}")
            for neighbor in getattr(bgp, "neighbors", []) or []:
                if getattr(neighbor, "remote_as", None) is not None:
                    lines.append(f" neighbor {neighbor.ip} remote-as {neighbor.remote_as}")
            address_family = getattr(bgp, "address_family", None)
            ipv4_unicast = getattr(address_family, "ipv4_unicast", None) if address_family else None
            ipv4_nets = getattr(ipv4_unicast, "networks", []) or [] if ipv4_unicast else []
            for net in ipv4_nets:
                mask = getattr(net, "mask", None) or "255.255.255.255"
                lines.append(f" network {net.network} mask {mask}")
    isis = routing.isis
    if isis and (getattr(isis, "area_tag", None) or getattr(isis, "nets", None) or getattr(isis, "is_type", None)):
        tag_suffix = f" {isis.area_tag}" if getattr(isis, "area_tag", None) else ""
        lines.append(f"router isis{tag_suffix}")
        for net in getattr(isis, "nets", []) or []:
            lines.append(f" net {net.tag}")
        if getattr(isis, "is_type", None):
            lines.append(f" is-type {isis.is_type}")
    return lines




def _services_lines(device: Device) -> list[str]:
    lines: list[str] = []
    config = device.configuration
    aaa = config.aaa
    if aaa and aaa.new_model:
        lines.append("aaa new-model")
    if aaa and aaa.authentication:
        for login in aaa.authentication.logins:
            lines.append(f"aaa authentication login {login.name} {' '.join(login.methods)}")
    if aaa and aaa.authorization:
        for authz in aaa.authorization.execs:
            lines.append(f"aaa authorization exec {authz.name} {' '.join(authz.methods)}")
    if aaa and aaa.accounting:
        for acct in aaa.accounting.execs:
            groups = " ".join(acct.start_stop_groups)
            action = acct.action_type or "start-stop"
            lines.append(f"aaa accounting login {acct.name} {action} group {groups}")
    snmp = config.snmp_server
    if snmp:
        for comm in snmp.snmp_communities:
            perm = f" {comm.permission}" if comm.permission else ""
            lines.append(f"snmp-server community {comm.name}{perm}")
        if snmp.contact:
            lines.append(f"snmp-server contact {snmp.contact}")
    ntp = config.ntp
    if ntp:
        for srv in ntp.servers:
            prefer = " prefer" if srv.prefer else ""
            lines.append(f"ntp server {srv.ip}{prefer}")
    if config.dhcp and config.dhcp.enabled:
        lines.append("service dhcp")
    for pool in config.dhcp_pools:
        lines.append(f"ip dhcp pool {pool.name}")
        if pool.network_number:
            mask = pool.network_mask or "255.255.255.0"
            lines.append(f" network {pool.network_number} {mask}")
        for router in pool.default_routers:
            lines.append(f" default-router {router}")
        for dns in pool.dns_servers:
            lines.append(f" dns-server {dns}")
    nat = config.nat
    if nat:
        for src in nat.inside_source_interfaces:
            for iface in src.interfaces:
                iname = f"{iface.interface_type}{iface.interface_id or ''}"
                overload = " overload" if iface.overload else ""
                lines.append(f"ip nat inside source list {src.id} interface {iname}{overload}")
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
    lines.extend(_access_list_lines(device))
    lines.extend(_prefix_list_lines(device))
    lines.extend(_route_map_lines(device))
    lines.extend(_vrf_lines(device))
    lines.extend(_routing_lines(device))
    lines.extend(_services_lines(device))
    for iface in device.interfaces:
        lines.extend(_iface_lines(iface))
    return "\n".join(lines) + ("\n" if lines else "")
