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

    yaml_out = generate_nac_yaml(parse_cli("").device, show_hints=True).content
    assert "users:  # ← type: username admin secret" in yaml_out
    assert "vrfs:  # ← type: vrf definition MGMT" in yaml_out
    assert "aaa:  # ← type: aaa new-model" in yaml_out
    assert "routing:" in yaml_out
    assert "ospf_processes:  # ← type: router ospf 1" in yaml_out
    assert "port_channels:  # ← type: int po1" in yaml_out
    assert "loopbacks:" not in yaml_out
    for section in NAC_CONFIGURATION_SECTIONS:
        assert f"{section.key}:" in yaml_out or f"{section.key}:  #" in yaml_out


def test_scaffold_hints_off():
    """Default YAML omits scaffold placeholder comments."""
    yaml_out = generate_nac_yaml(parse_cli("").device, show_hints=False).content
    assert "Scaffold hints: off" in yaml_out
    assert "# ←" not in yaml_out
    assert "interfaces:" in yaml_out
    assert "users:" not in yaml_out
    assert "routing:" not in yaml_out


def test_scaffold_hints_on_header():
    yaml_out = generate_nac_yaml(parse_cli("").device, show_hints=True).content
    assert "Scaffold hints: on" in yaml_out


def test_sync_show_hints_param():
    from app.main import SyncRequest, sync

    off = sync(SyncRequest(cli_text="", show_hints=False))
    assert "# ←" not in off.nac_yaml
    on = sync(SyncRequest(cli_text="", show_hints=True))
    assert "users:  # ← type: username admin secret" in on.nac_yaml


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


def test_vrf_definition_and_forwarding():
    cli = """vrf definition MGMT
 description Management VRF
 rd 65000:1
 address-family ipv4
  route-target import 65000:100
  route-target export 65000:100
 exit-address-family
interface GigabitEthernet0/0/0
 vrf forwarding MGMT"""
    result = parse_cli(cli)
    config = result.device.configuration
    assert len(config.vrfs) == 1
    vrf = config.vrfs[0]
    assert vrf.name == "MGMT"
    assert vrf.description == "Management VRF"
    assert vrf.route_distinguisher == "65000:1"
    assert vrf.address_family_ipv4 is not None
    assert vrf.address_family_ipv4.import_route_targets == ["65000:100"]
    assert vrf.address_family_ipv4.export_route_targets == ["65000:100"]
    gi = result.device.get_interface("GigabitEthernet0/0/0")
    assert gi is not None
    assert gi.vrf_forwarding == "MGMT"

    yaml_out = generate_nac_yaml(result.device).content
    assert "vrfs:" in yaml_out
    assert 'name: "MGMT"' in yaml_out
    assert 'route_distinguisher: "65000:1"' in yaml_out
    assert 'vrf: "MGMT"' in yaml_out
    assert "vrfs:  # ← type: vrf definition MGMT" not in yaml_out


def test_access_lists_standard_and_extended():
    cli = """ip access-list standard ACL-STD
 10 permit 10.0.0.0 0.0.0.255
 20 deny any
ip access-list extended ACL-EXT
 10 permit ip any any"""
    result = parse_cli(cli)
    acls = result.device.configuration.access_lists
    assert acls is not None
    assert len(acls.standard) == 1
    assert acls.standard[0].name == "ACL-STD"
    assert len(acls.standard[0].entries) == 2
    assert acls.standard[0].entries[0].prefix == "10.0.0.0"
    assert acls.standard[0].entries[1].prefix == "any"
    assert len(acls.extended) == 1
    assert acls.extended[0].entries[0].protocol == "ip"
    assert acls.extended[0].entries[0].source_any is True

    yaml_out = generate_nac_yaml(result.device).content
    assert "access_lists:" in yaml_out
    assert "standard:" in yaml_out
    assert 'name: "ACL-STD"' in yaml_out
    assert "extended:" in yaml_out
    assert "access_lists:  # ← type: ip access-list standard" not in yaml_out


def test_prefix_lists_and_route_maps():
    cli = """ip prefix-list PL-1 seq 10 permit 10.0.0.0/8 le 24
route-map RM permit 10
 match ip address prefix-list PL-1
 set local-preference 200"""
    result = parse_cli(cli)
    config = result.device.configuration
    assert len(config.prefix_lists) == 1
    assert config.prefix_lists[0].name == "PL-1"
    assert config.prefix_lists[0].seqs[0].less_equal == 24
    assert len(config.route_maps) == 1
    entry = config.route_maps[0].entries[0]
    assert entry.match is not None
    assert entry.match.ipv4_address_prefix_lists == ["PL-1"]
    assert entry.set is not None
    assert entry.set.local_preference == 200

    yaml_out = generate_nac_yaml(result.device).content
    assert 'name: "PL-1"' in yaml_out
    assert "less_equal: 24" in yaml_out
    assert 'name: "RM"' in yaml_out
    assert "local_preference: 200" in yaml_out


def test_policy_sections_no_scaffold_when_wired():
    cli = """vrf definition MGMT
 rd 65000:1
ip access-list standard ACL-STD
 10 permit any
ip prefix-list PL-1 seq 10 permit 10.0.0.0/8
route-map RM permit 10
 set local-preference 100"""
    yaml_out = generate_nac_yaml(parse_cli(cli).device).content
    assert "      vrfs:  # ←" not in yaml_out
    assert "      access_lists:  # ←" not in yaml_out
    assert "      prefix_lists:  # ←" not in yaml_out
    assert "      route_maps:  # ←" not in yaml_out


def test_generate_ios_cli_policy_roundtrip():
    from app.generators.ios_cli import generate_ios_cli

    cli = """vrf definition MGMT
 rd 65000:1
 address-family ipv4
  route-target import 65000:100
 exit-address-family
ip access-list standard ACL-STD
 10 permit 10.0.0.0 0.0.0.255
ip prefix-list PL-1 seq 10 permit 10.0.0.0/8 le 24
route-map RM permit 10
 match ip address prefix-list PL-1
 set local-preference 200
interface GigabitEthernet0/0/0
 vrf forwarding MGMT"""
    device = parse_cli(cli).device
    regenerated = generate_ios_cli(device)
    assert "vrf definition MGMT" in regenerated
    assert "rd 65000:1" in regenerated
    assert "ip access-list standard ACL-STD" in regenerated
    assert "ip prefix-list PL-1" in regenerated
    assert "route-map RM permit 10" in regenerated
    assert "vrf forwarding MGMT" in regenerated
    assert regenerated.strip()


def test_restconf_includes_policy_sections():
    from app.generators.restconf import generate_restconf_json

    cli = """vrf definition MGMT
 rd 65000:1
ip prefix-list PL-1 seq 10 permit 10.0.0.0/8 le 24
route-map RM permit 10
 set local-preference 200
interface GigabitEthernet0/0/0
 vrf forwarding MGMT"""
    payload = generate_restconf_json(parse_cli(cli).device)
    assert "vrf" in payload
    assert "prefix-list" in payload
    assert "route-map" in payload
    assert "bind-ni-name" in payload
    assert "MGMT" in payload


def test_username_secret_exact_in_yaml():
    """NDO-172: live preview shows exact secret values (no redaction)."""
    cli = "username cisco privilege 15 secret cisco"
    result = parse_cli(cli)
    assert len(result.device.configuration.users) == 1
    user = result.device.configuration.users[0]
    assert user.name == "cisco"
    assert user.privilege == 15
    assert user.secret == "cisco"
    yaml_out = generate_nac_yaml(result.device).content
    assert 'secret: "cisco"' in yaml_out
    assert "REDACTED" not in yaml_out


def test_username_password_variants():
    """NDO-172: password 0/7 and secret 5 type variants."""
    cli = """username plain password 0 cleartext
username enc password 7 060506080D
username scrypt secret 5 $8$hashed"""
    result = parse_cli(cli)
    users = {u.name: u for u in result.device.configuration.users}
    assert users["plain"].password == "cleartext"
    assert users["plain"].password_type == "0"
    assert users["enc"].password == "060506080D"
    assert users["enc"].password_type == "7"
    assert users["scrypt"].secret == "$8$hashed"
    assert users["scrypt"].secret_type == "5"
    yaml_out = generate_nac_yaml(result.device).content
    assert 'password: "cleartext"' in yaml_out
    assert 'password_type: "0"' in yaml_out
    assert 'secret_type: "5"' in yaml_out


def test_users_apply_safe_no_phantom():
    """NDO-172: hostname-only CLI must not emit phantom users block."""
    yaml_out = generate_nac_yaml(parse_cli("hostn R1").device).content
    assert "users:" not in yaml_out
    assert "      users:\n        - name:" not in yaml_out

    hinted = generate_nac_yaml(parse_cli("hostn R1").device, show_hints=True).content
    assert "users:  # ← type: username admin secret" in hinted
    assert "      users:\n        - name:" not in hinted


def test_system_mtu_domain_clock_banner():
    """NDO-173: system mtu/domain, top-level banner and clock."""
    cli = """mtu 9198
ip domain-name lab.local
clock timezone EST -5 0
banner motd #
Welcome to R1
#"""
    result = parse_cli(cli)
    assert result.device.system.mtu == 9198
    assert result.device.system.ip_domain_name == "lab.local"
    assert result.device.configuration.clock.timezone == "EST"
    assert result.device.configuration.clock.timezone_offset_hours == -5
    assert result.device.configuration.banner.motd == "Welcome to R1"
    yaml_out = generate_nac_yaml(result.device).content
    assert "mtu: 9198" in yaml_out
    assert 'ip_domain_name: "lab.local"' in yaml_out
    assert 'motd: "Welcome to R1"' in yaml_out
    assert 'timezone: "EST"' in yaml_out
    assert "timezone_offset_hours: -5" in yaml_out
    assert "      banner:" in yaml_out
    assert "      clock:" in yaml_out


def test_banner_single_line():
    cli = 'banner motd ^Authorized only^'
    result = parse_cli(cli)
    assert result.device.configuration.banner.motd == "Authorized only"
    yaml_out = generate_nac_yaml(result.device).content
    assert 'motd: "Authorized only"' in yaml_out


def test_users_system_line_mappings():
    from app.main import SyncRequest, sync

    cli = """username cisco privilege 15 secret cisco
mtu 9198
ip domain-name lab.local"""
    resp = sync(SyncRequest(cli_text=cli))
    user_map = next(m for m in resp.mappings if m.field_key == "users:cisco")
    assert user_map.cli_line == 1
    mtu_map = next(m for m in resp.mappings if m.field_key == "system.mtu")
    assert mtu_map.cli_line == 2
    domain_map = next(m for m in resp.mappings if m.field_key == "system.ip_domain_name")
    assert domain_map.cli_line == 3


def test_ospf_routing_parsed_and_emitted():
    cli = """router ospf 1
 router-id 1.1.1.1
 network 10.0.0.0 0.0.0.255 area 0
 passive-interface default
 passive-interface g0/0"""
    result = parse_cli(cli)
    proc = result.device.configuration.routing.ospf_processes[0]
    assert proc.id == 1
    assert proc.router_id == "1.1.1.1"
    assert proc.networks[0].ip == "10.0.0.0"
    assert proc.passive_interface_default is True
    assert proc.passive_interfaces[0].interface_id == "0/0"

    yaml_out = generate_nac_yaml(result.device).content
    assert "ospf_processes:" in yaml_out
    assert 'router_id: "1.1.1.1"' in yaml_out
    assert "passive_interface_default: true" in yaml_out
    assert "ospf_processes:  # ←" not in yaml_out


def test_bgp_routing_parsed_and_emitted():
    cli = """router bgp 65000
 neighbor 10.0.0.2 remote-as 65001
 network 192.168.0.0 mask 255.255.255.0"""
    result = parse_cli(cli)
    bgp = result.device.configuration.routing.bgp
    assert bgp.as_number == 65000
    assert bgp.neighbors[0].ip == "10.0.0.2"
    assert bgp.neighbors[0].remote_as == 65001
    nets = bgp.address_family.ipv4_unicast.networks
    assert nets[0].network == "192.168.0.0"

    yaml_out = generate_nac_yaml(result.device).content
    assert "as_number: 65000" in yaml_out
    assert 'remote_as: 65001' in yaml_out
    assert "bgp:  # ←" not in yaml_out


def test_isis_routing_parsed_and_emitted():
    cli = """router isis CORE
 net 49.0001.0001.0001.0001.00
 is-type level-2-only"""
    result = parse_cli(cli)
    isis = result.device.configuration.routing.isis
    assert isis.area_tag == "CORE"
    assert isis.nets[0].tag == "49.0001.0001.0001.0001.00"
    assert isis.is_type == "level-2-only"

    yaml_out = generate_nac_yaml(result.device).content
    assert 'area_tag: "CORE"' in yaml_out
    assert 'is_type: "level-2-only"' in yaml_out
    assert "isis:  # ←" not in yaml_out


def test_eigrp_skipped_with_warning():
    result = parse_cli("router eigrp 1")
    assert not result.device.configuration.routing.ospf_processes
    assert any("EIGRP" in w.message for w in result.warnings)


def test_routing_generators_include_protocols():
    from app.generators.ios_cli import generate_ios_cli
    from app.generators.restconf import generate_restconf_json
    from app.generators.terraform import generate_terraform

    cli = """router ospf 1
 router-id 1.1.1.1
router bgp 65000
 neighbor 10.0.0.2 remote-as 65001
router isis LAB
 net 49.0001.0001.0001.0001.00
 is-type level-1-2"""
    device = parse_cli(cli).device
    ios_out = generate_ios_cli(device)
    tf_out = generate_terraform(device)
    restconf_out = generate_restconf_json(device)
    assert "router ospf 1" in ios_out
    assert 'resource "iosxe_ospf"' in tf_out
    assert 'resource "iosxe_bgp"' in tf_out
    assert 'resource "iosxe_isis"' in tf_out
    assert "router-ospf" in restconf_out
    assert "router-bgp" in restconf_out
    assert "router-isis" in restconf_out


def test_port_channel_interface():
    result = parse_cli("int po1\nno sh\nip add 10.1.1.1 255.255.255.0")
    po = result.device.get_interface("Port-channel1")
    assert po.kind == "port_channel"
    assert po.port_channel_id == "1"
    yaml_out = generate_nac_yaml(result.device).content
    assert "port_channels:" in yaml_out
    assert "id: '1'" in yaml_out


def test_port_channel_subinterface():
    result = parse_cli("int po1.100\nip add 10.100.1.1 255.255.255.0")
    assert result.device.get_interface("Port-channel1.100").kind == "port_channel_subinterface"
    yaml_out = generate_nac_yaml(result.device).content
    assert "port_channel_subinterfaces:" in yaml_out
    assert "id: '1.100'" in yaml_out


def test_ethernet_subinterface():
    result = parse_cli("int g0/0/0.100\nip add 192.168.100.1 255.255.255.0")
    assert result.device.get_interface("GigabitEthernet0/0/0.100").kind == "ethernet_subinterface"
    yaml_out = generate_nac_yaml(result.device).content
    assert "ethernet_subinterfaces:" in yaml_out
    assert "id: 0/0/0.100" in yaml_out


def test_bdi_and_nve_interfaces():
    result = parse_cli("int bdi100\nint nve1\ndescription VXLAN")
    assert result.device.get_interface("BDI100").bdi_id == "100"
    assert result.device.get_interface("nve1").nve_id == "1"
    yaml_out = generate_nac_yaml(result.device).content
    assert "bdis:" in yaml_out
    assert "nves:" in yaml_out


def test_channel_group_on_ethernet():
    result = parse_cli("int g0/0/1\nchannel-group 1 mode active")
    gi = result.device.get_interface("GigabitEthernet0/0/1")
    assert gi.port_channel_id == "1"
    assert gi.port_channel_mode == "active"
    assert "port_channel_id: '1'" in generate_nac_yaml(result.device).content


def test_extended_interfaces_terraform_and_restconf():
    from app.generators.restconf import generate_restconf_json
    from app.generators.terraform import generate_terraform

    device = parse_cli("int po1\nint po1.100\nint g0/0/0.200\nint bdi200\nint nve1").device
    tf = generate_terraform(device)
    assert 'resource "iosxe_interface_port_channel" "po1"' in tf
    assert 'resource "iosxe_interface_nve" "nve1"' in tf
    restconf = generate_restconf_json(device)
    assert "Port-channel1" in restconf
    assert "nve1" in restconf


def test_aaa_new_model_and_login_default():
    cli = """aaa new-model
aaa authentication login default local
aaa authorization exec default local
aaa accounting login default start-stop group tacacs+"""
    device = parse_cli(cli).device
    aaa = device.configuration.aaa
    assert aaa is not None
    assert aaa.new_model is True
    assert aaa.authentication is not None
    assert aaa.authentication.logins[0].name == "default"
    assert aaa.authentication.logins[0].methods == ["local"]
    assert aaa.authorization is not None
    assert aaa.authorization.execs[0].methods == ["local"]
    assert aaa.accounting is not None
    assert aaa.accounting.execs[0].start_stop_groups == ["tacacs+"]

    yaml_out = generate_nac_yaml(device).content
    assert "new_model: true" in yaml_out
    assert "authentication:" in yaml_out
    assert 'name: "default"' in yaml_out
    assert "start_stop_groups:" in yaml_out
    assert '"tacacs+"' in yaml_out
    assert "aaa:  # " not in yaml_out


def test_aaa_line_mappings():
    from app.main import sync
    from app.main import SyncRequest

    cli = """aaa new-model
aaa authentication login default local
aaa authorization exec default local
aaa accounting login default start-stop group tacacs+"""
    resp = sync(SyncRequest(cli_text=cli))
    assert "aaa_line_mappings" in resp.features

    new_model = next(m for m in resp.mappings if m.field_key == "aaa.new_model")
    assert new_model.cli_line == 1

    login_map = next(m for m in resp.mappings if m.field_key == "aaa.authentication.logins:default")
    assert login_map.cli_line == 2
    assert login_map.yaml_end_line > login_map.yaml_start_line

    authz_map = next(m for m in resp.mappings if m.field_key == "aaa.authorization.execs:default")
    assert authz_map.cli_line == 3
    assert authz_map.yaml_start_line != login_map.yaml_start_line

    acct_map = next(m for m in resp.mappings if m.field_key == "aaa.accounting.execs:default")
    assert acct_map.cli_line == 4
    yaml_lines = resp.nac_yaml.splitlines()
    acct_block = yaml_lines[acct_map.yaml_start_line - 1 : acct_map.yaml_end_line]
    assert any("start_stop_groups:" in line for line in acct_block)


def test_snmp_and_ntp():
    cli = """snmp-server community public RO
snmp-server contact lab@example.com
ntp server 10.0.0.1 prefer"""
    device = parse_cli(cli).device
    snmp = device.configuration.snmp_server
    ntp = device.configuration.ntp
    assert snmp is not None
    assert snmp.snmp_communities[0].name == "public"
    assert snmp.snmp_communities[0].permission == "RO"
    assert snmp.contact == "lab@example.com"
    assert ntp is not None
    assert ntp.servers[0].ip == "10.0.0.1"
    assert ntp.servers[0].prefer is True

    yaml_out = generate_nac_yaml(device).content
    assert "snmp_communities:" in yaml_out
    assert 'name: "public"' in yaml_out
    assert "permission:" in yaml_out
    assert "servers:" in yaml_out
    assert 'ip: "10.0.0.1"' in yaml_out
    assert "prefer: true" in yaml_out


def test_ntp_server_vrf():
    cli = """hostn R1
ntp server 1.1.1.1
ntp server 1.1.1.2 vrf Mgmt-vrf
ntp peer 1.1.1.3"""
    device = parse_cli(cli).device
    servers = device.configuration.ntp.servers
    peers = device.configuration.ntp.peers
    assert len(servers) == 2
    assert servers[0].ip == "1.1.1.1"
    assert servers[0].vrf is None
    assert servers[1].ip == "1.1.1.2"
    assert servers[1].vrf == "Mgmt-vrf"
    assert len(peers) == 1
    assert peers[0].ip == "1.1.1.3"

    yaml_out = generate_nac_yaml(device).content
    assert 'ip: "1.1.1.1"' in yaml_out
    assert 'ip: "1.1.1.2"' in yaml_out
    assert 'vrf: "Mgmt-vrf"' in yaml_out
    assert "peers:" in yaml_out
    assert 'ip: "1.1.1.3"' in yaml_out

    from app.generators.ios_cli import generate_ios_cli

    regen = generate_ios_cli(device)
    assert "ntp server 1.1.1.1" in regen
    assert "ntp server 1.1.1.2 vrf Mgmt-vrf" in regen
    assert "ntp peer 1.1.1.3" in regen


def test_ntp_line_mappings():
    from app.main import SyncRequest, sync

    cli = """hostn R1
ntp peer 1.1.1.1
ntp server 1.1.1.2
ntp server 1.1.1.3 vrf Myvrf"""
    resp = sync(SyncRequest(cli_text=cli))
    assert "ntp_line_mappings" in resp.features

    peer_map = next(m for m in resp.mappings if m.field_key == "ntp.peers:1.1.1.1")
    assert peer_map.cli_line == 2
    assert peer_map.yaml_start_line <= peer_map.yaml_end_line

    server_map = next(m for m in resp.mappings if m.field_key == "ntp.servers:1.1.1.2")
    assert server_map.cli_line == 3

    vrf_map = next(m for m in resp.mappings if m.field_key == "ntp.servers:1.1.1.3")
    assert vrf_map.cli_line == 4
    assert 'vrf: "Myvrf"' in resp.nac_yaml


def test_nat_and_dhcp_pool():
    cli = """service dhcp
ip dhcp pool LAN
 network 192.168.1.0 255.255.255.0
 default-router 192.168.1.1
 dns-server 8.8.8.8
 exit
ip nat inside source list 1 interface GigabitEthernet0/0 overload
int g0/0
 ip nat inside
int g0/0/1
 ip nat outside"""
    device = parse_cli(cli).device
    assert device.configuration.dhcp is not None
    assert device.configuration.dhcp.enabled is True
    pool = device.configuration.dhcp_pools[0]
    assert pool.name == "LAN"
    assert pool.network_number == "192.168.1.0"
    assert pool.default_routers == ["192.168.1.1"]
    assert pool.dns_servers == ["8.8.8.8"]
    nat = device.configuration.nat
    assert nat is not None
    assert nat.inside_source_interfaces[0].id == 1
    assert nat.inside_source_interfaces[0].interfaces[0].interface_type == "GigabitEthernet"
    assert nat.inside_source_interfaces[0].interfaces[0].interface_id == "0/0"
    assert nat.inside_source_interfaces[0].interfaces[0].overload is True
    inside = device.get_interface("GigabitEthernet0/0")
    outside = device.get_interface("GigabitEthernet0/0/1")
    assert inside is not None and inside.nat_inside is True
    assert outside is not None and outside.nat_outside is True

    yaml_out = generate_nac_yaml(device).content
    assert "dhcp_pools:" in yaml_out
    assert 'name: "LAN"' in yaml_out
    assert "network_number:" in yaml_out
    assert "inside_source_interfaces:" in yaml_out
    assert "nat_inside: true" in yaml_out
    assert "nat_outside: true" in yaml_out


def test_services_lab_cli_regeneration():
    from app.generators.ios_cli import generate_ios_cli

    cli = """aaa new-model
snmp-server community private RW
ntp server 192.168.1.1
service dhcp
ip dhcp pool LAB
 network 10.0.0.0 255.255.255.0
 default-router 10.0.0.1"""
    regen = generate_ios_cli(parse_cli(cli).device)
    assert "aaa new-model" in regen
    assert "snmp-server community private RW" in regen
    assert "ntp server 192.168.1.1" in regen
    assert "service dhcp" in regen
    assert "ip dhcp pool LAB" in regen


def test_services_no_phantom_resources():
    yaml_out = generate_nac_yaml(parse_cli("hostn R1").device).content
    assert "snmp_communities:" not in yaml_out
    assert "network_number:" not in yaml_out
    assert "inside_source_interfaces:" not in yaml_out
    assert "new_model:" not in yaml_out
    assert "ipsec_profiles:" not in yaml_out
    assert "ikev2:" not in yaml_out


def test_crypto_ikev2_ipsec_pki():
    from app.main import SyncRequest, sync

    cli = """crypto ikev2 proposal PROP1
 encryption aes-cbc-256
 integrity sha256
 group 19
!
crypto ikev2 policy POL1
 proposal PROP1
 match fvrf VRF1
!
crypto ikev2 keyring KEY1
 peer PEER1
  address 192.168.1.1 255.255.255.0
  pre-shared-key mykey123
!
crypto ikev2 profile PROF1
 authentication local pre-share
 authentication remote pre-share
 keyring local KEY1
 lifetime 28800
!
crypto ipsec transform-set TS1 esp-aes esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC1
 set transform-set TS1
 set ikev2-profile PROF1
 set pfs group19
!
crypto pki trustpoint TP1
 enrollment terminal
 rsakeypair KEY1
 subject-name CN=router1
 usage ike
 revocation-check none
"""
    device = parse_cli(cli).device
    crypto = device.configuration.crypto
    assert crypto is not None
    assert crypto.ikev2 is not None
    assert crypto.ikev2.proposals[0].encryption == ["aes_cbc_256"]
    assert crypto.ikev2.policies[0].match_fvrf == "VRF1"
    assert crypto.ikev2.keyrings[0].peers[0].pre_shared_key == "mykey123"
    assert crypto.ikev2.profiles[0].keyring_local == "KEY1"
    assert crypto.ipsec_transform_sets[0].mode_tunnel is True
    assert crypto.ipsec_profiles[0].set_ikev2_profile == "PROF1"
    assert crypto.pki is not None
    assert crypto.pki.trustpoints[0].usage == "ike"

    yaml_out = generate_nac_yaml(device).content
    assert "crypto:" in yaml_out
    assert "ikev2:" in yaml_out
    assert "aes_cbc_256" in yaml_out
    assert "ipsec_profiles:" in yaml_out
    assert "set_ikev2_profile: PROF1" in yaml_out or 'set_ikev2_profile: "PROF1"' in yaml_out
    assert "pki:" in yaml_out
    assert "trustpoints:" in yaml_out
    assert "wire_crypto" in sync(SyncRequest(cli_text=cli)).features


def test_crypto_line_mappings():
    from app.main import sync
    from app.main import SyncRequest

    cli = """hostn R1
crypto ikev2 proposal PROP1
 encryption aes-cbc-256
!
crypto ikev2 profile PROF1
 authentication local pre-share
 keyring local KEY1
!
crypto ipsec transform-set TS1 esp-aes esp-sha256-hmac
 mode tunnel
!
crypto ipsec profile IPSEC1
 set transform-set TS1
 set ikev2-profile PROF1
"""
    resp = sync(SyncRequest(cli_text=cli))
    assert "crypto_line_mappings" in resp.features

    keyring_map = next(m for m in resp.mappings if m.field_key == "crypto.ikev2.profiles:PROF1:keyring_local")
    assert keyring_map.cli_line == 7
    yaml_lines = resp.nac_yaml.splitlines()
    assert "keyring_local:" in yaml_lines[keyring_map.yaml_start_line - 1]

    enc_map = next(m for m in resp.mappings if m.field_key == "crypto.ikev2.proposals:PROP1:encryption")
    assert enc_map.cli_line == 3

    ipsec_map = next(m for m in resp.mappings if m.field_key == "crypto.ipsec_profiles:IPSEC1:set_ikev2_profile")
    assert ipsec_map.cli_line == 14
    assert keyring_map.yaml_start_line != ipsec_map.yaml_start_line
