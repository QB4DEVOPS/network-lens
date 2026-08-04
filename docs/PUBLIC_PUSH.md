# Public push checklist

Use this before `git push public main`. Internal work stays on `origin`; public gets releases when you choose.

## 1. Scan for leaked internal metadata

```powershell
.\scripts\verify-public-clean.ps1
```

Must exit **0**. It flags patterns like internal GitHub hosts, machine-specific paths, and personal issue tracker URLs in **tracked** files.

## 2. Review diff against last public push

```powershell
git log public/main..HEAD --oneline
git diff public/main -- README.md docs/
```

Confirm README and docs still read for an external audience.

## 3. Run tests

```powershell
.\validate.bat
```

## 4. Push public only

```powershell
git push public main
```

Do **not** use `git push --all` unless you intend to update both remotes.

## 5. Verify on GitHub

Open https://github.com/QB4DEVOPS/network-lens and spot-check README rendering.

## Patterns that must not appear in tracked files

| Pattern | Why |
|---------|-----|
| `wwwin-github.cisco.com` | Internal GitHub |
| `cx-usps-auto` | Internal org/path |
| `sac-rohosfor` | Internal repo naming |
| `atlassian.net` / personal Jira | Internal tracking |
| `C:\dev\` or `Users\` machine paths | Local workspace leaks |

## Git history

Cleaning files on `main` does not remove old commits on `public`. If a prior public push exposed internal metadata, consider squashing or recreating the public repo before a major release.

## Optional helper

```powershell
.\scripts\push-public.ps1           # verify + push
.\scripts\push-public.ps1 -Validate  # also runs validate.bat
```
