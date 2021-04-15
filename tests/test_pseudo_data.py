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


def test_ignore_import_unsupported_from_cp2k():
    """Some potential format are not yet supported, check that we do not choke on them"""
    Pseudopotential = DataFactory("gaussian.pseudo")

    with open(TEST_DIR.joinpath("NLCC_POTENTIALS"), "r") as fhandle:
        # get only the He PADE pseudo
        pseudos = Pseudopotential.from_cp2k(fhandle, filters={"element": lambda x: x == "C"})

    assert len(pseudos) == 0


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
