from __future__ import annotations

import tomllib
from pathlib import Path


def _requirement_name(requirement: str) -> str:
    return requirement.split("[", 1)[0].split(">", 1)[0].split("<", 1)[0].split("=", 1)[0]


def test_pyproject_declares_all_production_dependencies() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    pyproject_names = {_requirement_name(item) for item in project["dependencies"]}
    requirement_names = {
        _requirement_name(line.strip())
        for line in Path("requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert pyproject_names == requirement_names
    assert "fastapi" in pyproject_names
