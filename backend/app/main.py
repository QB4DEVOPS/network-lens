"""Network Lens API — CLI to live nac.yaml sync."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.generators.nac_yaml import generate_nac_yaml
from app.generators.restconf import generate_restconf_json
from app.generators.terraform import generate_terraform
from app.models import Device, LineMapping, ParseWarning
from app.parsers.ios_cli import parse_cli
from app.sync.mappings import build_line_mappings
from app.version import API_VERSION, BUILD_ID, FEATURES, capability_manifest

app = FastAPI(title="Network Lens", version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SyncRequest(BaseModel):
    cli_text: str = ""


class SyncResponse(BaseModel):
    canonical: Device
    nac_yaml: str
    terraform_hcl: str
    restconf_json: str
    warnings: list[ParseWarning] = []
    mappings: list[LineMapping] = []
    context_by_line: dict[int, str | None] = Field(default_factory=dict)
    api_version: str = API_VERSION
    build_id: str = BUILD_ID
    features: list[str] = Field(default_factory=lambda: list(FEATURES))


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", **capability_manifest()}


@app.post("/sync", response_model=SyncResponse)
def sync(request: SyncRequest) -> SyncResponse:
    parse_result = parse_cli(request.cli_text)
    yaml_result = generate_nac_yaml(parse_result.device)
    mappings = build_line_mappings(parse_result, yaml_result)
    return SyncResponse(
        canonical=parse_result.device,
        nac_yaml=yaml_result.content,
        terraform_hcl=generate_terraform(parse_result.device),
        restconf_json=generate_restconf_json(parse_result.device),
        warnings=parse_result.warnings,
        mappings=mappings,
        context_by_line=parse_result.context_by_line,
    )
