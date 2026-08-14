"""Unit tests for the license-check skill."""

from __future__ import annotations

from supplyguard.skills.license_check import (
    LicenseCheckInput,
    LicenseCheckSkill,
    LicensePolicy,
    PackageLicense,
)


def _check(
    packages: list[PackageLicense], allowed: list[str], forbidden: list[str]
) -> object:
    skill = LicenseCheckSkill()
    return skill.run(
        LicenseCheckInput(
            packages=packages,
            project_license_policy=LicensePolicy(allowed=allowed, forbidden=forbidden),
        )
    )


def test_forbidden_license_violates() -> None:
    result = _check(
        [PackageLicense(name="foo", version="1.0.0", license="GPL-3.0")],
        allowed=["MIT"],
        forbidden=["GPL-3.0"],
    )
    assert result.compatible is False
    assert len(result.violations) == 1
    assert result.violations[0].package == "foo"


def test_allowed_license_passes() -> None:
    result = _check(
        [PackageLicense(name="foo", version="1.0.0", license="MIT")],
        allowed=["MIT"],
        forbidden=["GPL-3.0"],
    )
    assert result.compatible is True
    assert result.violations == []


def test_unknown_license_needs_confirmation_not_block() -> None:
    result = _check(
        [PackageLicense(name="foo", version="1.0.0", license="Something-Weird")],
        allowed=["MIT"],
        forbidden=["GPL-3.0"],
    )
    assert result.compatible is True  # unknown is never auto-blocked
    assert len(result.unknown_licenses) == 1


def test_missing_license_needs_confirmation() -> None:
    result = _check(
        [PackageLicense(name="foo", version="1.0.0", license=None)],
        allowed=["MIT"],
        forbidden=["GPL-3.0"],
    )
    assert len(result.unknown_licenses) == 1


def test_license_alias_normalization() -> None:
    # "Apache License 2.0" normalizes to SPDX id "Apache-2.0".
    result = _check(
        [PackageLicense(name="foo", version="1.0.0", license="Apache License 2.0")],
        allowed=["MIT"],
        forbidden=["Apache-2.0"],
    )
    assert result.compatible is False
    assert result.violations[0].license == "Apache License 2.0"
