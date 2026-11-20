"""Tests for the local HACS file checks."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HACS_SOURCE = ROOT / ".hacs-validation" / "integration"
PYTHON_VERSION_FILE = HACS_SOURCE / ".python-version"


@pytest.fixture
def hacs_python() -> Path:
    """Use the environment prepared by the local HACS command."""
    if not PYTHON_VERSION_FILE.is_file():
        pytest.skip("Run ./scripts/validate-hacs to prepare the HACS environment")
    python = (
        ROOT
        / ".hacs-validation"
        / f"venv-{PYTHON_VERSION_FILE.read_text().strip()}"
        / "bin"
        / "python"
    )
    if not python.is_file():
        pytest.skip("Run ./scripts/validate-hacs to prepare the HACS environment")
    return python


def run_validation(root: Path, python: Path) -> subprocess.CompletedProcess[str]:
    """Run the local checker with the upstream HACS schemas."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(HACS_SOURCE)
    return subprocess.run(
        [str(python), str(ROOT / "scripts" / "validate_hacs.py"), str(root)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create a minimal uncommitted integration working tree."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    integration = tmp_path / "custom_components" / "wth_umr2"
    (integration / "brand").mkdir(parents=True)
    (integration / "brand" / "icon.png").write_bytes(b"icon")
    (tmp_path / "README.md").write_text("Information", encoding="utf-8")
    (tmp_path / "hacs.json").write_text('{"name": "WTH"}', encoding="utf-8")
    (integration / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "wth_umr2",
                "name": "WTH",
                "version": "1.0.0",
                "documentation": "https://example.com",
                "issue_tracker": "https://example.com",
                "codeowners": [],
                "categories": ["climate.thermostats_heating"],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_local_checks_validate_uncommitted_files(repository: Path, hacs_python: Path) -> None:
    result = run_validation(repository, hacs_python)
    assert result.returncode == 0, result.stderr
    assert "local brand icon: passed" in result.stdout


@pytest.mark.parametrize(
    ("path", "content", "error"),
    [
        ("hacs.json", '{"name": "WTH", "unknown": true}', "unknown"),
        ("hacs.json", '{"name": "WTH", "zip_release": true}', "filename is not set"),
        ("custom_components/wth_umr2/manifest.json", "{}", "required key not provided"),
    ],
)
def test_local_checks_report_invalid_files(
    repository: Path, hacs_python: Path, path: str, content: str, error: str
) -> None:
    (repository / path).write_text(content, encoding="utf-8")
    result = run_validation(repository, hacs_python)
    assert result.returncode != 0
    assert error in result.stderr


def test_local_checks_report_missing_information(repository: Path, hacs_python: Path) -> None:
    (repository / "README.md").unlink()
    result = run_validation(repository, hacs_python)
    assert result.returncode != 0
    assert "no information file" in result.stderr
