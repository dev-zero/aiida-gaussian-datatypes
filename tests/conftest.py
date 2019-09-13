"""
For pytest
initialise a text database and profile
"""

import pytest

from aiida.manage.fixtures import fixture_manager


@pytest.fixture(scope="session", autouse=True)
def aiida_profile():
    """Set up a test profile for the duration of the tests"""
    with fixture_manager() as fixture_mgr:
        yield fixture_mgr


@pytest.fixture(scope="function", autouse=True)
def clear_database(aiida_profile):
    """Clear the database after each test"""
    yield
    aiida_profile.reset_db()
