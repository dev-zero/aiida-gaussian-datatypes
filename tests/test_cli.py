import subprocess as sp

from click.testing import CliRunner

from aiida.backends.testbase import AiidaTestCase

from aiida_gaussian_datatypes.basisset.cli import cli as basisset_cli, list_basisset, import_basisset, dump_basisset
from aiida_gaussian_datatypes.pseudopotential.cli import cli as pseudo_cli, list_pseudo, import_pseudo, dump_pseudo

from . import TEST_DIR


class TestCliBasisset(AiidaTestCase):
    def setUp(self):
        self.cli_runner = CliRunner()

    def test_help(self):
        self.cli_runner.invoke(basisset_cli, ["--help"], catch_exceptions=False)

    def test_reachable(self):
        output = sp.check_output(["verdi", "data", "gaussian.basisset", "--help"])
        assert b"Usage:" in output

    def test_empty_list(self):
        result = self.cli_runner.invoke(list_basisset)
        assert not result.exception
        assert "No Gaussian Basis Sets found." in result.output

    def test_import(self):
        result = self.cli_runner.invoke(
            import_basisset, ["--format", "cp2k", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))], input="y\n"
        )
        assert not result.exception
        assert "Add a Gaussian Basis Set for 'H' from 'SZV-MOLOPT-GTH-q1'" in result.output

        # a second import should be ignored silently
        result = self.cli_runner.invoke(import_basisset, ["--format", "cp2k", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))])
        assert not result.exception
        assert "No valid Gaussian Basis Sets found in the given file matching the given criteria" in result.output

        # unless explicitly asked for
        result = self.cli_runner.invoke(
            import_basisset, ["--format", "cp2k", "--duplicates", "error", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))]
        )
        assert result.exception

        # but we should be able to import as new nevertheless
        result = self.cli_runner.invoke(
            import_basisset,
            ["--format", "cp2k", "--duplicates", "new", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))],
            input="y\n",
        )
        assert not result.exception
        assert "Add a Gaussian Basis Set for 'H' from 'SZV-MOLOPT-GTH-q1'" in result.output

        result = self.cli_runner.invoke(list_basisset)
        assert not result.exception
        assert "2 Gaussian Basis Sets found" in result.output

    def test_dump(self):
        result = self.cli_runner.invoke(
            import_basisset, ["--format", "cp2k", "--sym", "H", str(TEST_DIR.joinpath("BASIS_MOLOPT.H"))], input="y\n"
        )
        assert not result.exception

        result = self.cli_runner.invoke(dump_basisset, ["--format", "cp2k", "--sym", "H"])

        assert not result.exception
        assert "H SZV-MOLOPT-GTH-q1" in result.output


class TestCliPseudo(AiidaTestCase):
    def setUp(self):
        self.cli_runner = CliRunner()

    def test_help(self):
        self.cli_runner.invoke(pseudo_cli, ["--help"], catch_exceptions=False)

    def test_reachable(self):
        output = sp.check_output(["verdi", "data", "gaussian.pseudo", "--help"])
        assert b"Usage:" in output

    def test_empty_list(self):
        result = self.cli_runner.invoke(list_pseudo)
        assert not result.exception
        assert "No Gaussian Pseudopotentials found." in result.output

    def test_import(self):
        result = self.cli_runner.invoke(
            import_pseudo,
            ["--format", "cp2k", "--sym", "He", "--tag", "PBE", str(TEST_DIR.joinpath("GTH_POTENTIALS"))],
            input="y\n",
        )
        assert not result.exception
        assert "Add a Gaussian 'GTH-PBE-q2' Pseudopotential for 'He'" in result.output

        # a second import should be ignored silently
        result = self.cli_runner.invoke(
            import_pseudo, ["--format", "cp2k", "--sym", "He", "--tag", "PBE", str(TEST_DIR.joinpath("GTH_POTENTIALS"))]
        )
        assert not result.exception
        assert "No valid Gaussian Pseudopotentials found in the given file matching the given criteria" in result.output

        # unless explicitly asked for
        result = self.cli_runner.invoke(
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
        )
        assert result.exception

        # but we should be able to import as new nevertheless
        result = self.cli_runner.invoke(
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

        result = self.cli_runner.invoke(list_pseudo)
        assert not result.exception
        assert "2 Gaussian Pseudopotentials found" in result.output

    def test_dump(self):
        result = self.cli_runner.invoke(
            import_pseudo,
            ["--format", "cp2k", "--sym", "He", "--tag", "PBE", str(TEST_DIR.joinpath("GTH_POTENTIALS"))],
            input="y\n",
        )
        assert not result.exception

        result = self.cli_runner.invoke(dump_pseudo, ["--format", "cp2k", "--sym", "He"])

        assert not result.exception
        assert "He GTH-PBE-q2" in result.output
