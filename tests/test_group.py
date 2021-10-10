from aiida.plugins import DataFactory, GroupFactory

from . import TEST_DIR


def test_create_basisset_group():
    BasisSetGroup = GroupFactory("gaussian.basisset")

    basisgroup, created = BasisSetGroup.objects.get_or_create("test")
    assert created
    basisgroup.store()


def test_create_pseudopotential_group():
    PseudopotentialGroup = GroupFactory("gaussian.pseudo")

    pseudogroup, created = PseudopotentialGroup.objects.get_or_create("test")
    assert created
    pseudogroup.store()


def test_pseudopotential_group_get():
    Pseudo = DataFactory("gaussian.pseudo")
    PseudopotentialGroup = GroupFactory("gaussian.pseudo")

    pseudogroup, created = PseudopotentialGroup.objects.get_or_create("test")
    assert created
    pseudogroup.store()

    with open(TEST_DIR.joinpath("GTH_POTENTIALS.LiH"), "r") as fhandle:
        pseudos = Pseudo.from_cp2k(fhandle)

    pseudogroup.add_nodes([pseudo.store() for pseudo in pseudos])

    retrieved_pseudos = pseudogroup.get_pseudos(elements=["Li", "H"])

    assert retrieved_pseudos == {
        "Li": [p for p in pseudos if p.element == "Li"],
        "H": [p for p in pseudos if p.element == "H"],
    }


def test_pseudopotential_group_get_structure():
    """Test get_pseudos from structure"""
    Pseudo = DataFactory("gaussian.pseudo")
    PseudopotentialGroup = GroupFactory("gaussian.pseudo")

    pseudogroup, created = PseudopotentialGroup.objects.get_or_create("test")
    assert created
    pseudogroup.store()

    with open(TEST_DIR.joinpath("GTH_POTENTIALS.LiH"), "r") as fhandle:
        pseudos = Pseudo.from_cp2k(fhandle)

    pseudogroup.add_nodes([pseudo.store() for pseudo in pseudos])

    StructureData = DataFactory("structure")
    structure = StructureData(cell=[[4.796302, 0, 0], [0, 4.796302, 0], [0, 0, 4.796302]], pbc=True)
    structure.append_atom(position=(0.000, 0.000, 0.000), symbols="Li")
    structure.append_atom(position=(0.500, 0.500, 0.000), symbols="Li")
    structure.append_atom(position=(0.500, 0.000, 0.500), symbols="Li")
    structure.append_atom(position=(0.000, 0.500, 0.500), symbols="Li")
    structure.append_atom(position=(0.000, 0.500, 0.000), symbols="H")
    structure.append_atom(position=(0.000, 0.000, 0.500), symbols="H")
    structure.append_atom(position=(0.500, 0.000, 0.000), symbols="H")
    structure.append_atom(position=(0.500, 0.500, 0.500), symbols="H")

    retrieved_pseudos = pseudogroup.get_pseudos(structure=structure)

    assert retrieved_pseudos == {
        "Li": [p for p in pseudos if p.element == "Li"],
        "H": [p for p in pseudos if p.element == "H"],
    }
