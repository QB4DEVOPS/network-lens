"""Canonical network device model aligned with nac.yaml (iosxe.devices[])."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StaticRoute(BaseModel):
    prefix: str
    prefix_length: int | None = None
    next_hop: str | None = None
    interface: str | None = None


class SemanticIssue(BaseModel):
    severity: str  # warning | error
    code: str
    message: str
    field_key: str | None = None


class ValidationStatus(BaseModel):
    deserialize_ok: bool = True
    validate_ok: bool = True
    operate_ok: bool = False
    issues: list[SemanticIssue] = Field(default_factory=list)
    incomplete_badges: list[str] = Field(default_factory=list)


class DeviceSystem(BaseModel):
    hostname: str | None = None
    ipv6_unicast_routing: bool = False


class Ipv6Address(BaseModel):
    prefix: str
    prefix_length: int | None = None
    eui_64: bool = False


class Interface(BaseModel):
    name: str
    kind: str = "loopback"  # loopback | ethernet | tunnel | vlan
    loopback_id: str | None = None
    ethernet_type: str | None = None  # GigabitEthernet
    ethernet_id: str | None = None  # 0/0/0
    tunnel_id: str | None = None  # 10
    vlan_id: str | None = None  # 888
    shutdown: bool = True
    description: str | None = None
    ipv4_address: str | None = None
    ipv4_address_mask: str | None = None
    ipv4_dhcp: bool = False
    ipv6_enable: bool = False
    ipv6_dhcp: bool = False
    ipv6_autoconfig: bool = False
    ipv6_addresses: list[Ipv6Address] = Field(default_factory=list)
    ipv6_link_local_addresses: list[str] = Field(default_factory=list)

    @property
    def has_ipv6(self) -> bool:
        return (
            self.ipv6_enable
            or self.ipv6_dhcp
            or self.ipv6_autoconfig
            or bool(self.ipv6_addresses)
            or bool(self.ipv6_link_local_addresses)
        )


class ParseWarning(BaseModel):
    line: int
    message: str
    cli_line: str


class CliFieldRef(BaseModel):
    cli_line: int
    field_key: str
    label: str


class LineMapping(BaseModel):
    cli_line: int
    yaml_start_line: int
    yaml_end_line: int
    label: str
    field_key: str


class ParseResult(BaseModel):
    device: Device
    warnings: list[ParseWarning] = Field(default_factory=list)
    cli_refs: list[CliFieldRef] = Field(default_factory=list)
    context_by_line: dict[int, str | None] = Field(default_factory=dict)


class NacYamlResult(BaseModel):
    content: str
    ranges: dict[str, tuple[int, int]] = Field(default_factory=dict)


class Device(BaseModel):
    """Structured representation of a single IOS-XE device (one entry in iosxe.devices[])."""

    name: str = "iosv-01"
    host: str | None = None
    system: DeviceSystem = Field(default_factory=DeviceSystem)
    interfaces: list[Interface] = Field(default_factory=list)
    static_routes: list[StaticRoute] = Field(default_factory=list)
    secrets_redacted: bool = False

    def get_interface(self, name: str) -> Interface | None:
        for iface in self.interfaces:
            if iface.name.lower() == name.lower():
                return iface
        return None

    def upsert_interface(self, iface: Interface) -> None:
        existing = self.get_interface(iface.name)
        if existing:
            idx = self.interfaces.index(existing)
            self.interfaces[idx] = iface
        else:
            self.interfaces.append(iface)

    @property
    def loopbacks(self) -> list[Interface]:
        return [i for i in self.interfaces if i.kind == "loopback"]

    @property
    def ethernets(self) -> list[Interface]:
        return [i for i in self.interfaces if i.kind == "ethernet"]

    @property
    def tunnels(self) -> list[Interface]:
        return [i for i in self.interfaces if i.kind == "tunnel"]

    @property
    def vlans(self) -> list[Interface]:
        return [i for i in self.interfaces if i.kind == "vlan"]
