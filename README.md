# Network Lens

**Live NaC first · CLI-first onboarding for brownfield and greenfield**

Type abbreviated IOS-style CLI on the left; see live **Cisco Network-as-Code YAML** on the right (`iosxe.devices[]` shape). Preview only — **Generated · Not applied** — nothing is pushed to a device.

**Repository:** [github.com/QB4DEVOPS/network-lens](https://github.com/QB4DEVOPS/network-lens)

## What it is

Network Lens is a dual-pane IDE for engineers moving from imperative IOS config to declarative NaC:

| Mode | How you use it |
|------|----------------|
| **Greenfield** | Type or paste CLI snippets; learn the NaC data model as YAML appears |
| **Brownfield** | Paste slices of existing config (same pipeline); bulk file import planned |

Outputs include **NaC YAML**, **Terraform HCL**, and **RESTCONF JSON** previews, with line-level mapping between CLI and structured fields.

Target contract: [netascode/terraform-iosxe-nac-iosxe](https://github.com/netascode/terraform-iosxe-nac-iosxe) · Schema docs: [Network as Code IOS-XE](https://netascode.cisco.com/docs/data_models/iosxe/overview/)

## Quick start (Windows)

From the repo root:

```powershell
.\dev.bat
```

Opens the backend API and Vite frontend. Then visit **http://localhost:5173**.

### Manual start

**Backend** (run first):

```powershell
cd backend
.\run.bat
```

**Frontend:**

```powershell
cd frontend
.\run.bat
```

`run.bat` clears stale API listeners, runs smoke tests, picks a free port, and writes `frontend\.env`.

On Linux or macOS, use the backend venv and run uvicorn/npm directly (see `backend/run.ps1` and `frontend/package.json` for the equivalent steps).

## Validate

```powershell
.\validate.bat
```

Runs backend pytest, smoke tests, and frontend build checks.

## Example — type left, learn right

Network Lens is a **live IDE preview**, not a bare YAML exporter. The right pane shows schema contract, safety labels, and structured config filling in as you type.

<table>
<tr>
<td width="50%" valign="top">

**CLI input** (left pane)

```
hostn R1
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64
enable password Cisco
username admin privilege 15 secret cisco
```

</td>
<td width="50%" valign="top">

**nac.yaml** (right pane — live preview)

```yaml
# Network Lens — Live NaC preview
# Schema: iosxe-devices-configuration-full
# Schema version: 4.0.0
# Canonical root: iosxe.devices[]
# Contract: iosxe.devices[].configuration.*
# Generated · Not applied
iosxe:
  devices:
  - name: iosv-01
    configuration:
      system:
        hostname: "R1"
        enable_password: "Cisco"
      users:
        - name: "admin"
          privilege: 15
          secret: "cisco"
      interfaces:
        loopbacks:
        - id: '0'
          ipv4:
            address: "10.0.0.1"
            address_mask: "255.255.255.255"
          ipv6:
            enable: true
            addresses:
              - prefix: "2001:db8::1/64"
          shutdown: false
```

</td>
</tr>
</table>

Preview headers are intentional: they teach **which schema**, **which contract**, and that output is **not applied**. Strip preview headers when exporting into a real NaC repo.

CLI abbreviations (input only): `hostn`, `int`, `no sh`, `ip add`, `lo0`, `g0/0/0`.

## Architecture

```
CLI input → parse_cli() → canonical Device → generate_nac_yaml() / terraform / restconf
```

Canonical JSON Schema: [`schemas/canonical-device.json`](schemas/canonical-device.json)  
Parser ↔ YAML line mapping: [`backend/app/field_keys.py`](backend/app/field_keys.py)  
Coverage checklist: [`docs/NAC_COVERAGE.md`](docs/NAC_COVERAGE.md)

## Packages

| Context | Name |
|---------|------|
| Product / UI | Network Lens |
| npm | `@network-lens/frontend` |
| Python | `network-lens-backend` |
| NaC contract | `netascode/nac-iosxe/iosxe` |

## Scope and safety

- **Preview only** — no `terraform apply` or device push in this tool
- **Growing coverage** — not full NaC parity; see coverage doc for wired vs scaffold sections
- **Fidelity** — secrets and passwords appear verbatim in live preview (learning/migration aid; treat exports accordingly)

## CI

GitHub Actions (`.github/workflows/ci.yml`): backend pytest + smoke tests; frontend `npm ci` + build.

## Maintainers

Before updating the public GitHub mirror, run the checks in [`docs/PUBLIC_PUSH.md`](docs/PUBLIC_PUSH.md).
