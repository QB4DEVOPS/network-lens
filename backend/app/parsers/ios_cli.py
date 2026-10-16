"""IOS CLI line parser with abbreviation support."""

from __future__ import annotations

import re

from app.parsers.crypto_cli import CryptoParseState, parse_crypto_line
from app import field_keys as fk
from app.models import (
    AaaAccountingConfig,
    AaaAccountingExec,
    AaaAuthLogin,
    AaaAuthenticationConfig,
    AaaAuthorizationConfig,
    AaaAuthzExec,
    AaaConfig,
    AccessListAce,
    AccessListsConfig,
    BannerConfig,
    BgpAddressFamily,
    BgpAddressFamilyIpv4Unicast,
    BgpConfig,
    BgpNeighbor,
    BgpNetwork,
    ClockConfig,
    CliFieldRef,
    Device,
    EigrpNetwork,
    EigrpProcess,
    ExtendedAccessList,
    Interface,
    Ipv6Address,
    IsisConfig,
    IsisNet,
    NhrpMap,
    NhrpNhs,
    OspfNetwork,
    OspfPassiveInterface,
    OspfProcess,
    ParseResult,
    ParseWarning,
    PrefixList,
    PrefixListSeq,
    RouteMap,
    RouteMapEntry,
    RouteMapMatch,
    RouteMapSet,
    StandardAccessList,
    DhcpConfig,
    DhcpPool,
    NatConfig,
    NatInsideInterface,
    NatInsideSource,
    NtpConfig,
    NtpServer,
    SnmpCommunity,
    SnmpServerConfig,
    StaticRoute,
    UserAccount,
    Vrf,
    VrfAddressFamily,
)

ABBREVS: dict[str, str] = {
    "hostn": "hostname",
    "int": "interface",
    "no sh": "no shutdown",
    "ip add": "ip address",
    "ipv6 add": "ipv6 address",
}

INTERFACE_ALIASES: dict[str, tuple[str, str]] = {
    "lo0": ("loopback", "Loopback0"),
    "lo1": ("loopback", "Loopback1"),
    "lo2": ("loopback", "Loopback2"),
    "lo3": ("loopback", "Loopback3"),
}


def expand_abbreviations(line: str) -> str:
    """Expand known CLI abbreviations anywhere in the line (repeat until stable)."""
    result = line.strip()
    if not result:
        return result

    changed = True
    while changed:
        changed = False
        lower = result.lower()
        for abbrev, full in sorted(ABBREVS.items(), key=lambda x: -len(x[0])):
            if lower.startswith(abbrev) and (len(lower) == len(abbrev) or lower[len(abbrev)] == " "):
                remainder = result[len(abbrev) :].lstrip()
                result = f"{full} {remainder}".rstrip() if remainder else full
                changed = True
                break

            needle = " " + abbrev
            idx = lower.find(needle)
            if idx != -1:
                end = idx + len(needle)
                if end == len(lower) or lower[end] == " ":
                    before = result[: idx + 1]
                    after = result[end:].lstrip()
                    result = f"{before}{full} {after}".rstrip() if after else f"{before}{full}"
                    changed = True
                    break
    return result


def normalize_interface_token(token: str) -> Interface | None:
    """Return an Interface stub for tokens like lo0, g0/0/0, tun10."""
    token = token.strip()
    lower = token.lower()

    if lower in INTERFACE_ALIASES:
        kind, name = INTERFACE_ALIASES[lower]
        loopback_id = name.replace("Loopback", "")
        return Interface(name=name, kind=kind, loopback_id=loopback_id, shutdown=True)

    lo_match = re.match(r"^lo(\d+)$", lower)
    if lo_match:
        num = lo_match.group(1)
        return Interface(name=f"Loopback{num}", kind="loopback", loopback_id=num, shutdown=True)

    lo_spaced = re.match(r"^lo\s+(\d+)$", lower)
    if lo_spaced:
        num = lo_spaced.group(1)
        return Interface(name=f"Loopback{num}", kind="loopback", loopback_id=num, shutdown=True)

    loopback_match = re.match(r"^loopback\s+(\d+)$", lower, re.IGNORECASE)
    if loopback_match:
        num = loopback_match.group(1)
        return Interface(name=f"Loopback{num}", kind="loopback", loopback_id=num, shutdown=True)

    vlan_short = re.match(r"^vlan(\d+)$", lower)
    if vlan_short:
        num = vlan_short.group(1)
        return Interface(name=f"Vlan{num}", kind="vlan", vlan_id=num, shutdown=True)

    vlan_spaced = re.match(r"^vlan\s+(\d+)$", lower)
    if vlan_spaced:
        num = vlan_spaced.group(1)
        return Interface(name=f"Vlan{num}", kind="vlan", vlan_id=num, shutdown=True)

    po_sub = re.match(r"^po(\d+)\.(\d+)$", lower)
    if po_sub:
        pc_id, sub_id = po_sub.group(1), po_sub.group(2)
        return Interface(
            name=f"Port-channel{pc_id}.{sub_id}",
            kind="port_channel_subinterface",
            port_channel_id=pc_id,
            subinterface_id=sub_id,
            shutdown=True,
        )

    po_sub_spaced = re.match(r"^po\s+(\d+)\.(\d+)$", lower)
    if po_sub_spaced:
        pc_id, sub_id = po_sub_spaced.group(1), po_sub_spaced.group(2)
        return Interface(
            name=f"Port-channel{pc_id}.{sub_id}",
            kind="port_channel_subinterface",
            port_channel_id=pc_id,
            subinterface_id=sub_id,
            shutdown=True,
        )

    gi_sub3 = re.match(r"^g(\d+)/(\d+)/(\d+)\.(\d+)$", lower)
    if gi_sub3:
        eid = f"{gi_sub3.group(1)}/{gi_sub3.group(2)}/{gi_sub3.group(3)}"
        sub_id = gi_sub3.group(4)
        return Interface(
            name=f"GigabitEthernet{eid}.{sub_id}",
            kind="ethernet_subinterface",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            subinterface_id=sub_id,
            shutdown=True,
        )

    gi_sub3_spaced = re.match(r"^g\s+(\d+/\d+/\d+)\.(\d+)$", lower)
    if gi_sub3_spaced:
        eid, sub_id = gi_sub3_spaced.group(1), gi_sub3_spaced.group(2)
        return Interface(
            name=f"GigabitEthernet{eid}.{sub_id}",
            kind="ethernet_subinterface",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            subinterface_id=sub_id,
            shutdown=True,
        )

    gi_sub2 = re.match(r"^g(\d+)/(\d+)\.(\d+)$", lower)
    if gi_sub2:
        eid = f"{gi_sub2.group(1)}/{gi_sub2.group(2)}"
        sub_id = gi_sub2.group(3)
        return Interface(
            name=f"GigabitEthernet{eid}.{sub_id}",
            kind="ethernet_subinterface",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            subinterface_id=sub_id,
            shutdown=True,
        )

    gi_sub2_spaced = re.match(r"^g\s+(\d+/\d+)\.(\d+)$", lower)
    if gi_sub2_spaced:
        eid, sub_id = gi_sub2_spaced.group(1), gi_sub2_spaced.group(2)
        return Interface(
            name=f"GigabitEthernet{eid}.{sub_id}",
            kind="ethernet_subinterface",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            subinterface_id=sub_id,
            shutdown=True,
        )

    po_short = re.match(r"^po(\d+)$", lower)
    if po_short:
        num = po_short.group(1)
        return Interface(
            name=f"Port-channel{num}",
            kind="port_channel",
            port_channel_id=num,
            shutdown=True,
        )

    po_spaced = re.match(r"^po\s+(\d+)$", lower)
    if po_spaced:
        num = po_spaced.group(1)
        return Interface(
            name=f"Port-channel{num}",
            kind="port_channel",
            port_channel_id=num,
            shutdown=True,
        )

    po_full = re.match(r"^port-channel\s*(\d+)$", lower)
    if po_full:
        num = po_full.group(1)
        return Interface(
            name=f"Port-channel{num}",
            kind="port_channel",
            port_channel_id=num,
            shutdown=True,
        )

    bdi_short = re.match(r"^bdi(\d+)$", lower)
    if bdi_short:
        num = bdi_short.group(1)
        return Interface(name=f"BDI{num}", kind="bdi", bdi_id=num, shutdown=True)

    bdi_spaced = re.match(r"^bdi\s+(\d+)$", lower)
    if bdi_spaced:
        num = bdi_spaced.group(1)
        return Interface(name=f"BDI{num}", kind="bdi", bdi_id=num, shutdown=True)

    nve_short = re.match(r"^nve(\d+)$", lower)
    if nve_short:
        num = nve_short.group(1)
        return Interface(name=f"nve{num}", kind="nve", nve_id=num, shutdown=True)

    nve_spaced = re.match(r"^nve\s+(\d+)$", lower)
    if nve_spaced:
        num = nve_spaced.group(1)
        return Interface(name=f"nve{num}", kind="nve", nve_id=num, shutdown=True)

    gi_short = re.match(r"^g(\d+)/(\d+)/(\d+)$", lower)
    if gi_short:
        eid = f"{gi_short.group(1)}/{gi_short.group(2)}/{gi_short.group(3)}"
        return Interface(
            name=f"GigabitEthernet{eid}",
            kind="ethernet",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            shutdown=True,
        )

    gi_short2 = re.match(r"^g(\d+)/(\d+)$", lower)
    if gi_short2:
        eid = f"{gi_short2.group(1)}/{gi_short2.group(2)}"
        return Interface(
            name=f"GigabitEthernet{eid}",
            kind="ethernet",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            shutdown=True,
        )

    gi_spaced3 = re.match(r"^g\s+(\d+/\d+/\d+)$", lower)
    if gi_spaced3:
        eid = gi_spaced3.group(1)
        return Interface(
            name=f"GigabitEthernet{eid}",
            kind="ethernet",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            shutdown=True,
        )

    gi_spaced2 = re.match(r"^g\s+(\d+/\d+)$", lower)
    if gi_spaced2:
        eid = gi_spaced2.group(1)
        return Interface(
            name=f"GigabitEthernet{eid}",
            kind="ethernet",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            shutdown=True,
        )

    gi_full = re.match(r"^gigabitethernet(\d+/\d+(?:/\d+)?)$", lower)
    if gi_full:
        eid = gi_full.group(1)
        return Interface(
            name=f"GigabitEthernet{eid}",
            kind="ethernet",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            shutdown=True,
        )

    gi_full_spaced = re.match(r"^gigabitethernet\s+(\d+/\d+(?:/\d+)?)$", lower)
    if gi_full_spaced:
        eid = gi_full_spaced.group(1)
        return Interface(
            name=f"GigabitEthernet{eid}",
            kind="ethernet",
            ethernet_type="GigabitEthernet",
            ethernet_id=eid,
            shutdown=True,
        )

    tunnel_glued = re.match(r"^tunnel(\d+)$", lower)
    if tunnel_glued:
        num = tunnel_glued.group(1)
        return Interface(
            name=f"Tunnel{num}",
            kind="tunnel",
            tunnel_id=num,
            shutdown=True,
        )

    tun_short = re.match(r"^tun(\d+)$", lower)
    if tun_short:
        num = tun_short.group(1)
        return Interface(
            name=f"Tunnel{num}",
            kind="tunnel",
            tunnel_id=num,
            shutdown=True,
        )

    tun_spaced = re.match(r"^tun\s+(\d+)$", lower)
    if tun_spaced:
        num = tun_spaced.group(1)
        return Interface(
            name=f"Tunnel{num}",
            kind="tunnel",
            tunnel_id=num,
            shutdown=True,
        )

    tunnel_match = re.match(r"^tunnel\s+(\d+)$", lower, re.IGNORECASE)
    if tunnel_match:
        num = tunnel_match.group(1)
        return Interface(
            name=f"Tunnel{num}",
            kind="tunnel",
            tunnel_id=num,
            shutdown=True,
        )

    return None


def _parse_ip_address_line(line: str, iface: Interface) -> None:
    """Parse 'ip address ...' into interface ipv4 fields."""
    lower = line.lower()
    if not lower.startswith("ip address "):
        return

    remainder = line[len("ip address ") :].strip()
    while remainder.lower().startswith("ip address "):
        remainder = remainder[len("ip address ") :].strip()

    if not remainder:
        return

    parts = remainder.split()
    if len(parts) == 1 and parts[0].lower() == "dhcp":
        iface.ipv4_dhcp = True
        iface.ipv4_address = None
        iface.ipv4_address_mask = None
        return

    if len(parts) >= 2:
        iface.ipv4_dhcp = False
        iface.ipv4_address = parts[0]
        iface.ipv4_address_mask = parts[1]


def _parse_ipv6_address_line(line: str, iface: Interface) -> None:
    """Parse 'ipv6 address ...' into interface ipv6 fields."""
    lower = line.lower()
    if not lower.startswith("ipv6 address "):
        return

    remainder = line[len("ipv6 address ") :].strip()
    while remainder.lower().startswith("ipv6 address "):
        remainder = remainder[len("ipv6 address ") :].strip()

    if not remainder:
        return

    token_lower = remainder.lower()
    if token_lower == "dhcp":
        iface.ipv6_dhcp = True
        iface.ipv6_enable = True
        return

    if token_lower in {"autoconfig", "auto"}:
        iface.ipv6_autoconfig = True
        iface.ipv6_enable = True
        return

    parts = remainder.split()
    eui_64 = False
    link_local = False

    while parts:
        tail = parts[-1].lower()
        if tail in {"eui-64", "eui64"}:
            eui_64 = True
            parts.pop()
            continue
        if tail in {"link-local", "link"}:
            link_local = True
            parts.pop()
            continue
        break

    if not parts:
        return

    if not link_local and len(parts) >= 2 and parts[-2].lower() == "link" and parts[-1].lower() == "local":
        link_local = True
        parts = parts[:-2]

    addr_token = parts[0]
    prefix_length: int | None = None
    prefix = addr_token

    if "/" in addr_token:
        prefix, plen_str = addr_token.rsplit("/", 1)
        if plen_str.isdigit():
            prefix_length = int(plen_str)
    elif len(parts) >= 2 and parts[1].isdigit():
        prefix_length = int(parts[1])

    iface.ipv6_enable = True

    if link_local:
        iface.ipv6_link_local_addresses.append(prefix)
        return

    iface.ipv6_addresses.append(Ipv6Address(prefix=prefix, prefix_length=prefix_length, eui_64=eui_64))


def _upsert_user(device: Device, user: UserAccount) -> None:
    for idx, existing in enumerate(device.configuration.users):
        if existing.name == user.name:
            device.configuration.users[idx] = user
            return
    device.configuration.users.append(user)


def _parse_username_line(line: str) -> UserAccount | None:
    lower = line.lower()
    if not lower.startswith("username "):
        return None
    parts = line.split()
    if len(parts) < 3:
        return None
    name = parts[1]
    privilege: int | None = None
    secret: str | None = None
    secret_type: str | None = None
    password: str | None = None
    password_type: str | None = None
    idx = 2
    while idx < len(parts):
        token = parts[idx].lower()
        if token == "privilege" and idx + 1 < len(parts) and parts[idx + 1].isdigit():
            privilege = int(parts[idx + 1])
            idx += 2
        elif token == "secret":
            idx += 1
            if idx < len(parts) and parts[idx].isdigit():
                secret_type = parts[idx]
                idx += 1
            if idx < len(parts):
                secret = parts[idx]
                idx += 1
        elif token == "password":
            idx += 1
            if idx < len(parts) and parts[idx].isdigit():
                password_type = parts[idx]
                idx += 1
            if idx < len(parts):
                password = parts[idx]
                idx += 1
        else:
            idx += 1
    if secret is None and password is None:
        return None
    return UserAccount(
        name=name,
        privilege=privilege,
        secret=secret,
        secret_type=secret_type,
        password=password,
        password_type=password_type,
    )


def _parse_enable_credential(line: str) -> tuple[str, str, str | None] | None:
    """Return (kind, value, enc_type) where kind is ``secret`` or ``password``."""
    lower = line.lower()
    if lower.startswith("enable secret "):
        kind = "secret"
        rest = line[len("enable secret ") :].strip()
    elif lower.startswith("enable password "):
        kind = "password"
        rest = line[len("enable password ") :].strip()
    else:
        return None
    parts = rest.split(None, 1)
    enc_type: str | None = None
    if parts and parts[0].isdigit():
        enc_type = parts[0]
        value = parts[1].strip() if len(parts) > 1 else ""
    else:
        value = rest
    if not value:
        return None
    return kind, value, enc_type


_BANNER_START = re.compile(r"^banner\s+(motd|login|exec)\s+(.)(.*)$", re.IGNORECASE)


def _parse_banner_start(line: str) -> tuple[str, str, str, bool] | None:
    match = _BANNER_START.match(line.strip())
    if not match:
        return None
    kind = match.group(1).lower()
    delim = match.group(2)
    rest = match.group(3)
    close_idx = rest.find(delim)
    if close_idx != -1:
        return kind, delim, rest[:close_idx], True
    return kind, delim, rest, False


def _set_banner_text(device: Device, kind: str, text: str) -> None:
    banner = device.configuration.banner or BannerConfig()
    if kind == "motd":
        banner.motd = text
    elif kind == "login":
        banner.login = text
    elif kind == "exec":
        banner.exec = text
    device.configuration.banner = banner


def _looks_like_mask(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _mask_to_prefixlen(mask: str) -> int:
    bits = "".join(f"{int(octet):08b}" for octet in mask.split("."))
    return bits.count("1")


def _get_vrf(device: Device, name: str) -> Vrf:
    for vrf in device.configuration.vrfs:
        if vrf.name == name:
            return vrf
    vrf = Vrf(name=name)
    device.configuration.vrfs.append(vrf)
    return vrf


def _get_vrf_af(vrf: Vrf, family: str) -> VrfAddressFamily:
    if family == "ipv4":
        if vrf.address_family_ipv4 is None:
            vrf.address_family_ipv4 = VrfAddressFamily(enable=True)
        return vrf.address_family_ipv4
    if vrf.address_family_ipv6 is None:
        vrf.address_family_ipv6 = VrfAddressFamily(enable=True)
    return vrf.address_family_ipv6


def _ensure_access_lists(device: Device) -> AccessListsConfig:
    if device.configuration.access_lists is None:
        device.configuration.access_lists = AccessListsConfig()
    return device.configuration.access_lists


def _get_standard_acl(device: Device, name: str) -> StandardAccessList:
    acls = _ensure_access_lists(device)
    for acl in acls.standard:
        if acl.name == name:
            return acl
    acl = StandardAccessList(name=name)
    acls.standard.append(acl)
    return acl


def _get_extended_acl(device: Device, name: str) -> ExtendedAccessList:
    acls = _ensure_access_lists(device)
    for acl in acls.extended:
        if acl.name == name:
            return acl
    acl = ExtendedAccessList(name=name)
    acls.extended.append(acl)
    return acl


def _parse_standard_ace(sequence: int, action: str, remainder: str) -> AccessListAce:
    parts = remainder.split()
    if not parts or parts[0].lower() == "any":
        return AccessListAce(sequence=sequence, action=action, prefix="any")
    prefix = parts[0]
    prefix_mask = parts[1] if len(parts) > 1 else None
    return AccessListAce(sequence=sequence, action=action, prefix=prefix, prefix_mask=prefix_mask)


def _parse_extended_ace(sequence: int, action: str, remainder: str) -> AccessListAce:
    parts = remainder.split()
    if len(parts) >= 4 and parts[0].lower() == "ip" and parts[1].lower() == "any" and parts[2].lower() == "any":
        return AccessListAce(
            sequence=sequence,
            action=action,
            protocol="ip",
            source_any=True,
            destination_any=True,
        )
    if len(parts) >= 3 and parts[-2].lower() == "any" and parts[-1].lower() == "any":
        return AccessListAce(
            sequence=sequence,
            action=action,
            protocol=parts[0],
            source_any=True,
            destination_any=True,
        )
    return AccessListAce(sequence=sequence, action=action, protocol=parts[0] if parts else None)


def _get_prefix_list(device: Device, name: str) -> PrefixList:
    for pl in device.configuration.prefix_lists:
        if pl.name == name:
            return pl
    pl = PrefixList(name=name)
    device.configuration.prefix_lists.append(pl)
    return pl


def _parse_prefix_list_line(line: str, device: Device) -> PrefixList | None:
    match = re.match(
        r"^ip prefix-list\s+(\S+)\s+(?:seq\s+)?(\d+)\s+(permit|deny)\s+(\S+)(?:\s+ge\s+(\d+))?(?:\s+le\s+(\d+))?$",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None
    name, seq_str, action, prefix, ge, le = match.groups()
    pl = _get_prefix_list(device, name)
    pl.seqs.append(
        PrefixListSeq(
            seq=int(seq_str),
            action=action.lower(),
            prefix=prefix,
            greater_equal=int(ge) if ge else None,
            less_equal=int(le) if le else None,
        )
    )
    return pl


def _get_route_map(device: Device, name: str) -> RouteMap:
    for rm in device.configuration.route_maps:
        if rm.name == name:
            return rm
    rm = RouteMap(name=name)
    device.configuration.route_maps.append(rm)
    return rm


def _interface_token_to_passive(token: str) -> OspfPassiveInterface:
    parsed = normalize_interface_token(token)
    if parsed:
        if parsed.kind == "ethernet":
            return OspfPassiveInterface(
                interface_type=parsed.ethernet_type or "GigabitEthernet",
                interface_id=parsed.ethernet_id,
            )
        if parsed.kind == "loopback":
            return OspfPassiveInterface(interface_type="Loopback", interface_id=parsed.loopback_id)
        if parsed.kind == "vlan":
            return OspfPassiveInterface(interface_type="Vlan", interface_id=parsed.vlan_id)
        if parsed.kind == "tunnel":
            return OspfPassiveInterface(interface_type="Tunnel", interface_id=parsed.tunnel_id)
        if parsed.kind == "port_channel":
            return OspfPassiveInterface(interface_type="PortChannel", interface_id=parsed.port_channel_id)
    return OspfPassiveInterface(interface_type=token, interface_id=None)


def _get_ospf_process(device: Device, proc_id: str | int) -> OspfProcess:
    routing = device.configuration.routing
    for proc in routing.ospf_processes:
        if str(proc.id) == str(proc_id):
            return proc
    proc = OspfProcess(id=int(proc_id) if str(proc_id).isdigit() else proc_id)
    routing.ospf_processes.append(proc)
    return proc


def _get_bgp(device: Device) -> BgpConfig:
    routing = device.configuration.routing
    if routing.bgp is None:
        routing.bgp = BgpConfig()
    return routing.bgp


def _ensure_bgp_ipv4_networks(bgp: BgpConfig) -> list[BgpNetwork]:
    if bgp.address_family is None:
        bgp.address_family = BgpAddressFamily()
    if bgp.address_family.ipv4_unicast is None:
        bgp.address_family.ipv4_unicast = BgpAddressFamilyIpv4Unicast()
    return bgp.address_family.ipv4_unicast.networks


_EIGRP_IPV4_AF = re.compile(
    r"^address-family\s+ipv4(?:\s+unicast)?"
    r"(?:\s+vrf\s+(?P<vrf_before>\S+))?"
    r"\s+autonomous-system\s+(?P<asn>\d+)"
    r"(?:\s+vrf\s+(?P<vrf_after>\S+))?$",
    re.IGNORECASE,
)

_EIGRP_ASN_MIN = 1
_EIGRP_ASN_MAX = 65535
_TUNNEL_KEY_MAX = 4294967295


def _parse_warning(warnings: list[ParseWarning], line_num: int, raw_line: str, message: str) -> None:
    warnings.append(ParseWarning(line=line_num, message=message, cli_line=raw_line.strip()))


def _get_eigrp_process(
    device: Device,
    name: str,
    autonomous_system: int,
    vrf: str | None,
    *,
    classic: bool,
) -> EigrpProcess:
    routing = device.configuration.routing
    for proc in routing.eigrp_processes:
        if proc.name == name and (proc.vrf or None) == (vrf or None):
            if proc.autonomous_system is None:
                proc.autonomous_system = autonomous_system
            return proc
    proc = EigrpProcess(
        name=name,
        autonomous_system=autonomous_system,
        vrf=vrf,
        classic=classic,
    )
    routing.eigrp_processes.append(proc)
    return proc


def _parse_eigrp_ipv4_af(line: str) -> tuple[int, str | None] | None:
    match = _EIGRP_IPV4_AF.match(line.strip())
    if not match:
        return None
    vrf = match.group("vrf_before") or match.group("vrf_after")
    return int(match.group("asn")), vrf


def _warn_eigrp_omitted(line: str, line_num: int, raw_line: str, warnings: list[ParseWarning]) -> None:
    """Warn for EIGRP commands that have no routing.eigrp_processes field."""
    lower = line.lower()
    if "passive-interface" in lower:
        message = "EIGRP passive-interface is not in the NaC schema (routing.eigrp_processes) — omitted"
    elif lower.startswith("redistribute"):
        message = "EIGRP redistribute is not in the NaC schema (routing.eigrp_processes) — omitted"
    elif lower == "stub" or lower.startswith("stub ") or lower.startswith("eigrp stub"):
        message = "EIGRP stub is not in the NaC schema (routing.eigrp_processes) — omitted"
    else:
        message = "EIGRP command is not in the NaC schema (routing.eigrp_processes) — omitted"
    _parse_warning(warnings, line_num, raw_line, message)


def _apply_eigrp_process_command(
    line: str,
    proc: EigrpProcess,
    *,
    line_num: int,
    raw_line: str,
    warnings: list[ParseWarning],
    cli_refs: list[CliFieldRef],
) -> str | None:
    """Apply one command under an EIGRP process or IPv4 address-family.

    Returns a submode name when the command enters af-interface, topology, or an
    unsupported address-family. Returns None when the command stays in the AF.
    """
    lower = line.lower()

    def mark(field: str, label: str) -> None:
        cli_refs.append(
            CliFieldRef(
                cli_line=line_num,
                field_key=fk.eigrp_process_key(proc.name, proc.vrf, field),
                label=label,
            )
        )

    if lower.startswith("af-interface"):
        _parse_warning(
            warnings,
            line_num,
            raw_line,
            "EIGRP af-interface is not in the NaC schema (routing.eigrp_processes) — omitted",
        )
        return "af-interface"
    if lower.startswith("topology "):
        _parse_warning(
            warnings,
            line_num,
            raw_line,
            "EIGRP topology is not a NaC YAML field (iosxe_eigrp topology_base defaults to base) — omitted",
        )
        return "topology"
    if re.match(r"^address-family\s+ipv6\b", line, re.IGNORECASE):
        _parse_warning(
            warnings,
            line_num,
            raw_line,
            "EIGRP IPv6 address-family is not in the NaC schema (IPv4 unicast only) — omitted",
        )
        return "unsupported-af"
    if (
        "passive-interface" in lower
        or lower.startswith("redistribute")
        or lower == "stub"
        or lower.startswith("stub ")
        or lower.startswith("eigrp stub")
    ):
        _warn_eigrp_omitted(line, line_num, raw_line, warnings)
        return None

    router_id = re.match(r"^(?:eigrp\s+)?router-id\s+(\S+)$", line, re.IGNORECASE)
    if router_id:
        value = router_id.group(1)
        if _looks_like_mask(value):
            proc.router_id = value
            mark("router_id", "eigrp router-id")
        else:
            _parse_warning(warnings, line_num, raw_line, "EIGRP router-id is not an IPv4 address — omitted")
        return None

    if lower.startswith("network "):
        parts = line.split()
        if len(parts) == 3 and _looks_like_mask(parts[1]) and _looks_like_mask(parts[2]):
            proc.networks.append(EigrpNetwork(ip=parts[1], wildcard=parts[2]))
            mark("networks", "network")
        else:
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "EIGRP network requires an IP and wildcard (schema networks[].ip and networks[].wildcard) — omitted",
            )
        return None

    if lower == "no auto-summary":
        proc.auto_summary = False
        mark("auto_summary", "no auto-summary")
        return None
    if lower == "auto-summary":
        proc.auto_summary = True
        mark("auto_summary", "auto-summary")
        return None
    if lower == "shutdown":
        proc.shutdown = True
        mark("shutdown", "shutdown")
        return None
    if lower == "no shutdown":
        proc.shutdown = False
        mark("shutdown", "no shutdown")
        return None

    _warn_eigrp_omitted(line, line_num, raw_line, warnings)
    return None


def _apply_tunnel_command(
    line: str,
    iface: Interface,
    *,
    line_num: int,
    raw_line: str,
    warnings: list[ParseWarning],
    cli_refs: list[CliFieldRef],
) -> None:
    """Apply tunnel/NHRP commands that exist on interfaces.tunnels[]."""
    lower = line.lower()

    def mark(suffix: str, label: str) -> None:
        cli_refs.append(
            CliFieldRef(cli_line=line_num, field_key=fk.interface_key(iface.name, suffix), label=label)
        )

    source = re.match(r"^tunnel\s+source\s+(.+)$", line, re.IGNORECASE)
    if source:
        iface.tunnel_source = source.group(1).strip()
        mark("tunnel_source", "tunnel source")
        return

    destination = re.match(r"^tunnel\s+destination\s+(\S+)$", line, re.IGNORECASE)
    if destination:
        value = destination.group(1)
        if _looks_like_mask(value):
            iface.tunnel_destination_ipv4 = value
            mark("tunnel_destination_ipv4", "tunnel destination")
        else:
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "tunnel destination hostnames are not in the NaC schema (tunnel_destination_ipv4 is an IP) — omitted",
            )
        return

    if lower == "tunnel mode gre multipoint":
        iface.tunnel_mode_gre_multipoint = True
        mark("tunnel_mode_gre_multipoint", "tunnel mode gre multipoint")
        return
    if lower == "no tunnel mode gre multipoint":
        iface.tunnel_mode_gre_multipoint = False
        mark("tunnel_mode_gre_multipoint", "no tunnel mode gre multipoint")
        return
    if lower == "tunnel mode ipsec ipv4":
        iface.tunnel_mode_ipsec_ipv4 = True
        mark("tunnel_mode_ipsec_ipv4", "tunnel mode ipsec ipv4")
        return
    if lower.startswith("tunnel mode "):
        _parse_warning(
            warnings,
            line_num,
            raw_line,
            "Tunnel mode is not in the NaC schema (only tunnel_mode_gre_multipoint and tunnel_mode_ipsec_ipv4) — omitted",
        )
        return

    key_match = re.match(r"^tunnel\s+key\s+(\d+)$", line, re.IGNORECASE)
    if key_match:
        value = int(key_match.group(1))
        if 0 <= value <= _TUNNEL_KEY_MAX:
            iface.tunnel_key = value
            mark("tunnel_key", "tunnel key")
        else:
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "tunnel key is outside the schema range 0-4294967295 — omitted",
            )
        return

    protection = re.match(
        r"^tunnel\s+protection\s+ipsec\s+profile\s+(\S+)(?:\s+(\S+))?$",
        line,
        re.IGNORECASE,
    )
    if protection:
        iface.tunnel_protection_ipsec_profile = protection.group(1)
        mark("tunnel_protection_ipsec_profile", "tunnel protection ipsec profile")
        extra = protection.group(2)
        if extra and extra.lower() == "shared":
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "tunnel protection ipsec profile shared is not a NaC field — profile name only",
            )
        elif extra:
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "Extra tunnel protection option is not in the NaC schema — omitted",
            )
        return

    authentication = re.match(r"^ip\s+nhrp\s+authentication\s+(.+)$", line, re.IGNORECASE)
    if authentication:
        iface.ip_nhrp_authentication = authentication.group(1)
        mark("ip_nhrp_authentication", "ip nhrp authentication")
        return

    network_id = re.match(r"^ip\s+nhrp\s+network-id\s+(\d+)$", line, re.IGNORECASE)
    if network_id:
        value = int(network_id.group(1))
        if 1 <= value <= _TUNNEL_KEY_MAX:
            iface.ip_nhrp_network_id = value
            mark("ip_nhrp_network_id", "ip nhrp network-id")
        else:
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "ip nhrp network-id is outside the schema range 1-4294967295 — omitted",
            )
        return

    nhs = re.match(r"^ip\s+nhrp\s+nhs\s+(\S+)(?:\s+(.*))?$", line, re.IGNORECASE)
    if nhs:
        if _looks_like_mask(nhs.group(1)):
            iface.ip_nhrp_nhs.append(NhrpNhs(ipv4=nhs.group(1)))
            mark("ip_nhrp_nhs", "ip nhrp nhs")
            if nhs.group(2):
                _parse_warning(
                    warnings,
                    line_num,
                    raw_line,
                    "ip nhrp nhs nbma/multicast suffixes are not NaC fields (ip_nhrp_nhs is ipv4 only) — omitted",
                )
        else:
            _parse_warning(
                warnings,
                line_num,
                raw_line,
                "ip nhrp nhs dynamic is not in the NaC schema (ip_nhrp_nhs.ipv4 only) — omitted",
            )
        return

    nhrp_map = re.match(r"^ip\s+nhrp\s+map\s+(\S+)\s+(\S+)$", line, re.IGNORECASE)
    if nhrp_map and _looks_like_mask(nhrp_map.group(1)) and _looks_like_mask(nhrp_map.group(2)):
        iface.ip_nhrp_maps.append(NhrpMap(dest_ipv4=nhrp_map.group(1), nbma_ipv4=nhrp_map.group(2)))
        mark("ip_nhrp_maps", "ip nhrp map")
        return
    if lower.startswith("ip nhrp map "):
        _parse_warning(
            warnings,
            line_num,
            raw_line,
            "ip nhrp map multicast/dynamic is not in the NaC schema (ip_nhrp_maps is dest_ipv4 and nbma_ipv4) — omitted",
        )
        return

    if lower == "ip nhrp redirect":
        iface.ip_nhrp_redirect = True
        mark("ip_nhrp_redirect", "ip nhrp redirect")
        return
    if lower == "no ip nhrp redirect":
        iface.ip_nhrp_redirect = False
        mark("ip_nhrp_redirect", "no ip nhrp redirect")
        return
    if lower == "ip nhrp shortcut":
        iface.ip_nhrp_shortcut = True
        mark("ip_nhrp_shortcut", "ip nhrp shortcut")
        return
    if lower == "no ip nhrp shortcut":
        iface.ip_nhrp_shortcut = False
        mark("ip_nhrp_shortcut", "no ip nhrp shortcut")
        return
    if lower == "mpls nhrp":
        iface.mpls_nhrp = True
        mark("mpls_nhrp", "mpls nhrp")
        return
    if lower == "no mpls nhrp":
        iface.mpls_nhrp = False
        mark("mpls_nhrp", "no mpls nhrp")
        return
    if lower.startswith("ip nhrp"):
        _parse_warning(warnings, line_num, raw_line, "NHRP command is not in the NaC tunnel schema — omitted")
        return
    if lower.startswith("tunnel ") or lower.startswith("no tunnel "):
        _parse_warning(warnings, line_num, raw_line, "Tunnel command is not in the NaC tunnel schema — omitted")


def _get_isis(device: Device, area_tag: str | None = None) -> IsisConfig:
    routing = device.configuration.routing
    if routing.isis is None:
        routing.isis = IsisConfig(area_tag=area_tag)
    elif area_tag and not routing.isis.area_tag:
        routing.isis.area_tag = area_tag
    return routing.isis




def _ensure_aaa(device: Device) -> AaaConfig:
    if device.configuration.aaa is None:
        device.configuration.aaa = AaaConfig()
    return device.configuration.aaa


def _ensure_snmp(device: Device) -> SnmpServerConfig:
    if device.configuration.snmp_server is None:
        device.configuration.snmp_server = SnmpServerConfig()
    return device.configuration.snmp_server


def _parse_ntp_server_options(parts: list[str]) -> tuple[bool, str | None]:
    """Parse tokens after ``ntp server <ip>`` (prefer, vrf, etc.)."""
    prefer = False
    vrf: str | None = None
    idx = 3
    while idx < len(parts):
        token = parts[idx].lower()
        if token == "prefer":
            prefer = True
            idx += 1
        elif token == "vrf" and idx + 1 < len(parts):
            vrf = parts[idx + 1]
            idx += 2
        else:
            idx += 1
    return prefer, vrf


def _append_ntp_endpoint(
    device: Device,
    cli_refs: list[CliFieldRef],
    *,
    line_num: int,
    kind: str,
    parts: list[str],
) -> None:
    if len(parts) < 3:
        return
    prefer, vrf = _parse_ntp_server_options(parts)
    ntp = _ensure_ntp(device)
    entry = NtpServer(ip=parts[2], prefer=prefer or None, vrf=vrf)
    bucket = "peers" if kind == "peer" else "servers"
    if kind == "peer":
        ntp.peers.append(entry)
    else:
        ntp.servers.append(entry)
    field_key = fk.ntp_endpoint_key(kind, parts[2])
    label = f"ntp {kind} {parts[2]}"
    if vrf:
        label += f" vrf {vrf}"
    cli_refs.append(CliFieldRef(cli_line=line_num, field_key=field_key, label=label))


def _ensure_ntp(device: Device) -> NtpConfig:
    if device.configuration.ntp is None:
        device.configuration.ntp = NtpConfig()
    return device.configuration.ntp


def _ensure_nat(device: Device) -> NatConfig:
    if device.configuration.nat is None:
        device.configuration.nat = NatConfig()
    return device.configuration.nat


def _ensure_dhcp(device: Device) -> DhcpConfig:
    if device.configuration.dhcp is None:
        device.configuration.dhcp = DhcpConfig()
    return device.configuration.dhcp


def _split_interface_ref(name: str) -> tuple[str, str | None]:
    prefixes = (
        "TenGigabitEthernet",
        "GigabitEthernet",
        "FastEthernet",
        "Ethernet",
        "Port-channel",
        "Loopback",
        "Vlan",
        "Tunnel",
    )
    for prefix in prefixes:
        if name.lower().startswith(prefix.lower()):
            rest = name[len(prefix) :]
            return prefix, rest or None
    parsed = normalize_interface_token(name)
    if parsed:
        if parsed.kind == "ethernet":
            return parsed.ethernet_type or "GigabitEthernet", parsed.ethernet_id
        if parsed.kind == "loopback":
            return "Loopback", parsed.loopback_id
        if parsed.kind == "vlan":
            return "Vlan", parsed.vlan_id
    return name, None


def _parse_aaa_accounting_groups(parts: list[str], start_idx: int) -> tuple[str | None, list[str]]:
    action_type: str | None = None
    groups: list[str] = []
    idx = start_idx
    if idx < len(parts) and parts[idx] in ("start-stop", "stop-only", "none"):
        action_type = parts[idx]
        idx += 1
    if idx < len(parts) and parts[idx].lower() == "group":
        idx += 1
        while idx < len(parts):
            groups.append(parts[idx])
            idx += 1
    return action_type, groups


def _upsert_dhcp_pool(device: Device, name: str) -> DhcpPool:
    for pool in device.configuration.dhcp_pools:
        if pool.name == name:
            return pool
    pool = DhcpPool(name=name)
    device.configuration.dhcp_pools.append(pool)
    return pool


def parse_cli(cli_text: str) -> ParseResult:
    """Parse IOS-style CLI text into a canonical Device model and warnings."""
    device = Device()
    warnings: list[ParseWarning] = []
    cli_refs: list[CliFieldRef] = []
    context_by_line: dict[int, str | None] = {}
    current_iface: Interface | None = None
    pending_banner: tuple[str, str, int] | None = None
    banner_buffer: list[str] = []
    current_vrf: Vrf | None = None
    current_vrf_af: str | None = None
    current_std_acl: StandardAccessList | None = None
    current_ext_acl: ExtendedAccessList | None = None
    current_rm: RouteMap | None = None
    current_rm_entry: RouteMapEntry | None = None
    current_router: str | None = None
    current_ospf_id: str | int | None = None
    current_isis_tag: str | None = None
    current_eigrp: EigrpProcess | None = None
    current_eigrp_name: str | None = None
    current_eigrp_sub: str | None = None
    eigrp_named_without_af = False
    eigrp_router_line: int | None = None
    eigrp_router_text = ""
    current_dhcp_pool: DhcpPool | None = None
    crypto_state = CryptoParseState()

    def leave_interface() -> None:
        nonlocal current_iface
        current_iface = None

    def leave_vrf() -> None:
        nonlocal current_vrf, current_vrf_af
        current_vrf = None
        current_vrf_af = None

    def leave_acl() -> None:
        nonlocal current_std_acl, current_ext_acl
        current_std_acl = None
        current_ext_acl = None

    def leave_route_map() -> None:
        nonlocal current_rm, current_rm_entry
        current_rm = None
        current_rm_entry = None

    def leave_route_map_entry() -> None:
        nonlocal current_rm_entry
        current_rm_entry = None

    def leave_vrf_af() -> None:
        nonlocal current_vrf_af
        current_vrf_af = None

    def leave_router() -> None:
        nonlocal current_router, current_ospf_id, current_isis_tag
        nonlocal current_eigrp, current_eigrp_name, current_eigrp_sub, eigrp_named_without_af
        nonlocal eigrp_router_line, eigrp_router_text
        if eigrp_named_without_af and eigrp_router_line is not None:
            _parse_warning(
                warnings,
                eigrp_router_line,
                eigrp_router_text,
                "Named EIGRP requires address-family ipv4 unicast autonomous-system — nothing emitted",
            )
        current_router = None
        current_ospf_id = None
        current_isis_tag = None
        current_eigrp = None
        current_eigrp_name = None
        current_eigrp_sub = None
        eigrp_named_without_af = False
        eigrp_router_line = None
        eigrp_router_text = ""

    def leave_dhcp_pool() -> None:
        nonlocal current_dhcp_pool
        current_dhcp_pool = None

    def leave_crypto() -> None:
        crypto_state.clear_nested()

    def leave_nested() -> None:
        leave_vrf()
        leave_acl()
        leave_route_map()
        leave_router()
        leave_dhcp_pool()
        leave_crypto()

    for line_num, raw_line in enumerate(cli_text.splitlines(), start=1):
        line = expand_abbreviations(raw_line)
        if not line or line.startswith("!"):
            continue

        lower = line.lower()

        if parse_crypto_line(
            line, line_num=line_num, device=device, cli_refs=cli_refs, state=crypto_state
        ):
            leave_interface()
            context_by_line[line_num] = crypto_state.active_context
            continue

        if pending_banner is not None:
            kind, delim, start_line = pending_banner
            close_idx = line.find(delim)
            if close_idx != -1:
                banner_buffer.append(line[:close_idx])
                _set_banner_text(device, kind, "\n".join(banner_buffer).rstrip("\n"))
                cli_refs.append(
                    CliFieldRef(cli_line=start_line, field_key=fk.banner_key(kind), label=f"banner {kind}")
                )
                pending_banner = None
                banner_buffer = []
            else:
                banner_buffer.append(line)
            context_by_line[line_num] = current_iface.name if current_iface else None
            continue

        if lower.startswith("username "):
            user = _parse_username_line(line)
            if user:
                _upsert_user(device, user)
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key=fk.user_key(user.name), label=f"username {user.name}")
                )
            leave_interface()
        elif lower.startswith("banner "):
            parsed_banner = _parse_banner_start(line)
            if parsed_banner:
                kind, delim, text, complete = parsed_banner
                if complete:
                    _set_banner_text(device, kind, text)
                    cli_refs.append(
                        CliFieldRef(cli_line=line_num, field_key=fk.banner_key(kind), label=f"banner {kind}")
                    )
                else:
                    pending_banner = (kind, delim, line_num)
                    banner_buffer = [text] if text else []
                leave_interface()
        elif lower.startswith("clock timezone "):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    offset = int(parts[3])
                except ValueError:
                    offset = None
                device.configuration.clock = ClockConfig(
                    timezone=parts[2],
                    timezone_offset_hours=offset,
                    summer_time_zone=parts[4] if len(parts) >= 5 else None,
                )
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key=fk.clock_timezone(), label="clock timezone")
                )
            leave_interface()
        elif lower.startswith("mtu "):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                device.system.mtu = int(parts[1])
                cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.system_mtu(), label="mtu"))
            leave_interface()
        elif lower.startswith("ip domain-name ") or lower.startswith("ip domain name "):
            device.system.ip_domain_name = line.split(None, 2)[2].strip()
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.system_ip_domain_name(), label="ip domain-name")
            )
            leave_interface()
        elif lower.startswith("hostname "):
            device.system.hostname = line.split(None, 1)[1].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.system_hostname(), label="hostname"))
            leave_interface()
            leave_nested()
        elif lower == "ipv6 unicast-routing":
            device.system.ipv6_unicast_routing = True
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.system_ipv6_unicast_routing(),
                    label="ipv6 unicast-routing",
                )
            )
            leave_interface()
        elif lower == "no ipv6 unicast-routing":
            device.system.ipv6_unicast_routing = False
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.system_ipv6_unicast_routing(),
                    label="no ipv6 unicast-routing",
                )
            )
            leave_interface()
        elif lower in {"exit", "end"}:
            if current_router:
                leave_router()
            elif current_rm_entry is not None:
                leave_route_map_entry()
            elif current_vrf_af is not None:
                leave_vrf_af()
            elif current_vrf is not None or current_std_acl is not None or current_ext_acl is not None:
                leave_vrf()
                leave_acl()
                leave_route_map()
            else:
                leave_interface()
        elif lower == "exit-address-family":
            leave_vrf_af()
            if current_router == "eigrp":
                current_eigrp = None
                current_eigrp_sub = None
        elif lower.startswith("router "):
            parts = line.split()
            proto = parts[1].lower() if len(parts) >= 2 else ""
            leave_interface()
            leave_nested()
            if proto == "ospf" and len(parts) >= 3:
                current_router = "ospf"
                current_ospf_id = int(parts[2]) if parts[2].isdigit() else parts[2]
                _get_ospf_process(device, current_ospf_id)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.ospf_process_key(current_ospf_id),
                        label=f"router ospf {current_ospf_id}",
                    )
                )
            elif proto == "bgp" and len(parts) >= 3:
                current_router = "bgp"
                bgp = _get_bgp(device)
                bgp.as_number = int(parts[2]) if parts[2].isdigit() else parts[2]
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.bgp_key(),
                        label=f"router bgp {parts[2]}",
                    )
                )
            elif proto == "isis":
                current_router = "isis"
                current_isis_tag = parts[2] if len(parts) >= 3 else None
                _get_isis(device, current_isis_tag)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.isis_key(),
                        label=line.strip(),
                    )
                )
            elif proto == "eigrp":
                if len(parts) < 3:
                    _parse_warning(
                        warnings,
                        line_num,
                        raw_line,
                        "EIGRP requires a process name or autonomous system — omitted",
                    )
                    leave_router()
                elif parts[2].isdigit():
                    asn = int(parts[2])
                    if not _EIGRP_ASN_MIN <= asn <= _EIGRP_ASN_MAX:
                        _parse_warning(
                            warnings,
                            line_num,
                            raw_line,
                            "EIGRP autonomous-system is outside the schema range 1-65535 — omitted",
                        )
                        leave_router()
                    else:
                        current_router = "eigrp"
                        current_eigrp_name = parts[2]
                        current_eigrp = _get_eigrp_process(
                            device, parts[2], asn, None, classic=True
                        )
                        eigrp_named_without_af = False
                        eigrp_router_line = line_num
                        eigrp_router_text = raw_line.strip()
                        _parse_warning(
                            warnings,
                            line_num,
                            raw_line,
                            "Classic EIGRP (router eigrp <asn>) has no dedicated NaC resource; "
                            "preview maps it to routing.eigrp_processes with name set to the autonomous system",
                        )
                        cli_refs.append(
                            CliFieldRef(
                                cli_line=line_num,
                                field_key=fk.eigrp_process_key(parts[2]),
                                label=f"router eigrp {parts[2]}",
                            )
                        )
                else:
                    current_router = "eigrp"
                    current_eigrp_name = parts[2]
                    current_eigrp = None
                    eigrp_named_without_af = True
                    eigrp_router_line = line_num
                    eigrp_router_text = raw_line.strip()
            else:
                leave_router()
        elif current_router == "ospf" and current_ospf_id is not None:
            proc = _get_ospf_process(device, current_ospf_id)
            if lower.startswith("router-id "):
                proc.router_id = line.split(None, 1)[1].strip()
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.ospf_process_key(current_ospf_id, "router_id"),
                        label="router-id",
                    )
                )
            elif lower.startswith("network "):
                parts = line.split()
                if len(parts) >= 5 and parts[3].lower() == "area":
                    proc.networks.append(
                        OspfNetwork(ip=parts[1], wildcard=parts[2], area=parts[4])
                    )
                    cli_refs.append(
                        CliFieldRef(
                            cli_line=line_num,
                            field_key=fk.ospf_process_key(current_ospf_id, "networks"),
                            label="network",
                        )
                    )
            elif lower == "passive-interface default":
                proc.passive_interface_default = True
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.ospf_process_key(current_ospf_id, "passive_interface_default"),
                        label="passive-interface default",
                    )
                )
            elif lower.startswith("passive-interface "):
                token = line.split(None, 1)[1].strip()
                if token.lower() != "default":
                    proc.passive_interfaces.append(_interface_token_to_passive(token))
                    cli_refs.append(
                        CliFieldRef(
                            cli_line=line_num,
                            field_key=fk.ospf_process_key(current_ospf_id, "passive_interfaces"),
                            label="passive-interface",
                        )
                    )
        elif current_router == "bgp":
            bgp = _get_bgp(device)
            neighbor_match = re.match(r"neighbor\s+(\S+)\s+remote-as\s+(\S+)", line, re.IGNORECASE)
            if neighbor_match:
                remote_as = neighbor_match.group(2)
                bgp.neighbors.append(
                    BgpNeighbor(
                        ip=neighbor_match.group(1),
                        remote_as=int(remote_as) if remote_as.isdigit() else remote_as,
                    )
                )
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.bgp_key("neighbors"),
                        label="neighbor remote-as",
                    )
                )
            elif lower.startswith("network "):
                parts = line.split()
                if len(parts) >= 4 and parts[2].lower() == "mask":
                    _ensure_bgp_ipv4_networks(bgp).append(
                        BgpNetwork(network=parts[1], mask=parts[3])
                    )
                    cli_refs.append(
                        CliFieldRef(
                            cli_line=line_num,
                            field_key=fk.bgp_key("address_family.ipv4_unicast.networks"),
                            label="network",
                        )
                    )
        elif current_router == "isis":
            isis = _get_isis(device, current_isis_tag)
            if lower.startswith("net "):
                isis.nets.append(IsisNet(tag=line.split(None, 1)[1].strip()))
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.isis_key("nets"),
                        label="net",
                    )
                )
            elif lower.startswith("is-type "):
                isis.is_type = line.split(None, 1)[1].strip()
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.isis_key("is_type"),
                        label="is-type",
                    )
                )
        elif current_router == "eigrp":
            if lower in {"exit-af-interface", "exit-af-topology"}:
                current_eigrp_sub = None
            elif lower.startswith("address-family "):
                current_eigrp_sub = None
                if re.match(r"^address-family\s+ipv6\b", line, re.IGNORECASE):
                    current_eigrp = None
                    current_eigrp_sub = "unsupported-af"
                    _parse_warning(
                        warnings,
                        line_num,
                        raw_line,
                        "EIGRP IPv6 address-family is not in the NaC schema (IPv4 unicast only) — omitted",
                    )
                else:
                    parsed_af = _parse_eigrp_ipv4_af(line)
                    if parsed_af is None:
                        current_eigrp = None
                        _parse_warning(
                            warnings,
                            line_num,
                            raw_line,
                            "EIGRP address-family requires autonomous-system — omitted",
                        )
                    else:
                        asn, vrf_name = parsed_af
                        if not _EIGRP_ASN_MIN <= asn <= _EIGRP_ASN_MAX:
                            current_eigrp = None
                            _parse_warning(
                                warnings,
                                line_num,
                                raw_line,
                                "EIGRP autonomous-system is outside the schema range 1-65535 — omitted",
                            )
                        else:
                            process_name = current_eigrp_name or str(asn)
                            current_eigrp = _get_eigrp_process(
                                device, process_name, asn, vrf_name, classic=False
                            )
                            eigrp_named_without_af = False
                            cli_refs.append(
                                CliFieldRef(
                                    cli_line=line_num,
                                    field_key=fk.eigrp_process_key(process_name, vrf_name),
                                    label=line.strip(),
                                )
                            )
            elif current_eigrp_sub in {"af-interface", "topology", "unsupported-af"}:
                _warn_eigrp_omitted(line, line_num, raw_line, warnings)
            elif current_eigrp is None:
                _parse_warning(
                    warnings,
                    line_num,
                    raw_line,
                    "EIGRP command before IPv4 address-family is not applied — omitted",
                )
            else:
                entered = _apply_eigrp_process_command(
                    line,
                    current_eigrp,
                    line_num=line_num,
                    raw_line=raw_line,
                    warnings=warnings,
                    cli_refs=cli_refs,
                )
                if entered:
                    current_eigrp_sub = entered
                    if entered == "unsupported-af":
                        current_eigrp = None
        elif (vrf_def := re.match(r"^vrf definition\s+(\S+)$", line, re.IGNORECASE)):
            leave_interface()
            leave_nested()
            current_vrf = _get_vrf(device, vrf_def.group(1))
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.vrf_key(current_vrf.name), label=f"vrf definition {current_vrf.name}")
            )
        elif current_vrf is not None and lower.startswith("description "):
            current_vrf.description = line.split(None, 1)[1].strip()
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.vrf_key(current_vrf.name, "description"), label="description")
            )
        elif current_vrf is not None and (rd_match := re.match(r"^rd\s+(\S+)$", line, re.IGNORECASE)):
            current_vrf.route_distinguisher = rd_match.group(1)
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.vrf_key(current_vrf.name, "rd"), label="rd")
            )
        elif current_vrf is not None and (af_match := re.match(r"^address-family\s+(ipv4|ipv6)$", line, re.IGNORECASE)):
            current_vrf_af = af_match.group(1).lower()
            af = _get_vrf_af(current_vrf, current_vrf_af)
            af.enable = True
        elif (
            current_vrf is not None
            and current_vrf_af is not None
            and (rt_match := re.match(r"^route-target\s+(import|export)\s+(\S+)$", line, re.IGNORECASE))
        ):
            direction, target = rt_match.group(1).lower(), rt_match.group(2)
            af = _get_vrf_af(current_vrf, current_vrf_af)
            if direction == "import":
                af.import_route_targets.append(target)
            else:
                af.export_route_targets.append(target)
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.vrf_key(current_vrf.name, f"address_family_{current_vrf_af}"),
                    label="route-target",
                )
            )
        elif (std_acl := re.match(r"^ip access-list standard\s+(\S+)$", line, re.IGNORECASE)):
            leave_interface()
            leave_vrf()
            leave_route_map()
            current_std_acl = _get_standard_acl(device, std_acl.group(1))
            current_ext_acl = None
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.access_list_standard_key(current_std_acl.name),
                    label=f"ip access-list standard {current_std_acl.name}",
                )
            )
        elif current_std_acl is not None and (ace_match := re.match(r"^(\d+)\s+(permit|deny)\s+(.+)$", line, re.IGNORECASE)):
            seq, action, remainder = ace_match.groups()
            current_std_acl.entries.append(_parse_standard_ace(int(seq), action.lower(), remainder.strip()))
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.access_list_standard_key(current_std_acl.name, "entries"),
                    label="access-list entry",
                )
            )
        elif (ext_acl := re.match(r"^ip access-list extended\s+(\S+)$", line, re.IGNORECASE)):
            leave_interface()
            leave_vrf()
            leave_route_map()
            current_ext_acl = _get_extended_acl(device, ext_acl.group(1))
            current_std_acl = None
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.access_list_extended_key(current_ext_acl.name),
                    label=f"ip access-list extended {current_ext_acl.name}",
                )
            )
        elif current_ext_acl is not None and (ace_match := re.match(r"^(\d+)\s+(permit|deny)\s+(.+)$", line, re.IGNORECASE)):
            seq, action, remainder = ace_match.groups()
            current_ext_acl.entries.append(_parse_extended_ace(int(seq), action.lower(), remainder.strip()))
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key=fk.access_list_extended_key(current_ext_acl.name, "entries"),
                    label="access-list entry",
                )
            )
        elif _parse_prefix_list_line(line, device):
            leave_interface()
            leave_vrf()
            leave_acl()
            leave_route_map()
            pl_name = re.match(r"^ip prefix-list\s+(\S+)", line, re.IGNORECASE).group(1)
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.prefix_list_key(pl_name), label="ip prefix-list")
            )
        elif (rm_match := re.match(r"^route-map\s+(\S+)\s+(permit|deny)\s+(\d+)$", line, re.IGNORECASE)):
            leave_interface()
            leave_vrf()
            leave_acl()
            rm_name, operation, seq_str = rm_match.group(1), rm_match.group(2).lower(), int(rm_match.group(3))
            current_rm = _get_route_map(device, rm_name)
            current_rm_entry = RouteMapEntry(seq=seq_str, operation=operation, match=RouteMapMatch(), set=RouteMapSet())
            current_rm.entries.append(current_rm_entry)
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.route_map_key(rm_name, seq_str), label="route-map")
            )
        elif current_rm_entry is not None and lower.startswith("description "):
            current_rm_entry.description = line.split(None, 1)[1].strip()
        elif current_rm_entry is not None and (
            match_pl := re.match(r"^match ip address prefix-list\s+(\S+)$", line, re.IGNORECASE)
        ):
            if current_rm_entry.match is None:
                current_rm_entry.match = RouteMapMatch()
            current_rm_entry.match.ipv4_address_prefix_lists.append(match_pl.group(1))
        elif current_rm_entry is not None and (
            match_acl := re.match(r"^match ip address\s+(\S+)$", line, re.IGNORECASE)
        ):
            if current_rm_entry.match is None:
                current_rm_entry.match = RouteMapMatch()
            current_rm_entry.match.ipv4_address_access_lists.append(match_acl.group(1))
        elif current_rm_entry is not None and (
            set_lp := re.match(r"^set local-preference\s+(\d+)$", line, re.IGNORECASE)
        ):
            if current_rm_entry.set is None:
                current_rm_entry.set = RouteMapSet()
            current_rm_entry.set.local_preference = int(set_lp.group(1))
        elif current_rm_entry is not None and (
            set_metric := re.match(r"^set metric\s+(\d+)$", line, re.IGNORECASE)
        ):
            if current_rm_entry.set is None:
                current_rm_entry.set = RouteMapSet()
            current_rm_entry.set.metric_value = int(set_metric.group(1))
        elif lower == "aaa new-model":
            _ensure_aaa(device).new_model = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.aaa_new_model(), label="aaa new-model"))
            leave_nested()
        elif lower.startswith("aaa authentication login "):
            parts = line.split()
            if len(parts) >= 5:
                aaa = _ensure_aaa(device)
                if aaa.authentication is None:
                    aaa.authentication = AaaAuthenticationConfig()
                aaa.authentication.logins.append(AaaAuthLogin(name=parts[3], methods=parts[4:]))
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key=fk.aaa_login_key(parts[3]), label="aaa authentication login")
                )
            leave_nested()
        elif lower.startswith("aaa authorization exec "):
            parts = line.split()
            if len(parts) >= 5:
                aaa = _ensure_aaa(device)
                if aaa.authorization is None:
                    aaa.authorization = AaaAuthorizationConfig()
                aaa.authorization.execs.append(AaaAuthzExec(name=parts[3], methods=parts[4:]))
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key=fk.aaa_authz_key(parts[3]), label="aaa authorization exec")
                )
            leave_nested()
        elif lower.startswith("aaa accounting "):
            parts = line.split()
            if len(parts) >= 5:
                aaa = _ensure_aaa(device)
                if aaa.accounting is None:
                    aaa.accounting = AaaAccountingConfig()
                action_type, groups = _parse_aaa_accounting_groups(parts, 4)
                aaa.accounting.execs.append(
                    AaaAccountingExec(name=parts[3], action_type=action_type, start_stop_groups=groups)
                )
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key=fk.aaa_acct_key(parts[3]), label="aaa accounting")
                )
            leave_nested()
        elif lower.startswith("snmp-server community "):
            parts = line.split()
            if len(parts) >= 3:
                snmp = _ensure_snmp(device)
                snmp.snmp_communities.append(
                    SnmpCommunity(name=parts[2], permission=parts[3] if len(parts) > 3 else None)
                )
                cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.snmp_server_section(), label="snmp-server community"))
            leave_nested()
        elif lower.startswith("snmp-server contact "):
            _ensure_snmp(device).contact = line.split(None, 2)[2].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.snmp_server_contact(), label="snmp-server contact"))
            leave_nested()
        elif lower.startswith("ntp server ") or lower.startswith("ntp peer "):
            parts = line.split()
            kind = "peer" if lower.startswith("ntp peer ") else "server"
            _append_ntp_endpoint(device, cli_refs, line_num=line_num, kind=kind, parts=parts)
            leave_nested()
        elif lower == "service dhcp":
            _ensure_dhcp(device).enabled = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.dhcp_enabled(), label="service dhcp"))
            leave_nested()
        elif lower.startswith("ip dhcp pool "):
            leave_nested()
            current_dhcp_pool = _upsert_dhcp_pool(device, line.split(None, 3)[3].strip())
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=fk.dhcp_pool_key(current_dhcp_pool.name), label="ip dhcp pool")
            )
        elif current_dhcp_pool is not None and lower.startswith("network "):
            parts = line.split()
            if len(parts) >= 2:
                current_dhcp_pool.network_number = parts[1]
                if len(parts) >= 3:
                    current_dhcp_pool.network_mask = parts[2]
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.dhcp_pool_key(current_dhcp_pool.name, "network"),
                        label="network",
                    )
                )
        elif current_dhcp_pool is not None and lower.startswith("default-router "):
            current_dhcp_pool.default_routers.append(line.split(None, 1)[1].strip())
        elif current_dhcp_pool is not None and lower.startswith("dns-server "):
            current_dhcp_pool.dns_servers.append(line.split(None, 1)[1].strip())
        elif current_dhcp_pool is not None and lower.startswith("domain-name "):
            current_dhcp_pool.domain_name = line.split(None, 1)[1].strip()
        elif lower.startswith("ip nat inside source list "):
            parts = line.split()
            if len(parts) >= 8 and parts[4].lower() == "list" and parts[6].lower() == "interface":
                list_id = int(parts[5])
                iface_name = parts[7]
                overload = any(p.lower() == "overload" for p in parts[8:])
                itype, iid = _split_interface_ref(iface_name)
                nat = _ensure_nat(device)
                nat.inside_source_interfaces.append(
                    NatInsideSource(
                        id=list_id,
                        interfaces=[
                            NatInsideInterface(
                                interface_type=itype,
                                interface_id=iid,
                                overload=True if overload else None,
                            )
                        ],
                    )
                )
                cli_refs.append(CliFieldRef(cli_line=line_num, field_key=fk.nat_section(), label="ip nat inside source"))
            leave_nested()
        elif (parsed_enable := _parse_enable_credential(line)) is not None:
            kind, value, enc_type = parsed_enable
            if kind == "secret":
                device.system.enable_secret = value
                device.system.enable_secret_type = enc_type
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.system_enable_secret(),
                        label="enable secret",
                    )
                )
            else:
                device.system.enable_password = value
                device.system.enable_password_type = enc_type
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.system_enable_password(),
                        label="enable password",
                    )
                )
            leave_interface()
        elif lower.startswith("ip route "):
            parts = line.split()
            if len(parts) >= 4:
                prefix = parts[2]
                plen: int | None = None
                next_idx = 3
                if "/" in prefix:
                    prefix, plen_str = prefix.rsplit("/", 1)
                    if plen_str.isdigit():
                        plen = int(plen_str)
                elif len(parts) >= 5 and _looks_like_mask(parts[3]):
                    plen = _mask_to_prefixlen(parts[3])
                    prefix = f"{parts[2]}/{plen}"
                    next_idx = 4
                next_hop = parts[next_idx] if len(parts) > next_idx else None
                route_prefix = prefix if "/" in prefix or plen is None else f"{prefix}/{plen}"
                device.static_routes.append(
                    StaticRoute(prefix=prefix, prefix_length=plen, next_hop=next_hop)
                )
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key=fk.static_route_key(route_prefix), label="ip route")
                )
            leave_interface()
        elif lower.startswith("interface "):
            leave_nested()
            token = line.split(None, 1)[1].strip()
            parsed = normalize_interface_token(token)
            if parsed:
                current_iface = parsed
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(parsed.name),
                        label=f"interface {parsed.name}",
                    )
                )
            else:
                leave_interface()
                warnings.append(
                    ParseWarning(
                        line=line_num,
                        message=f'Unknown interface "{token}" — config lines below will not apply until a recognized interface',
                        cli_line=raw_line.strip(),
                    )
                )
        elif current_iface is not None:
            if lower == "no shutdown":
                current_iface.shutdown = False
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "shutdown"),
                        label="no shutdown",
                    )
                )
            elif lower.startswith("shutdown") and lower != "no shutdown":
                current_iface.shutdown = True
                device.upsert_interface(current_iface)
            elif lower.startswith("description "):
                current_iface.description = line.split(None, 1)[1].strip()
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "description"),
                        label="description",
                    )
                )
            elif (vrf_fwd := re.match(r"^vrf forwarding\s+(\S+)$", line, re.IGNORECASE)):
                current_iface.vrf_forwarding = vrf_fwd.group(1)
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "vrf"),
                        label="vrf forwarding",
                    )
                )
            elif lower.startswith("ip address "):
                _parse_ip_address_line(line, current_iface)
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "ipv4"),
                        label="ip address",
                    )
                )
            elif lower == "ipv6 enable":
                current_iface.ipv6_enable = True
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "ipv6"),
                        label="ipv6 enable",
                    )
                )
            elif lower.startswith("ipv6 address "):
                _parse_ipv6_address_line(line, current_iface)
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "ipv6"),
                        label="ipv6 address",
                    )
                )
            elif lower == "ip nat inside":
                current_iface.nat_inside = True
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "nat_inside"),
                        label="ip nat inside",
                    )
                )
            elif lower == "ip nat outside":
                current_iface.nat_outside = True
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=fk.interface_key(current_iface.name, "nat_outside"),
                        label="ip nat outside",
                    )
                )
            elif lower.startswith("channel-group "):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    current_iface.port_channel_id = parts[1]
                    if len(parts) >= 4 and parts[2].lower() == "mode":
                        current_iface.port_channel_mode = parts[3].lower()
                    device.upsert_interface(current_iface)
                    cli_refs.append(
                        CliFieldRef(
                            cli_line=line_num,
                            field_key=fk.interface_key(current_iface.name, "channel_group"),
                            label="channel-group",
                        )
                    )
            elif (
                lower.startswith("tunnel ")
                or lower.startswith("no tunnel ")
                or lower.startswith("ip nhrp ")
                or lower.startswith("no ip nhrp ")
                or lower in {"mpls nhrp", "no mpls nhrp"}
            ):
                if current_iface.kind != "tunnel":
                    _parse_warning(
                        warnings,
                        line_num,
                        raw_line,
                        "NHRP and tunnel commands are modeled on interfaces.tunnels only — omitted",
                    )
                else:
                    _apply_tunnel_command(
                        line,
                        current_iface,
                        line_num=line_num,
                        raw_line=raw_line,
                        warnings=warnings,
                        cli_refs=cli_refs,
                    )
                    device.upsert_interface(current_iface)

        context_by_line[line_num] = current_iface.name if current_iface else None

    leave_router()
    return ParseResult(device=device, warnings=warnings, cli_refs=cli_refs, context_by_line=context_by_line)
