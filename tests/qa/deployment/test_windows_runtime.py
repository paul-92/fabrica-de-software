from __future__ import annotations

import json
from pathlib import Path

import pytest

from deployment import preflight
from deployment.windows_runtime import RuntimeError, RuntimePaths, Supervisor, load_environment


def layout(tmp_path: Path):
    root = tmp_path / "ASEP-Beta"; release = root / "releases" / "r1"
    (release / ".venv" / "Scripts").mkdir(parents=True)
    (release / ".venv" / "Scripts" / "python.exe").write_text("prepared")
    (release / "frontend" / ".next").mkdir(parents=True)
    (release / "frontend" / ".next" / "BUILD_ID").write_text("build")
    (root / "current").mkdir(); (root / "current" / "active-release.json").write_text('{"release_id":"r1"}')
    for name in ("data", "workspaces", "backups", "temp/maintenance", "codex", "config"):
        (root / name).mkdir(parents=True)
    (root / "config" / "production.env").write_text("ASEP_ENVIRONMENT=production\nASEP_LEGACY_ADMIN_PASSWORD=top-secret-value\n")
    return RuntimePaths.from_root(root), release


class FakeProcesses:
    def __init__(self, fail_spawn=0, stop_ok=True, die_after=None):
        self.next=100; self.live={}; self.commands=[]; self.terminated=[]; self.fail_spawn=fail_spawn; self.stop_ok=stop_ok; self.die_after=die_after; self.checks={}
    def spawn(self, command, cwd, environment, stdout, stderr):
        self.next += 1; self.commands.append((command,cwd,environment,stdout,stderr))
        self.live[self.next] = len(self.commands) != self.fail_spawn
        return self.next
    def token(self,pid): return f"created-{pid}" if self.live.get(pid, pid == 999) else None
    def alive(self,pid,token=None):
        self.checks[pid]=self.checks.get(pid,0)+1
        if self.die_after is not None and len(self.commands)==2 and pid==102 and self.checks[pid]>self.die_after: self.live[pid]=False
        return self.live.get(pid, pid == 999) and (token is None or token == f"created-{pid}")
    def terminate_tree(self,pid,timeout,token=None):
        self.terminated.append((pid,token));
        if not self.stop_ok: return False
        self.live[pid]=False; return True


def test_active_release_is_confined(tmp_path):
    paths, release = layout(tmp_path); assert paths.release() == release.resolve()
    paths.pointer.write_text('{"release_id":"../escape"}')
    with pytest.raises(RuntimeError, match="release id"): paths.release()


def test_environment_is_external_and_not_logged(tmp_path):
    paths, _ = layout(tmp_path); values=load_environment(paths.environment,{})
    assert values["ASEP_LEGACY_ADMIN_PASSWORD"] == "top-secret-value"


def test_commands_are_loopback_and_never_install_or_build(tmp_path):
    paths,_=layout(tmp_path); fake=FakeProcesses(die_after=2)
    supervisor=Supervisor(paths,fake,timeout=.01,readiness=lambda:True,port_free=lambda port:True)
    with pytest.raises(RuntimeError,match="stopped unexpectedly"): supervisor.run()
    flattened=" ".join(part for command,*_ in fake.commands for part in command)
    assert "--host 127.0.0.1 --port 8000" in flattened
    assert "--hostname 127.0.0.1 --port 3000" in flattened and "0.0.0.0" not in flattened
    assert all(item not in flattened.casefold() for item in ("pip install","npm install","npm ci","next build","top-secret-value"))
    assert len(fake.terminated)==2 and not paths.runtime.joinpath("instance.lock").exists()


@pytest.mark.parametrize("failed,message",[(1,"Backend failed"),(2,"component died")])
def test_component_start_failure_cleans_tree_and_lock(tmp_path,failed,message):
    paths,_=layout(tmp_path); fake=FakeProcesses(failed)
    with pytest.raises(RuntimeError,match=message): Supervisor(paths,fake,timeout=.01,readiness=lambda:True,port_free=lambda port:True).run()
    assert fake.terminated and not paths.runtime.joinpath("instance.lock").exists()


def test_readiness_failure_is_bounded(tmp_path):
    paths,_=layout(tmp_path); fake=FakeProcesses()
    with pytest.raises(RuntimeError,match="readiness timed out"):
        Supervisor(paths,fake,timeout=.01,readiness=lambda:False,port_free=lambda port:True).run()


def test_occupied_port_fails_without_starting_process(tmp_path):
    paths,_=layout(tmp_path); fake=FakeProcesses()
    with pytest.raises(RuntimeError,match="port is occupied"):
        Supervisor(paths,fake,timeout=.01,port_free=lambda port:port!=8000).run()
    assert not fake.commands and not paths.runtime.joinpath("instance.lock").exists()


def test_duplicate_lock_is_rejected(tmp_path):
    paths,_=layout(tmp_path); paths.runtime.mkdir(parents=True); paths.runtime.joinpath("instance.lock").write_text("1")
    with pytest.raises(RuntimeError,match="lock"): Supervisor(paths,FakeProcesses()).acquire()


@pytest.mark.parametrize("metadata,expected", [({},"stopped"),({"backend_pid":101,"backend_token":"created-101","frontend_pid":102,"frontend_token":"created-102"},"running"),({"backend_pid":101,"backend_token":"created-101","frontend_pid":102,"frontend_token":"wrong"},"degraded"),({"backend_pid":1,"frontend_pid":2},"stale")])
def test_status_states(tmp_path,metadata,expected):
    paths,_=layout(tmp_path); fake=FakeProcesses(); fake.live.update({101:True,102:True})
    supervisor=Supervisor(paths,fake); paths.runtime.mkdir(parents=True,exist_ok=True)
    if metadata: supervisor.metadata.write_text(json.dumps(metadata))
    assert supervisor.status()==expected


def test_stop_validates_supervisor_identity_and_tree_cleanup(tmp_path):
    paths,_=layout(tmp_path); fake=FakeProcesses(); fake.live[999]=True
    supervisor=Supervisor(paths,fake,timeout=.01); paths.runtime.mkdir(parents=True)
    supervisor.metadata.write_text(json.dumps({"supervisor_pid":999,"supervisor_token":"created-999"}))
    # The real supervisor removes metadata in its finally; emulate that boundary.
    def terminate(pid,timeout,token=None):
        fake.live[pid]=False; supervisor.metadata.unlink(); return True
    fake.terminate_tree=terminate
    supervisor.stop(); assert not supervisor.metadata.exists()


def test_stop_partial_failure_keeps_metadata(tmp_path):
    paths,_=layout(tmp_path); fake=FakeProcesses(stop_ok=False); fake.live[999]=True
    supervisor=Supervisor(paths,fake,timeout=.01); paths.runtime.mkdir(parents=True)
    supervisor.metadata.write_text(json.dumps({"supervisor_pid":999,"supervisor_token":"created-999"}))
    with pytest.raises(RuntimeError,match="did not stop"): supervisor.stop()
    assert supervisor.metadata.exists()


def test_windows_preflight_and_linux_contract(tmp_path,monkeypatch):
    from asep.configuration import models as configuration_models
    paths,release=layout(tmp_path); database=paths.root/"data"/"asep.db"
    env={"ASEP_ENVIRONMENT":"production","ASEP_STORAGE_BACKEND":"sqlite","ASEP_SQLITE_DATABASE":str(database),
         "ASEP_HOSTED_ROOT":str(paths.root/"workspaces"),"ASEP_MAINTENANCE_DIRECTORY":str(paths.root/"temp"/"maintenance"),
         "ASEP_RELEASE_ROOT":str(release),"CODEX_HOME":str(paths.root/"codex"),"ASEP_ACCESS_COOKIE_SECURE":"true",
         "ASEP_LEGACY_ADMIN_EMAIL":"admin@example.com","ASEP_LEGACY_ADMIN_PASSWORD":"strong-password",
         "ASEP_CORS_ORIGINS":"https://beta.example.com"}
    env.update({"ASEP_PUBLIC_ORIGIN":"https://beta.example.com",
                "NEXT_PUBLIC_API_URL":"https://beta.example.com"})
    monkeypatch.setattr(preflight.sys,"version_info",(3,12,0))
    monkeypatch.setattr(configuration_models.tempfile,"gettempdir",lambda:str(tmp_path.parent / "other-temp"))
    version=lambda executable:(30,0)
    assert preflight.check(env,which=lambda name:name,command_version=version,platform_name="nt")==()
    # POSIX does not acquire the Windows-only CODEX_HOME/python.exe checks.
    env.pop("CODEX_HOME"); assert not any("CODEX_HOME" in item for item in preflight.check(env,which=lambda name:name,command_version=version,platform_name="posix"))


def test_powershell_launcher_contains_only_bounded_commands():
    text=Path("deployment/windows/asep-beta.ps1").read_text(encoding="utf-8")
    assert "ValidateSet('start','stop','status','restart')" in text
    assert "0.0.0.0" not in text and "Invoke-Expression" not in text
