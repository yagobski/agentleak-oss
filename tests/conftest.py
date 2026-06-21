"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolate_agentleak_home(tmp_path_factory):
    """Point the platform store at a throwaway dir so tests never touch
    the user's real ~/.agentleak database.
    """
    home = tmp_path_factory.mktemp("agentleak_home")
    os.environ["AGENTLEAK_HOME"] = str(home)
    yield
