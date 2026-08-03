"""IOS CLI parser for crypto (IKEv2, IPsec, PKI)."""

from __future__ import annotations

import re

from app.models import (
    CliFieldRef,
    CryptoConfig,
    CryptoIkev2Config,
    CryptoIkev2Keyring,
    CryptoIkev2KeyringPeer,
    CryptoIkev2Policy,
    CryptoIkev2Profile,
    CryptoIkev2ProfileMatchRemoteIpv4,
    CryptoIkev2Proposal,
    CryptoIpsecProfile,
    CryptoIpsecTransformSet,
    CryptoPkiConfig,
    CryptoPkiTrustpoint,
    Device,
)

_IKEV2_ENCRYPTION = {
    "aes-cbc-128": "aes_cbc_128",
    "aes-cbc-192": "aes_cbc_192",
    "aes-cbc-256": "aes_cbc_256",
    "3des": "en_3des",
}

_IKEV2_INTEGRITY = {"md5": "md5", "sha1": "sha1", "sha256": "sha256", "sha384": "sha384", "sha512": "sha512"}
_IKEV2_PRF = _IKEV2_INTEGRITY
_IKEV2_GROUP = {"1": "1", "2": "2", "5": "5", "14": "14", "15": "15", "16": "16", "19": "19", "20": "20", "21": "21", "24": "24"}

_ESP_ALGO = {
    "esp-aes": "esp-aes",
    "esp-3des": "esp-3des",
    "esp-des": "esp-des",
    "esp-gcm": "esp-gcm",
    "esp-gmac": "esp-gmac",
    "esp-null": "esp-null",
    "esp-seal": "esp-seal",
}

_ESP_HMAC = {
    "esp-md5-hmac": "esp-md5-hmac",
    "esp-sha-hmac": "esp-sha-hmac",
    "esp-sha256-hmac": "esp-sha256-hmac",
    "esp-sha384-hmac": "esp-sha384-hmac",
    "esp-sha512-hmac": "esp-sha512-hmac",
}


def _proposal_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.proposals:{name}"
    return f"{base}:{field}" if field else base


def _policy_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.policies:{name}"
    return f"{base}:{field}" if field else base


def _keyring_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.keyrings:{name}"
    return f"{base}:{field}" if field else base


def _profile_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ikev2.profiles:{name}"
    return f"{base}:{field}" if field else base


def _transform_set_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ipsec_transform_sets:{name}"
    return f"{base}:{field}" if field else base


def _ipsec_profile_key(name: str, field: str | None = None) -> str:
    base = f"crypto.ipsec_profiles:{name}"
    return f"{base}:{field}" if field else base


def _trustpoint_key(tp_id: str, field: str | None = None) -> str:
    base = f"crypto.pki.trustpoints:{tp_id}"
    return f"{base}:{field}" if field else base


class CryptoParseState:
    __slots__ = (
        "proposal",
        "policy",
        "keyring",
        "keyring_peer",
        "profile",
        "transform_set",
        "ipsec_profile",
        "trustpoint",
    )

    def __init__(self) -> None:
        self.proposal: CryptoIkev2Proposal | None = None
        self.policy: CryptoIkev2Policy | None = None
        self.keyring: CryptoIkev2Keyring | None = None
        self.keyring_peer: CryptoIkev2KeyringPeer | None = None
        self.profile: CryptoIkev2Profile | None = None
        self.transform_set: CryptoIpsecTransformSet | None = None
        self.ipsec_profile: CryptoIpsecProfile | None = None
        self.trustpoint: CryptoPkiTrustpoint | None = None

    def clear_nested(self) -> None:
        self.proposal = None
        self.policy = None
        self.keyring = None
        self.keyring_peer = None
        self.profile = None
        self.transform_set = None
        self.ipsec_profile = None
        self.trustpoint = None

    @property
    def active_context(self) -> str | None:
        if self.proposal:
            return f"crypto ikev2 proposal {self.proposal.name}"
        if self.policy:
            return f"crypto ikev2 policy {self.policy.name}"
        if self.keyring:
            return f"crypto ikev2 keyring {self.keyring.name}"
        if self.profile:
            return f"crypto ikev2 profile {self.profile.name}"
        if self.transform_set:
            return f"crypto ipsec transform-set {self.transform_set.name}"
        if self.ipsec_profile:
            return f"crypto ipsec profile {self.ipsec_profile.name}"
        if self.trustpoint:
            return f"crypto pki trustpoint {self.trustpoint.id}"
        return None


def _ensure_crypto(device: Device) -> CryptoConfig:
    if device.configuration.crypto is None:
        device.configuration.crypto = CryptoConfig()
    return device.configuration.crypto


def _ensure_ikev2(crypto: CryptoConfig) -> CryptoIkev2Config:
    if crypto.ikev2 is None:
        crypto.ikev2 = CryptoIkev2Config()
    return crypto.ikev2


def _ensure_pki(crypto: CryptoConfig) -> CryptoPkiConfig:
    if crypto.pki is None:
        crypto.pki = CryptoPkiConfig()
    return crypto.pki


def _map_tokens(tokens: list[str], mapping: dict[str, str]) -> list[str]:
    out: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in mapping:
            out.append(mapping[key])
        elif key.isdigit() and key in mapping:
            out.append(mapping[key])
    return out


def _parse_transform_set_algos(parts: list[str]) -> tuple[str | None, str | None]:
    """Parse esp + hmac from transform-set line tail."""
    esp: str | None = None
    esp_hmac: str | None = None
    idx = 0
    while idx < len(parts):
        token = parts[idx].lower()
        if token in _ESP_ALGO:
            esp = _ESP_ALGO[token]
            if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                idx += 1
            idx += 1
            continue
        if token in _ESP_HMAC:
            esp_hmac = _ESP_HMAC[token]
            idx += 1
            continue
        idx += 1
    return esp, esp_hmac


def _parse_pfs_group(token: str) -> str | None:
    lower = token.lower()
    allowed = {
        "group1", "group2", "group5", "group14", "group15", "group16",
        "group19", "group20", "group21", "group24",
    }
    if lower in allowed:
        return lower
    if lower.startswith("group") and lower[5:].isdigit():
        candidate = lower
        return candidate if candidate in allowed else None
    return None


def parse_crypto_line(
    line: str,
    *,
    line_num: int,
    device: Device,
    cli_refs: list[CliFieldRef],
    state: CryptoParseState,
) -> bool:
    """Return True when the line is handled by the crypto parser."""
    lower = line.lower()
    crypto = _ensure_crypto(device)

    if lower.startswith("crypto ikev2 proposal "):
        state.clear_nested()
        name = line.split(None, 3)[3].strip()
        state.proposal = CryptoIkev2Proposal(name=name)
        _ensure_ikev2(crypto).proposals.append(state.proposal)
        cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_proposal_key(name), label="crypto ikev2 proposal"))
        return True

    if lower.startswith("crypto ikev2 policy "):
        state.clear_nested()
        name = line.split(None, 3)[3].strip()
        state.policy = CryptoIkev2Policy(name=name)
        _ensure_ikev2(crypto).policies.append(state.policy)
        cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_policy_key(name), label="crypto ikev2 policy"))
        return True

    if lower.startswith("crypto ikev2 keyring "):
        state.clear_nested()
        name = line.split(None, 3)[3].strip()
        state.keyring = CryptoIkev2Keyring(name=name)
        _ensure_ikev2(crypto).keyrings.append(state.keyring)
        cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_keyring_key(name), label="crypto ikev2 keyring"))
        return True

    if lower.startswith("crypto ikev2 profile "):
        state.clear_nested()
        name = line.split(None, 3)[3].strip()
        state.profile = CryptoIkev2Profile(name=name)
        _ensure_ikev2(crypto).profiles.append(state.profile)
        cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_profile_key(name), label="crypto ikev2 profile"))
        return True

    if lower.startswith("crypto ipsec transform-set "):
        state.clear_nested()
        parts = line.split()
        if len(parts) >= 4:
            name = parts[3]
            esp, esp_hmac = _parse_transform_set_algos(parts[4:])
            state.transform_set = CryptoIpsecTransformSet(name=name, esp=esp, esp_hmac=esp_hmac)
            crypto.ipsec_transform_sets.append(state.transform_set)
            cli_refs.append(
                CliFieldRef(cli_line=line_num, field_key=_transform_set_key(name), label="crypto ipsec transform-set")
            )
        return True

    if lower.startswith("crypto ipsec profile "):
        state.clear_nested()
        name = line.split(None, 3)[3].strip()
        state.ipsec_profile = CryptoIpsecProfile(name=name)
        crypto.ipsec_profiles.append(state.ipsec_profile)
        cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_ipsec_profile_key(name), label="crypto ipsec profile"))
        return True

    if lower.startswith("crypto pki trustpoint "):
        state.clear_nested()
        tp_id = line.split(None, 3)[3].strip()
        state.trustpoint = CryptoPkiTrustpoint(id=tp_id)
        _ensure_pki(crypto).trustpoints.append(state.trustpoint)
        cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_trustpoint_key(tp_id), label="crypto pki trustpoint"))
        return True

    if lower.startswith("crypto ikev2 nat keepalive "):
        parts = line.split()
        if len(parts) >= 5 and parts[4].isdigit():
            _ensure_ikev2(crypto).nat_keepalive = int(parts[4])
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key="crypto.ikev2:nat_keepalive", label="crypto ikev2 nat keepalive"))
        return True

    if lower.startswith("crypto ikev2 dpd "):
        parts = line.split()
        if len(parts) >= 4 and parts[3].isdigit():
            ike = _ensure_ikev2(crypto)
            ike.dpd_interval = int(parts[3])
            if len(parts) >= 5 and parts[4].isdigit():
                ike.dpd_retry = int(parts[4])
            if len(parts) >= 6 and parts[5].lower() in {"on-demand", "periodic"}:
                ike.dpd_query = parts[5].lower()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key="crypto.ikev2:dpd_interval", label="crypto ikev2 dpd"))
        return True

    # Nested IKEv2 proposal
    if state.proposal is not None:
        pname = state.proposal.name
        if lower.startswith("encryption "):
            state.proposal.encryption = _map_tokens(line.split()[1:], _IKEV2_ENCRYPTION)
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_proposal_key(pname, "encryption"), label="encryption"))
            return True
        if lower.startswith("integrity "):
            state.proposal.integrity = _map_tokens(line.split()[1:], _IKEV2_INTEGRITY)
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_proposal_key(pname, "integrity"), label="integrity"))
            return True
        if lower.startswith("group "):
            state.proposal.group = _map_tokens(line.split()[1:], _IKEV2_GROUP)
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_proposal_key(pname, "group"), label="group"))
            return True
        if lower.startswith("prf "):
            state.proposal.prf = _map_tokens(line.split()[1:], _IKEV2_PRF)
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_proposal_key(pname, "prf"), label="prf"))
            return True

    # Nested IKEv2 policy
    if state.policy is not None:
        polname = state.policy.name
        if lower.startswith("proposal "):
            state.policy.proposals = line.split()[1:]
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_policy_key(polname, "proposals"), label="proposal"))
            return True
        if lower.startswith("match fvrf "):
            state.policy.match_fvrf = line.split(None, 2)[2].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_policy_key(polname, "match_fvrf"), label="match fvrf"))
            return True
        if lower == "match fvrf any":
            state.policy.match_fvrf_any = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_policy_key(polname, "match_fvrf_any"), label="match fvrf any"))
            return True
        if lower.startswith("match address local "):
            state.policy.match_address_local_ip = line.split()[3:]
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_policy_key(polname, "match_address_local_ip"), label="match address local"))
            return True
        if lower == "match inbound-only":
            state.policy.match_inbound_only = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_policy_key(polname, "match_inbound_only"), label="match inbound-only"))
            return True

    # Nested IKEv2 keyring peer
    if state.keyring is not None:
        krname = state.keyring.name
        if lower.startswith("peer "):
            peer_name = line.split(None, 1)[1].strip()
            peer = CryptoIkev2KeyringPeer(name=peer_name)
            state.keyring.peers.append(peer)
            state.keyring_peer = peer
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_keyring_key(krname, f"peers:{peer_name}"), label="peer"))
            return True
        peer = state.keyring_peer
        if peer is not None:
            if lower.startswith("description "):
                peer.description = line.split(None, 1)[1].strip()
                return True
            if lower.startswith("address "):
                parts = line.split()
                if len(parts) >= 2:
                    peer.ipv4_address = parts[1]
                if len(parts) >= 3:
                    peer.ipv4_mask = parts[2]
                cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_keyring_key(krname, f"peers:{peer.name}"), label="address"))
                return True
            if lower.startswith("hostname "):
                peer.hostname = line.split(None, 1)[1].strip()
                return True
            if lower.startswith("identity fqdn "):
                peer.identity_fqdn_domain = line.split(None, 2)[2].strip()
                return True
            if lower.startswith("identity key-id "):
                peer.identity_key_id = line.split(None, 2)[2].strip()
                return True
            if lower.startswith("pre-shared-key local "):
                peer.pre_shared_key_local = line.split(None, 2)[2].strip()
                return True
            if lower.startswith("pre-shared-key remote "):
                peer.pre_shared_key_remote = line.split(None, 2)[2].strip()
                return True
            if lower.startswith("pre-shared-key "):
                peer.pre_shared_key = line.split(None, 1)[1].strip()
                cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_keyring_key(krname, f"peers:{peer.name}"), label="pre-shared-key"))
                return True

    # Nested IKEv2 profile
    if state.profile is not None:
        profname = state.profile.name
        if lower.startswith("description "):
            state.profile.description = line.split(None, 1)[1].strip()
            return True
        if lower == "authentication local pre-share":
            state.profile.authentication_local_pre_share = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_profile_key(profname, "authentication_local_pre_share"), label="authentication local"))
            return True
        if lower == "authentication remote pre-share":
            state.profile.authentication_remote_pre_share = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_profile_key(profname, "authentication_remote_pre_share"), label="authentication remote"))
            return True
        if lower == "config-exchange request":
            state.profile.config_exchange_request = True
            return True
        if lower.startswith("dpd "):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                state.profile.dpd_interval = int(parts[1])
            if len(parts) >= 3 and parts[2].isdigit():
                state.profile.dpd_retry = int(parts[2])
            if len(parts) >= 4 and parts[3].lower() in {"on-demand", "periodic"}:
                state.profile.dpd_query = parts[3].lower()
            return True
        if lower.startswith("identity local key-id "):
            state.profile.identity_local_key_id = line.split(None, 3)[3].strip()
            return True
        if lower.startswith("ivrf "):
            state.profile.ivrf = line.split(None, 1)[1].strip()
            return True
        if lower.startswith("keyring local "):
            state.profile.keyring_local = line.split(None, 2)[2].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_profile_key(profname, "keyring_local"), label="keyring local"))
            return True
        if lower.startswith("lifetime "):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                state.profile.lifetime = int(parts[1])
            return True
        if lower.startswith("match address local "):
            parts = line.split()
            if len(parts) >= 5 and parts[3].lower() == "interface":
                lb_match = re.match(r"loopback(\d+)", parts[4], re.I)
                if lb_match:
                    state.profile.match_address_local_interface_loopback_legacy = int(lb_match.group(1))
            else:
                ips = line.split()[3:]
                if ips:
                    state.profile.match_address_local_ip = ips[0]
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_profile_key(profname, "match_address_local_ip"), label="match address local"))
            return True
        if lower.startswith("match fvrf "):
            state.profile.match_fvrf = line.split(None, 2)[2].strip()
            return True
        if lower == "match fvrf any":
            state.profile.match_fvrf_any = True
            return True
        if lower.startswith("match identity remote address "):
            parts = line.split()
            if len(parts) >= 5:
                state.profile.match_identity_remote_ipv4_addresses.append(
                    CryptoIkev2ProfileMatchRemoteIpv4(address=parts[4], mask=parts[5] if len(parts) > 5 else None)
                )
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_profile_key(profname, "match_identity_remote_ipv4_addresses"), label="match identity remote"))
            return True
        if lower.startswith("match identity remote ipv6 "):
            state.profile.match_identity_remote_ipv6_prefixes.append(line.split(None, 4)[4].strip())
            return True
        if lower.startswith("match identity remote key "):
            state.profile.match_identity_remote_keys.extend(line.split()[4:])
            return True
        if lower == "match inbound-only":
            state.profile.match_inbound_only = True
            return True

    # Nested transform-set
    if state.transform_set is not None and lower == "mode tunnel":
        state.transform_set.mode_tunnel = True
        cli_refs.append(
            CliFieldRef(cli_line=line_num, field_key=_transform_set_key(state.transform_set.name, "mode_tunnel"), label="mode tunnel")
        )
        return True

    # Nested ipsec profile
    if state.ipsec_profile is not None:
        ipname = state.ipsec_profile.name
        if lower.startswith("set transform-set "):
            state.ipsec_profile.set_transform_set = line.split()[2:]
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_ipsec_profile_key(ipname, "set_transform_set"), label="set transform-set"))
            return True
        if lower.startswith("set ikev2-profile "):
            state.ipsec_profile.set_ikev2_profile = line.split(None, 2)[2].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_ipsec_profile_key(ipname, "set_ikev2_profile"), label="set ikev2-profile"))
            return True
        if lower.startswith("set isakmp-profile "):
            state.ipsec_profile.set_isakmp_profile = line.split(None, 2)[2].strip()
            return True
        if lower.startswith("set pfs "):
            pfs = _parse_pfs_group(line.split()[2])
            if pfs:
                state.ipsec_profile.set_pfs_group = pfs
            return True
        if lower.startswith("set security-association lifetime seconds "):
            parts = line.split()
            if len(parts) >= 5 and parts[4].isdigit():
                state.ipsec_profile.set_security_association_lifetime_seconds = int(parts[4])
            return True

    # Nested PKI trustpoint
    if state.trustpoint is not None:
        tpid = state.trustpoint.id
        if lower == "enrollment terminal":
            state.trustpoint.enrollment_terminal = True
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_trustpoint_key(tpid, "enrollment_terminal"), label="enrollment terminal"))
            return True
        if lower == "enrollment selfsigned":
            state.trustpoint.enrollment_selfsigned = True
            return True
        if lower.startswith("rsakeypair "):
            state.trustpoint.rsakeypair = line.split(None, 1)[1].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_trustpoint_key(tpid, "rsakeypair"), label="rsakeypair"))
            return True
        if lower.startswith("subject-name "):
            state.trustpoint.subject_name = line.split(None, 1)[1].strip()
            return True
        if lower.startswith("usage "):
            state.trustpoint.usage = line.split(None, 1)[1].strip()
            cli_refs.append(CliFieldRef(cli_line=line_num, field_key=_trustpoint_key(tpid, "usage"), label="usage"))
            return True
        if lower.startswith("revocation-check "):
            state.trustpoint.revocation_check = line.split()[1:]
            return True

    return False
