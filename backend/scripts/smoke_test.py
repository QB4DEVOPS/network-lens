"""Smoke tests — run in-process and optionally against a live API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.generators.nac_yaml import generate_nac_yaml
from app.main import sync
from app.main import SyncRequest
from app.parsers.ios_cli import parse_cli
from app.version import FEATURES, capability_manifest

FULL_STACK_CLI = """hostn R1
ipv6 unicast-routing

int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64
ipv6 add fe80::1 link"""


def run_in_process_checks() -> None:
    manifest = capability_manifest()
    assert manifest["api_version"], "api_version missing"
    assert manifest["build_id"], "build_id missing"
    assert "ipv6_unicast_routing" in FEATURES

    result = parse_cli(FULL_STACK_CLI)
    assert result.device.system.hostname == "R1"
    assert result.device.system.ipv6_unicast_routing is True
    assert result.context_by_line[2] is None, "unicast-routing should be global context"
    lo0 = result.device.get_interface("Loopback0")
    assert lo0 is not None
    assert lo0.ipv6_link_local_addresses == ["fe80::1"]

    yaml_out = generate_nac_yaml(result.device).content
    assert "ipv6_unicast_routing: true" in yaml_out
    assert "link_local_addresses:" in yaml_out

    resp = sync(SyncRequest(cli_text=FULL_STACK_CLI))
    assert resp.api_version
    assert resp.build_id == manifest["build_id"]
    assert "ipv6_unicast_routing" in resp.features
    assert resp.canonical.system.ipv6_unicast_routing is True
    assert "ipv6_unicast_routing: true" in resp.nac_yaml
    assert resp.context_by_line, "context_by_line missing from sync response"
    assert "iosxe_system" in resp.terraform_hcl, "terraform_hcl missing from sync response"
    assert "ietf-interfaces:interfaces" in resp.restconf_json, "restconf_json missing from sync response"


def _http_json(url: str, method: str = "GET", body: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def run_live_checks(base_url: str) -> None:
    base = base_url.rstrip("/")
    health = _http_json(f"{base}/health")
    assert health.get("status") == "ok", health
    for feature in ("ipv6_unicast_routing", "cli_context_by_line", "restconf_json_preview"):
        assert feature in health.get("features", []), f"/health missing feature {feature}"

    sync_body = _http_json(f"{base}/sync", method="POST", body={"cli_text": FULL_STACK_CLI})
    assert sync_body.get("canonical", {}).get("system", {}).get("ipv6_unicast_routing") is True
    assert "ipv6_unicast_routing: true" in sync_body.get("nac_yaml", "")
    assert sync_body.get("context_by_line"), "live /sync missing context_by_line"
    assert "ietf-interfaces:interfaces" in sync_body.get("restconf_json", ""), "live /sync missing restconf_json"
    assert health.get("build_id") == sync_body.get("build_id"), "health vs sync build_id mismatch"


def main() -> int:
    parser = argparse.ArgumentParser(description="Network Lens smoke tests")
    parser.add_argument(
        "--live",
        metavar="URL",
        help="Also validate a running API, e.g. http://127.0.0.1:8000",
    )
    args = parser.parse_args()

    try:
        run_in_process_checks()
        print(f"OK in-process smoke (build_id={capability_manifest()['build_id']})")
        if args.live:
            run_live_checks(args.live)
            print(f"OK live smoke against {args.live}")
        return 0
    except (AssertionError, urllib.error.URLError, TimeoutError) as exc:
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
