"""Tests for IOS CLI parser and nac.yaml generator."""

from app.generators.nac_yaml import generate_nac_yaml
from app.parsers.ios_cli import parse_cli


def test_hostname_abbrev():
    result = parse_cli("hostn R1")
    assert result.device.system.hostname == "R1"
    yaml_out = generate_nac_yaml(result.device).content
    assert 'hostname: "R1"' in yaml_out
    assert "iosxe:" in yaml_out


def test_loopback_full_example():
    cli = """hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255"""
    result = parse_cli(cli)
    device = result.device
    assert device.system.hostname == "R1"
    lo0 = device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.shutdown is False
    assert lo0.ipv4_address == "10.0.0.1"
    assert lo0.ipv4_address_mask == "255.255.255.255"

    yaml_out = generate_nac_yaml(device).content
    assert "loopbacks:" in yaml_out
    assert 'address: "10.0.0.1"' in yaml_out
    assert 'hostname: "R1"' in yaml_out


def test_scaffold_never_blank():
    yaml_out = generate_nac_yaml(parse_cli("").device).content
    assert "iosxe:" in yaml_out
    assert "devices:" in yaml_out
    assert "interfaces:" in yaml_out
    assert "Generated · Not applied" in yaml_out
    assert "Schema version: 4.0.0" in yaml_out
    assert "iosxe-devices-configuration-full" in yaml_out
    assert "netascode.cisco.com/docs/data_models/iosxe/overview/" in yaml_out
    assert "loopbacks:" not in yaml_out


def test_ethernet_only_no_phantom_loopback():
    cli = """hostn R1
int g0/0
ip add 1.1.1.1 255.0.0.0"""
    yaml_out = generate_nac_yaml(parse_cli(cli).device).content
    assert "ethernets:" in yaml_out
    assert 'address: "1.1.1.1"' in yaml_out
    assert "loopbacks:" not in yaml_out


def test_gigabit_interface_and_dhcp():
    cli = """hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
int g0/0/0
no sh
ip add ip add dhcp"""
    result = parse_cli(cli)
    gi = result.device.get_interface("GigabitEthernet0/0/0")
    assert gi is not None
    assert gi.ipv4_dhcp is True
    assert gi.shutdown is False

    yaml_out = generate_nac_yaml(result.device).content
    assert "GigabitEthernet" in yaml_out
    assert "id: 0/0/0" in yaml_out
    assert "address: dhcp" in yaml_out


def test_double_ip_add_expansion():
    result = parse_cli("int lo0\nip add ip add dhcp")
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv4_dhcp is True


def test_tunnel_interface():
    cli = """int g1/1
ip add dhcp
int tun10
ip add 172.16.1.1 255.255.255.0"""
    result = parse_cli(cli)
    g1 = result.device.get_interface("GigabitEthernet1/1")
    tun = result.device.get_interface("Tunnel10")
    assert g1 is not None
    assert g1.ipv4_dhcp is True
    assert tun is not None
    assert tun.ipv4_address == "172.16.1.1"
    assert tun.ipv4_address_mask == "255.255.255.0"

    yaml_out = generate_nac_yaml(result.device).content
    assert "tunnels:" in yaml_out
    assert "id: '10'" in yaml_out
    assert 'address: "172.16.1.1"' in yaml_out


def test_loopback_spaced():
    result = parse_cli("int lo 999\nip add 10.0.0.1 255.255.255.255")
    lo = result.device.get_interface("Loopback999")
    assert lo is not None
    assert lo.loopback_id == "999"
    assert lo.ipv4_address == "10.0.0.1"
    assert len(result.warnings) == 0
    yaml_out = generate_nac_yaml(result.device).content
    assert "id: '999'" in yaml_out


def test_gigabit_interface_spaced():
    result = parse_cli("int g 0/0\nip add 1.1.1.1 255.0.0.0")
    gi = result.device.get_interface("GigabitEthernet0/0")
    assert gi is not None
    assert gi.ipv4_address == "1.1.1.1"
    assert len(result.warnings) == 0
    yaml_out = generate_nac_yaml(result.device).content
    assert "id: 0/0" in yaml_out


def test_tunnel_interface_spaced():
    result = parse_cli("int tun 10\nip add 172.16.1.1 255.255.255.0")
    tun = result.device.get_interface("Tunnel10")
    assert tun is not None
    assert tun.ipv4_address == "172.16.1.1"
    assert len(result.warnings) == 0
    yaml_out = generate_nac_yaml(result.device).content
    assert "tunnels:" in yaml_out
    assert "id: '10'" in yaml_out


def test_vlan_interface_spaced():
    result = parse_cli("int vlan 888\nip add 192.168.88.1 255.255.255.0")
    vlan = result.device.get_interface("Vlan888")
    assert vlan is not None
    assert vlan.vlan_id == "888"
    assert vlan.ipv4_address == "192.168.88.1"
    assert len(result.warnings) == 0
    yaml_out = generate_nac_yaml(result.device).content
    assert "vlans:" in yaml_out
    assert "id: '888'" in yaml_out


def test_line_mappings():
    from app.main import sync
    from app.main import SyncRequest

    resp = sync(SyncRequest(cli_text="hostn R1\nint lo0\nip add 10.0.0.1 255.255.255.255"))
    assert len(resp.mappings) >= 3
    hostname_map = next(m for m in resp.mappings if m.field_key == "system.hostname")
    assert hostname_map.cli_line == 1
    assert hostname_map.yaml_start_line == hostname_map.yaml_end_line
    lo_map = next(m for m in resp.mappings if m.field_key == "interface:Loopback0")
    assert lo_map.cli_line == 2
    assert lo_map.yaml_end_line > lo_map.yaml_start_line


def test_unknown_interface_warning():
    cli = """int lo0
int bvi999
ip add 1.2.3.4 255.255.255.0"""
    result = parse_cli(cli)
    assert len(result.warnings) == 1
    assert result.warnings[0].line == 2
    assert "bvi999" in result.warnings[0].message
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv4_address is None


def test_ipv6_address_cidr():
    cli = """int lo0
no sh
ipv6 enable
ipv6 address 2001:db8::1/64"""
    result = parse_cli(cli)
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv6_enable is True
    assert len(lo0.ipv6_addresses) == 1
    assert lo0.ipv6_addresses[0].prefix == "2001:db8::1"
    assert lo0.ipv6_addresses[0].prefix_length == 64

    yaml_out = generate_nac_yaml(result.device).content
    assert "ipv6:" in yaml_out
    assert "enable: true" in yaml_out
    assert 'prefix: "2001:db8::1/64"' in yaml_out


def test_ipv6_address_abbrev_and_eui64():
    cli = """int g0/0
ipv6 add 2001:db8::/64 eui-64"""
    result = parse_cli(cli)
    gi = result.device.get_interface("GigabitEthernet0/0")
    assert gi is not None
    assert gi.ipv6_enable is True
    assert len(gi.ipv6_addresses) == 1
    assert gi.ipv6_addresses[0].prefix == "2001:db8::"
    assert gi.ipv6_addresses[0].prefix_length == 64
    assert gi.ipv6_addresses[0].eui_64 is True

    yaml_out = generate_nac_yaml(result.device).content
    assert 'prefix: "2001:db8::/64"' in yaml_out
    assert "eui_64: true" in yaml_out


def test_ipv6_dhcp_and_link_local():
    cli = """int vlan888
ipv6 address dhcp
ipv6 address FE80::1 link-local"""
    result = parse_cli(cli)
    vlan = result.device.get_interface("Vlan888")
    assert vlan is not None
    assert vlan.ipv6_dhcp is True
    assert vlan.ipv6_link_local_addresses == ["FE80::1"]

    yaml_out = generate_nac_yaml(result.device).content
    assert "address_dhcp: true" in yaml_out
    assert 'link_local_addresses:' in yaml_out
    assert '"FE80::1"' in yaml_out


def test_ipv6_line_mappings():
    from app.main import sync
    from app.main import SyncRequest

    resp = sync(SyncRequest(cli_text="int lo0\nipv6 address 2001:db8::1/64"))
    ipv6_map = next(m for m in resp.mappings if m.field_key == "interface:Loopback0:ipv6")
    assert ipv6_map.cli_line == 2
    assert ipv6_map.yaml_end_line > ipv6_map.yaml_start_line


def test_ipv6_link_local_spaced():
    result = parse_cli("int lo0\nipv6 address fe80::1 link local")
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv6_link_local_addresses == ["fe80::1"]


def test_ipv6_link_local_abbrev():
    result = parse_cli("int lo0\nipv6 address fe80::1 link")
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv6_link_local_addresses == ["fe80::1"]
    assert lo0.ipv6_addresses == []

    yaml_out = generate_nac_yaml(result.device).content
    assert "link_local_addresses:" in yaml_out
    assert '"fe80::1"' in yaml_out
    assert yaml_out.count("- prefix:") == 0


def test_ipv6_unicast_routing_global():
    result = parse_cli("ipv6 unicast-routing")
    assert result.device.system.ipv6_unicast_routing is True
    yaml_out = generate_nac_yaml(result.device).content
    assert "ipv6_unicast_routing: true" in yaml_out


def test_ipv6_unicast_routing_from_interface_context():
    cli = """hostn R1
int lo0
ipv6 unicast-routing"""
    result = parse_cli(cli)
    assert result.device.system.ipv6_unicast_routing is True
    yaml_out = generate_nac_yaml(result.device).content
    assert 'hostname: "R1"' in yaml_out
    assert "ipv6_unicast_routing: true" in yaml_out


def test_ipv6_unicast_routing_exits_interface_context():
    cli = """int lo0
ip add 1.1.1.1 255.255.255.255
ipv6 unicast-routing
ip add 2.2.2.2 255.255.255.255"""
    result = parse_cli(cli)
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv4_address == "1.1.1.1"
    assert lo0.ipv4_address_mask == "255.255.255.255"
    assert result.device.system.ipv6_unicast_routing is True
    assert result.context_by_line[2] == "Loopback0"
    assert result.context_by_line[3] is None
    assert result.context_by_line[4] is None


def test_exit_returns_to_global_context():
    result = parse_cli("int lo0\nno sh\nexit\nip add 9.9.9.9 255.255.255.0")
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.shutdown is False
    assert lo0.ipv4_address is None
    assert result.context_by_line[4] is None


def test_health_capability_manifest():
    from app.main import health
    from app.version import API_VERSION, BUILD_ID, FEATURES

    payload = health()
    assert payload["status"] == "ok"
    assert payload["api_version"] == API_VERSION
    assert payload["build_id"] == BUILD_ID
    assert "ipv6_unicast_routing" in payload["features"]
    assert payload["features"] == FEATURES


def test_sync_includes_capability_manifest():
    from app.main import sync
    from app.main import SyncRequest
    from app.version import BUILD_ID

    resp = sync(SyncRequest(cli_text="ipv6 unicast-routing"))
    assert resp.build_id == BUILD_ID
    assert "ipv6_unicast_routing" in resp.features
    assert resp.canonical.system.ipv6_unicast_routing is True


def test_ipv6_multiple_addresses_on_interface():
    cli = """int lo0
no sh
ipv6 enable
ipv6 address 2001:db8::1/64
ipv6 address 2001:db8:1::1/64
ipv6 address 2001:db8:2::1 128
ipv6 address FE80::1 link-local"""
    result = parse_cli(cli)
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv6_enable is True
    assert len(lo0.ipv6_addresses) == 3
    assert lo0.ipv6_addresses[0].prefix == "2001:db8::1"
    assert lo0.ipv6_addresses[1].prefix == "2001:db8:1::1"
    assert lo0.ipv6_addresses[2].prefix == "2001:db8:2::1"
    assert lo0.ipv6_addresses[2].prefix_length == 128
    assert lo0.ipv6_link_local_addresses == ["FE80::1"]

    yaml_out = generate_nac_yaml(result.device).content
    assert yaml_out.count("- prefix:") == 3
    assert 'prefix: "2001:db8::1/64"' in yaml_out
    assert 'prefix: "2001:db8:1::1/64"' in yaml_out
    assert 'prefix: "2001:db8:2::1/128"' in yaml_out
    assert 'link_local_addresses:' in yaml_out
    assert '"FE80::1"' in yaml_out


def test_generate_restconf_json_loopback():
    from app.generators.restconf import generate_restconf_json

    cli = """hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64
ipv6 address 2001:db8:1::1/64"""
    device = parse_cli(cli).device
    payload = generate_restconf_json(device)
    assert "ietf-interfaces:interfaces" in payload
    assert '"hostname": "R1"' in payload
    assert "Loopback0" in payload
    assert "2001:db8::1/64" in payload
    assert "2001:db8:1::1/64" in payload
    assert "_network_lens_preview" in payload


def test_sync_includes_restconf_json():
    from app.main import SyncRequest, sync

    resp = sync(
        SyncRequest(
            cli_text="hostn R1\nint lo0\nno sh\nip add 10.0.0.1 255.255.255.255",
        ),
    )
    assert "ietf-interfaces:interfaces" in resp.restconf_json
    assert "restconf_json_preview" in resp.features


def test_full_schema_scaffold_hints():
    """Empty CLI shows comment hints for unwired NaC sections (apply-safe)."""
    from app.nac_sections import NAC_CONFIGURATION_SECTIONS

    yaml_out = generate_nac_yaml(parse_cli("").device).content
    assert "users:  # ← type: username admin secret" in yaml_out
    assert "vrfs:  # ← type: vrf definition MGMT" in yaml_out
    assert "aaa:  # ← type: aaa new-model" in yaml_out
    assert "routing:" in yaml_out
    assert "ospf_processes:  # ← type: router ospf 1" in yaml_out
    assert "port_channels:  # ← type: int po1" in yaml_out
    assert "loopbacks:" not in yaml_out
    for section in NAC_CONFIGURATION_SECTIONS:
        assert f"{section.key}:" in yaml_out or f"{section.key}:  #" in yaml_out


def test_device_has_full_configuration_shape():
    device = parse_cli("hostn R1").device
    config = device.configuration
    assert config.system.hostname == "R1"
    assert hasattr(config, "users")
    assert hasattr(config, "vrfs")
    assert hasattr(config, "routing")
    assert hasattr(config.interfaces, "port_channels")
    assert device.system.hostname == "R1"
    dumped = device.model_dump()
    assert "configuration" in dumped
    assert dumped["system"]["hostname"] == "R1"
