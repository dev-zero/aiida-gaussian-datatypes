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
