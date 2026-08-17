from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from asep.providers.process import (
    ProcessExecutableNotFoundError,
    ProcessInterruptedError,
    ProcessRunner,
    ProcessStartError,
    ProcessTimeoutError,
)


class Completed:
    returncode = 0
    stdout = "stdout"
    stderr = "stderr"


def run_process(runner: ProcessRunner, command: tuple[str, ...], tmp_path: Path):
    return runner.run(
        command,
        input_text="stdin",
        timeout=12.5,
        working_directory=tmp_path,
        environment={"EXPLICIT": "value"},
        encoding="utf-16",
    )


def test_resolves_executable_and_preserves_process_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    requested = ("codex", "exec", "argument with spaces")
    resolved = str(tmp_path / "codex.CMD")

    monkeypatch.setattr("asep.providers.process.shutil.which", lambda _: resolved)

    def fake_run(command: tuple[str, ...], **kwargs: object) -> Completed:
        captured["command"] = command
        captured.update(kwargs)
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)

    result = run_process(ProcessRunner(), requested, tmp_path)

    assert captured["command"] == (resolved, "exec", "argument with spaces")
    assert captured["input"] == "stdin"
    assert captured["timeout"] == 12.5
    assert captured["cwd"] == tmp_path
    assert captured["encoding"] == "utf-16"
    assert captured["shell"] is False
    assert captured["env"]["EXPLICIT"] == "value"  # type: ignore[index]
    assert result.command == requested
    assert (result.exit_code, result.stdout, result.stderr) == (0, "stdout", "stderr")


def test_host_environment_is_allowlisted_and_explicit_values_win(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setenv("PATH", "host-path")
    monkeypatch.setenv("ASEP_UNSAFE_TEST_VALUE", "excluded")
    monkeypatch.setattr("asep.providers.process.shutil.which", lambda _: "resolved")

    def fake_run(command: tuple[str, ...], **kwargs: object) -> Completed:
        captured.update(kwargs)
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)
    ProcessRunner().run(
        ("tool",), input_text="", timeout=1, working_directory=tmp_path,
        environment={"PATH": "explicit-path", "CUSTOM": "included"},
        encoding="utf-8",
    )

    environment = captured["env"]
    assert environment["PATH"] == "explicit-path"  # type: ignore[index]
    assert environment["CUSTOM"] == "included"  # type: ignore[index]
    assert "ASEP_UNSAFE_TEST_VALUE" not in environment


def test_missing_executable_is_consistent_and_does_not_start_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asep.providers.process.shutil.which", lambda _: None)
    started = False

    def fake_run(*args: object, **kwargs: object) -> Completed:
        nonlocal started
        started = True
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)
    runner = ProcessRunner()

    assert runner.is_available("missing") is False
    with pytest.raises(ProcessExecutableNotFoundError):
        run_process(runner, ("missing",), tmp_path)
    assert started is False


@pytest.mark.parametrize("requested", ["codex", "codex.CMD"])
def test_availability_and_run_share_windows_wrapper_resolution(
    requested: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = str(tmp_path / "codex.CMD")
    monkeypatch.setattr("asep.providers.process.shutil.which", lambda _: resolved)
    commands: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], **kwargs: object) -> Completed:
        commands.append(command)
        return Completed()

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)
    runner = ProcessRunner()

    assert runner.is_available(requested) is True
    run_process(runner, (requested, "--version"), tmp_path)
    assert commands == [(resolved, "--version")]


def test_absolute_executable_is_resolved_without_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = str(tmp_path / ("tool.exe" if os.name == "nt" else "tool"))
    seen: list[str] = []

    def fake_which(requested: str) -> str:
        seen.append(requested)
        return requested

    monkeypatch.setattr("asep.providers.process.shutil.which", fake_which)
    monkeypatch.setattr("asep.providers.process.subprocess.run", lambda *a, **k: Completed())

    run_process(ProcessRunner(), (executable, "--version"), tmp_path)
    assert seen == [executable]


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (FileNotFoundError(), ProcessExecutableNotFoundError),
        (subprocess.TimeoutExpired(("tool",), 12.5), ProcessTimeoutError),
        (KeyboardInterrupt(), ProcessInterruptedError),
        (PermissionError(), ProcessStartError),
    ],
)
def test_start_failures_keep_existing_error_mapping(
    raised: BaseException,
    expected: type[Exception],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asep.providers.process.shutil.which", lambda _: "resolved")

    def fake_run(*args: object, **kwargs: object) -> Completed:
        raise raised

    monkeypatch.setattr("asep.providers.process.subprocess.run", fake_run)

    with pytest.raises(expected):
        run_process(ProcessRunner(), ("tool",), tmp_path)
