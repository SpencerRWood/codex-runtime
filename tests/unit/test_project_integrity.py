"""Preserve template packaging and centralized release conventions."""

import tomllib
from pathlib import Path

from dagster import Definitions

import codex_runtime
from codex_runtime.dagster.definitions import defs

ROOT = Path(__file__).resolve().parents[2]


def test_typed_package_and_release_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["name"] == "codex-runtime"
    assert project["project"]["requires-python"] == ">=3.14"
    assert "dagster>=1.12,<2" in project["project"]["dependencies"]
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/codex_runtime"
    ]
    assert (ROOT / "src/codex_runtime/py.typed").is_file()
    assert "check_availability" in codex_runtime.__all__
    for workflow in ("validate", "release"):
        assert (
            f"SpencerRWood/workflows/.github/workflows/{workflow}.yml@v1"
            in (ROOT / f".github/workflows/{workflow}.yml").read_text()
        )
    release = tomllib.loads((ROOT / ".github/release.toml").read_text())
    assert release["build"]["python_package"] is True
    assert release["release"]["semantic_release"] is True
    assert "codex_runtime.dagster.definitions" in (ROOT / "Dockerfile").read_text()


def test_code_location_loads_without_scheduling_consumer_workflows() -> None:
    Definitions.validate_loadable(defs)
    assert not defs.resolve_asset_graph().get_all_asset_keys()
    assert not defs.jobs
    assert not defs.schedules
    assert not defs.sensors
