# ASEP Private Beta runtime packaging

**Owner:** DevOps/Runtime Owner | **Status:** candidate | **Version:** 0.2.0

## Objective and scope

This directory packages the existing ASEP backend and frontend processes and its Caddy HTTPS edge for one Linux VM. It does not provision a VM, register a domain, issue a real certificate, configure a firewall, backup, containers, or remote deployment.

## Runtime contract

- Python 3.12 or newer, matching `pyproject.toml`;
- Node.js 20.9 or newer, the minimum supported by the pinned Next.js 16 runtime;
- npm 10 or newer for the versioned lockfile and `npm start` contract;
- Codex CLI available through the service `PATH` and able to answer `codex --version`. No Codex version is pinned because the repository has no trustworthy pin.
- Caddy 2.10 or newer; the minimum is required by the versioned 10 MB `request_body` limit.

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

## Public HTTPS edge

Caddy is the selected reverse proxy because its packaged service provides automatic certificate lifecycle and HTTP-to-HTTPS redirects with a small configuration. Install `caddy/Caddyfile` as `/etc/caddy/Caddyfile`; keep the distribution-provided `caddy.service` and its dedicated Caddy identity. The example `caddy/asep.conf` is a systemd drop-in for setting the future domain and contains no secret. Replace `beta.example.com`; never deploy the placeholder as a real production hostname.

The public contract is same-origin:

```text
https://<domain>/api/*  -> 127.0.0.1:8000
https://<domain>/*      -> 127.0.0.1:3000
```

Port 80 only redirects to HTTPS. Caddy preserves methods and query strings, overwrites the necessary `Host`, `X-Forwarded-For`, and `X-Forwarded-Proto` values instead of trusting client-supplied forwarding headers, and returns a generic bounded service-unavailable response when an upstream cannot be reached. No filesystem handler is configured. WebSocket-specific configuration is unnecessary because the current application exposes no WebSocket route and Caddy's reverse proxy supports protocol upgrades when needed.

Requests are capped at 10 MB. Current ASEP endpoints exchange bounded JSON and do not expose file upload, so this leaves headroom without accepting unbounded bodies. Reassess the limit before adding uploads. Security headers include HSTS on the HTTPS site, MIME sniffing protection, a conservative referrer policy, and frame denial. The CSP is deliberately limited to `frame-ancestors 'none'` to avoid breaking Next.js scripts and styles.

`/api/v1/health` remains public and returns only the existing bounded liveness contract. `/api/v1/ready` is answered with a generic 404 at the public edge; operators must call readiness through `127.0.0.1:8000`. This keeps persistence availability private while retaining an internal readiness gate. Upstream API responses, including bounded application errors, are otherwise preserved.

`NEXT_PUBLIC_API_URL` must equal `https://<domain>` during `npm run build`, not a separate API hostname and not a runtime-only value. Existing clients append `/api/v1/...` and send credentials. The backend CORS origin must be the same HTTPS origin. Development remains `http://localhost:3000` -> `http://localhost:8000` using the existing development configuration.

The existing session cookie crosses the proxy unchanged: `HttpOnly`, `Secure`, `SameSite=Lax`, and `Path=/`. Caddy does not rewrite its domain or path, so login, logout, and session reconstruction remain same-origin.

## DNS, firewall, Caddy, and service procedure

Future operator-owned activation order:

1. Point an A/AAAA record for the approved domain to the VM and wait for authoritative DNS resolution.
2. Allow inbound `80/tcp` and `443/tcp`; keep `3000/tcp` and `8000/tcp` loopback-only. SSH follows the provider/operator access policy and is not opened by ASEP scripts.
3. Set `ASEP_PUBLIC_DOMAIN` for `caddy.service`, install the Caddyfile, and run `caddy validate --config /etc/caddy/Caddyfile`.
4. Set `NEXT_PUBLIC_API_URL=https://<domain>` at frontend build time and `ASEP_CORS_ORIGINS=https://<domain>` in `/etc/asep/asep.env`.
5. Start the ASEP backend and frontend units, verify internal readiness, then reload Caddy.
6. Verify the HTTP redirect, HTTPS frontend, public health, restricted public readiness, login/logout/session reconstruction, and journal output with bounded request timeouts.

Automatic public TLS requires a valid domain resolving to the VM and externally reachable ports 80/443. The committed template does not use self-signed certificates and does not contain an ACME credential or real domain.

## Security notes and next boundary

The hardening keeps the release read-only while permitting `/var/lib/asep` and `/var/tmp/asep`. `PrivateTmp` does not block hosted workspaces or validators. VM provisioning, real DNS/TLS activation, firewall application, backup/restore, release activation/rollback automation, monitoring, and remote deployment remain for 26.6E or a separately authorized sprint.
