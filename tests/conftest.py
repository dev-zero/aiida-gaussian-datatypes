"""
For pytest
initialise a text database and profile
"""

import pathlib
from typing import IO, List, Optional, Union

import click
import pytest

pytest_plugins = ["aiida.manage.tests.pytest_fixtures"]


@pytest.fixture(scope="function", autouse=True)
def clear_database_auto(clear_database_before_test):
    """Automatically clear database in between tests."""


# copied directly from aiida-core
@pytest.fixture
def run_cli_command(reset_log_level):  # pylint: disable=unused-argument
    """Run a `click` command with the given options.

    The call will raise if the command triggered an exception or the exit code returned is non-zero.
    """
    from click.testing import Result

    def _run_cli_command(
        command: click.Command,
        options: Optional[List] = None,
        input: Optional[Union[str, bytes, IO]] = None,
        raises: bool = False,
    ) -> Result:
        """Run the command and check the result.

        .. note:: the `output_lines` attribute is added to return value containing list of stripped output lines.

        :param options: the list of command line options to pass to the command invocation
        :param raises: whether the command is expected to raise an exception
        :return: test result
        """
        import traceback

        from aiida.cmdline.commands.cmd_verdi import VerdiCommandGroup
        from aiida.common import AttributeDict
        from aiida.manage.configuration import get_config, get_profile

        config = get_config()
        profile = get_profile()
        obj = AttributeDict({"config": config, "profile": profile})

        # Convert any ``pathlib.Path`` objects in the ``options`` to their absolute filepath string representation.
        # This is necessary because the ``invoke`` command does not support these path objects.
        options = [str(option) if isinstance(option, pathlib.Path) else option for option in options or []]

        # We need to apply the ``VERBOSITY`` option. When invoked through the command line, this is done by the logic
        # of the ``VerdiCommandGroup``, but when testing commands, the command is retrieved directly from the module
        # which circumvents this machinery.
        command = VerdiCommandGroup.add_verbosity_option(command)

        runner = click.testing.CliRunner()
        result = runner.invoke(command, args=options, obj=obj, input=input)

        if raises:
            assert result.exception is not None, result.output
            assert result.exit_code != 0
        else:
            assert result.exception is None, "".join(traceback.format_exception(*result.exc_info))
            assert result.exit_code == 0, result.output

        result.output_lines = [line.strip() for line in result.output.split("\n") if line.strip()]

        return result

    return _run_cli_command


@pytest.fixture
def reset_log_level():
    """Reset the `aiida.common.log.CLI_LOG_LEVEL` global and reconfigure the logging.

    This fixture should be used by tests that will change the ``CLI_LOG_LEVEL`` global, for example, through the
    :class:`~aiida.cmdline.params.options.main.VERBOSITY` option in a CLI command invocation.
    """
    from aiida.common import log

    try:
        yield
    finally:
        log.CLI_LOG_LEVEL = None
        log.configure_logging()
