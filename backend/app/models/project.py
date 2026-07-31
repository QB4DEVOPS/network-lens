"""Project and topology models."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models import Device


class TopologyNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str
    type: str = "router"  # router | switch | host
    device_ref: str | None = None
    x: float = 0
    y: float = 0


class TopologyEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str
    target: str
    source_if: str | None = None
    target_if: str | None = None


class Topology(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Branch Lab"
    devices: list[Device] = Field(default_factory=lambda: [Device()])
    topology: Topology = Field(default_factory=Topology)
    inferred: bool = False
    inference_warnings: list[str] = Field(default_factory=list)

    @property
    def primary_device(self) -> Device:
        return self.devices[0] if self.devices else Device()
