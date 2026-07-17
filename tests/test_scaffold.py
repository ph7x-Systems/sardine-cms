"""Smoke tests: the workspace packages are importable and versioned."""

import cms_build
import cms_core
import cms_validation


def test_packages_expose_a_version() -> None:
    for package in (cms_core, cms_validation, cms_build):
        assert isinstance(package.__version__, str)
        assert package.__version__


def test_versions_are_in_sync() -> None:
    assert cms_core.__version__ == cms_validation.__version__ == cms_build.__version__
