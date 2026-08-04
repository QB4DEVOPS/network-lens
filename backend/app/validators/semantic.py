"""Semantic validation — parse success ≠ good config."""

from __future__ import annotations

from app.models import Device, SemanticIssue, ValidationStatus


def validate_device(device: Device) -> ValidationStatus:
    issues: list[SemanticIssue] = []
    incomplete: list[str] = []

    if device.system.hostname is None:
        incomplete.append("system.hostname")

    for iface in device.interfaces:
        base = f"interface:{iface.name}"
        has_ipv4 = iface.ipv4_dhcp or (iface.ipv4_address and not iface.ipv4_dhcp)
        if not has_ipv4 and not iface.has_ipv6:
            incomplete.append(base)

        if iface.kind == "loopback" and iface.ipv4_dhcp:
            issues.append(
                SemanticIssue(
                    severity="warning",
                    code="dhcp_on_loopback",
                    message=f"DHCP on {iface.name} is unusual for a loopback",
                    field_key=f"{base}:ipv4",
                )
            )

        if iface.kind == "loopback" and iface.shutdown:
            issues.append(
                SemanticIssue(
                    severity="warning",
                    code="loopback_shutdown",
                    message=f"{iface.name} is administratively down",
                    field_key=f"{base}:shutdown",
                )
            )

    validate_ok = not any(i.severity == "error" for i in issues)
    return ValidationStatus(
        deserialize_ok=True,
        validate_ok=validate_ok,
        operate_ok=False,
        issues=issues,
        incomplete_badges=incomplete,
    )
