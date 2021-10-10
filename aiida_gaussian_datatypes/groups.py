# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Groups for the GTO data classes
"""

from typing import Dict, Generic, List, Optional, Sequence, Type, TypeVar

from aiida.orm import Group, QueryBuilder, StructureData

from .basisset.data import BasisSet
from .pseudopotential.data import Pseudopotential

_T = TypeVar("_T")


class _MemberMixin(Generic[_T]):
    member_type: Type[_T]

    def get_members(
        self, elements: Optional[Sequence[str]] = None, structure: Optional[StructureData] = None
    ) -> Dict[str, List[_T]]:
        """
        Return a dict of kind names/elements to a list of respective data nodes
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
            .append(self.member_type, with_group="group", filters={"attributes.element": {"in": elements}})
        )

        pseudos: Dict[str, List[_T]] = {}

        for (pseudo,) in query.iterall():
            pseudos.setdefault(pseudo.element, []).append(pseudo)

        return pseudos


class BasisSetGroup(Group, _MemberMixin):
    """Group for Gaussian.Basisset nodes"""

    member_type = BasisSet


class PseudopotentialGroup(Group, _MemberMixin):
    """Group for Gaussian.Pseudopotential nodes"""

    member_type = Pseudopotential

    def get_pseudos(
        self, elements: Optional[Sequence[str]] = None, structure: Optional[StructureData] = None
    ) -> Dict[str, List[_T]]:
        return self.get_members(elements, structure)
