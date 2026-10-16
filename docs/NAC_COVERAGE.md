# NaC IOS-XE coverage checklist

Schema: **`iosxe-devices-configuration-full`** (v4.0.0)  
Contract: `iosxe.devices[].configuration.*`  
Module: [netascode/terraform-iosxe-nac-iosxe](https://github.com/netascode/terraform-iosxe-nac-iosxe)

Legend: **Wired** = CLI parser + live YAML emitter | **Scaffold** = model + hint comment only | **—** = not in NaC module / skipped

| Section | Status | Notes |
|---------|--------|-------|
| `system` | Wired | hostname, ipv6_unicast_routing, mtu, ip_domain_name, enable_password, enable_secret |
| `users` | Wired | exact secret/password in live preview (no redaction) |
| `banner` | Wired | top-level in NaC (not under system) |
| `clock` | Wired | top-level in NaC |
| `line` | Scaffold | |
| `aaa` | Wired | |
| `access_lists` | Wired | |
| `as_path_access_lists` | Scaffold | |
| `community_lists` | Scaffold | |
| `prefix_lists` | Wired | |
| `route_maps` | Wired | |
| `policy` | Scaffold | |
| `class_maps` | Scaffold | |
| `policy_maps` | Scaffold | |
| `parameter_maps` | Scaffold | |
| `key_chains` | Scaffold | |
| `routing.static_routes` | Partial | legacy flat parser fields |
| `routing.ospf_processes` | Wired | |
| `routing.bgp` | Wired | |
| `routing.isis` | Wired | |
| `routing.eigrp_processes` | Wired | Named mode. Classic `router eigrp <asn>` is previewed on the same list with `name` set to the AS. passive-interface, stub, and redistribute are not in the schema |
| `vrfs` | Wired | NaC key is `vrfs` |
| `interfaces.loopbacks` | Partial | |
| `interfaces.ethernets` | Partial | |
| `interfaces.vlans` | Partial | |
| `interfaces.tunnels` | Partial | DMVPN: `tunnel_mode_gre_multipoint`, `tunnel_source`, `tunnel_key`, `tunnel_destination_ipv4`, `tunnel_protection_ipsec_profile`, `ip_nhrp_*`, `mpls_nhrp` |
| `interfaces.port_channels` | Wired | |
| `interfaces.port_channel_subinterfaces` | Wired | |
| `interfaces.ethernet_subinterfaces` | Wired | |
| `interfaces.bdis` | Wired | |
| `interfaces.nves` | Wired | |
| `vlan` | Scaffold | device-level VLAN config |
| `templates` | Scaffold | |
| `snmp_server` | Wired | |
| `ntp` | Wired | |
| `logging` | Scaffold | |
| `dhcp` / `dhcp_pools` / `ipv6_dhcp_pools` | Wired | |
| `nat` | Wired | |
| `evpn` / `evpn_profile` | Scaffold | |
| `mpls` | Scaffold | |
| `bfd`, `cdp`, `lldp`, `spanning_tree`, `udld`, `vtp` | Scaffold | |
| `pim`, `msdp`, `multicast` | Scaffold | |
| `crypto`, `flow`, `license`, `service*` | Partial | IKEv2, IPsec, PKI trustpoints wired; GDOI/GET VPN not in NaC |

## Roadmap

| Feature | Status | Notes |
|---------|--------|-------|
| File-based CLI converter | Planned | Load IOS config file → export `nac.yaml`, HCL, RESTCONF JSON (apply-safe, no preview headers) |
| `nac-validate` integration | Planned | Validate generated YAML against NaC schema before export |
