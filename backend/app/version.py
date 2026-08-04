"""API version and capability manifest for stale-backend detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

API_VERSION = "0.5.7"

# Bump API_VERSION when response shape or behavior changes materially.
FEATURES: list[str] = [
    "hints_toggle",
    "wire_crypto",
    "crypto_line_mappings",
    "aaa_line_mappings",
    "ntp_line_mappings",
    "field_key_registry",
    "nac_full_schema",
    "schema_version_4",
    "wire_users",
    "wire_system_banner_clock_mtu",
    "wire_routing_ospf_bgp_isis",
    "wire_vrfs_access_lists_policy",
    "wire_aaa_snmp_ntp_nat_dhcp",
    "wire_extended_interfaces",
    "ipv6_interface_addresses",
    "ipv6_link_local_shorthand",
    "ipv6_unicast_routing",
    "cli_context_by_line",
    "global_command_exits_interface",
    "terraform_hcl_preview",
    "restconf_json_preview",
]

_BUILD_SOURCES = (
    "version.py",
    "field_keys.py",
    "models.py",
    "nac_sections.py",
    "main.py",
    "parsers/ios_cli.py",
    "parsers/crypto_cli.py",
    "generators/nac_yaml.py",
    "generators/terraform.py",
    "generators/restconf.py",
    "sync/mappings.py",
)


def compute_build_id() -> str:
    """Short fingerprint of backend source mtimes — changes when code changes."""
    parts: list[str] = []
    for rel in _BUILD_SOURCES:
        path = APP_DIR / rel
        if path.exists():
            parts.append(f"{rel}:{path.stat().st_mtime_ns}")
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest[:12]


BUILD_ID = compute_build_id()


def capability_manifest() -> dict[str, object]:
    import os

    return {
        "api_version": API_VERSION,
        "build_id": BUILD_ID,
        "features": FEATURES,
        "pid": os.getpid(),
    }
