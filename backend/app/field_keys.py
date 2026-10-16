"""Single source of truth for CLI ↔ YAML line-mapping field keys.

Parser ``CliFieldRef.field_key`` values and generator ``_YamlBuilder.mark()`` keys
must be built only through these helpers so drift is caught in CI.
"""

from __future__ import annotations

from app.models import CliFieldRef


# ---------------------------------------------------------------------------
# System / users / banner / clock
# ---------------------------------------------------------------------------


def system_hostname() -> str:
    return "system.hostname"


def system_mtu() -> str:
    return "system.mtu"


def system_ip_domain_name() -> str:
    return "system.ip_domain_name"


def system_enable_secret() -> str:
    return "system.enable_secret"


def system_enable_password() -> str:
    return "system.enable_password"


def system_ipv6_unicast_routing() -> str:
    return "system.ipv6_unicast_routing"


def user_key(name: str) -> str:
    return f"users:{name}"


def users_section() -> str:
    return "users"


def banner_key(kind: str) -> str:
    return f"banner.{kind}"


def banner_section() -> str:
    return "banner"


def clock_timezone() -> str:
    return "clock.timezone"


def clock_section() -> str:
    return "clock"


# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------


def interface_key(name: str, suffix: str | None = None) -> str:
    if suffix:
        return f"interface:{name}:{suffix}"
    return f"interface:{name}"


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def static_route_key(prefix: str) -> str:
    """Key for one static route entry (prefix may include /length)."""
    return f"routing.static_routes:{prefix}"


def ospf_process_key(proc_id: str | int, field: str | None = None) -> str:
    base = f"routing.ospf_processes.{proc_id}"
    return f"{base}.{field}" if field else base


def bgp_key(field: str | None = None) -> str:
    if field is None:
        return "routing.bgp"
    if field.startswith("routing."):
        return field
    return f"routing.bgp.{field}"


def isis_key(field: str | None = None) -> str:
    if field is None:
        return "routing.isis"
    if field.startswith("routing."):
        return field
    return f"routing.isis.{field}"


def eigrp_process_key(name: str, vrf: str | None = None, field: str | None = None) -> str:
    """Key for one routing.eigrp_processes[] entry (vrf distinguishes a second AF)."""
    ident = f"{name}@{vrf}" if vrf else str(name)
    base = f"routing.eigrp_processes.{ident}"
    return f"{base}.{field}" if field else base


# ---------------------------------------------------------------------------
# VRF / policy objects
# ---------------------------------------------------------------------------


def vrf_key(name: str, field: str | None = None) -> str:
    base = f"vrf:{name}"
    return f"{base}:{field}" if field else base


def access_list_standard_key(name: str, field: str | None = None) -> str:
    base = f"access_lists.standard:{name}"
    return f"{base}:{field}" if field else base


def access_list_extended_key(name: str, field: str | None = None) -> str:
    base = f"access_lists.extended:{name}"
    return f"{base}:{field}" if field else base


def prefix_list_key(name: str) -> str:
    return f"prefix_lists:{name}"


def route_map_key(name: str, seq: int | str) -> str:
    return f"route_maps:{name}:{seq}"


# ---------------------------------------------------------------------------
# AAA / SNMP / NTP / DHCP / NAT
# ---------------------------------------------------------------------------


def aaa_new_model() -> str:
    return "aaa.new_model"


def aaa_login_key(name: str, field: str | None = None) -> str:
    base = f"aaa.authentication.logins:{name}"
    return f"{base}:{field}" if field else base


def aaa_authz_key(name: str, field: str | None = None) -> str:
    base = f"aaa.authorization.execs:{name}"
    return f"{base}:{field}" if field else base


def aaa_acct_key(name: str, field: str | None = None) -> str:
    base = f"aaa.accounting.execs:{name}"
    return f"{base}:{field}" if field else base


def aaa_section() -> str:
    return "aaa"


def snmp_server_section() -> str:
    return "snmp_server"


def snmp_server_contact() -> str:
    return "snmp_server.contact"


def ntp_endpoint_key(kind: str, ip: str) -> str:
    bucket = "peers" if kind == "peer" else "servers"
    return f"ntp.{bucket}:{ip}"


def ntp_section() -> str:
    return "ntp"


def dhcp_enabled() -> str:
    return "dhcp.enabled"


def dhcp_section() -> str:
    return "dhcp"


def dhcp_pool_key(name: str, field: str | None = None) -> str:
    base = f"dhcp_pools:{name}"
    return f"{base}:{field}" if field else base


def dhcp_pools_section() -> str:
    return "dhcp_pools"


def nat_section() -> str:
    return "nat"


# ---------------------------------------------------------------------------
# Crypto (IKEv2 / IPsec / PKI)
# ---------------------------------------------------------------------------


def crypto_section() -> str:
    return "crypto"


def crypto_ikev2_global(field: str) -> str:
    return f"crypto.ikev2:{field}"


def crypto_proposal_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.proposals:{name}"
    return f"{base}:{field}" if field else base


def crypto_policy_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.policies:{name}"
    return f"{base}:{field}" if field else base


def crypto_keyring_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.keyrings:{name}"
    return f"{base}:{field}" if field else base


def crypto_profile_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.profiles:{name}"
    return f"{base}:{field}" if field else base


def crypto_transform_set_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ipsec_transform_sets:{name}"
    return f"{base}:{field}" if field else base


def crypto_ipsec_profile_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ipsec_profiles:{name}"
    return f"{base}:{field}" if field else base


def crypto_trustpoint_key(tp_id: str, field: str | None = None) -> str:
    base = f"crypto.pki.trustpoints:{tp_id}"
    return f"{base}:{field}" if field else base


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def mapping_specificity(field_key: str) -> int:
    """Higher wins when multiple refs share a CLI line."""
    if field_key.endswith(":ipv4") or field_key.endswith(":ipv6") or field_key.endswith(":shutdown") or field_key.endswith(":description"):
        return 3
    if field_key.startswith("interface:"):
        return 2
    if field_key.startswith("crypto.") and ":" in field_key:
        return 2 + field_key.count(":")
    if field_key.startswith("aaa.") and ":" in field_key:
        return 2 + field_key.count(":")
    if field_key.startswith("ntp.") and ":" in field_key:
        return 2
    return 1


def find_unmapped_cli_refs(
    cli_refs: list[CliFieldRef],
    yaml_ranges: dict[str, tuple[int, int]],
) -> list[CliFieldRef]:
    """Refs whose field_key has no matching YAML line range."""
    return [ref for ref in cli_refs if ref.field_key not in yaml_ranges]


def format_unmapped_refs(unmapped: list[CliFieldRef]) -> str:
    if not unmapped:
        return ""
    lines = [f"  line {ref.cli_line} {ref.field_key!r} ({ref.label})" for ref in unmapped]
    return "Unmapped CLI field keys (parser vs generator drift):\n" + "\n".join(lines)
