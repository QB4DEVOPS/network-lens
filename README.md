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

The CLI is how you *enter* config. **nac.yaml is what you're building** — drop this into a real NaC repo.

**Left (CLI input)** — familiar, abbreviated:

```
hostn R1
ipv6 unicast-routing
int lo0
no sh
ip add 10.0.0.1 255.255.255.255
ipv6 enable
ipv6 address 2001:db8::1/64
```

**Right (nac.yaml)** — the strong side, `iosxe.devices[]`:

```yaml
iosxe:
  devices:
  - name: iosv-01
    configuration:
      system:
        hostname: "R1"
        ipv6_unicast_routing: true
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

That's the lesson: **`configuration:` is where router config lives.** CLI lines become typed fields under `iosxe.devices[].configuration.*` — ready for `netascode/nac-iosxe` and `nac-validate`.

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
