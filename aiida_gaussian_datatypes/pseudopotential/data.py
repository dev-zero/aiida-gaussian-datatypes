# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Pseudopotential Data class
"""

from decimal import Decimal
from typing import Any, Dict

from aiida.common.exceptions import (
    MultipleObjectsError,
    NotExistent,
    UniquenessError,
    ValidationError,
)
from aiida.orm import Data, Group
from cp2k_input_tools.pseudopotentials import PseudopotentialData


class Pseudopotential(Data):
    """
    Gaussian Pseudopotential (gpp) class to store gpp's in database and retrieve them.
    fixme: extend to NLCC pseudos.
    """

    def __init__(
        self,
        element=None,
        name=None,
        aliases=None,
        tags=None,
        n_el=None,
        local=None,
        non_local=None,
        nlcc=None,
        version=1,
        **kwargs,
    ):
        """
        :param element: string containing the name of the element
        :param name: identifier for this basis set, usually something like <name>-<size>[-q<nvalence>]
        :param aliases: alternative names
        :param tags: additional tags
        :param n_el: number of valence electrons covered by this basis set
        :param local: see :py:attr:`~local`
        :param local: see :py:attr:`~non_local`
        """

        if not aliases:
            aliases = []

        if not tags:
            tags = []

        if not n_el:
            n_el = []

        if not non_local:
            non_local = []

        if not nlcc:
            nlcc = []

        if "label" not in kwargs:
            kwargs["label"] = name

        super().__init__(**kwargs)

        for attr in ("name", "element", "tags", "aliases", "n_el", "local", "non_local", "nlcc", "version"):
            self.set_attribute(attr, locals()[attr])

    def store(self, *args, **kwargs):
        """
        Store the node, ensuring that the combination (element,name,version) is unique.
        """
        # TODO: this uniqueness check is not race-condition free.

        try:
            existing = self.get(self.element, self.name, self.version, match_aliases=False)
        except NotExistent:
            pass
        else:
            raise UniquenessError(
                f"Gaussian Pseudopotential already exists for"
                f" element={self.element}, name={self.name}, version={self.version}: {existing.uuid}"
            )

        return super().store(*args, **kwargs)

    def _validate(self):
        super()._validate()

        try:
            # directly raises a ValidationError for the pseudo data if something's amiss
            _dict2pseudodata(self.attributes)

            assert isinstance(self.name, str) and self.name
            assert (
                isinstance(self.aliases, list)
                and all(isinstance(alias, str) for alias in self.aliases)
                and self.aliases
            )
            assert isinstance(self.tags, list) and all(isinstance(tag, str) for tag in self.tags)
            assert isinstance(self.version, int) and self.version > 0
        except Exception as exc:
            raise ValidationError("One or more invalid fields found") from exc

    @property
    def element(self):
        """
        the atomic kind/element this pseudopotential is for

        :rtype: str
        """
        return self.get_attribute("element", None)

    @property
    def name(self):
        """
        the name for this pseudopotential

        :rtype: str
        """
        return self.get_attribute("name", None)

    @property
    def aliases(self):
        """
        a list of alternative names

        :rtype: []
        """
        return self.get_attribute("aliases", [])

    @property
    def tags(self):
        """
        a list of tags

        :rtype: []
        """
        return self.get_attribute("tags", [])

    @property
    def version(self):
        """
        the version of this pseudopotential

        :rtype: int
        """
        return self.get_attribute("version", None)

    @property
    def n_el(self):
        """
        Return the number of electrons per angular momentum
        :rtype:list
        """

        return self.get_attribute("n_el", [])

    @property
    def local(self):
        """
        Return the local part

        The format of the returned dictionary::

            {
                'r': float,
                'coeffs': [float, float, ...],
            }

        :rtype:dict
        """
        return self.get_attribute("local", None)

    @property
    def non_local(self):
        """
        Return a list of non-local projectors (for l=0,1...).

        Each list element will have the following format::

            {
                'r': float,
                'nproj': int,
                'coeffs': [float, float, ...],  # only the upper-triangular elements
            }

        :rtype:list
        """
        return self.get_attribute("non_local", [])

    @property
    def nlcc(self):
        """
        Return a list of the non-local core-corrections data

        :rtype:list
        """
        return self.get_attribute("nlcc", [])

    @classmethod
    def get(cls, element, name=None, version="latest", match_aliases=True, group_label=None, n_el=None):
        """
        Get the first matching Pseudopotential for the given parameters.

        :param element: The atomic symbol
        :param name: The name of the pseudo
        :param version: A specific version (if more than one in the database and not the highest/latest)
        :param match_aliases: Whether to look in the list of of aliases for a matching name
        """
        from aiida.orm.querybuilder import QueryBuilder

        query = QueryBuilder()

        params = {}

        if group_label:
            query.append(Group, filters={"label": group_label}, tag="group")
            params["with_group"] = "group"

        query.append(Pseudopotential, **params)

        filters = {"attributes.element": {"==": element}}

        if version != "latest":
            filters["attributes.version"] = {"==": version}

        if name:
            if match_aliases:
                filters["attributes.aliases"] = {"contains": [name]}
            else:
                filters["attributes.name"] = {"==": name}

        query.add_filter(Pseudopotential, filters)

        # SQLA ORM only solution:
        # query.order_by({Pseudopotential: [{"attributes.version": {"cast": "i", "order": "desc"}}]})
        # items = query.first()

        all_iter = query.iterall()

        if n_el:
            all_iter = filter(lambda p: sum(p[0].n_el) == n_el, all_iter)

        items = sorted(all_iter, key=lambda p: p[0].version, reverse=True)

        if not items:
            raise NotExistent(
                f"No Gaussian Pseudopotential found for element={element}, name={name}, version={version}"
            )

        # if we get different names there is no well ordering, sorting by version only works if they have the same name
        if len(set(p[0].name for p in items)) > 1:
            raise MultipleObjectsError(
                f"Multiple Gaussian Pseudopotentials found for element={element}, name={name}, version={version}"
            )

        return items[0][0]

    @classmethod
    def from_cp2k(cls, fhandle, filters=None, duplicate_handling="ignore", ignore_invalid=False):
        """
        Constructs a list with pseudopotential objects from a Pseudopotential in CP2K format

        :param fhandle: open file handle
        :param filters: a dict with attribute filter functions
        :param duplicate_handling: how to handle duplicates ("ignore", "error", "new" (version))
        :param ignore_invalid: whether to ignore invalid entries silently
        :rtype: list
        """
        from cp2k_input_tools.pseudopotentials import PseudopotentialData

        if not filters:
            filters = {}

        def matches_criteria(pseudo):
            return all(fspec(pseudo[field]) for field, fspec in filters.items())

        def exists(pseudo):
            try:
                cls.get(pseudo["element"], pseudo["name"], match_aliases=False)
            except NotExistent:
                return False

            return True

        pseudos = [
            p
            for p in (
                _pseudodata2dict(p) for p in PseudopotentialData.datafile_iter(fhandle, keep_going=ignore_invalid)
            )
            if matches_criteria(p)
        ]

        if duplicate_handling == "ignore":  # simply filter duplicates
            pseudos = [p for p in pseudos if not exists(p)]

        elif duplicate_handling == "error":
            for pseudo in pseudos:
                try:
                    latest = cls.get(pseudo["element"], pseudo["name"], match_aliases=False)
                except NotExistent:
                    pass
                else:
                    raise UniquenessError(
                        f"Gaussian Pseudopotential already exists for"
                        f" element={pseudo['element']}, name={pseudo['name']}: {latest.uuid}"
                    )

        elif duplicate_handling == "new":
            for pseudo in pseudos:
                try:
                    latest = cls.get(pseudo["element"], pseudo["name"], match_aliases=False)
                except NotExistent:
                    pass
                else:
                    pseudo["version"] = latest.version + 1

        else:
            raise ValueError(f"Specified duplicate handling strategy not recognized: '{duplicate_handling}'")

        return [cls(**p) for p in pseudos]

    def to_cp2k(self, fhandle):
        """
        Write this Pseudopotential instance to a file in CP2K format.

        :param fhandle: open file handle
        """

        fhandle.write(f"# from AiiDA Pseudopotential<uuid: {self.uuid}>\n")
        for line in _dict2pseudodata(self.attributes).cp2k_format_line_iter():
            fhandle.write(line)
            fhandle.write("\n")

    def get_matching_basisset(self, *args, **kwargs):
        """
        Get a pseudopotential matching this basis set by at least element and number of valence electrons.
        Additional arguments are passed on to BasisSet.get()
        """
        from ..basisset.data import BasisSet

        if self.n_el:
            return BasisSet.get(element=self.element, n_el=sum(self.n_el), *args, **kwargs)
        else:
            return BasisSet.get(element=self.element, *args, **kwargs)


def _pseudodata2dict(data: PseudopotentialData) -> Dict[str, Any]:
    """
    Convert a PseudopotentialData to a compatible dict with:
    * Decimals replaced by strings
    * the required attrs set on the root
    * the key "coefficients" replaced with "coeffs"
    """

    pseudo_dict = data.dict(by_alias=True)

    stack = [pseudo_dict]
    while stack:
        current = stack.pop()
        for key, val in current.items():
            if isinstance(val, dict):
                stack.append(val)
            elif isinstance(val, Decimal):
                current[key] = str(val)
            elif isinstance(val, list) and val and isinstance(val[0], dict):
                stack += val
            elif isinstance(val, list) and val and isinstance(val[0], Decimal):
                current[key] = [str(v) for v in val]

    pseudo_dict["aliases"] = sorted(pseudo_dict.pop("identifiers"), key=lambda i: -len(i))
    pseudo_dict["name"] = pseudo_dict["aliases"][0]
    pseudo_dict["tags"] = pseudo_dict["name"].split("-")

    return pseudo_dict


def _dict2pseudodata(data: Dict[str, Any]) -> PseudopotentialData:
    obj = {k: v for k, v in data.items() if k not in ("name", "tags", "version")}
    obj["identifiers"] = obj.pop("aliases")
    return PseudopotentialData.parse_obj(obj)
