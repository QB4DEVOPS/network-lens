"""RESTCONF JSON generator (OpenConfig interfaces subset)."""

from __future__ import annotations

import json

from app.models import Device, Interface, Ipv6Address


def _ipv6_ip(addr: Ipv6Address) -> str:
    if addr.prefix_length is not None and "/" not in addr.prefix:
        return f"{addr.prefix}/{addr.prefix_length}"
    return addr.prefix


def _iface_json(iface: Interface) -> dict[str, object]:
    name = iface.name
    if iface.kind == "ethernet" and iface.ethernet_id:
        name = f"{iface.ethernet_type or 'GigabitEthernet'}{iface.ethernet_id}"
    elif iface.kind == "ethernet_subinterface" and iface.ethernet_id and iface.subinterface_id:
        name = f"{iface.ethernet_type or 'GigabitEthernet'}{iface.ethernet_id}.{iface.subinterface_id}"
    elif iface.kind == "port_channel" and iface.port_channel_id:
        name = f"Port-channel{iface.port_channel_id}"
    elif iface.kind == "port_channel_subinterface" and iface.port_channel_id and iface.subinterface_id:
        name = f"Port-channel{iface.port_channel_id}.{iface.subinterface_id}"
    elif iface.kind == "bdi" and iface.bdi_id:
        name = f"BDI{iface.bdi_id}"
    elif iface.kind == "nve" and iface.nve_id:
        name = f"nve{iface.nve_id}"

    subif_index = 0
    if iface.kind in {"ethernet_subinterface", "port_channel_subinterface"} and iface.subinterface_id:
        subif_index = int(iface.subinterface_id)

    entry: dict[str, object] = {
        "name": name,
        "config": {
            "name": name,
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
                    "index": subif_index,
                    "config": {"index": subif_index},
                    "openconfig-if-ip:ipv4": {"addresses": {"address": addresses}},
                }
            ]
        }

    if iface.has_ipv6:
        v6_addrs = [{"ip": _ipv6_ip(a), "config": {"ip": _ipv6_ip(a)}} for a in iface.ipv6_addresses]
        if v6_addrs:
            if "subinterfaces" not in entry:
                entry["subinterfaces"] = {
                    "subinterface": [{"index": subif_index, "config": {"index": subif_index}}]
                }
            sub = entry["subinterfaces"]["subinterface"][0]  # type: ignore[index]
            sub["openconfig-if-ip:ipv6"] = {"config": {"enabled": True}, "addresses": {"address": v6_addrs}}

    if iface.port_channel_id and iface.kind == "ethernet":
        entry["openconfig-if-aggregate:aggregation"] = {"config": {"lag-type": "LACP", "min-links": 1}}
        entry["config"]["port-channel-id"] = int(iface.port_channel_id)  # type: ignore[index]

    if iface.vrf_forwarding:
        entry["openconfig-network-instance:bind-ni-name"] = iface.vrf_forwarding

    if iface.kind == "tunnel":
        overlay: dict[str, object] = {}
        if iface.tunnel_source:
            overlay["tunnel_source"] = iface.tunnel_source
        if iface.tunnel_destination_ipv4:
            overlay["tunnel_destination_ipv4"] = iface.tunnel_destination_ipv4
        if iface.tunnel_mode_gre_multipoint is not None:
            overlay["tunnel_mode_gre_multipoint"] = iface.tunnel_mode_gre_multipoint
        if iface.tunnel_mode_ipsec_ipv4 is not None:
            overlay["tunnel_mode_ipsec_ipv4"] = iface.tunnel_mode_ipsec_ipv4
        if iface.tunnel_key is not None:
            overlay["tunnel_key"] = iface.tunnel_key
        if iface.tunnel_protection_ipsec_profile:
            overlay["tunnel_protection_ipsec_profile"] = iface.tunnel_protection_ipsec_profile
        if iface.ip_nhrp_authentication is not None:
            overlay["ip_nhrp_authentication"] = iface.ip_nhrp_authentication
        if iface.ip_nhrp_network_id is not None:
            overlay["ip_nhrp_network_id"] = iface.ip_nhrp_network_id
        if iface.ip_nhrp_nhs:
            overlay["ip_nhrp_nhs"] = [{"ipv4": nhs.ipv4} for nhs in iface.ip_nhrp_nhs]
        if iface.ip_nhrp_maps:
            overlay["ip_nhrp_maps"] = [
                {"dest_ipv4": item.dest_ipv4, "nbma_ipv4": item.nbma_ipv4} for item in iface.ip_nhrp_maps
            ]
        if iface.ip_nhrp_redirect is not None:
            overlay["ip_nhrp_redirect"] = iface.ip_nhrp_redirect
        if iface.ip_nhrp_shortcut is not None:
            overlay["ip_nhrp_shortcut"] = iface.ip_nhrp_shortcut
        if iface.mpls_nhrp is not None:
            overlay["mpls_nhrp"] = iface.mpls_nhrp
        if overlay:
            entry["tunnel"] = overlay

    return entry


def _policy_native(config) -> dict[str, object]:
    native: dict[str, object] = {}
    if config.vrfs:
        vrf_defs: list[dict[str, object]] = []
        for vrf in config.vrfs:
            entry: dict[str, object] = {"name": vrf.name}
            if vrf.description:
                entry["description"] = vrf.description
            if vrf.route_distinguisher:
                entry["rd"] = vrf.route_distinguisher
            if vrf.address_family_ipv4:
                af4: dict[str, object] = {}
                if vrf.address_family_ipv4.import_route_targets:
                    af4["route-target"] = {
                        "import": [{"rt-value": rt} for rt in vrf.address_family_ipv4.import_route_targets]
                    }
                if vrf.address_family_ipv4.export_route_targets:
                    af4.setdefault("route-target", {})
                    af4["route-target"]["export"] = [  # type: ignore[index]
                        {"rt-value": rt} for rt in vrf.address_family_ipv4.export_route_targets
                    ]
                if af4:
                    entry["address-family"] = {"ipv4": af4}
            vrf_defs.append(entry)
        native["vrf"] = {"definition": vrf_defs}
    if config.prefix_lists:
        pl_entries: list[dict[str, object]] = []
        for pl in config.prefix_lists:
            for seq in pl.seqs:
                pl_entry: dict[str, object] = {
                    "name": pl.name,
                    "seq": seq.seq,
                    "action": seq.action,
                    "prefix": seq.prefix,
                }
                if seq.less_equal is not None:
                    pl_entry["le"] = seq.less_equal
                if seq.greater_equal is not None:
                    pl_entry["ge"] = seq.greater_equal
                pl_entries.append(pl_entry)
        native["ip"] = {"prefix-list": pl_entries}
    if config.route_maps:
        rm_entries: list[dict[str, object]] = []
        for rm in config.route_maps:
            for entry in rm.entries:
                rm_entry: dict[str, object] = {
                    "name": rm.name,
                    "seq": entry.seq,
                    "operation": entry.operation,
                }
                if entry.match and entry.match.ipv4_address_prefix_lists:
                    rm_entry["match"] = {
                        "ip": {"address": {"prefix-list": entry.match.ipv4_address_prefix_lists[0]}}
                    }
                if entry.set and entry.set.local_preference is not None:
                    rm_entry["set"] = {"local-preference": entry.set.local_preference}
                rm_entries.append(rm_entry)
        native["route-map"] = rm_entries
    if config.access_lists and not config.section_is_empty("access_lists"):
        acl_entries: list[dict[str, object]] = []
        for acl in config.access_lists.standard:
            acl_entries.append({"name": acl.name, "type": "standard", "entries": len(acl.entries)})
        for acl in config.access_lists.extended:
            acl_entries.append({"name": acl.name, "type": "extended", "entries": len(acl.entries)})
        native.setdefault("ip", {})
        native["ip"]["access-list"] = acl_entries  # type: ignore[index]
    return native


def _routing_native(device: Device) -> dict[str, object] | None:
    routing = device.configuration.routing
    router: dict[str, object] = {}
    if routing.ospf_processes:
        ospf_list: list[dict[str, object]] = []
        for proc in routing.ospf_processes:
            entry: dict[str, object] = {"id": proc.id}
            if proc.router_id:
                entry["router-id"] = proc.router_id
            if proc.networks:
                entry["network"] = [
                    {
                        "ip": net.ip,
                        "wildcard": net.wildcard,
                        "area": net.area,
                    }
                    for net in proc.networks
                ]
            if proc.passive_interface_default:
                entry["passive-interface-default"] = True
            if proc.passive_interfaces:
                entry["passive-interface"] = [
                    f"{pi.interface_type}{pi.interface_id or ''}"
                    for pi in proc.passive_interfaces
                ]
            ospf_list.append(entry)
        router["router-ospf"] = {"ospf": {"process-id": ospf_list}}
    if routing.bgp:
        bgp = routing.bgp
        bgp_entry: dict[str, object] = {}
        if bgp.as_number is not None:
            bgp_entry["as-no"] = bgp.as_number
        if bgp.neighbors:
            bgp_entry["neighbor"] = [
                {"id": n.ip, "remote-as": n.remote_as} for n in bgp.neighbors
            ]
        ipv4_nets = (
            bgp.address_family.ipv4_unicast.networks
            if bgp.address_family and bgp.address_family.ipv4_unicast
            else []
        )
        if ipv4_nets:
            bgp_entry["network"] = [
                {"number": net.network, "mask": net.mask} for net in ipv4_nets
            ]
        if bgp_entry:
            router["router-bgp"] = {"bgp": bgp_entry}
    if routing.isis and (routing.isis.area_tag or routing.isis.nets or routing.isis.is_type):
        isis = routing.isis
        isis_entry: dict[str, object] = {}
        if isis.area_tag:
            isis_entry["tag"] = isis.area_tag
        if isis.nets:
            isis_entry["net"] = [{"tag": net.tag} for net in isis.nets]
        if isis.is_type:
            isis_entry["is-type"] = isis.is_type
        router["router-isis"] = {"isis": isis_entry}
    if routing.eigrp_processes:
        eigrp_entries: list[dict[str, object]] = []
        for proc in routing.eigrp_processes:
            entry: dict[str, object] = {"name": proc.name}
            if proc.autonomous_system is not None:
                entry["autonomous_system"] = proc.autonomous_system
            if proc.vrf:
                entry["vrf"] = proc.vrf
            if proc.router_id:
                entry["router_id"] = proc.router_id
            if proc.networks:
                entry["networks"] = [{"ip": net.ip, "wildcard": net.wildcard} for net in proc.networks]
            if proc.auto_summary is not None:
                entry["auto_summary"] = proc.auto_summary
            if proc.shutdown is not None:
                entry["shutdown"] = proc.shutdown
            eigrp_entries.append(entry)
        router["eigrp_processes"] = eigrp_entries
    return router or None


def generate_restconf_json(device: Device) -> str:
    hostname = device.system.hostname or device.name
    config = device.configuration
    native: dict[str, object] = {
        "hostname": hostname,
        "ipv6": {"unicast-routing": device.system.ipv6_unicast_routing},
    }
    if device.system.mtu is not None:
        native["mtu"] = device.system.mtu
    if device.system.ip_domain_name:
        native["ip"] = {"domain-name": device.system.ip_domain_name}
    if config.users:
        native["username"] = [
            {
                "name": user.name,
                **({"privilege": {"level": user.privilege}} if user.privilege is not None else {}),
                **({"secret": user.secret} if user.secret is not None else {}),
                **({"password": user.password} if user.password is not None else {}),
            }
            for user in config.users
        ]
    if config.banner and not config.section_is_empty("banner"):
        banner_native: dict[str, str] = {}
        if config.banner.motd:
            banner_native["motd"] = config.banner.motd
        if config.banner.login:
            banner_native["login"] = config.banner.login
        if config.banner.exec:
            banner_native["exec"] = config.banner.exec
        if banner_native:
            native["banner"] = banner_native
    if config.clock and not config.section_is_empty("clock"):
        clock_native: dict[str, object] = {}
        if config.clock.timezone:
            clock_native["timezone"] = config.clock.timezone
        if config.clock.timezone_offset_hours is not None:
            clock_native["timezone-offset-hours"] = config.clock.timezone_offset_hours
        if config.clock.summer_time_zone:
            clock_native["summer-time-zone"] = config.clock.summer_time_zone
        if clock_native:
            native["clock"] = clock_native
    if config.aaa and not config.section_is_empty("aaa"):
        aaa_native: dict[str, object] = {}
        if config.aaa.new_model:
            aaa_native["new-model"] = True
        native["aaa"] = aaa_native
    if config.snmp_server and not config.section_is_empty("snmp_server"):
        snmp_native: dict[str, object] = {}
        if config.snmp_server.contact:
            snmp_native["contact"] = config.snmp_server.contact
        if config.snmp_server.snmp_communities:
            snmp_native["community"] = [
                {"name": c.name, "permission": c.permission}
                for c in config.snmp_server.snmp_communities
            ]
        native["snmp-server"] = snmp_native
    if config.ntp and not config.section_is_empty("ntp"):
        ntp_native: dict[str, object] = {}
        if config.ntp.servers:
            ntp_native["server"] = [
                {"ip-address": s.ip, "prefer": s.prefer, **({"vrf": s.vrf} if s.vrf else {})}
                for s in config.ntp.servers
            ]
        if config.ntp.peers:
            ntp_native["peer"] = [
                {"ip-address": p.ip, "prefer": p.prefer, **({"vrf": p.vrf} if p.vrf else {})}
                for p in config.ntp.peers
            ]
        native["ntp"] = ntp_native
    if config.dhcp and config.dhcp.enabled:
        native["service"] = {"dhcp": True}
    if config.dhcp_pools:
        ip_block = native.get("ip")
        if not isinstance(ip_block, dict):
            ip_block = {}
        ip_block["dhcp"] = {
            "pool": [
                {
                    "name": p.name,
                    **(
                        {"network": {"number": p.network_number, "mask": p.network_mask}}
                        if p.network_number
                        else {}
                    ),
                }
                for p in config.dhcp_pools
            ]
        }
        native["ip"] = ip_block
    if config.nat and not config.section_is_empty("nat"):
        nat_entries = []
        for src in config.nat.inside_source_interfaces:
            for iface in src.interfaces:
                nat_entries.append(
                    {
                        "id": src.id,
                        "interface": f"{iface.interface_type}{iface.interface_id or ''}",
                        "overload": iface.overload,
                    }
                )
        if nat_entries:
            ip_block = native.get("ip")
            if not isinstance(ip_block, dict):
                ip_block = {}
            ip_block["nat"] = {"inside": {"source": {"list": nat_entries}}}
            native["ip"] = ip_block
    payload = {
        "_network_lens_preview": {
            "generated": "Not applied",
            "dialect": "RESTCONF JSON (OpenConfig interfaces + IOS-XE native subset)",
            "nac_path": "iosxe.devices[].configuration → ietf-interfaces + Cisco-IOS-XE-native",
        },
        "ietf-interfaces:interfaces": {
            "interface": [_iface_json(i) for i in device.interfaces]
        },
        "Cisco-IOS-XE-native:native": native,
    }
    router_native = _routing_native(device)
    if router_native:
        payload["Cisco-IOS-XE-native:native"]["router"] = router_native  # type: ignore[index]
    policy_native = _policy_native(config)
    if policy_native:
        for key, value in policy_native.items():
            if key in native and isinstance(native[key], dict) and isinstance(value, dict):
                native[key] = {**native[key], **value}  # type: ignore[arg-type]
            else:
                native[key] = value
    return json.dumps(payload, indent=2) + "\n"
