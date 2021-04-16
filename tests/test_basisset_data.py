import pytest
from aiida.plugins import DataFactory

from . import TEST_DIR


def test_import_from_cp2k():
    BasisSet = DataFactory("gaussian.basisset")

    with open(TEST_DIR.joinpath("BASIS_MOLOPT.H"), "r") as fhandle:
        bsets = BasisSet.from_cp2k(fhandle)

    assert len(bsets) == 1

    bsets[0].store()

    # check that the name is used for the node label
    assert bsets[0].label == bsets[0].name


def test_lookup():
    BasisSet = DataFactory("gaussian.basisset")

    with open(TEST_DIR.joinpath("BASIS_MOLOPT.H"), "r") as fhandle:
        bsets = BasisSet.from_cp2k(fhandle)
        bsets[0].store()

    basis_H = BasisSet.get(element="H", name="SZV-MOLOPT-GTH")
    assert basis_H


def test_n_orbital_functions():
    BasisSet = DataFactory("gaussian.basisset")

    with open(TEST_DIR.joinpath("BASIS_MOLOPT.Hf"), "r") as fhandle:
        bsets = BasisSet.from_cp2k(fhandle)

    assert bsets
    assert bsets[0].n_orbital_functions == 1 * 3 + 3 * 2 + 5 * 2 + 7 * 1  # l=0,1,2,3 with respective nshells=3,2,2,1


def test_get():
    from aiida.common.exceptions import NotExistent, MultipleObjectsError

    BasisSet = DataFactory("gaussian.basisset")

    with open(TEST_DIR.joinpath("MOLOPT_PBE.LiH"), "r") as fhandle:
        bsets = BasisSet.from_cp2k(fhandle)

    for bset in bsets:
        bset.store()

    # getting a single one should work
    bset = BasisSet.get(element="H", name="DZVP-MOLOPT-PBE-GTH-q1")
    assert bset.element == "H" and bset.name == "DZVP-MOLOPT-PBE-GTH-q1"

    with pytest.raises(NotExistent):
        BasisSet.get(element="C")

    # leaving away the name should return multiple ones, raising an error
    with pytest.raises(MultipleObjectsError):
        BasisSet.get(element="H")
