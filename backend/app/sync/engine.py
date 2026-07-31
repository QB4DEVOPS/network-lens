"""Central sync — canonical model to all representations."""

from __future__ import annotations

from app.generators.export import generate_export_yaml
from app.generators.ios_cli import generate_ios_cli
from app.generators.nac_yaml import generate_nac_yaml
from app.generators.restconf import generate_restconf_json
from app.generators.terraform import generate_terraform
from app.models import Device, ValidationStatus
from app.models.project import Project
from app.operational.mock import compute_operational_state
from app.parsers.ios_cli import parse_cli
from app.sync.mappings import build_line_mappings
from app.validators.semantic import validate_device


class SyncBundle:
    def __init__(
        self,
        device: Device,
        project: Project,
        parse_warnings: list,
        mappings: list,
        context_by_line: dict,
        validation: ValidationStatus,
    ) -> None:
        self.device = device
        self.project = project
        self.parse_warnings = parse_warnings
        self.mappings = mappings
        self.context_by_line = context_by_line
        self.validation = validation
        self.nac_yaml = generate_nac_yaml(device).content
        self.terraform_hcl = generate_terraform(device)
        self.restconf_json = generate_restconf_json(device)
        self.ios_cli = generate_ios_cli(device)
        self.export_yaml = generate_export_yaml(device)
        self.operational = compute_operational_state(device)


def sync_from_cli(cli_text: str, project: Project | None = None) -> SyncBundle:
    parse_result = parse_cli(cli_text)
    device = parse_result.device
    if project:
        if project.devices:
            device.name = project.devices[0].name
            device.host = project.devices[0].host
            project.devices[0] = device
        else:
            project.devices = [device]
    else:
        project = Project(devices=[device])

    yaml_result = generate_nac_yaml(device)
    mappings = build_line_mappings(parse_result, yaml_result)
    validation = validate_device(device)

    return SyncBundle(
        device=device,
        project=project,
        parse_warnings=parse_result.warnings,
        mappings=mappings,
        context_by_line=parse_result.context_by_line,
        validation=validation,
    )


def sync_from_project(project: Project) -> SyncBundle:
    device = project.primary_device
    cli = generate_ios_cli(device)
    return sync_from_cli(cli, project)
