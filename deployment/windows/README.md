# ASEP Windows Private Beta runtime

**Owner:** DevOps/Runtime Owner | **Status:** candidate | **Version:** 0.1.0

This package operates one prepared ASEP release on a temporary Windows Private Beta host. It does not install dependencies, configure a tunnel, TLS, firewall, Task Scheduler or a Windows service.

Set `ASEP_WINDOWS_ROOT` or use the default `%USERPROFILE%\ASEP-Beta`. Create `releases`, `current`, `data`, `workspaces`, `backups`, `temp`, `logs`, `codex` and `config` below that root. Copy `asep.env.example` to `config\production.env`, replace deployment values, and restrict its ACL to the dedicated Beta account. Store only `{"release_id":"<prepared-id>"}` in `current\active-release.json`; the ID is validated and resolved strictly below `releases` without a symlink or junction.

From a PowerShell session owned by the dedicated account:

```powershell
.\deployment\windows\asep-beta.ps1 start
.\deployment\windows\asep-beta.ps1 status
.\deployment\windows\asep-beta.ps1 restart
.\deployment\windows\asep-beta.ps1 stop
```

Start launches a persistent supervisor, which exclusively acquires `temp\runtime\instance.lock`, rejects occupied loopback ports, starts the backend on `127.0.0.1:8000` and frontend on `127.0.0.1:3000`, waits up to 30 seconds for internal readiness, and records bounded PID plus process-creation identities. Stop targets only the validated supervisor tree and confirms that its recorded components ended before removing metadata. Stale metadata is cleaned only when none of its process identities remains alive.

Backend and frontend stdout/stderr are separated below `logs`; each active log rolls to one `.1` file at 5 MiB before a new runtime instance starts. The supervisor never prints environment values. Production configuration and Codex state remain outside releases. The application `ProcessRunner` continues to pass only its existing host allowlist to Codex and validators.

The prepared release must contain `.venv\Scripts\python.exe`, installed Python dependencies, installed frontend dependencies and `frontend\.next\BUILD_ID`. Start and restart never install or build. The PC must remain powered, awake, connected and logged into the dedicated account. External access is intentionally absent until 26.7C.
