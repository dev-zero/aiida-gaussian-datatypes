from aiida.plugins import DataFactory

from . import TEST_DIR


def test_import_from_cp2k():
    BasisSet = DataFactory("gaussian.basisset")

    with open(TEST_DIR.joinpath("BASIS_MOLOPT.H"), "r") as fhandle:
        bsets = BasisSet.from_cp2k(fhandle)

    assert len(bsets) == 1

    bsets[0].store()


def test_lookup():
    BasisSet = DataFactory("gaussian.basisset")

    with open(TEST_DIR.joinpath("BASIS_MOLOPT.H"), "r") as fhandle:
        bsets = BasisSet.from_cp2k(fhandle)
        bsets[0].store()

    basis_H = BasisSet.get(element="H", name="SZV-MOLOPT-GTH")
    assert basis_H
