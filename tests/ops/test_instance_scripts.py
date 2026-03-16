from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "ops" / "instance"


def _script(name: str) -> Path:
    return SCRIPTS_DIR / name


def test_restart_script_does_not_use_global_pkill() -> None:
    content = _script("restart_instance.sh").read_text(encoding="utf-8")
    assert "pkill" not in content
    assert "stop_instance.sh" in content
    assert "start_instance.sh" in content


def test_bash_n_smoke_all_instance_scripts() -> None:
    for path in SCRIPTS_DIR.glob("*.sh"):
        proc = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        assert proc.returncode == 0, f"bash -n failed for {path}: {proc.stderr}"


def test_shellcheck_smoke_if_available() -> None:
    if not shutil_which("shellcheck"):
        pytest.skip("shellcheck not installed")

    proc = subprocess.run(
        ["shellcheck", *[str(p) for p in SCRIPTS_DIR.glob("*.sh")]],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def shutil_which(cmd: str) -> str | None:
    for base in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(base) / cmd
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def test_env_parsing_and_scoped_start_stop(tmp_path: Path) -> None:
    instance_dir = tmp_path / "inst-a"
    run_dir = instance_dir / "run"
    log_dir = instance_dir / "log"
    run_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)

    openmork_env = instance_dir / ".env"
    openmork_env.write_text("DUMMY=1\n", encoding="utf-8")

    env_file = instance_dir / "instance.env"
    env_file.write_text(
        "\n".join(
            [
                "INSTANCE_NAME=dev-a",
                f"OPENMORK_HOME={instance_dir}",
                f"OPENMORK_REPO={REPO_ROOT}",
                f"OPENMORK_ENV_FILE={openmork_env}",
                f"PID_FILE={run_dir / 'openmork.pid'}",
                f"LOG_FILE={log_dir / 'openmork.log'}",
                f"INSTANCE_LOCK_FILE={run_dir / 'restart.lock'}",
                "MODEL=test-model",
                "OPENMORK_START_CMD=\"sleep 30\"",
                "STARTUP_WAIT_SECONDS=3",
                "STOP_WAIT_SECONDS=3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run([str(_script("bootstrap_instance.sh")), str(env_file)], check=True)
    subprocess.run([str(_script("start_instance.sh")), str(env_file)], check=True)
    subprocess.run([str(_script("health_instance.sh")), str(env_file)], check=True)
    subprocess.run([str(_script("restart_instance.sh")), str(env_file)], check=True)
    subprocess.run([str(_script("stop_instance.sh")), str(env_file)], check=True)

    pid_file = run_dir / "openmork.pid"
    assert not pid_file.exists(), "PID file should be removed after stop"
