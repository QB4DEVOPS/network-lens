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
    enable_secret_type: str | None = None
    enable_password: str | None = None
    enable_password_type: str | None = None


class Ipv6Address(BaseModel):
    prefix: str
    prefix_length: int | None = None
    eui_64: bool = False


class NhrpNhs(BaseModel):
    """NaC interfaces.tunnels[].ip_nhrp_nhs[] — ipv4 only."""

    ipv4: str


class NhrpMap(BaseModel):
    """NaC interfaces.tunnels[].ip_nhrp_maps[] — dest_ipv4 + nbma_ipv4."""

    dest_ipv4: str
    nbma_ipv4: str


class Interface(BaseModel):
    name: str
    kind: str = "loopback"  # loopback | ethernet | tunnel | vlan | port_channel | ...
    loopback_id: str | None = None
    ethernet_type: str | None = None
    ethernet_id: str | None = None
    tunnel_id: str | None = None
    vlan_id: str | None = None
    port_channel_id: str | None = None
    port_channel_mode: str | None = None
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
    vrf_forwarding: str | None = None
    nat_inside: bool = False
    nat_outside: bool = False
    tunnel_source: str | None = None
    tunnel_destination_ipv4: str | None = None
    tunnel_mode_gre_multipoint: bool | None = None
    tunnel_mode_ipsec_ipv4: bool | None = None
    tunnel_key: int | None = None
    tunnel_protection_ipsec_profile: str | None = None
    ip_nhrp_authentication: str | None = None
    ip_nhrp_network_id: int | None = None
    ip_nhrp_nhs: list[NhrpNhs] = Field(default_factory=list)
    ip_nhrp_maps: list[NhrpMap] = Field(default_factory=list)
    ip_nhrp_redirect: bool | None = None
    ip_nhrp_shortcut: bool | None = None
    mpls_nhrp: bool | None = None

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


class AaaAuthLogin(BaseModel):
    name: str
    methods: list[str] = Field(default_factory=list)


class AaaAuthenticationConfig(BaseModel):
    logins: list[AaaAuthLogin] = Field(default_factory=list)


class AaaAuthzExec(BaseModel):
    name: str
    methods: list[str] = Field(default_factory=list)


class AaaAuthorizationConfig(BaseModel):
    execs: list[AaaAuthzExec] = Field(default_factory=list)


class AaaAccountingExec(BaseModel):
    name: str
    action_type: str | None = None
    start_stop_groups: list[str] = Field(default_factory=list)
    stop_only_groups: list[str] = Field(default_factory=list)


class AaaAccountingConfig(BaseModel):
    execs: list[AaaAccountingExec] = Field(default_factory=list)


class AaaConfig(BaseModel):
    new_model: bool | None = None
    authentication: AaaAuthenticationConfig | None = None
    authorization: AaaAuthorizationConfig | None = None
    accounting: AaaAccountingConfig | None = None



class AccessListAce(BaseModel):
    sequence: int
    action: str
    prefix: str | None = None
    prefix_mask: str | None = None
    protocol: str | None = None
    source_any: bool | None = None
    destination_any: bool | None = None


class StandardAccessList(BaseModel):
    name: str
    entries: list[AccessListAce] = Field(default_factory=list)


class ExtendedAccessList(BaseModel):
    name: str
    entries: list[AccessListAce] = Field(default_factory=list)


class AccessListEntry(BaseModel):
    model_config = {"extra": "allow"}


class AccessListsConfig(BaseModel):
    standard: list[StandardAccessList] = Field(default_factory=list)
    extended: list[ExtendedAccessList] = Field(default_factory=list)
    role_based: list[AccessListEntry] = Field(default_factory=list)


class NamedListEntry(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class CommunityListsConfig(BaseModel):
    standard: list[NamedListEntry] = Field(default_factory=list)
    expanded: list[NamedListEntry] = Field(default_factory=list)


class PrefixListSeq(BaseModel):
    seq: int
    action: str | None = None
    prefix: str | None = None
    greater_equal: int | None = None
    less_equal: int | None = None


class PrefixList(BaseModel):
    name: str
    description: str | None = None
    seqs: list[PrefixListSeq] = Field(default_factory=list)


class RouteMapMatch(BaseModel):
    ipv4_address_prefix_lists: list[str] = Field(default_factory=list)
    ipv4_address_access_lists: list[str] = Field(default_factory=list)


class RouteMapSet(BaseModel):
    local_preference: int | None = None
    metric_value: int | None = None


class RouteMapEntry(BaseModel):
    seq: int
    operation: str | None = None
    description: str | None = None
    match: RouteMapMatch | None = None
    set: RouteMapSet | None = None


class RouteMap(BaseModel):
    name: str
    entries: list[RouteMapEntry] = Field(default_factory=list)


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


class OspfNetwork(BaseModel):
    ip: str
    wildcard: str | None = None
    area: str | int | None = None


class OspfPassiveInterface(BaseModel):
    interface_type: str | None = None
    interface_id: str | None = None


class OspfProcess(BaseModel):
    id: int | str
    router_id: str | None = None
    networks: list[OspfNetwork] = Field(default_factory=list)
    passive_interface_default: bool | None = None
    passive_interfaces: list[OspfPassiveInterface] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class BgpNeighbor(BaseModel):
    ip: str
    remote_as: int | str | None = None


class BgpNetwork(BaseModel):
    network: str
    mask: str | None = None


class BgpAddressFamilyIpv4Unicast(BaseModel):
    networks: list[BgpNetwork] = Field(default_factory=list)


class BgpAddressFamily(BaseModel):
    ipv4_unicast: BgpAddressFamilyIpv4Unicast | None = None


class BgpConfig(BaseModel):
    as_number: int | str | None = None
    neighbors: list[BgpNeighbor] = Field(default_factory=list)
    address_family: BgpAddressFamily | None = None
    model_config = {"extra": "allow"}


class IsisNet(BaseModel):
    tag: str


class IsisConfig(BaseModel):
    area_tag: str | None = None
    nets: list[IsisNet] = Field(default_factory=list)
    is_type: str | None = None
    model_config = {"extra": "allow"}


class EigrpNetwork(BaseModel):
    """NaC routing.eigrp_processes[].networks[] — both fields are mandatory upstream."""

    ip: str
    wildcard: str


class EigrpProcess(BaseModel):
    """NaC routing.eigrp_processes[] (named-mode shape).

    ``classic`` records ``router eigrp <asn>`` so CLI regen can keep that dialect.
    It is not a NaC key and is excluded from serialized output.
    """

    name: str
    autonomous_system: int | None = None
    vrf: str | None = None
    router_id: str | None = None
    networks: list[EigrpNetwork] = Field(default_factory=list)
    auto_summary: bool | None = None
    shutdown: bool | None = None
    classic: bool = Field(default=False, exclude=True)


class RoutingConfig(BaseModel):
    static_routes: list[StaticRoute] = Field(default_factory=list)
    ospf_processes: list[OspfProcess] = Field(default_factory=list)
    bgp: BgpConfig | None = None
    isis: IsisConfig | None = None
    eigrp_processes: list[EigrpProcess] = Field(default_factory=list)


class VrfAddressFamily(BaseModel):
    enable: bool | None = None
    import_route_targets: list[str] = Field(default_factory=list)
    export_route_targets: list[str] = Field(default_factory=list)


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


class SnmpCommunity(BaseModel):
    name: str
    permission: str | None = None
    encryption: str | None = None


class SnmpServerConfig(BaseModel):
    snmp_communities: list[SnmpCommunity] = Field(default_factory=list)
    contact: str | None = None
    location: str | None = None


class NtpServer(BaseModel):
    ip: str
    prefer: bool | None = None
    vrf: str | None = None


class NtpConfig(BaseModel):
    servers: list[NtpServer] = Field(default_factory=list)
    peers: list[NtpServer] = Field(default_factory=list)



class LoggingConfig(BaseModel):
    model_config = {"extra": "allow"}


class DhcpConfig(BaseModel):
    enabled: bool | None = None


class DhcpPool(BaseModel):
    name: str
    network_number: str | None = None
    network_mask: str | None = None
    default_routers: list[str] = Field(default_factory=list)
    dns_servers: list[str] = Field(default_factory=list)
    domain_name: str | None = None
    lease_days: int | None = None



class Ipv6DhcpPool(BaseModel):
    name: str
    model_config = {"extra": "allow"}


class NatInsideInterface(BaseModel):
    interface_type: str
    interface_id: str | None = None
    overload: bool | None = None


class NatInsideSource(BaseModel):
    id: int
    interfaces: list[NatInsideInterface] = Field(default_factory=list)


class NatConfig(BaseModel):
    inside_source_interfaces: list[NatInsideSource] = Field(default_factory=list)



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


class CryptoIkev2Proposal(BaseModel):
    name: str
    encryption: list[str] = Field(default_factory=list)
    group: list[str] = Field(default_factory=list)
    integrity: list[str] = Field(default_factory=list)
    prf: list[str] = Field(default_factory=list)


class CryptoIkev2Policy(BaseModel):
    name: str
    proposals: list[str] = Field(default_factory=list)
    match_fvrf: str | None = None
    match_fvrf_any: bool | None = None
    match_address_local_ip: list[str] = Field(default_factory=list)
    match_inbound_only: bool | None = None


class CryptoIkev2KeyringPeer(BaseModel):
    name: str
    description: str | None = None
    hostname: str | None = None
    ipv4_address: str | None = None
    ipv4_mask: str | None = None
    ipv6_prefix: str | None = None
    identity_fqdn_domain: str | None = None
    identity_key_id: str | None = None
    pre_shared_key: str | None = None
    pre_shared_key_local: str | None = None
    pre_shared_key_remote: str | None = None


class CryptoIkev2Keyring(BaseModel):
    name: str
    peers: list[CryptoIkev2KeyringPeer] = Field(default_factory=list)


class CryptoIkev2ProfileMatchRemoteIpv4(BaseModel):
    address: str
    mask: str | None = None


class CryptoIkev2Profile(BaseModel):
    name: str
    description: str | None = None
    authentication_local_pre_share: bool | None = None
    authentication_remote_pre_share: bool | None = None
    config_exchange_request: bool | None = None
    dpd_interval: int | None = None
    dpd_query: str | None = None
    dpd_retry: int | None = None
    identity_local_key_id: str | None = None
    ivrf: str | None = None
    keyring_local: str | None = None
    lifetime: int | None = None
    match_address_local_ip: str | None = None
    match_address_local_interface_loopback_legacy: int | None = None
    match_fvrf: str | None = None
    match_fvrf_any: bool | None = None
    match_identity_remote_ipv4_addresses: list[CryptoIkev2ProfileMatchRemoteIpv4] = Field(
        default_factory=list
    )
    match_identity_remote_ipv6_prefixes: list[str] = Field(default_factory=list)
    match_identity_remote_keys: list[str] = Field(default_factory=list)
    match_inbound_only: bool | None = None


class CryptoIkev2Config(BaseModel):
    nat_keepalive: int | None = None
    dpd_interval: int | None = None
    dpd_query: str | None = None
    dpd_retry: int | None = None
    proposals: list[CryptoIkev2Proposal] = Field(default_factory=list)
    policies: list[CryptoIkev2Policy] = Field(default_factory=list)
    keyrings: list[CryptoIkev2Keyring] = Field(default_factory=list)
    profiles: list[CryptoIkev2Profile] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return len(self.model_dump(exclude_none=True)) == 0


class CryptoIpsecTransformSet(BaseModel):
    name: str
    esp: str | None = None
    esp_hmac: str | None = None
    mode_tunnel: bool | None = None


class CryptoIpsecProfile(BaseModel):
    name: str
    set_transform_set: list[str] = Field(default_factory=list)
    set_ikev2_profile: str | None = None
    set_isakmp_profile: str | None = None
    set_pfs_group: str | None = None
    set_security_association_lifetime_seconds: int | None = None


class CryptoPkiTrustpoint(BaseModel):
    id: str
    enrollment_terminal: bool | None = None
    enrollment_selfsigned: bool | None = None
    rsakeypair: str | None = None
    subject_name: str | None = None
    usage: str | None = None
    revocation_check: list[str] = Field(default_factory=list)


class CryptoPkiConfig(BaseModel):
    trustpoints: list[CryptoPkiTrustpoint] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.trustpoints


class CryptoConfig(BaseModel):
    ipsec_profiles: list[CryptoIpsecProfile] = Field(default_factory=list)
    ipsec_transform_sets: list[CryptoIpsecTransformSet] = Field(default_factory=list)
    ikev2: CryptoIkev2Config | None = None
    pki: CryptoPkiConfig | None = None

    def is_empty(self) -> bool:
        return (
            not self.ipsec_profiles
            and not self.ipsec_transform_sets
            and (self.ikev2 is None or self.ikev2.is_empty())
            and (self.pki is None or self.pki.is_empty())
        )


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
                return not (
                    value.hostname
                    or value.ipv6_unicast_routing
                    or value.mtu
                    or value.enable_secret
                    or value.enable_password
                )
            if isinstance(value, DeviceInterfaces):
                return not value.all_flat()
            if isinstance(value, RoutingConfig):
                return not (
                    value.static_routes
                    or value.ospf_processes
                    or value.bgp
                    or value.isis
                    or value.eigrp_processes
                )
            if isinstance(value, AccessListsConfig):
                return not (value.standard or value.extended or value.role_based)
            if isinstance(value, CommunityListsConfig):
                return not (value.standard or value.expanded)
            if isinstance(value, CryptoConfig):
                return value.is_empty()
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
