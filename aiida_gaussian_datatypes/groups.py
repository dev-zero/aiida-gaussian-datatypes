# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Groups for the GTO data classes
"""

from typing import Dict, List, Optional, Sequence

from aiida.orm import Group, QueryBuilder, StructureData

from .pseudopotential.data import Pseudopotential


class BasisSetGroup(Group):
    """Group for Gaussian.Basisset nodes"""


class PseudopotentialGroup(Group):
    """Group for Gaussian.Pseudopotential nodes"""

    def get_pseudos(
        self, elements: Optional[Sequence[str]] = None, structure: Optional[StructureData] = None
    ) -> Dict[str, List[Pseudopotential]]:
        """
        Return a dict of kind names/elements to a list of pseudopotential data nodes
        for the given list of elements or structure.

        :param elements: list of element symbols.
        :param structure: the ``StructureData`` node.
        """

        assert (elements is None) ^ (
            structure is None
        ), "Exactly one of the parameters elements and structure must be specified"
        assert isinstance(elements, Sequence) or isinstance(structure, StructureData)

        if structure:
            elements = list(structure.get_symbols_set())

        query = (
            QueryBuilder()
            .append(self.__class__, filters={"id": self.pk}, tag="group")
            .append(Pseudopotential, with_group="group", filters={"attributes.element": {"in": elements}})
        )

        pseudos: Dict[str, List[Pseudopotential]] = {}

        for (pseudo,) in query.iterall():
            pseudos.setdefault(pseudo.element, []).append(pseudo)

        return pseudos
