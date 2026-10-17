"""Ensure parser field_keys stay in sync with generator YAML range marks."""

from __future__ import annotations

import pytest

from app.field_keys import find_unmapped_cli_refs, format_unmapped_refs
from app.generators.nac_yaml import generate_nac_yaml
from app.parsers.ios_cli import parse_cli

# Representative CLIs that emit CliFieldRefs — must all map to YAML ranges.
MAPPING_FIXTURE_CLIS: tuple[str, ...] = (
    """hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64""",
    """username cisco privilege 15 secret cisco
mtu 9198
ip domain-name lab.local
clock timezone EST -5 0
banner motd ^Welcome^""",
    """vrf definition MGMT
 description Management VRF
 rd 65000:1
 address-family ipv4
  route-target import 65000:100
  route-target export 65000:100
 exit-address-family
interface GigabitEthernet0/0/0
 vrf forwarding MGMT""",
    """ip access-list standard ACL-STD
 10 permit 10.0.0.0 0.0.0.255
ip access-list extended ACL-EXT
 10 permit ip any any""",
    """ip prefix-list PL-1 seq 10 permit 10.0.0.0/8 le 24
route-map RM permit 10
 match ip address prefix-list PL-1
 set local-preference 200""",
    """ip route 10.0.0.0 255.255.255.0 192.168.1.1
router ospf 1
 router-id 1.1.1.1
 network 10.0.0.0 0.255.255.255 area 0
 passive-interface default""",
    """router bgp 65000
 neighbor 10.0.0.2 remote-as 65001
 network 10.0.0.0 mask 255.0.0.0""",
    """router isis CORE
 net 49.0001.0000.0001.00
 is-type level-2-only""",
    """router eigrp LAB
 address-family ipv4 unicast autonomous-system 100
  eigrp router-id 192.0.2.1
  network 10.10.0.0 0.0.255.255
  no auto-summary
 exit-address-family
 address-family ipv4 unicast vrf RED autonomous-system 100
  network 10.20.0.0 0.0.255.255
  shutdown""",
    """interface Tunnel100
 description overlay
 ip address 10.0.0.1 255.255.255.0
 no shutdown
 ip nhrp authentication nhrp-key
 ip nhrp network-id 100
 ip nhrp nhs 10.0.0.254
 ip nhrp map 10.0.0.2 192.0.2.10
 ip nhrp redirect
 ip nhrp shortcut
 mpls nhrp
 tunnel source GigabitEthernet1
 tunnel destination 192.0.2.20
 tunnel mode gre multipoint
 tunnel key 10
 tunnel protection ipsec profile LAB-IPSEC""",
    """aaa new-model
aaa authentication login default local
aaa authorization exec default local
aaa accounting exec default start-stop group tacacs+""",
    """snmp-server community public RO
snmp-server contact ops@example.com
ntp server 1.1.1.1
ntp peer 1.1.1.2
ntp server 1.1.1.3 vrf MGMT""",
    """service dhcp
ip dhcp pool LAN
 network 192.168.1.0 255.255.255.0
ip nat inside source list 1 interface GigabitEthernet0/0/0 overload
interface GigabitEthernet0/0/0
 ip nat inside""",
    """hostn R1
crypto ikev2 proposal PROP1
 encryption aes-cbc-256
crypto ikev2 profile PROF1
 keyring local KEY1
crypto ipsec transform-set TS1 esp-aes esp-sha256-hmac
 mode tunnel
crypto ipsec profile IPSEC1
 set transform-set TS1
 set ikev2-profile PROF1""",
    """int g0/0/0
 channel-group 1 mode active""",
)


@pytest.mark.parametrize("cli_text", MAPPING_FIXTURE_CLIS, ids=range(len(MAPPING_FIXTURE_CLIS)))
def test_cli_refs_map_to_yaml_ranges(cli_text: str) -> None:
    parse_result = parse_cli(cli_text)
    yaml_result = generate_nac_yaml(parse_result.device)
    unmapped = find_unmapped_cli_refs(parse_result.cli_refs, yaml_result.ranges)
    assert not unmapped, format_unmapped_refs(unmapped)
