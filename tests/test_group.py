from aiida.plugins import GroupFactory


def test_create_basisset_group():
    BasisSetGroup = GroupFactory("gaussian.basisset")

    bg, created = BasisSetGroup.objects.get_or_create("test")
    assert created
    bg.store()


def test_create_pseudopotential_group():
    PseudopotentialGroup = GroupFactory("gaussian.pseudo")

    bg, created = PseudopotentialGroup.objects.get_or_create("test")
    assert created
    bg.store()
