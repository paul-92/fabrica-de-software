from pathlib import Path

from deployment.preflight import check


ROOT = Path(__file__).parents[3]
CADDY = ROOT / "deployment" / "caddy" / "Caddyfile.windows-tunnel"


def test_tunnel_caddy_is_loopback_http_and_routes_existing_upstreams():
    config = CADDY.read_text(encoding="utf-8")
    assert "http://127.0.0.1:8080" in config
    assert "https://" not in config
    assert "0.0.0.0" not in config
    assert "redir " not in config
    assert "reverse_proxy @api 127.0.0.1:8000" in config
    assert "reverse_proxy 127.0.0.1:3000" in config
    assert config.index("respond @readiness 404") < config.index("reverse_proxy @api")


def test_tunnel_caddy_normalizes_forwarded_proto_and_bounds_failures():
    config = CADDY.read_text(encoding="utf-8")
    assert config.count("header_up X-Forwarded-Proto https") == 2
    assert "header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}" not in config
    assert config.count("header_up X-Forwarded-For {remote_host}") == 2
    assert "max_size 10MB" in config
    assert 'respond "Service unavailable." 503' in config


def test_linux_caddy_contract_remains_direct_https():
    config = (ROOT / "deployment" / "caddy" / "Caddyfile").read_text(encoding="utf-8")
    assert "redir https://{host}{uri} permanent" in config
    assert "https://{$ASEP_PUBLIC_DOMAIN:beta.example.com}" in config
    assert "header_up X-Forwarded-Proto {scheme}" in config


def test_remote_origin_must_be_https_non_local_and_same_origin(tmp_path, monkeypatch):
    from tests.qa.deployment.test_runtime_packaging import valid_environment

    environment = valid_environment(tmp_path)
    monkeypatch.setattr("deployment.preflight.sys.version_info", (3, 12, 0))
    versions = lambda executable: (30, 0)
    assert check(environment, which=lambda name: name, command_version=versions,
                 platform_name="posix") == ()

    environment["ASEP_PUBLIC_ORIGIN"] = "http://localhost:3000"
    failures = check(environment, which=lambda name: name, command_version=versions,
                     platform_name="posix")
    assert any("non-local HTTPS" in failure for failure in failures)

    environment["ASEP_PUBLIC_ORIGIN"] = "https://other.example"
    failures = check(environment, which=lambda name: name, command_version=versions,
                     platform_name="posix")
    assert any("NEXT_PUBLIC_API_URL" in failure for failure in failures)
    assert any("ASEP_CORS_ORIGINS" in failure for failure in failures)


def test_tunnel_lifecycle_is_separate_and_contains_no_provider_or_secret():
    launcher = (ROOT / "deployment" / "windows" / "asep-tunnel.ps1").read_text(encoding="utf-8")
    assert "ValidateSet('start','stop','status')" in launcher
    assert "connector.ps1" in launcher
    assert "asep-beta.ps1" not in launcher
    folded = launcher.casefold()
    assert all(value not in folded for value in ("token=", "password=", "cloudflare", "ngrok"))
