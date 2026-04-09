"""Shared test configuration and fixtures."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration/sandbox tests unless their flags are passed."""
    run_integration = config.getoption("--run-integration", default=False)
    run_sandbox = config.getoption("--run-sandbox", default=False)

    skip_integration = pytest.mark.skip(reason="Requires --run-integration flag and live database")
    skip_sandbox = pytest.mark.skip(reason="Requires --run-sandbox flag and bwrap binary")

    for item in items:
        if not run_integration and "integration" in item.keywords:
            item.add_marker(skip_integration)
        if not run_sandbox and "sandbox" in item.keywords:
            item.add_marker(skip_sandbox)


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require live database connections",
    )
    parser.addoption(
        "--run-sandbox",
        action="store_true",
        default=False,
        help="Run sandbox tests that require bwrap binary",
    )
