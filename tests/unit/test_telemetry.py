from unittest import mock

import pytest
from exasol.telemetry import client as telemetry
from pyexasol.exceptions import ExaConnectionDsnError

from dbt.adapters.exasol.connections import ExasolConnection


@pytest.fixture
def telemetry_unset_ci(monkeypatch):
    """
    Temporary remove CI env variable if present
    """
    monkeypatch.delenv("CI", raising=False)


@pytest.fixture
def telemetry_unset_disable(monkeypatch):
    """
    Temporary remove EXASOL_TELEMETRY_DISABLE env variable if present
    """
    monkeypatch.delenv("EXASOL_TELEMETRY_DISABLE", raising=False)


@mock.patch("requests.post")
def test_disabled_globally(
    post_mock: mock.MagicMock,
    telemetry_unset_ci,
    telemetry_unset_disable,
):
    # check that telemetry was disabled during the import
    telemetry.track("test", "0.0", "test")
    post_mock.assert_not_called()


@mock.patch("requests.post")
def test_no_send_on_connection(
    post_mock: mock.MagicMock,
    telemetry_unset_ci,
    telemetry_unset_disable,
):
    # telemetry tracking is before dsn check
    try:
        ExasolConnection()
    except ExaConnectionDsnError:
        pass
    post_mock.assert_not_called()
