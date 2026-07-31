"""Explain-only AI sidebar (template-based MVP — no silent mutations)."""

from __future__ import annotations

from app.models import Device, ValidationStatus


def explain_query(device: Device, question: str, validation: ValidationStatus | None = None) -> str:
    q = question.lower().strip()
    hostname = device.system.hostname or "(not set)"

    if "hostname" in q or "hostn" in q:
        return f'The hostname is stored under `configuration.system.hostname` and is currently "{hostname}". CLI `hostname` maps to this field.'

    if "loopback" in q or "lo0" in q:
        lo = device.get_interface("Loopback0")
        if lo:
            return (
                f"Loopback0 is `interfaces.loopbacks[0]` with id '{lo.loopback_id}'. "
                f"IPv4: {lo.ipv4_address or 'unset'}. shutdown={lo.shutdown}."
            )
        return "No loopback configured yet. Type `int lo0` in CLI to create one."

    if "ipv6" in q:
        if device.system.ipv6_unicast_routing:
            return "`ipv6 unicast-routing` is global — it maps to `system.ipv6_unicast_routing: true`, not under an interface."
        return "IPv6 unicast routing is not enabled. Add `ipv6 unicast-routing` in global config."

    if "ping" in q or "fail" in q:
        return "In mock mode, ping fails when all interfaces are down or have no addresses. Check `shutdown` and IP config."

    if validation and validation.incomplete_badges:
        return f"Incomplete objects: {', '.join(validation.incomplete_badges)}. Parsed OK, but design is not complete."

    return (
        "Explain-only mode: I describe the model but never change it. "
        f"Ask about hostname, loopback, ipv6, or ping. Current device: {device.name}, hostname={hostname}."
    )
