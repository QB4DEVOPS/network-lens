# NaC ios-xe Coverage Checklist

Schema: **`iosxe-devices-configuration-full`** (v4.0.0)  
Contract: `iosxe.devices[].configuration.*`  
Module: [netascode/terraform-iosxe-nac-iosxe](https://github.com/netascode/terraform-iosxe-nac-iosxe)

Legend: **Wired** = CLI parser + live yaml emitter | **Scaffold** = model + hint comment only | **—** = not in NaC module / skipped

| Section | Jira | Status | Notes |
|---------|------|--------|-------|
| `system` | NDO-173 | Partial | hostname, ipv6_unicast_routing wired; mtu/banner/clock pending |
| `users` | NDO-172 | Scaffold | |
| `banner` | NDO-173 | Scaffold | top-level in NaC (not under system) |
| `clock` | NDO-173 | Scaffold | top-level in NaC |
| `line` | — | Scaffold | |
| `aaa` | NDO-180 | Scaffold | |
| `access_lists` | NDO-178 | Scaffold | |
| `as_path_access_lists` | — | Scaffold | |
| `community_lists` | NDO-179 | Scaffold | |
| `prefix_lists` | NDO-179 | Scaffold | |
| `route_maps` | NDO-179 | Scaffold | |
| `policy` | — | Scaffold | |
| `class_maps` | — | Scaffold | |
| `policy_maps` | — | Scaffold | |
| `parameter_maps` | — | Scaffold | |
| `key_chains` | — | Scaffold | |
| `routing.static_routes` | — | Partial | legacy flat parser fields |
| `routing.ospf_processes` | NDO-174 | Scaffold | |
| `routing.bgp` | NDO-175 | Scaffold | |
| `routing.isis` | NDO-176 | Scaffold | |
| `vrfs` | NDO-177 | Scaffold | NaC key is `vrfs` |
| `interfaces.loopbacks` | NDO-183 | Partial | |
| `interfaces.ethernets` | NDO-183 | Partial | |
| `interfaces.vlans` | NDO-183 | Partial | |
| `interfaces.tunnels` | NDO-183 | Partial | |
| `interfaces.port_channels` | NDO-183 | Scaffold | |
| `interfaces.port_channel_subinterfaces` | NDO-183 | Scaffold | |
| `interfaces.ethernet_subinterfaces` | NDO-183 | Scaffold | |
| `interfaces.bdis` | NDO-183 | Scaffold | |
| `interfaces.nves` | NDO-183 | Scaffold | |
| `vlan` | — | Scaffold | device-level VLAN config |
| `templates` | — | Scaffold | |
| `snmp_server` | NDO-181 | Scaffold | |
| `ntp` | NDO-181 | Scaffold | |
| `logging` | — | Scaffold | |
| `dhcp` / `dhcp_pools` / `ipv6_dhcp_pools` | NDO-182 | Scaffold | |
| `nat` | NDO-182 | Scaffold | |
| `evpn` / `evpn_profile` | NDO-184 | Scaffold | |
| `mpls` | NDO-184 | Scaffold | |
| `bfd`, `cdp`, `lldp`, `spanning_tree`, `udld`, `vtp` | — | Scaffold | |
| `pim`, `msdp`, `multicast` | — | Scaffold | |
| `crypto`, `flow`, `license`, `service*` | — | Scaffold | |
| EIGRP | — | **Skipped** | not in Network Lens scope |

Epic: [NDO-170](https://roberthosford.atlassian.net/browse/NDO-170)
