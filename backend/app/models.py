"""Canonical network device model aligned with nac.yaml (iosxe.devices[])."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_serializer, model_validator


# ---------------------------------------------------------------------------
# Shared / leaf types
# ---------------------------------------------------------------------------


class StaticRouteNextHop(BaseModel):
    ip: str | None = None
    interface_type: str | None = None
    interface_id: str | None = None
    distance: int | None = None
    global_: bool | None = Field(default=None, alias="global")
    name: str | None = None
    permanent: bool | None = None
    tag: int | None = None
    track_id: str | None = None


class StaticRoute(BaseModel):
    """NaC routing.static_routes[] entry (legacy flat next_hop fields retained for parser)."""

    prefix: str
    prefix_length: int | None = None
    mask: str | None = None
    vrf: str | None = None
    next_hop: str | None = None
    interface: str | None = None
    next_hops: list[StaticRouteNextHop] = Field(default_factory=list)


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
    mtu: int | None = None
    ip_routing: bool | None = None
    ip_domain_name: str | None = None
    enable_secret: str | None = None


class Ipv6Address(BaseModel):
    prefix: str
    prefix_length: int | None = None
    eui_64: bool = False


class Interface(BaseModel):
    name: str
    kind: str = "loopback"  # loopback | ethernet | tunnel | vlan | port_channel | ...
    loopback_id: str | None = None
    ethernet_type: str | None = None
    ethernet_id: str | None = None
    tunnel_id: str | None = None
    vlan_id: str | None = None
    port_channel_id: str | None = None
    subinterface_id: str | None = None
    bdi_id: str | None = None
    nve_id: str | None = None
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


# ---------------------------------------------------------------------------
# NaC configuration section stubs (expanded in NDO-172+)
# ---------------------------------------------------------------------------


class UserAccount(BaseModel):
    name: str
    privilege: int | None = None
    password: str | None = None
    password_type: str | None = None
    secret: str | None = None
    secret_type: str | None = None


class BannerConfig(BaseModel):
    exec: str | None = None
    login: str | None = None
    motd: str | None = None
    prompt_timeout: str | None = None


class ClockConfig(BaseModel):
    timezone: str | None = None
    timezone_offset_hours: int | None = None
    summer_time_zone: str | None = None


class LineConfig(BaseModel):
    """line.consoles[], line.vtys[], line.auxes[] — detail wired in later stories."""

    model_config = {"extra": "allow"}


class AaaConfig(BaseModel):
    model_config = {"extra": "allow"}


class AccessListEntry(BaseModel):
    model_config = {"extra": "allow"}


class AccessListsConfig(BaseModel):
    standard: list[AccessListEntry] = Field(default_factory=list)
    extended: list[AccessListEntry] = Field(default_factory=list)
    role_based: list[AccessListEntry] = Field(default_factory=list)


class NamedListEntry(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class CommunityListsConfig(BaseModel):
    standard: list[NamedListEntry] = Field(default_factory=list)
    expanded: list[NamedListEntry] = Field(default_factory=list)


class PrefixList(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class RouteMap(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class PolicyConfig(BaseModel):
    model_config = {"extra": "allow"}


class ClassMap(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class PolicyMap(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class ParameterMap(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class KeyChain(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class OspfProcess(BaseModel):
    id: int | str
    model_config = {"extra": "allow"}


class BgpConfig(BaseModel):
    as_number: int | str | None = None
    model_config = {"extra": "allow"}


class IsisConfig(BaseModel):
    name: str | None = None
    model_config = {"extra": "allow"}


class RoutingConfig(BaseModel):
    static_routes: list[StaticRoute] = Field(default_factory=list)
    ospf_processes: list[OspfProcess] = Field(default_factory=list)
    bgp: BgpConfig | None = None
    isis: IsisConfig | None = None


class VrfAddressFamily(BaseModel):
    model_config = {"extra": "allow"}


class Vrf(BaseModel):
    name: str
    description: str | None = None
    route_distinguisher: str | None = None
    rd_auto: bool | None = None
    address_family_ipv4: VrfAddressFamily | None = None
    address_family_ipv6: VrfAddressFamily | None = None
    model_config = {"extra": "allow"}


class DeviceInterfaces(BaseModel):
    """NaC interfaces.* container — flat parser list maps into typed buckets."""

    loopbacks: list[Interface] = Field(default_factory=list)
    ethernets: list[Interface] = Field(default_factory=list)
    vlans: list[Interface] = Field(default_factory=list)
    tunnels: list[Interface] = Field(default_factory=list)
    port_channels: list[Interface] = Field(default_factory=list)
    port_channel_subinterfaces: list[Interface] = Field(default_factory=list)
    ethernet_subinterfaces: list[Interface] = Field(default_factory=list)
    bdis: list[Interface] = Field(default_factory=list)
    nves: list[Interface] = Field(default_factory=list)

    _KIND_TO_ATTR: dict[str, str] = {
        "loopback": "loopbacks",
        "ethernet": "ethernets",
        "vlan": "vlans",
        "tunnel": "tunnels",
        "port_channel": "port_channels",
        "port_channel_subinterface": "port_channel_subinterfaces",
        "ethernet_subinterface": "ethernet_subinterfaces",
        "bdi": "bdis",
        "nve": "nves",
    }

    def all_flat(self) -> list[Interface]:
        return (
            self.loopbacks
            + self.ethernets
            + self.vlans
            + self.tunnels
            + self.port_channels
            + self.port_channel_subinterfaces
            + self.ethernet_subinterfaces
            + self.bdis
            + self.nves
        )

    def get(self, name: str) -> Interface | None:
        for iface in self.all_flat():
            if iface.name.lower() == name.lower():
                return iface
        return None

    def upsert(self, iface: Interface) -> None:
        attr = self._KIND_TO_ATTR.get(iface.kind, "ethernets")
        bucket: list[Interface] = getattr(self, attr)
        existing = self.get(iface.name)
        if existing:
            idx = bucket.index(existing)
            bucket[idx] = iface
        else:
            bucket.append(iface)

    def set_from_flat(self, interfaces: list[Interface]) -> None:
        self.loopbacks = []
        self.ethernets = []
        self.vlans = []
        self.tunnels = []
        self.port_channels = []
        self.port_channel_subinterfaces = []
        self.ethernet_subinterfaces = []
        self.bdis = []
        self.nves = []
        for iface in interfaces:
            self.upsert(iface)


class VlanConfig(BaseModel):
    model_config = {"extra": "allow"}


class InterfaceTemplate(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class SnmpServerConfig(BaseModel):
    model_config = {"extra": "allow"}


class NtpConfig(BaseModel):
    model_config = {"extra": "allow"}


class LoggingConfig(BaseModel):
    model_config = {"extra": "allow"}


class DhcpConfig(BaseModel):
    model_config = {"extra": "allow"}


class DhcpPool(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class Ipv6DhcpPool(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class NatConfig(BaseModel):
    model_config = {"extra": "allow"}


class BfdConfig(BaseModel):
    model_config = {"extra": "allow"}


class CdpConfig(BaseModel):
    model_config = {"extra": "allow"}


class LldpConfig(BaseModel):
    model_config = {"extra": "allow"}


class SpanningTreeConfig(BaseModel):
    model_config = {"extra": "allow"}


class UdldConfig(BaseModel):
    model_config = {"extra": "allow"}


class VtpConfig(BaseModel):
    model_config = {"extra": "allow"}


class LicenseConfig(BaseModel):
    model_config = {"extra": "allow"}


class CryptoConfig(BaseModel):
    model_config = {"extra": "allow"}


class FlowConfig(BaseModel):
    model_config = {"extra": "allow"}


class EvpnConfig(BaseModel):
    model_config = {"extra": "allow"}


class EvpnProfile(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class MplsConfig(BaseModel):
    model_config = {"extra": "allow"}


class PimConfig(BaseModel):
    model_config = {"extra": "allow"}


class MsdpConfig(BaseModel):
    model_config = {"extra": "allow"}


class MulticastConfig(BaseModel):
    model_config = {"extra": "allow"}


class ErrdisableConfig(BaseModel):
    model_config = {"extra": "allow"}


class Dot1xConfig(BaseModel):
    model_config = {"extra": "allow"}


class EemConfig(BaseModel):
    model_config = {"extra": "allow"}


class CtsConfig(BaseModel):
    model_config = {"extra": "allow"}


class DeviceSensorConfig(BaseModel):
    model_config = {"extra": "allow"}


class DeviceTrackingConfig(BaseModel):
    model_config = {"extra": "allow"}


class BridgeDomain(BaseModel):
    model_config = {"extra": "allow"}


class L2Vfi(BaseModel):
    model_config = {"extra": "allow"}


class Sla(BaseModel):
    model_config = {"extra": "allow"}


class MdtSubscription(BaseModel):
    model_config = {"extra": "allow"}


class ZoneSecurity(BaseModel):
    model_config = {"extra": "allow"}


class ZonePairSecurity(BaseModel):
    model_config = {"extra": "allow"}


class ServiceConfig(BaseModel):
    model_config = {"extra": "allow"}


class ServiceTemplate(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class ArpConfig(BaseModel):
    model_config = {"extra": "allow"}


class RadiusConfig(BaseModel):
    model_config = {"extra": "allow"}


class TacacsServerConfig(BaseModel):
    model_config = {"extra": "allow"}


class DeviceConfiguration(BaseModel):
    """Full iosxe.devices[].configuration.* shape (netascode/nac-iosxe/iosxe)."""

    system: DeviceSystem = Field(default_factory=DeviceSystem)
    users: list[UserAccount] = Field(default_factory=list)
    banner: BannerConfig | None = None
    clock: ClockConfig | None = None
    line: LineConfig | None = None
    aaa: AaaConfig | None = None
    access_lists: AccessListsConfig | None = None
    as_path_access_lists: list[NamedListEntry] = Field(default_factory=list)
    community_lists: CommunityListsConfig | None = None
    prefix_lists: list[PrefixList] = Field(default_factory=list)
    route_maps: list[RouteMap] = Field(default_factory=list)
    policy: PolicyConfig | None = None
    class_maps: list[ClassMap] = Field(default_factory=list)
    policy_maps: list[PolicyMap] = Field(default_factory=list)
    parameter_maps: list[ParameterMap] = Field(default_factory=list)
    key_chains: list[KeyChain] = Field(default_factory=list)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    vrfs: list[Vrf] = Field(default_factory=list)
    interfaces: DeviceInterfaces = Field(default_factory=DeviceInterfaces)
    vlan: VlanConfig | None = None
    templates: list[InterfaceTemplate] = Field(default_factory=list)
    snmp_server: SnmpServerConfig | None = None
    ntp: NtpConfig | None = None
    logging: LoggingConfig | None = None
    dhcp: DhcpConfig | None = None
    dhcp_pools: list[DhcpPool] = Field(default_factory=list)
    ipv6_dhcp_pools: list[Ipv6DhcpPool] = Field(default_factory=list)
    nat: NatConfig | None = None
    bfd: BfdConfig | None = None
    cdp: CdpConfig | None = None
    lldp: LldpConfig | None = None
    spanning_tree: SpanningTreeConfig | None = None
    udld: UdldConfig | None = None
    vtp: VtpConfig | None = None
    license: LicenseConfig | None = None
    crypto: CryptoConfig | None = None
    flow: FlowConfig | None = None
    evpn: EvpnConfig | None = None
    evpn_profile: list[EvpnProfile] = Field(default_factory=list)
    mpls: MplsConfig | None = None
    pim: PimConfig | None = None
    msdp: MsdpConfig | None = None
    multicast: MulticastConfig | None = None
    errdisable: ErrdisableConfig | None = None
    dot1x: Dot1xConfig | None = None
    eem: EemConfig | None = None
    cts: CtsConfig | None = None
    device_sensor: DeviceSensorConfig | None = None
    device_tracking: DeviceTrackingConfig | None = None
    bridge_domain: list[BridgeDomain] = Field(default_factory=list)
    l2_vfi: list[L2Vfi] = Field(default_factory=list)
    sla: list[Sla] = Field(default_factory=list)
    mdt_subscription: list[MdtSubscription] = Field(default_factory=list)
    zone_security: list[ZoneSecurity] = Field(default_factory=list)
    zone_pair_security: list[ZonePairSecurity] = Field(default_factory=list)
    service: ServiceConfig | None = None
    service_templates: list[ServiceTemplate] = Field(default_factory=list)
    arp: ArpConfig | None = None
    radius: RadiusConfig | None = None
    tacacs_server: TacacsServerConfig | None = None

    def section_is_empty(self, key: str) -> bool:
        """True when a top-level section has no modeled content yet."""
        value = getattr(self, key)
        if value is None:
            return True
        if isinstance(value, list):
            return len(value) == 0
        if isinstance(value, BaseModel):
            if isinstance(value, DeviceSystem):
                return not (value.hostname or value.ipv6_unicast_routing or value.mtu)
            if isinstance(value, DeviceInterfaces):
                return not value.all_flat()
            if isinstance(value, RoutingConfig):
                return not (
                    value.static_routes
                    or value.ospf_processes
                    or value.bgp
                    or value.isis
                )
            if isinstance(value, AccessListsConfig):
                return not (value.standard or value.extended or value.role_based)
            if isinstance(value, CommunityListsConfig):
                return not (value.standard or value.expanded)
            dumped = value.model_dump(exclude_none=True)
            return len(dumped) == 0
        return False


# ---------------------------------------------------------------------------
# Parser / API helpers (unchanged surface for ios_cli + tests)
# ---------------------------------------------------------------------------


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
    configuration: DeviceConfiguration = Field(default_factory=DeviceConfiguration)
    secrets_redacted: bool = False

    @model_validator(mode="before")
    @classmethod
    def _lift_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        config = dict(data.get("configuration") or {})
        for legacy_key in ("system", "interfaces", "static_routes"):
            if legacy_key in data and legacy_key not in config:
                if legacy_key == "static_routes":
                    routing = dict(config.get("routing") or {})
                    routing["static_routes"] = data.pop("static_routes")
                    config["routing"] = routing
                elif legacy_key == "interfaces":
                    flat = data.pop("interfaces")
                    iface_container = DeviceInterfaces()
                    if isinstance(flat, list):
                        iface_container.set_from_flat([Interface.model_validate(i) for i in flat])
                    config["interfaces"] = iface_container.model_dump()
                else:
                    config[legacy_key] = data.pop(legacy_key)
        data["configuration"] = config
        return data

    @property
    def system(self) -> DeviceSystem:
        return self.configuration.system

    @system.setter
    def system(self, value: DeviceSystem) -> None:
        self.configuration.system = value

    @property
    def interfaces(self) -> list[Interface]:
        return self.configuration.interfaces.all_flat()

    @interfaces.setter
    def interfaces(self, value: list[Interface]) -> None:
        self.configuration.interfaces.set_from_flat(value)

    @property
    def static_routes(self) -> list[StaticRoute]:
        return self.configuration.routing.static_routes

    @static_routes.setter
    def static_routes(self, value: list[StaticRoute]) -> None:
        self.configuration.routing.static_routes = value

    @model_serializer(mode="wrap")
    def _serialize_with_legacy_fields(self, handler: Any) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        data["system"] = self.configuration.system.model_dump()
        data["interfaces"] = [i.model_dump() for i in self.configuration.interfaces.all_flat()]
        data["static_routes"] = [r.model_dump() for r in self.configuration.routing.static_routes]
        return data

    def get_interface(self, name: str) -> Interface | None:
        return self.configuration.interfaces.get(name)

    def upsert_interface(self, iface: Interface) -> None:
        self.configuration.interfaces.upsert(iface)

    @property
    def loopbacks(self) -> list[Interface]:
        return self.configuration.interfaces.loopbacks

    @property
    def ethernets(self) -> list[Interface]:
        return self.configuration.interfaces.ethernets

    @property
    def tunnels(self) -> list[Interface]:
        return self.configuration.interfaces.tunnels

    @property
    def vlans(self) -> list[Interface]:
        return self.configuration.interfaces.vlans
