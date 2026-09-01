# ASEP Private Beta runtime packaging

**Owner:** DevOps/Runtime Owner | **Status:** candidate | **Version:** 0.5.0

The temporary Windows Private Beta runtime is documented separately in [windows/README.md](windows/README.md); Linux packaging below remains unchanged.

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

Build/deploy time installs the Python package and dependencies into `/opt/asep/current/.venv`, runs `npm ci` in `frontend/`, and runs `npm run build` once. Runtime only runs preflight, Uvicorn, `next start`, Codex, controlled dependency provisioning, and allowlisted validators. For hosted Node projects, Project Engineering may materialize only exact dependencies from an approved dependency plan. It validates every project manifest, permits coherent local workspace packages, uses an allowlisted registry, disables lifecycle scripts/audit/funding, persists fingerprinted evidence, and blocks validation on any mismatch or package-manager failure.

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

The hardening keeps the release read-only while permitting `/var/lib/asep` and `/var/tmp/asep`. `PrivateTmp` does not block hosted workspaces or validators. VM provisioning, real DNS/TLS activation, firewall application, release activation/rollback automation, monitoring, and remote deployment remain for 26.6F or a separately authorized sprint.

## Backup and restore

SQLite and `ASEP_HOSTED_ROOT` form one logical backup. `deployment.backup` creates an online SQLite backup through SQLite's backup API, copies only safe hosted workspace entries, writes a versioned manifest with UTC timestamp, application version, schema version, sizes and SHA-256 checksums, validates the staged result, and atomically promotes its directory. Partial directories are hidden and never valid backups.

The API maintenance gate rejects new POST/PUT/PATCH/DELETE requests with a bounded 503 while allowing health checks. Existing mutations hold leases; entering maintenance waits up to the configured timeout for those leases to drain. A normal daily backup enters and releases this boundary automatically:

```bash
/opt/asep/current/.venv/bin/python -m deployment.backup backup \
  --database /var/lib/asep/asep.db \
  --hosted-root /var/lib/asep/workspaces \
  --backup-root /var/backups/asep \
  --maintenance-root /var/tmp/asep/maintenance \
  --release-root /opt/asep/current \
  --retention-count 7
```

The destination must be absolute and disjoint from both persistence roots. It should be `asep:asep` mode `0700`, outside the release and never served by Caddy. Retention keeps the newest N completed backups and never removes the current or a `.partial` backup. Excluded workspace content includes `.env*`, logs, `.next`, caches, `node_modules`, `__pycache__`, and temporary directories. Any symlink/reparse point or malformed `organization/project/workspace` layout fails closed. External configuration, Codex state and credentials are never source paths.

Deployment backup sequence:

```bash
python -m deployment.backup maintenance-enter --maintenance-root /var/tmp/asep/maintenance --timeout-seconds 30
python -m deployment.backup backup --maintenance-active --database /var/lib/asep/asep.db --hosted-root /var/lib/asep/workspaces --backup-root /var/backups/asep --maintenance-root /var/tmp/asep/maintenance --release-root /opt/asep/current --retention-count 7
python -m deployment.backup verify /var/backups/asep/<backup_id>
# deploy/update, then run internal health/readiness and the bounded application smoke
python -m deployment.backup maintenance-release --maintenance-root /var/tmp/asep/maintenance
```

Release maintenance only after the new release passes smoke. If the maintenance command is interrupted, the marker intentionally remains fail-closed; an operator must confirm no backup/deploy is active before releasing it.

Restore requires backend/frontend services stopped, active maintenance, an already verified backup, a nonexistent SQLite target and an absent or empty hosted target:

```bash
systemctl stop asep-frontend.service asep-backend.service
python -m deployment.backup maintenance-enter --maintenance-root /var/tmp/asep/maintenance
python -m deployment.backup verify /var/backups/asep/<backup_id>
python -m deployment.backup restore /var/backups/asep/<backup_id> --database /var/lib/asep/asep.db --hosted-root /var/lib/asep/workspaces --maintenance-root /var/tmp/asep/maintenance
# run production preflight, start backend, check internal readiness and smoke
# start frontend/Caddy only after validation, then reopen access
python -m deployment.backup maintenance-release --maintenance-root /var/tmp/asep/maintenance
```

Restore stages both components, verifies checksums and supported schema without migration, reconstructs project ownership/workspace mappings, parses session/execution and AI usage/quota payloads, then promotes into the empty targets. It never overwrites active state. On failure it reports a bounded error, leaves the source backup untouched and does not declare success.

Private Beta recommendation: back up daily, always back up before deploy, retain the latest seven completed backups, test restore regularly, and add an encrypted off-VM copy in a future authorized sprint. This sprint does not implement cloud storage, PITR, replication or remote scheduling.

## Immutable release deployment and rollback

Prepared releases live at `/opt/asep/releases/<release_id>` and the active release is the atomic symlink `/opt/asep/current`. Release IDs are 1–64 characters from letters, digits, dot, underscore and hyphen, must start alphanumeric, and cannot contain separators, traversal or absolute paths. Candidate and previous releases are never edited or removed during activation.

Every prepared release must already contain its Python virtual environment, installed frontend dependencies, `.next/BUILD_ID`, `deployment/preflight.py`, and `deployment/release.json`. Preparation performs dependency installation, build and quality gates before the release reaches the VM release directory. Activation performs no `pip`, `npm`, package registry access or `next build`.

The release manifest declares the exact SQLite schema expected by that binary. Deployment reads `schema_metadata` directly in read-only mode and does not instantiate `SQLiteDatabase`, because initialization can run forward migrations. The current policy performs no migration: schema mismatch fails closed before activation. A future migration must be separately authorized, run under maintenance after the mandatory backup, and declare binary rollback compatibility. ASEP does not invent reverse migrations; if persistence no longer matches the previous binary, automatic rollback is blocked and maintenance remains active for the restore/operator runbook.

Future Linux deployment command:

```bash
sudo /opt/asep/current/.venv/bin/python -m deployment.deploy deploy <release_id>
```

Workflow:

```text
PREPARE -> PREFLIGHT -> MAINTENANCE -> BACKUP -> ACTIVATE
        -> RESTART -> READY -> LOCAL SMOKE -> OPEN
```

The operator process needs narrowly scoped authority to create the atomic `current` symlink, write `/var/lib/asep/deployment`, create `/var/backups/asep`, and restart only `asep-backend.service` and `asep-frontend.service`. The runtime `asep` user remains non-root and cannot change releases or invoke arbitrary systemd operations. Caddy is not restarted because its configuration is unchanged.

Activation creates a temporary sibling symlink and promotes it with one filesystem `os.replace`; the previous release directory remains intact. A cross-process `deploy.lock` prevents concurrent deploys. An existing/abandoned lock fails closed and records PID/timestamp. Only after the operator confirms no deploy process exists may it run:

```bash
sudo /opt/asep/current/.venv/bin/python -m deployment.deploy unlock --confirm-abandoned
```

After restart, deployment polls only `http://127.0.0.1:8000/api/v1/ready` with finite timeout and interval. Local smoke checks backend health, the frontend root and the expected unauthenticated API session boundary. Internet, DNS, TLS and Caddy are not required.

Failure after activation follows:

```text
FAIL -> KEEP MAINTENANCE -> REACTIVATE PREVIOUS -> RESTART
     -> READY -> LOCAL SMOKE -> OPEN
```

If previous-schema compatibility or rollback validation fails:

```text
FAIL -> KEEP MAINTENANCE -> OPERATOR REVIEW / RESTORE RUNBOOK
```

No backup restore occurs automatically. Failure before activation leaves `current` untouched, avoids service restart, and releases maintenance only when active persistence remains safe.

Manual rollback uses the same compatibility, preflight, maintenance, atomic activation, restart, readiness and smoke boundaries:

```bash
sudo /opt/asep/current/.venv/bin/python -m deployment.deploy rollback <previous_release_id>
```

Maintenance is released only after the rollback is healthy. A failed rollback remains closed for operator review.

Dry-run performs structural path/release/build checks and read-only schema compatibility, and prints the intended services and probe URLs. It does not run candidate preflight, enter maintenance, create backup, change `current`, restart services or claim runtime checks succeeded:

```bash
sudo /opt/asep/current/.venv/bin/python -m deployment.deploy deploy <release_id> --dry-run
```

Each real operation writes a bounded JSON audit record under `/var/lib/asep/deployment/deploys` with candidate, previous release, UTC timestamp, stage, outcome and pre-deploy backup ID. No environment, command output or secret is persisted.

## Private Beta remote smoke and opening runbook

The deploy workflow's local smoke remains intentionally limited to loopback health, frontend, readiness and anonymous access. After it passes, the operator runs the separate same-origin acceptance flow through Caddy and real TLS. Credentials are external secrets and never command-line arguments or versioned files:

```bash
export ASEP_SMOKE_EMAIL='<tenant-a-smoke-user>'
export ASEP_SMOKE_PASSWORD='<external-secret>'
export ASEP_SMOKE_TENANT_B_EMAIL='<tenant-b-smoke-user>'
export ASEP_SMOKE_TENANT_B_PASSWORD='<external-secret>'
export ASEP_SMOKE_RUNTIME_ID='<configured-provider-runtime>'
export ASEP_RELEASE_ID='<active-release-id>'
/opt/asep/current/.venv/bin/python -m deployment.smoke --base-url https://<approved-domain>
```

The controlled instruction creates one small Python module and focused test in a newly created hosted project. There is no project deletion API, so automation does not invent unsafe filesystem cleanup: identify these projects by the `Private Beta smoke <UTC>` name and retain/remove them only under an authorized data-retention procedure. Node coverage is conditional on the selected provider plan and already-installed project dependencies; ASEP never installs them during smoke.

The remote sequence is fail-closed: HTTPS frontend, HTTP redirect, public health, externally hidden readiness, anonymous rejection, Beta login and secure cookie, session reconstruction, hosted project/session, non-mutating prepare, approve, real validator and Quality Gate, execution-scoped provider usage, quota call increment, history/direct reopen, cross-tenant denial, then logout and rejected old session. Output contains only release ID, UTC timestamp, execution ID, overall status and elapsed milliseconds. Failures identify one stage, return non-zero and omit bodies, credentials, cookies, prompts and provider output. Missing provider token counts are accepted; a recorded provider call and quota call increment are mandatory.

Checks that require the real VM/network and cannot be proven by unit tests:

- authoritative DNS resolves the approved hostname to the intended VM; public certificate chain and hostname validate;
- ports 80/443 are reachable, while external probes to 3000/8000 fail and internal loopback probes succeed;
- Caddy returns a public 404 for `/api/v1/ready`, redirects HTTP to HTTPS and preserves the secure same-origin cookie;
- systemd units run as the dedicated identity, the release is immutable, and journal output contains no credential or sensitive payload;
- the configured provider and allowlisted validators actually execute in the disposable hosted workspace.

Opening checklist, in order: VM baseline and ownership; DNS; firewall; real TLS; systemd units; production preflight; known verified backup; prepared release; deploy dry-run; deploy; internal readiness/local smoke; remote smoke; restart smoke; restore drill; rollback drill; authorized Beta opening. Do not mark an item passed from templates or fake tests.

Restart smoke: record the controlled project/session/execution and quota snapshot, restart only `asep-backend.service` and `asep-frontend.service`, wait for internal readiness, rerun the remote smoke, and directly reopen the recorded project/execution. Confirm project, hosted files, history, usage and quota survived; login again because in-memory cookie/session validity across process restart is not promised. Do not restart Caddy when its configuration is unchanged.

Restore drill: choose and verify a known backup; close maintenance and stop application units; restore into clean, nonexistent/empty persistence targets using the 26.6E procedure; run preflight; start backend; verify internal readiness; start frontend; release maintenance; run the controlled remote smoke. Preserve the source backup and record its ID and result.

Deploy drill: prepare the immutable release off-VM, run `deployment.deploy ... --dry-run`, deploy, verify internal readiness/local smoke, then run remote smoke. For rollback, use a deliberately invalid candidate that fails preflight or local validation without changing schema/data, confirm automatic reactivation of the previous release, internal readiness and remote smoke. Never inject corruption or an incompatible migration into future production.
