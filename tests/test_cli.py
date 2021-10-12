import subprocess as sp

from aiida_gaussian_datatypes.basisset.cli import cli as basisset_cli
from aiida_gaussian_datatypes.basisset.cli import (
    dump_basisset,
    import_basisset,
    list_basisset,
)
from aiida_gaussian_datatypes.pseudopotential.cli import cli as pseudo_cli
from aiida_gaussian_datatypes.pseudopotential.cli import (
    dump_pseudo,
    import_pseudo,
    list_pseudo,
)

from . import TEST_DIR


def test_basisset_help(run_cli_command):
    run_cli_command(basisset_cli, ["--help"])


def test_basisset_reachable(run_cli_command):
    output = sp.check_output(["verdi", "data", "gaussian.basisset", "--help"])
    assert b"Usage:" in output


def test_basisset_empty_list(run_cli_command):
    result = run_cli_command(list_basisset)
    assert not result.exception
    assert "No Gaussian Basis Sets found." in result.output


def test_basisset_import(run_cli_command):
    result = run_cli_command(
        import_basisset, ["--format", "cp2k", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))], input="y\n"
    )
    assert not result.exception
    assert "Add a Gaussian Basis Set for 'H' from 'SZV-MOLOPT-GTH-q1'" in result.output

    # a second import should be ignored silently
    result = run_cli_command(import_basisset, ["--format", "cp2k", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))])
    assert not result.exception
    assert "No valid Gaussian Basis Sets found in the given file matching the given criteria" in result.output

    # unless explicitly asked for
    result = run_cli_command(
        import_basisset,
        ["--format", "cp2k", "--duplicates", "error", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))],
        raises=True,
    )

    # but we should be able to import as new nevertheless
    result = run_cli_command(
        import_basisset,
        ["--format", "cp2k", "--duplicates", "new", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))],
        input="y\n",
    )
    assert not result.exception
    assert "Add a Gaussian Basis Set for 'H' from 'SZV-MOLOPT-GTH-q1'" in result.output

    result = run_cli_command(list_basisset)
    assert not result.exception
    assert "2 Gaussian Basis Sets found" in result.output


def test_basisset_dump(run_cli_command):
    result = run_cli_command(
        import_basisset, ["--format", "cp2k", "--sym", "H", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))], input="y\n"
    )
    assert not result.exception

    result = run_cli_command(dump_basisset, ["--format", "cp2k", "--sym", "H"])

    assert not result.exception
    assert "H  SZV-MOLOPT-GTH-q1" in result.output


def test_pseudo_help(run_cli_command):
    run_cli_command(pseudo_cli, ["--help"])


def test_pseudo_reachable(run_cli_command):
    output = sp.check_output(["verdi", "data", "gaussian.pseudo", "--help"])
    assert b"Usage:" in output


def test_pseudo_empty_list(run_cli_command):
    result = run_cli_command(list_pseudo)
    assert not result.exception
    assert "No Gaussian Pseudopotentials found." in result.output


def test_pseudo_import(run_cli_command):
    result = run_cli_command(
        import_pseudo,
        ["--format", "cp2k", "--sym", "He", "--tag", "PBE", str(TEST_DIR.joinpath("GTH_POTENTIALS"))],
        input="y\n",
    )
    assert not result.exception
    assert "Add a Gaussian 'GTH-PBE-q2' Pseudopotential for 'He'" in result.output

    # a second import should be ignored silently
    result = run_cli_command(
        import_pseudo, ["--format", "cp2k", "--sym", "He", "--tag", "PBE", str(TEST_DIR.joinpath("GTH_POTENTIALS"))]
    )
    assert not result.exception
    assert "No valid Gaussian Pseudopotentials found in the given file matching the given criteria" in result.output

    # unless explicitly asked for
    result = run_cli_command(
        import_pseudo,
        [
            "--format",
            "cp2k",
            "--sym",
            "He",
            "--tag",
            "PBE",
            "--duplicates",
            "error",
            str(TEST_DIR.joinpath("GTH_POTENTIALS")),
        ],
        raises=True,
    )

    # but we should be able to import as new nevertheless
    result = run_cli_command(
        import_pseudo,
        [
            "--format",
            "cp2k",
            "--sym",
            "He",
            "--tag",
            "PBE",
            "--duplicates",
            "new",
            str(TEST_DIR.joinpath("GTH_POTENTIALS")),
        ],
        input="y\n",
    )
    assert not result.exception
    assert "Add a Gaussian 'GTH-PBE-q2' Pseudopotential for 'He'" in result.output

    result = run_cli_command(list_pseudo)
    assert not result.exception
    assert "2 Gaussian Pseudopotentials found" in result.output


def test_pseudo_dump(run_cli_command):
    result = run_cli_command(
        import_pseudo,
        ["--format", "cp2k", "--sym", "He", "--tag", "PBE", str(TEST_DIR.joinpath("GTH_POTENTIALS"))],
        input="y\n",
    )
    assert not result.exception

    result = run_cli_command(dump_pseudo, ["--format", "cp2k", "--sym", "He"])

    assert not result.exception
    assert "He GTH-PBE-q2" in result.output
