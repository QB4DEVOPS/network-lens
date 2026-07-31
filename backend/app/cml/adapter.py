"""Optional CML SSH adapter (mock-first)."""

from __future__ import annotations

import os

from app.models import Device
from app.generators.ios_cli import generate_ios_cli


def cml_configured() -> bool:
    return bool(os.environ.get("CML_HOST") and os.environ.get("CML_USERNAME"))


def apply_cli_mock(device: Device, confirmed: bool) -> dict[str, object]:
    if not confirmed:
        return {"applied": False, "message": "Apply requires confirmed=true"}
    cli = generate_ios_cli(device)
    if cml_configured():
        return {
            "applied": False,
            "message": "CML credentials detected but live push is not enabled in MVP — mock apply only",
            "cli_preview": cli,
        }
    return {"applied": True, "mode": "mock", "message": "Mock apply succeeded", "cli_preview": cli}
