"""EIGRP and DMVPN/NHRP parsing against the NaC IOS-XE schema."""

from app.generators.ios_cli import generate_ios_cli
from app.generators.nac_yaml import generate_nac_yaml
from app.generators.restconf import generate_restconf_json
from app.generators.terraform import generate_terraform
from app.parsers.ios_cli import parse_cli

NAMED_EIGRP = """router eigrp LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 192.0.2.1
  network 10.10.0.0 0.0.255.255
  network 10.20.0.0 0.0.0.255
  no auto-summary
 exit-address-family
 address-family ipv4 unicast vrf RED autonomous-system 100
  eigrp router-id 192.0.2.2
  network 10.20.0.0 0.0.255.255
  shutdown
 exit-address-family
"""

CLASSIC_EIGRP = """router eigrp 100
 eigrp router-id 192.0.2.10
 network 10.0.0.0 0.255.255.255
 no auto-summary
 passive-interface GigabitEthernet0/0
 eigrp stub connected summary
 redistribute static
 network 10.1.0.0
"""

DMVPN = """interface Tunnel100
 description overlay
 ip address 10.0.0.1 255.255.255.0
 no shutdown
 ip nhrp authentication nhrp-key
 ip nhrp network-id 100
 ip nhrp nhs 10.0.0.254 nbma 192.0.2.11 multicast
 ip nhrp map 10.0.0.2 192.0.2.10
 ip nhrp map multicast dynamic
 ip nhrp redirect
 ip nhrp shortcut
 mpls nhrp
 tunnel source GigabitEthernet1
 tunnel destination 192.0.2.20
 tunnel mode gre multipoint
 tunnel key 10
 tunnel protection ipsec profile LAB-IPSEC shared
 tunnel mode gre ip
"""


def test_named_eigrp_global_and_vrf():
    result = parse_cli(NAMED_EIGRP)
    processes = result.device.configuration.routing.eigrp_processes
    assert len(processes) == 2

    global_proc = processes[0]
    assert global_proc.name == "LAB"
    assert global_proc.classic is False
    assert global_proc.autonomous_system == 100
    assert global_proc.vrf is None
    assert global_proc.router_id == "192.0.2.1"
    assert global_proc.auto_summary is False
    assert [(net.ip, net.wildcard) for net in global_proc.networks] == [
        ("10.10.0.0", "0.0.255.255"),
        ("10.20.0.0", "0.0.0.255"),
    ]

    vrf_proc = processes[1]
    assert vrf_proc.name == "LAB"
    assert vrf_proc.vrf == "RED"
    assert vrf_proc.autonomous_system == 100
    assert vrf_proc.router_id == "192.0.2.2"
    assert vrf_proc.shutdown is True
    assert vrf_proc.networks[0].ip == "10.20.0.0"
    assert vrf_proc.networks[0].wildcard == "0.0.255.255"

    yaml_out = generate_nac_yaml(result.device).content
    assert "eigrp_processes:" in yaml_out
    assert 'name: "LAB"' in yaml_out
    assert "autonomous_system: 100" in yaml_out
    assert 'router_id: "192.0.2.1"' in yaml_out
    assert 'router_id: "192.0.2.2"' in yaml_out
    assert "auto_summary: false" in yaml_out
    assert 'vrf: "RED"' in yaml_out
    assert "shutdown: true" in yaml_out
    assert 'wildcard: "0.0.255.255"' in yaml_out
    assert "topology_base" not in yaml_out

    tf_out = generate_terraform(result.device)
    assert 'resource "iosxe_eigrp" "eigrp_LAB"' in tf_out
    assert 'resource "iosxe_eigrp_vrf" "eigrp_LAB_RED"' in tf_out
    assert 'name = "LAB"' in tf_out
    assert "autonomous_system = 100" in tf_out
    assert 'vrf = "RED"' in tf_out
    assert 'router_id = "192.0.2.1"' in tf_out
    assert "auto_summary = false" in tf_out
    assert "shutdown = true" in tf_out
    assert 'ip = "10.10.0.0", wildcard = "0.0.255.255"' in tf_out
    assert "topology_base" not in tf_out

    restconf = generate_restconf_json(result.device)
    assert '"eigrp_processes"' in restconf
    assert '"autonomous_system": 100' in restconf
    assert '"vrf": "RED"' in restconf

    regen = generate_ios_cli(result.device)
    assert "router eigrp LAB" in regen
    assert "address-family ipv4 unicast autonomous-system 100" in regen
    assert "address-family ipv4 unicast vrf RED autonomous-system 100" in regen
    assert "eigrp router-id 192.0.2.1" in regen
    assert "network 10.10.0.0 0.0.255.255" in regen
    assert "no auto-summary" in regen
    assert "shutdown" in regen


def test_classic_eigrp_projects_supported_fields_and_omits_the_rest():
    result = parse_cli(CLASSIC_EIGRP)
    proc = result.device.configuration.routing.eigrp_processes[0]
    assert proc.classic is True
    assert proc.name == "100"
    assert proc.autonomous_system == 100
    assert proc.router_id == "192.0.2.10"
    assert proc.auto_summary is False
    assert len(proc.networks) == 1
    assert proc.networks[0].ip == "10.0.0.0"
    assert proc.networks[0].wildcard == "0.255.255.255"

    messages = [warning.message for warning in result.warnings]
    assert any("Classic EIGRP" in message for message in messages)
    assert any("passive-interface" in message for message in messages)
    assert any("stub" in message for message in messages)
    assert any("redistribute" in message for message in messages)
    assert any("wildcard" in message for message in messages)

    yaml_out = generate_nac_yaml(result.device).content
    assert 'name: "100"' in yaml_out
    assert "autonomous_system: 100" in yaml_out
    assert 'router_id: "192.0.2.10"' in yaml_out
    assert "auto_summary: false" in yaml_out
    assert "passive_interface" not in yaml_out
    assert "redistribute" not in yaml_out
    assert "stub" not in yaml_out

    tf_out = generate_terraform(result.device)
    assert 'resource "iosxe_eigrp" "eigrp_100"' in tf_out
    assert "autonomous_system = 100" in tf_out
    assert "passive" not in tf_out
    assert "redistribute" not in tf_out

    regen = generate_ios_cli(result.device)
    assert "router eigrp 100" in regen
    assert "network 10.0.0.0 0.255.255.255" in regen
    assert "eigrp router-id 192.0.2.10" in regen
    assert "address-family" not in regen


def test_named_eigrp_without_address_family_emits_nothing():
    result = parse_cli("router eigrp LAB")
    assert result.device.configuration.routing.eigrp_processes == []
    assert any("address-family" in warning.message for warning in result.warnings)
    assert "eigrp_processes:" not in generate_nac_yaml(result.device).content


def test_eigrp_ipv6_address_family_is_omitted():
    cli = """router eigrp LAB
 address-family ipv6 unicast autonomous-system 100
  eigrp router-id 192.0.2.1
"""
    result = parse_cli(cli)
    assert result.device.configuration.routing.eigrp_processes == []
    assert any("IPv6" in warning.message for warning in result.warnings)


def test_dmvpn_tunnel_nhrp_and_ipsec_profile():
    result = parse_cli(DMVPN)
    tun = result.device.get_interface("Tunnel100")
    assert tun is not None
    assert tun.tunnel_id == "100"
    assert tun.description == "overlay"
    assert tun.ipv4_address == "10.0.0.1"
    assert tun.ipv4_address_mask == "255.255.255.0"
    assert tun.shutdown is False
    assert tun.ip_nhrp_authentication == "nhrp-key"
    assert tun.ip_nhrp_network_id == 100
    assert [nhs.ipv4 for nhs in tun.ip_nhrp_nhs] == ["10.0.0.254"]
    assert len(tun.ip_nhrp_maps) == 1
    assert tun.ip_nhrp_maps[0].dest_ipv4 == "10.0.0.2"
    assert tun.ip_nhrp_maps[0].nbma_ipv4 == "192.0.2.10"
    assert tun.ip_nhrp_redirect is True
    assert tun.ip_nhrp_shortcut is True
    assert tun.mpls_nhrp is True
    assert tun.tunnel_source == "GigabitEthernet1"
    assert tun.tunnel_destination_ipv4 == "192.0.2.20"
    assert tun.tunnel_mode_gre_multipoint is True
    assert tun.tunnel_key == 10
    assert tun.tunnel_protection_ipsec_profile == "LAB-IPSEC"

    messages = [warning.message for warning in result.warnings]
    assert any("nbma/multicast" in message for message in messages)
    assert any("multicast/dynamic" in message for message in messages)
    assert any("shared" in message for message in messages)
    assert any("Tunnel mode is not in the NaC schema" in message for message in messages)

    yaml_out = generate_nac_yaml(result.device).content
    assert "tunnels:" in yaml_out
    assert "id: '100'" in yaml_out
    assert "name: 100" in yaml_out
    assert 'ip_nhrp_authentication: "nhrp-key"' in yaml_out
    assert "ip_nhrp_network_id: 100" in yaml_out
    assert 'ipv4: "10.0.0.254"' in yaml_out
    assert 'dest_ipv4: "10.0.0.2"' in yaml_out
    assert 'nbma_ipv4: "192.0.2.10"' in yaml_out
    assert "ip_nhrp_redirect: true" in yaml_out
    assert "ip_nhrp_shortcut: true" in yaml_out
    assert "mpls_nhrp: true" in yaml_out
    assert 'tunnel_source: "GigabitEthernet1"' in yaml_out
    assert 'tunnel_destination_ipv4: "192.0.2.20"' in yaml_out
    assert "tunnel_mode_gre_multipoint: true" in yaml_out
    assert "tunnel_key: 10" in yaml_out
    assert 'tunnel_protection_ipsec_profile: "LAB-IPSEC"' in yaml_out
    assert "multicast" not in yaml_out
    assert "shared" not in yaml_out

    tf_out = generate_terraform(result.device)
    assert 'resource "iosxe_interface_tunnel" "tun100"' in tf_out
    assert "name = 100" in tf_out
    assert 'ip_nhrp_authentication = "nhrp-key"' in tf_out
    assert "ip_nhrp_network_id = 100" in tf_out
    assert 'ipv4 = "10.0.0.254"' in tf_out
    assert 'dest_ipv4 = "10.0.0.2", nbma_ipv4 = "192.0.2.10"' in tf_out
    assert "ip_nhrp_redirect = true" in tf_out
    assert "ip_nhrp_shortcut = true" in tf_out
    assert "mpls_nhrp = true" in tf_out
    assert 'tunnel_source = "GigabitEthernet1"' in tf_out
    assert "tunnel_mode_gre_multipoint = true" in tf_out
    assert "tunnel_key = 10" in tf_out
    assert 'tunnel_protection_ipsec_profile = "LAB-IPSEC"' in tf_out
    assert "shared" not in tf_out

    restconf = generate_restconf_json(result.device)
    assert '"ip_nhrp_authentication": "nhrp-key"' in restconf
    assert '"tunnel_mode_gre_multipoint": true' in restconf
    assert '"tunnel_protection_ipsec_profile": "LAB-IPSEC"' in restconf

    regen = generate_ios_cli(result.device)
    assert "interface Tunnel100" in regen
    assert "ip nhrp authentication nhrp-key" in regen
    assert "ip nhrp network-id 100" in regen
    assert "ip nhrp nhs 10.0.0.254" in regen
    assert "ip nhrp map 10.0.0.2 192.0.2.10" in regen
    assert "tunnel mode gre multipoint" in regen
    assert "tunnel protection ipsec profile LAB-IPSEC" in regen
    assert "shared" not in regen
    assert "multicast" not in regen


def test_nhrp_authentication_stays_cleartext():
    result = parse_cli("interface Tunnel1\n ip nhrp authentication Nhrp-Key")
    tun = result.device.get_interface("Tunnel1")
    assert tun is not None
    assert tun.ip_nhrp_authentication == "Nhrp-Key"
    rendered = "\n".join(
        [
            generate_nac_yaml(result.device).content,
            generate_terraform(result.device),
            generate_restconf_json(result.device),
            generate_ios_cli(result.device),
        ]
    )
    assert "Nhrp-Key" in rendered
    assert "****" not in rendered
    assert "sha256" not in rendered.lower()


def test_named_eigrp_passive_stub_and_redistribute_are_omitted():
    cli = """router eigrp LAB
 address-family ipv4 unicast autonomous-system 100
  network 10.10.0.0 0.0.255.255
  af-interface default
   passive-interface
  exit-af-interface
  eigrp stub connected
  topology base
   redistribute static
"""
    result = parse_cli(cli)
    proc = result.device.configuration.routing.eigrp_processes[0]
    assert proc.autonomous_system == 100
    assert proc.networks[0].ip == "10.10.0.0"
    messages = [warning.message for warning in result.warnings]
    assert any("af-interface" in message for message in messages)
    assert any("passive-interface" in message for message in messages)
    assert any("stub" in message for message in messages)
    assert any("redistribute" in message for message in messages)
    assert any("topology" in message for message in messages)
    yaml_out = generate_nac_yaml(result.device).content
    assert "passive_interface" not in yaml_out
    assert "redistribute" not in yaml_out
    assert "topology_base" not in yaml_out


def test_tunnel_mode_ipsec_ipv4():
    result = parse_cli(
        "interface Tunnel20\n tunnel mode ipsec ipv4\n tunnel protection ipsec profile LAB-IPSEC\n"
    )
    tun = result.device.get_interface("Tunnel20")
    assert tun is not None
    assert tun.tunnel_mode_ipsec_ipv4 is True
    assert tun.tunnel_protection_ipsec_profile == "LAB-IPSEC"
    yaml_out = generate_nac_yaml(result.device).content
    assert "tunnel_mode_ipsec_ipv4: true" in yaml_out
    tf_out = generate_terraform(result.device)
    assert "tunnel_mode_ipsec_ipv4 = true" in tf_out
    assert 'tunnel_protection_ipsec_profile = "LAB-IPSEC"' in tf_out


def test_nhrp_on_ethernet_is_omitted():
    result = parse_cli("interface GigabitEthernet0/0\n ip nhrp network-id 100")
    gi = result.device.get_interface("GigabitEthernet0/0")
    assert gi is not None
    assert gi.ip_nhrp_network_id is None
    assert any("interfaces.tunnels" in warning.message for warning in result.warnings)
