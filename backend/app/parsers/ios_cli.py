"""IOS CLI line parser with abbreviation support."""

from __future__ import annotations

import re

from app.models import Device, DeviceSystem, Interface, Ipv6Address, ParseResult, ParseWarning, CliFieldRef, StaticRoute

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


def _looks_like_mask(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _mask_to_prefixlen(mask: str) -> int:
    bits = "".join(f"{int(octet):08b}" for octet in mask.split("."))
    return bits.count("1")


def parse_cli(cli_text: str) -> ParseResult:
    """Parse IOS-style CLI text into a canonical Device model and warnings."""
    device = Device()
    warnings: list[ParseWarning] = []
    cli_refs: list[CliFieldRef] = []
    context_by_line: dict[int, str | None] = {}
    current_iface: Interface | None = None

    def iface_key(name: str, suffix: str | None = None) -> str:
        if suffix:
            return f"interface:{name}:{suffix}"
        return f"interface:{name}"

    def leave_interface() -> None:
        nonlocal current_iface
        current_iface = None

    for line_num, raw_line in enumerate(cli_text.splitlines(), start=1):
        line = expand_abbreviations(raw_line)
        if not line or line.startswith("!"):
            continue

        lower = line.lower()

        if lower.startswith("hostname "):
            device.system.hostname = line.split(None, 1)[1].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key="system.hostname", label="hostname"))
            leave_interface()
        elif lower == "ipv6 unicast-routing":
            device.system.ipv6_unicast_routing = True
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key="system.ipv6_unicast_routing",
                    label="ipv6 unicast-routing",
                )
            )
            leave_interface()
        elif lower == "no ipv6 unicast-routing":
            device.system.ipv6_unicast_routing = False
            cli_refs.append(
                CliFieldRef(
                    cli_line=line_num,
                    field_key="system.ipv6_unicast_routing",
                    label="no ipv6 unicast-routing",
                )
            )
            leave_interface()
        elif lower in {"exit", "end"}:
            leave_interface()
        elif lower.startswith("enable secret ") or lower.startswith("enable password "):
            device.secrets_redacted = True
            warnings.append(
                ParseWarning(
                    line=line_num,
                    message="Secret redacted from generated output",
                    cli_line="enable secret [REDACTED-SECRET]",
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
                device.static_routes.append(
                    StaticRoute(prefix=prefix, prefix_length=plen, next_hop=next_hop)
                )
                cli_refs.append(
                    CliFieldRef(cli_line=line_num, field_key="routing.static_route", label="ip route")
                )
            leave_interface()
        elif lower.startswith("interface "):
            token = line.split(None, 1)[1].strip()
            parsed = normalize_interface_token(token)
            if parsed:
                current_iface = parsed
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=iface_key(parsed.name),
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
                        field_key=iface_key(current_iface.name, "shutdown"),
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
                        field_key=iface_key(current_iface.name, "description"),
                        label="description",
                    )
                )
            elif lower.startswith("ip address "):
                _parse_ip_address_line(line, current_iface)
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=iface_key(current_iface.name, "ipv4"),
                        label="ip address",
                    )
                )
            elif lower == "ipv6 enable":
                current_iface.ipv6_enable = True
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=iface_key(current_iface.name, "ipv6"),
                        label="ipv6 enable",
                    )
                )
            elif lower.startswith("ipv6 address "):
                _parse_ipv6_address_line(line, current_iface)
                device.upsert_interface(current_iface)
                cli_refs.append(
                    CliFieldRef(
                        cli_line=line_num,
                        field_key=iface_key(current_iface.name, "ipv6"),
                        label="ipv6 address",
                    )
                )

        context_by_line[line_num] = current_iface.name if current_iface else None

    return ParseResult(device=device, warnings=warnings, cli_refs=cli_refs, context_by_line=context_by_line)
