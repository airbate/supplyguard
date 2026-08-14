"""S01: sbom-build skill implementation (npm lockfile, v2/v3).

Parses a package-lock.json into a dependency graph: nodes carry name, version,
license, direct/transitive flag, and their immediate dependencies. This is the
foundation of the "shared engine" — both the guard and response modes consume
its output.

v1 supports npm lockfile v2/v3 (`packages` key). Older v1 lockfiles (nested
`dependencies`) are reported as a build error rather than silently mis-parsed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Skill


class SbomBuildInput(BaseModel):
    """Input for sbom-build."""

    ecosystem: str = "npm"
    lockfile_path: str = ""
    include_dev: bool = False


class PackageNode(BaseModel):
    """A single node in the dependency graph."""

    name: str
    version: str = ""
    license: str | None = None
    direct: bool = False
    dependencies: list[str] = Field(default_factory=list)


class SbomBuildOutput(BaseModel):
    """Output for sbom-build."""

    sbom_id: str
    packages: list[PackageNode] = Field(default_factory=list)
    build_errors: list[str] = Field(default_factory=list)


class SbomBuildSkill(Skill[SbomBuildInput, SbomBuildOutput]):
    """Build a dependency graph from an npm lockfile."""

    name = "sbom-build"
    description = "Parse a lockfile into a dependency graph / SBOM snapshot"

    def run(self, input_data: SbomBuildInput) -> SbomBuildOutput:
        path = input_data.lockfile_path
        sbom_id = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]

        if not path or not Path(path).is_file():
            return SbomBuildOutput(
                sbom_id=sbom_id,
                build_errors=[f"lockfile not found: {path or '(empty path)'}"],
            )

        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return SbomBuildOutput(sbom_id=sbom_id, build_errors=[f"parse error: {exc}"])

        errors: list[str] = []
        packages: list[PackageNode] = []

        if "packages" not in data:
            return SbomBuildOutput(
                sbom_id=sbom_id,
                build_errors=["unsupported lockfile format (missing 'packages'; v1 nested lockfiles not supported)"],
            )

        pkg_map: dict = data["packages"]
        root = pkg_map.get("", {})
        root_deps: set[str] = set((root.get("dependencies") or {}).keys())

        for key, meta in pkg_map.items():
            if key == "":
                continue
            if not isinstance(meta, dict):
                errors.append(f"unexpected node shape for '{key}'")
                continue
            if not input_data.include_dev and meta.get("dev"):
                continue

            name = key.removeprefix("node_modules/")
            packages.append(
                PackageNode(
                    name=name,
                    version=meta.get("version", ""),
                    license=meta.get("license"),
                    direct=name in root_deps,
                    dependencies=list((meta.get("dependencies") or {}).keys()),
                )
            )

        return SbomBuildOutput(sbom_id=sbom_id, packages=packages, build_errors=errors)
