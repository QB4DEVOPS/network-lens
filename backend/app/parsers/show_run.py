"""Parse IOS show running-config into inferred canonical model."""

from __future__ import annotations

from app.models import Device
from app.models.project import Project, Topology, TopologyNode
from app.parsers.ios_cli import parse_cli


def parse_show_run(config_text: str, project_name: str = "Imported Lab") -> Project:
    """Best-effort import — labeled inferred with warnings."""
    result = parse_cli(config_text)
    device = result.device
    warnings = [
        "This is an inferred model from show running-config. Verify before applying.",
        *([w.message for w in result.warnings]),
    ]

    hostname = device.system.hostname or "R1"
    node = TopologyNode(label=hostname, type="router", device_ref=device.name, x=100, y=100)

    return Project(
        name=project_name,
        devices=[device],
        topology=Topology(nodes=[node], edges=[]),
        inferred=True,
        inference_warnings=warnings,
    )
