from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from asep.api.composition import create_default_app
from asep.configuration import ApplicationSettings


ROOT = Path(__file__).parents[3]
CADDYFILE = ROOT / "deployment" / "caddy" / "Caddyfile"
ENVIRONMENT = ROOT / "deployment" / "asep.env.example"
BACKEND_UNIT = ROOT / "deployment" / "systemd" / "asep-backend.service"
FRONTEND_UNIT = ROOT / "deployment" / "systemd" / "asep-frontend.service"


def caddyfile() -> str:
    return CADDYFILE.read_text(encoding="utf-8")


def production(tmp_path: Path) -> ApplicationSettings:
    return ApplicationSettings(
        environment="production",
        storage_backend="sqlite",
        sqlite_database=tmp_path / "database" / "asep.db",
        hosted_root=tmp_path / "workspaces",
        maintenance_directory=tmp_path / "maintenance",
        cors_origins=("https://beta.example.com",),
        access_cookie_secure=True,
        legacy_admin_email="admin@example.test",
        legacy_admin_password="strong-private-beta-password",
    )


def test_caddy_routes_api_and_frontend_to_loopback_only():
    config = caddyfile()
    assert "@api path /api/*" in config
    assert "reverse_proxy @api 127.0.0.1:8000" in config
    assert "reverse_proxy 127.0.0.1:3000" in config
    assert "0.0.0.0" not in config
    assert "file_server" not in config


def test_http_redirects_to_https_and_domain_is_configurable_placeholder():
    config = caddyfile()
    assert "http://{$ASEP_PUBLIC_DOMAIN:beta.example.com}" in config
    assert "redir https://{host}{uri} permanent" in config
    assert "https://{$ASEP_PUBLIC_DOMAIN:beta.example.com}" in config


def test_proxy_overwrites_forwarded_headers_and_sets_minimum_security_headers():
    config = caddyfile()
    for expected in (
        "header_up Host {host}",
        "header_up X-Forwarded-For {remote_host}",
        "header_up X-Forwarded-Proto {scheme}",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "frame-ancestors 'none'",
        "max_size 10MB",
    ):
        assert expected in config


def test_documented_caddy_contract_supports_request_limit():
    runbook = (ROOT / "deployment" / "README.md").read_text(encoding="utf-8")
    assert "Caddy 2.10 or newer" in runbook


def test_health_is_proxied_but_public_readiness_is_restricted():
    config = caddyfile()
    assert "@readiness path /api/v1/ready" in config
    assert "respond @readiness 404" in config
    assert "/api/v1/health" not in config
    assert config.index("respond @readiness 404") < config.index("reverse_proxy @api")


def test_same_origin_contract_and_private_application_binds():
    environment = ENVIRONMENT.read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_API_URL=https://beta.example.invalid" in environment
    assert "ASEP_CORS_ORIGINS=https://beta.example.invalid" in environment
    assert "--host 127.0.0.1 --port 8000" in BACKEND_UNIT.read_text(encoding="utf-8")
    assert "--hostname 127.0.0.1 --port 3000" in FRONTEND_UNIT.read_text(encoding="utf-8")


def test_proxy_configuration_contains_no_secret_material():
    config = caddyfile().casefold()
    for forbidden in ("password=", "api_key", "private key", "bearer ", "token="):
        assert forbidden not in config


def test_production_cookie_and_health_contracts_remain_bounded(tmp_path):
    client = TestClient(create_default_app(production(tmp_path)), base_url="https://beta.example.com")
    response = client.post(
        "/api/v1/access/login",
        json={"email": "admin@example.test", "password": "strong-private-beta-password"},
    )
    cookie = response.headers["set-cookie"]
    assert all(value in cookie for value in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"))
    assert client.get("/api/v1/health").json() == {"status": "ok", "api_version": "v1"}
    assert client.get("/api/v1/ready").json() == {"status": "ready"}
    assert str(tmp_path) not in client.get("/api/v1/health").text
