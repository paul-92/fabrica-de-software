# ASEP Private Beta runtime packaging

**Owner:** DevOps/Runtime Owner | **Status:** candidate | **Version:** 0.1.0

## Objective and scope

This directory packages the existing ASEP backend and frontend processes for one Linux VM. It does not provision a VM, configure a reverse proxy, domain, TLS, firewall, backup, containers, or remote deployment.

## Runtime contract

- Python 3.12 or newer, matching `pyproject.toml`;
- Node.js 20.9 or newer, the minimum supported by the pinned Next.js 16 runtime;
- npm 10 or newer for the versioned lockfile and `npm start` contract;
- Codex CLI available through the service `PATH` and able to answer `codex --version`. No Codex version is pinned because the repository has no trustworthy pin.

## Layout and permissions

```text
/opt/asep/current -> /opt/asep/releases/<version>
/opt/asep/releases/<version>/     immutable release, root-owned, asep read/execute
/etc/asep/asep.env                external configuration/secrets, root:asep 0640
/var/lib/asep/asep.db             SQLite, asep read/write
/var/lib/asep/workspaces/         hosted workspaces, asep read/write
/var/tmp/asep/                    runtime temporary files, asep read/write
```

The dedicated `asep` user/group is non-root and should have no interactive shell. Codex state lives under `/var/lib/asep/codex` through `CODEX_HOME`, where the service identity can read its deployment-time authentication. Account creation, Codex login, and filesystem installation are intentionally outside this sprint. Releases must not contain SQLite data, hosted workspaces, or secrets.

## Build/deploy time versus runtime

Build/deploy time installs the Python package and dependencies into `/opt/asep/current/.venv`, runs `npm ci` in `frontend/`, and runs `npm run build` once. Runtime only runs preflight, Uvicorn, `next start`, Codex, and allowlisted validators. ASEP never installs dependencies in hosted projects; current Project Engineering validators continue to execute only predefined Python/npm commands against already-present dependencies.

## Processes and startup

Install the example environment externally as `/etc/asep/asep.env`, replace every deployment value, and install the two units from `systemd/`. The backend uses the existing application factory, binds `127.0.0.1:8000`, has no reload/debug mode, and receives SIGTERM with a bounded stop timeout. The frontend uses the previously built `.next` output through `next start`, binds `127.0.0.1:3000`, and never builds during restart.

Run as the `asep` service identity, after loading the external environment:

```bash
/opt/asep/current/.venv/bin/python -m deployment.preflight
systemctl start asep-backend.service
systemctl start asep-frontend.service
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/api/v1/health
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/api/v1/ready
```

There is no infinite polling. systemd sends stdout/stderr to the journal and bounds restart attempts. The backend inherits `PATH` for Codex discovery. When Codex runs, the existing `ProcessRunner` allowlist passes only basic OS variables plus explicit per-call values, so backend secrets and API keys are not propagated to Codex or validators.

## Security notes and next boundary

The hardening keeps the release read-only while permitting `/var/lib/asep` and `/var/tmp/asep`. `PrivateTmp` does not block hosted workspaces or validators. Reverse proxy, public routing, TLS, firewall, backup/restore, release activation/rollback automation, monitoring, and remote deployment remain for later work (26.6D or a separately authorized sprint).
