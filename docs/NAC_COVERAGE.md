# NaC ios-xe Coverage Checklist

Schema: **`iosxe-devices-configuration-full`** (v4.0.0)  
Contract: `iosxe.devices[].configuration.*`  
Module: [netascode/terraform-iosxe-nac-iosxe](https://github.com/netascode/terraform-iosxe-nac-iosxe)

Legend: **Wired** = CLI parser + live yaml emitter | **Scaffold** = model + hint comment only | **—** = not in NaC module / skipped

| Section | Jira | Status | Notes |
|---------|------|--------|-------|
| `system` | NDO-173 | Wired | hostname, ipv6_unicast_routing, mtu, ip_domain_name |
| `users` | NDO-172 | Wired | exact secret/password in live preview (no redaction) |
| `banner` | NDO-173 | Wired | top-level in NaC (not under system) |
| `clock` | NDO-173 | Wired | top-level in NaC |
| `line` | — | Scaffold | |
| `aaa` | NDO-180 | Wired | |
| `access_lists` | NDO-178 | Wired | |
| `as_path_access_lists` | — | Scaffold | |
| `community_lists` | NDO-179 | Scaffold | |
| `prefix_lists` | NDO-179 | Wired | |
| `route_maps` | NDO-179 | Wired | |
| `policy` | — | Scaffold | |
| `class_maps` | — | Scaffold | |
| `policy_maps` | — | Scaffold | |
| `parameter_maps` | — | Scaffold | |
| `key_chains` | — | Scaffold | |
| `routing.static_routes` | — | Partial | legacy flat parser fields |
| `routing.ospf_processes` | NDO-174 | Wired | |
| `routing.bgp` | NDO-175 | Wired | |
| `routing.isis` | NDO-176 | Wired | |
| `vrfs` | NDO-177 | Wired | NaC key is `vrfs` |
| `interfaces.loopbacks` | NDO-183 | Partial | |
| `interfaces.ethernets` | NDO-183 | Partial | |
| `interfaces.vlans` | NDO-183 | Partial | |
| `interfaces.tunnels` | NDO-183 | Partial | |
| `interfaces.port_channels` | NDO-183 | Wired | |
| `interfaces.port_channel_subinterfaces` | NDO-183 | Wired | |
| `interfaces.ethernet_subinterfaces` | NDO-183 | Wired | |
| `interfaces.bdis` | NDO-183 | Wired | |
| `interfaces.nves` | NDO-183 | Wired | |
| `vlan` | — | Scaffold | device-level VLAN config |
| `templates` | — | Scaffold | |
| `snmp_server` | NDO-181 | Wired | |
| `ntp` | NDO-181 | Wired | |
| `logging` | — | Scaffold | |
| `dhcp` / `dhcp_pools` / `ipv6_dhcp_pools` | NDO-182 | Wired | |
| `nat` | NDO-182 | Wired | |
| `evpn` / `evpn_profile` | NDO-184 | Scaffold | |
| `mpls` | NDO-184 | Scaffold | |
| `bfd`, `cdp`, `lldp`, `spanning_tree`, `udld`, `vtp` | — | Scaffold | |
| `pim`, `msdp`, `multicast` | — | Scaffold | |
| `crypto`, `flow`, `license`, `service*` | — | Scaffold | |
| EIGRP | — | **Skipped** | not in Network Lens scope |

Epic: [NDO-170](https://roberthosford.atlassian.net/browse/NDO-170)
