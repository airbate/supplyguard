"""Unit tests for the sbom-build skill (npm lockfile v2/v3)."""

from __future__ import annotations

import json

from supplyguard.skills.sbom_build import SbomBuildInput, SbomBuildSkill


def _write_lockfile(tmp_path, data: dict) -> str:
    path = tmp_path / "package-lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_parses_npm_v3_lockfile(tmp_path) -> None:
    lock = {
        "name": "app",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "app", "version": "1.0.0", "dependencies": {"lodash": "^4.17.21"}},
            "node_modules/lodash": {"version": "4.17.21", "license": "MIT"},
            "node_modules/@scope/pkg": {"version": "1.0.0", "license": "MIT"},
        },
    }
    out = SbomBuildSkill().run(SbomBuildInput(lockfile_path=_write_lockfile(tmp_path, lock)))

    assert out.build_errors == []
    names = {p.name for p in out.packages}
    assert {"lodash", "@scope/pkg"} <= names

    lodash = next(p for p in out.packages if p.name == "lodash")
    assert lodash.direct is True
    assert lodash.license == "MIT"

    scoped = next(p for p in out.packages if p.name == "@scope/pkg")
    assert scoped.direct is False


def test_excludes_dev_dependencies_by_default(tmp_path) -> None:
    lock = {
        "name": "app",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "app", "version": "1.0.0", "dependencies": {"lodash": "^4.17.21"}},
            "node_modules/lodash": {"version": "4.17.21", "license": "MIT"},
            "node_modules/jest": {"version": "29.0.0", "license": "MIT", "dev": True},
        },
    }
    path = _write_lockfile(tmp_path, lock)

    out = SbomBuildSkill().run(SbomBuildInput(lockfile_path=path))
    assert "jest" not in {p.name for p in out.packages}

    out_dev = SbomBuildSkill().run(SbomBuildInput(lockfile_path=path, include_dev=True))
    assert "jest" in {p.name for p in out_dev.packages}


def test_missing_lockfile_reports_error(tmp_path) -> None:
    out = SbomBuildSkill().run(
        SbomBuildInput(lockfile_path=str(tmp_path / "does-not-exist.json"))
    )
    assert out.packages == []
    assert out.build_errors


def test_v1_nested_lockfile_reports_error(tmp_path) -> None:
    lock = {"name": "app", "version": "1.0.0", "lockfileVersion": 1, "dependencies": {}}
    out = SbomBuildSkill().run(SbomBuildInput(lockfile_path=_write_lockfile(tmp_path, lock)))
    assert out.build_errors
