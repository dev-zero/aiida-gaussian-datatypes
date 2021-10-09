import io

import pytest
from aiida.common.exceptions import NotExistent, ValidationError
from aiida.plugins import DataFactory

from . import TEST_DIR


def test_import_from_cp2k():
    Pseudopotential = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("GTH_POTENTIALS"), "r") as fhandle:
        # get only the He PADE pseudo
        pseudos = Pseudopotential.from_cp2k(
            fhandle, filters={"element": lambda x: x == "He", "tags": lambda x: set(("PADE",)).issubset(x)}
        )

    assert len(pseudos) == 1

    pseudos[0].store()

    # check that the name is used for the node label
    assert pseudos[0].label == pseudos[0].name


def test_nlcc_import():
    """With the usage of the cp2k-input-tools for file handling we also gained support for the NLCC pseudos"""
    Pseudopotential = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("NLCC_POTENTIALS"), "r") as fhandle:
        # get only the He PADE pseudo
        pseudos = Pseudopotential.from_cp2k(fhandle, filters={"element": lambda x: x == "C"})

    assert len(pseudos) == 1


def test_lookup():
    Pseudopotential = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("GTH_POTENTIALS"), "r") as fhandle:
        # get only the He PBE pseudo
        pseudos = Pseudopotential.from_cp2k(
            fhandle, filters={"element": lambda x: x == "He", "tags": lambda x: set(("PBE",)).issubset(x)}
        )
        pseudos[0].store()

    assert Pseudopotential.get(element="He", name="GTH-PBE-q2")
    assert Pseudopotential.get(element="He", name="GTH-PBE")


def test_get():
    from aiida.common.exceptions import MultipleObjectsError, NotExistent

    Pseudo = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("GTH_POTENTIALS.LiH"), "r") as fhandle:
        pseudos = Pseudo.from_cp2k(fhandle)

    for pseudo in pseudos:
        pseudo.store()

    # getting a single one should work
    pseudo = Pseudo.get(element="H", name="GTH-PBE-q1")
    assert pseudo.element == "H" and pseudo.name == "GTH-PBE-q1"

    with pytest.raises(NotExistent):
        Pseudo.get(element="C")

    # leaving away the name should return multiple ones, raising an error
    with pytest.raises(MultipleObjectsError):
        Pseudo.get(element="Li")


def test_validation_empty():
    Pseudo = DataFactory("gaussian.pseudo")
    pseudo = Pseudo()

    with pytest.raises(ValidationError):
        pseudo.store()


def test_validation_invalid_local():
    Pseudo = DataFactory("gaussian.pseudo")
    pseudo = Pseudo(name="test", element="H", local={"r": 1.23, "coeffs": [], "something": "else"})

    with pytest.raises(ValidationError):
        pseudo.store()


def test_get_matching_empty():
    Pseudo = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("GTH_POTENTIALS.LiH"), "r") as fhandle:
        pseudos = Pseudo.from_cp2k(fhandle)

    with pytest.raises(NotExistent):
        pseudos[0].get_matching_basisset()


def test_to_cp2k():
    """Check whether writing a CP2K datafile works"""
    Pseudo = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("GTH_POTENTIALS.LiH"), "r") as fhandle:
        pseudos = Pseudo.from_cp2k(fhandle)

    fhandle = io.StringIO()
    for pseudo in pseudos:
        pseudo.to_cp2k(fhandle)

    assert fhandle.getvalue()


def test_to_cp2k_nlcc_missing():
    """Check whether writing a CP2K datafile works, also with missing NLCC attribute"""
    Pseudo = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("GTH_POTENTIALS.LiH"), "r") as fhandle:
        pseudos = Pseudo.from_cp2k(fhandle)

    fhandle = io.StringIO()
    for pseudo in pseudos:
        del pseudo.attributes["nlcc"]
        pseudo.to_cp2k(fhandle)

    assert fhandle.getvalue()
