# Windows outbound HTTPS tunnel contract

**Owner:** DevOps/Runtime Owner | **Status:** candidate | **Version:** 0.1.0

## Objective and architecture

Prepare the temporary Windows Private Beta host for a future outbound HTTPS
tunnel without selecting, installing, authenticating, or operating a provider.
No domain, DNS, router, firewall, Windows Service, Task Scheduler, VM, Docker, or
application data contract is changed.

```text
Internet -> provider HTTPS endpoint -> outbound connector on Windows
         -> http://127.0.0.1:8080 (Caddy)
         -> /api/* -> 127.0.0.1:8000 (FastAPI)
         -> /*     -> 127.0.0.1:3000 (Next.js)
```

Use `deployment/caddy/Caddyfile.windows-tunnel` as the separate Windows profile.
Caddy listens only on loopback HTTP, performs no local TLS or redirect, and is
the connector's only ingress target. Ports 3000 and 8000 remain private.

The loopback listener is the trusted connector boundary. Caddy overwrites
`X-Forwarded-Proto` with `https` and `X-Forwarded-For` with its local peer rather
than accepting client values, while preserving public Host. Do not expose 8080
beyond loopback. Public TLS and verified client-IP attribution remain provider
responsibilities; ASEP does not trust an arbitrary forwarded client header.

The profile preserves the 10 MiB request limit, security headers, generic 503,
API/frontend routing and public 404 for `/api/v1/ready`. The Linux `Caddyfile`
remains the unchanged direct-HTTPS profile.

## Provider-neutral contract and recommendation

A future connector adapter must:

- provide one stable temporary public HTTPS origin;
- create only outbound connections and require no inbound router port;
- forward HTTP only to `127.0.0.1:8080` and preserve public Host;
- support cookies without rewriting Path, Secure, HttpOnly or SameSite;
- reconnect after bounded failures and expose `start`, `stop`, and `status`;
- keep logs bounded and redact credentials, cookies and authorization headers;
- read credentials from an external provider file or secure store, not from the
  release, command line, validators, logs, or `ProjectExecution`;
- make `stop` prevent the endpoint from reaching local Caddy.

Provider selection is deferred. Recommendation: accept one only after its adapter
demonstrates this contract in a disposable drill; do not couple ASEP configuration
or a future ASEP domain to a provider CLI or hostname. There is no objective need
for a vendor comparison before that evidence exists.

## Origin, build, cookie and lifecycle

External configuration declares one canonical origin:

```text
ASEP_PUBLIC_ORIGIN=https://<temporary-beta-address>
ASEP_CORS_ORIGINS=https://<temporary-beta-address>
NEXT_PUBLIC_API_URL=https://<temporary-beta-address>
```

`deployment.preflight` rejects HTTP, localhost/loopback, multiple CORS origins,
or disagreement among these values. `NEXT_PUBLIC_API_URL` is compiled into the
Next.js artifact: choosing or changing the origin requires a new immutable release
built with that value. Runtime start/restart and tunnel reconnect never build.

The existing same-origin cookie remains `Secure`, `HttpOnly`, `SameSite=Lax`, and
`Path=/`; no token is stored in localStorage.

`asep-tunnel.ps1` delegates to an external `config\tunnel\connector.ps1` adapter:

```powershell
.\deployment\windows\asep-tunnel.ps1 start
.\deployment\windows\asep-tunnel.ps1 status
.\deployment\windows\asep-tunnel.ps1 stop
```

The adapter does not exist in this sprint. Its lifecycle stays separate from
`asep-beta.ps1`; runtime may remain running while the connector stops/reconnects.

## Future real drill

- [ ] Frontend build used the exact approved temporary HTTPS origin.
- [ ] Production preflight passes with equal origin, API URL and CORS.
- [ ] Backend/frontend run on loopback; Caddy listens on loopback 8080.
- [ ] Connector runs outbound and its bounded logs contain no secret/cookie.
- [ ] Public HTTPS serves frontend and bounded public health.
- [ ] Public readiness returns 404; direct external 3000/8000/8080 probes fail.
- [ ] Login cookie attributes and session reconstruction pass.
- [ ] Project creation, prepare/approve, history, logout pass remote smoke.
- [ ] Tunnel stop removes public reachability while local health remains.

Static/fake tests prove configuration contracts only. They do not claim provider
availability, TLS, external port closure, reconnect, log retention, or endpoint
removal. Record those as real drill evidence before opening the Beta.

## Portability

Migration remains: maintenance, verified backup, Linux host, restore, direct Caddy
HTTPS, remote smoke. Only ingress profile and public origin/build change; backup,
workspace, identity, usage and quota formats remain intact.
