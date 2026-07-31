# Network Lens

**Live NaC first · Programmatically first**

Type IOS-style CLI on the left, see live **nac.yaml** on the right (`iosxe.devices[]` shape).

**Repo:** `sac-rohosfor-network-lens-labs-as-code`  
**GitHub:** `https://wwwin-github.cisco.com/cx-usps-auto/sac-rohosfor-network-lens-labs-as-code`  
**Local path:** `C:\dev\sac-rohosfor-network-lens-labs-as-code`

## Quick start (one command)

From repo root:

```powershell
.\dev.bat
```

This opens two windows: backend API + Vite frontend. Then open http://localhost:5173

## Manual start

### Backend

```powershell
cd backend
.\run.bat
```

### Frontend

```powershell
cd frontend
.\run.bat
```

Always start **backend before** frontend. `run.bat` kills stale listeners, runs smoke tests, picks a free port, and writes `frontend\.env`.

## Validate

```powershell
.\validate.bat
```

Runs pytest + in-process smoke tests (+ live smoke if API is running).

## CI

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push/PR:

- Backend: `pytest` + smoke tests
- Frontend: `npm ci` + `npm run build`

## Example — type left, **learn right**

Network Lens is a **live IDE preview** — not a bare YAML exporter. The right pane shows what you see in the app: schema contract, safety labels, and structured config filling in as you type.

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
ipv6 address 2001:db8:1::1/64
```

</td>
<td width="50%" valign="top">

**nac.yaml** (right pane — live preview)

```yaml
# Network Lens — Live NaC preview
# Schema: iosxe-devices-configuration-mvp
# Schema version: 3.0.0
# Canonical root: iosxe.devices[]
# Contract: lean iosxe.devices[].configuration.*
# Model docs: https://netascode.cisco.com/docs/data_models/iosxe/overview/
# Module: netascode/nac-iosxe/iosxe 0.1.0
# Generated · Not applied
# Apply-safe: only interfaces you typed in CLI — no placeholder resources
iosxe:
  devices:
  - name: iosv-01
    configuration:
      system:
        hostname: "R1"
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
              - prefix: "2001:db8:1::1/64"
          shutdown: false
```

</td>
</tr>
</table>

The header lines are intentional — they teach **which schema**, **which contract**, and **Generated · Not applied** (preview only, no push to device). When you export to a real NaC repo, strip the preview header; in the IDE, keep it — that's the lesson happening live.
CLI abbreviations (left pane only): `hostn`, `int`, `no sh`, `ip add`, `lo0`, `g0/0/0`.

## Architecture

```
CLI input → parse_cli() → canonical Device model → generate_nac_yaml() → nac.yaml pane
```

Canonical JSON Schema: `schemas/canonical-device.json`

## Package names

| Context | Name |
|---------|------|
| Product / UI | Network Lens |
| npm | `@network-lens/frontend` |
| Python | `network-lens-backend` |
| NaC contract | `netascode/nac-iosxe/iosxe` |

Generated output is **Generated · Not applied** — no `terraform apply` in Phase 0.
