"""NaC iosxe.devices[].configuration.* top-level sections (terraform-iosxe-nac-iosxe).

Source of truth: netascode/terraform-iosxe-nac-iosxe device_config lookups.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NacSection:
    """Metadata for a configuration.* section."""

    key: str
    hint: str
    story: str | None = None  # Jira story that wires CLI → model → yaml


# Top-level keys under iosxe.devices[].configuration.*
# Order matches typical NaC YAML layout and epic backlog sequencing.
NAC_CONFIGURATION_SECTIONS: tuple[NacSection, ...] = (
    NacSection("system", "type: hostn R1 | ipv6 unicast-routing | mtu 9198", "NDO-173"),
    NacSection("users", "type: username admin secret ...", "NDO-172"),
    NacSection("banner", "type: banner motd ^C...^C", "NDO-173"),
    NacSection("clock", "type: clock timezone EST -5", "NDO-173"),
    NacSection("line", "type: line vty 0 15 ..."),
    NacSection("aaa", "type: aaa new-model ...", "NDO-180"),
    NacSection("access_lists", "type: ip access-list standard ...", "NDO-178"),
    NacSection("as_path_access_lists", "type: ip as-path access-list ..."),
    NacSection("community_lists", "type: ip community-list standard ..."),
    NacSection("prefix_lists", "type: ip prefix-list ...", "NDO-179"),
    NacSection("route_maps", "type: route-map RM permit 10", "NDO-179"),
    NacSection("policy", "type: policy ..."),
    NacSection("class_maps", "type: class-map match-all ..."),
    NacSection("policy_maps", "type: policy-map ..."),
    NacSection("parameter_maps", "type: parameter-map type ..."),
    NacSection("key_chains", "type: key chain ..."),
    NacSection("routing", "type: router ospf 1 | router bgp ... | router eigrp LAB", "NDO-174"),
    NacSection("vrfs", "type: vrf definition MGMT", "NDO-177"),
    NacSection("interfaces", "type: int lo0 | int g0/0/0 | int po1 | int nve1", "NDO-183"),
    NacSection("vlan", "type: vlan 10 ..."),
    NacSection("templates", "type: template ..."),
    NacSection("snmp_server", "type: snmp-server community ...", "NDO-181"),
    NacSection("ntp", "type: ntp server 10.0.0.1", "NDO-181"),
    NacSection("logging", "type: logging buffered 16384"),
    NacSection("dhcp", "type: ip dhcp ...", "NDO-182"),
    NacSection("dhcp_pools", "type: ip dhcp pool LAN"),
    NacSection("ipv6_dhcp_pools", "type: ipv6 dhcp pool ..."),
    NacSection("nat", "type: ip nat inside source ...", "NDO-182"),
    NacSection("bfd", "type: bfd ..."),
    NacSection("cdp", "type: cdp run"),
    NacSection("lldp", "type: lldp run"),
    NacSection("spanning_tree", "type: spanning-tree mode rapid-pvst"),
    NacSection("udld", "type: udld enable"),
    NacSection("vtp", "type: vtp mode transparent"),
    NacSection("license", "type: license udi pid ..."),
    NacSection("crypto", "type: crypto ikev2 proposal ...", "NDO-185"),
    NacSection("flow", "type: flow exporter ..."),
    NacSection("evpn", "type: l2vpn evpn ...", "NDO-184"),
    NacSection("evpn_profile", "type: evpn profile ...", "NDO-184"),
    NacSection("mpls", "type: mpls label protocol ldp", "NDO-184"),
    NacSection("pim", "type: ip pim ..."),
    NacSection("msdp", "type: ip msdp ..."),
    NacSection("multicast", "type: ip multicast-routing"),
    NacSection("errdisable", "type: errdisable recovery ..."),
    NacSection("dot1x", "type: dot1x system-auth-control"),
    NacSection("eem", "type: event manager applet ..."),
    NacSection("cts", "type: cts role-based ..."),
    NacSection("device_sensor", "type: device-sensor filter-spec ..."),
    NacSection("device_tracking", "type: device-tracking policy ..."),
    NacSection("bridge_domain", "type: bridge-domain ..."),
    NacSection("l2_vfi", "type: l2 vfi ..."),
    NacSection("sla", "type: ip sla ..."),
    NacSection("mdt_subscription", "type: mdt subscription ..."),
    NacSection("zone_security", "type: zone security ..."),
    NacSection("zone_pair_security", "type: zone-pair security ..."),
    NacSection("service", "type: service ..."),
    NacSection("service_templates", "type: service-template ..."),
    NacSection("arp", "type: arp ..."),
    NacSection("radius", "type: radius-server host ..."),
    NacSection("tacacs_server", "type: tacacs-server host ..."),
)

# Sub-keys under routing.* (shown when routing section is empty of wired content)
ROUTING_SUBSECTION_HINTS: tuple[NacSection, ...] = (
    NacSection("static_routes", "type: ip route 0.0.0.0 0.0.0.0 ..."),
    NacSection("ospf_processes", "type: router ospf 1", "NDO-174"),
    NacSection("bgp", "type: router bgp 65000", "NDO-175"),
    NacSection("isis", "type: router isis CORE", "NDO-176"),
    NacSection(
        "eigrp_processes",
        "type: router eigrp LAB | address-family ipv4 unicast autonomous-system 100",
    ),
)
