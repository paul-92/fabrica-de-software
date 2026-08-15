# Windows local production drill

**Owner:** DevOps/Runtime Owner | **Status:** candidate | **Version:** 0.1.0

## Purpose and boundaries

Exercise the existing backup, maintenance, deploy, rollback and restore contracts
on the temporary Windows host before public exposure. This procedure never edits
an active release, copies an open SQLite file, restores over active data, installs
dependencies, builds the frontend, opens a port or starts a public listener.

The portable parts are `deployment.backup`, `MaintenanceGate`, schema checks,
`LocalRuntimeProbe`, `Deployer` orchestration and bounded audit. Windows replaces
only three Linux boundaries: symlink activation with atomic
`current\active-release.json`, systemd with `deployment.windows_runtime restart`,
and `.venv/bin/python` with `.venv\Scripts\python.exe`.

## Expected layout

```text
%USERPROFILE%\ASEP-Beta\
  releases\<release_id>\
  current\active-release.json
  data\asep.db
  workspaces\<organization>\<project>\workspace\
  backups\
  temp\maintenance\
  temp\deployment\
  config\production.env
```

The pointer contains only `{"release_id":"<prepared-id>"}`. Activation validates
the ID and safe release directory, writes a sibling temporary file and atomically
replaces the pointer. Neither candidate nor previous release is removed.

## Prepared Release B

Prepare Release B outside activation using known source. It must have its own
Python 3.12 virtual environment with ASEP installed, installed frontend
dependencies, prebuilt `.next/BUILD_ID`, and `deployment/release.json`. Give it a
new validated ID and place the complete immutable directory below `releases`.
Never clone an active release merely to manufacture drill success, and never run
`pip install`, `npm install`, `npm ci`, or `next build` from deploy/restart.

Run the read-only plan first:

```powershell
.\deployment\windows\asep-deploy.ps1 plan <release-b-id>
```

## Safe sequence

1. Confirm runtime `running`, internal health/readiness/frontend and anonymous 401.
2. Record bounded database counts and workspace inventory; never emit payloads.
3. Enter maintenance, confirm mutations return 503 and health/readiness remain.
4. Create and verify an online SQLite/workspace backup, then release maintenance.
5. Restart via `asep-beta.ps1 restart`; repeat step 1 and compare bounded counts.
6. Plan and deploy prepared Release B with `asep-deploy.ps1 deploy <id>`.
7. Confirm pointer B, readiness and local smoke.
8. Run `asep-deploy.ps1 rollback <release-a-id>` and confirm pointer A/smoke.
9. Verify the backup, then restore only into a newly created isolated root such as
   `%USERPROFILE%\ASEP-Beta-restore-drill`; targets must be absent/empty.
10. Validate checksum, schema, ownership, project/history/usage/quota payload
    structure and workspace mapping. Do not start a listener in the isolated root.

Deployment performs `VALIDATE -> PREFLIGHT -> MAINTENANCE -> BACKUP -> ACTIVATE
-> RESTART -> READY -> LOCAL SMOKE -> OPEN`. Pre-activation failure leaves the
pointer and runtime untouched. Post-activation failure atomically restores the
previous pointer, restarts and smokes it before reopening. Failed rollback keeps
maintenance active and preserves releases, backup and bounded audit.

## Isolated restore example

Run with an operator-confirmed new root. Do not reuse a prior drill directory:

```powershell
$drill = Join-Path $env:USERPROFILE 'ASEP-Beta-restore-drill'
New-Item -ItemType Directory -Path (Join-Path $drill 'data')
New-Item -ItemType Directory -Path (Join-Path $drill 'temp\maintenance')
python -m deployment.backup maintenance-enter --maintenance-root (Join-Path $drill 'temp\maintenance')
python -m deployment.backup restore <backup-path> --database (Join-Path $drill 'data\asep.db') --hosted-root (Join-Path $drill 'workspaces') --maintenance-root (Join-Path $drill 'temp\maintenance')
python -m deployment.backup maintenance-release --maintenance-root (Join-Path $drill 'temp\maintenance')
```

Cleanup is a separate operator decision after evidence review. Remove only the
resolved isolated root created for this drill, never `%USERPROFILE%\ASEP-Beta`.

## Evidence and empty-state interpretation

Audit contains timestamp UTC, previous/candidate releases, stage, outcome,
backup ID and rollback flag only. No environment, password, cookie, API key,
Codex authentication, prompt or provider output is recorded.

When the active environment has no organizations/projects, persistence checks for
projects, sessions, executions, usage, quota and hosted ownership are structural;
do not create fake business or AI activity merely to make non-zero counts.

## Administrative break-glass

An authenticated administrator cannot suspend its own account through the access
service or API, and every organization must retain at least one active
administrator. Recovery of an administrator suspended before these invariants is
a break-glass operation: preserve a backup and audit evidence, use an authorized
maintenance procedure, and validate login afterward. Never record a password or
hash, and do not treat direct SQLite editing as normal user administration.
