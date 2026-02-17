"""Shared test configuration and fixtures."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is passed."""
    if config.getoption("--run-integration", default=False):
        return

    skip_integration = pytest.mark.skip(reason="Requires --run-integration flag and live database")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require live database connections",
    )
