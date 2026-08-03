"""API version and capability manifest for stale-backend detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

API_VERSION = "0.4.0"

# Bump API_VERSION when response shape or behavior changes materially.
FEATURES: list[str] = [
    "nac_full_schema",
    "schema_version_4",
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
    "models.py",
    "nac_sections.py",
    "main.py",
    "parsers/ios_cli.py",
    "generators/nac_yaml.py",
    "generators/terraform.py",
    "generators/restconf.py",
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
