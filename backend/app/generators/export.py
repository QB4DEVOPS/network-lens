"""Export-ready nac.yaml without preview hints."""

from __future__ import annotations

import re

from app.generators.nac_yaml import generate_nac_yaml
from app.models import Device


def strip_preview_artifacts(yaml_text: str) -> str:
    """Remove Network Lens preview header and inline teaching hints."""
    lines: list[str] = []
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "  # ←" in line:
            line = line.split("  # ←", 1)[0].rstrip()
        if "  # ⚠" in line:
            line = line.split("  # ⚠", 1)[0].rstrip()
        if re.match(r"^\s+# ←", line):
            continue
        lines.append(line)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def generate_export_yaml(device: Device) -> str:
    raw = generate_nac_yaml(device).content
    return strip_preview_artifacts(raw)
