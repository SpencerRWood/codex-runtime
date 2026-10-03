"""Real subprocess coverage without auth, network, or an inference turn."""

import os
import sys
import time
from pathlib import Path

import pytest

from codex_runtime import AppServerProvider, Reason, check_availability


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "timeout",
        "eof",
        "malformed",
        "oversized",
        "nonobject",
        "wrong_id",
        "bool_id",
        "rpc_error",
        "no_result",
        "flood",
    ],
)
def test_bounded_transport_and_cleanup(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "fake-codex"
    fixture = Path(__file__).parents[1] / "fixtures/fake_codex.py"
    executable.write_text(f"#!{sys.executable}\n" + fixture.read_text())
    executable.chmod(0o700)
    pid_file = tmp_path / "pid"
    monkeypatch.setenv("FAKE_CODEX_PID_FILE", str(pid_file))
    monkeypatch.setenv("FAKE_CODEX_MODE", mode)
    start = time.monotonic()
    result = check_availability(AppServerProvider(str(executable), timeout_seconds=1))
    assert time.monotonic() - start < 5
    assert result.available is (mode == "success")
    assert result.reason == (
        Reason.AVAILABLE if mode == "success" else Reason.PROVIDER_ERROR
    )
    assert "secret-token-example" not in repr(result)
    pid = int(pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_missing_executable_fails_closed(tmp_path: Path) -> None:
    result = check_availability(AppServerProvider(str(tmp_path / "absent")))
    assert result.reason == Reason.PROVIDER_ERROR
    assert not result.available


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_timeouts_rejected(timeout: float) -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        AppServerProvider(timeout_seconds=timeout)
