# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Basis Set Data Class
"""

from aiida.orm import Data

from .utils import write_cp2k_basisset, cp2k_basisset_file_iter


class BasisSet(Data):
    """
    Provide a general way to store GTO basis sets from different codes within the AiiDA framework.
    """

    def __init__(self, element=None, name=None, aliases=None, tags=None, n_el=None, blocks=None, version=1, **kwargs):
        """
        :param element: string containing the name of the element
        :param name: identifier for this basis set, usually something like <name>-<size>[-q<nvalence>]
        :param aliases: alternative names
        :param tags: additional tags
        :param n_el: number of valence electrons covered by this basis set
        :param blocks: see :py:attr:`~blocks`
        """

        if not aliases:
            aliases = []

        if not tags:
            tags = []

        if not blocks:
            blocks = []

        super(BasisSet, self).__init__(**kwargs)

        self.set_attribute("name", name)
        self.set_attribute("element", element)
        self.set_attribute("tags", tags)
        self.set_attribute("aliases", aliases)
        self.set_attribute("n_el", n_el)
        self.set_attribute("blocks", blocks)
        self.set_attribute("version", version)

    def store(self, *args, **kwargs):
        """
        Store the node, ensuring that the combination (element,name,version) is unique.
        """
        # TODO: this uniqueness check is not race-condition free.

        from aiida.common.exceptions import UniquenessError, NotExistent

        try:
            existing = self.get(self.element, self.name, self.version, match_aliases=False)
        except NotExistent:
            pass
        else:
            raise UniquenessError(
                f"Gaussian Basis Set already exists for"
                f" element={self.element}, name={self.name}, version={self.version}: {existing.uuid}"
            )

        return super(BasisSet, self).store(*args, **kwargs)

    def _validate(self):
        super(BasisSet, self)._validate()

        from voluptuous import Schema, MultipleInvalid, ALLOW_EXTRA, All, Any, Length
        from aiida.common.exceptions import ValidationError

        # fmt: off
        schema = Schema({
            'name': str,
            'element': str,
            'tags': [str],
            'aliases': [str],
            'n_el': Any(int, None),
            'blocks': [{
                "n": int,
                "l": [All([int], Length(2, 2)), All((int,), Length(2, 2))],
                "coefficients": [[float]],
                }],
            'version': int,
            }, extra=ALLOW_EXTRA, required=True)
        # fmt: on

        try:
            schema(self.attributes)
        except MultipleInvalid as exc:
            raise ValidationError(str(exc))

    @property
    def element(self):
        """
        the atomic kind/element this basis set is for

        :rtype: str
        """
        return self.get_attribute("element", None)

    @property
    def name(self):
        """
        the name for this basis set

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
        the version of this basis set

        :rtype: int
        """
        return self.get_attribute("version", None)

    @property
    def n_el(self):
        """
        number of valence electrons covered by this basis set

        :rtype: int
        """
        return self.get_attribute("n_el", None)

    @property
    def blocks(self):
        """
        Return the shells/blocks in the following format::

            [
                {
                    "n": 2,
                    "l": [
                        (0, 2),  # 2 sets of coefficients for the same exponents for s
                        (1, 1),  # 1 set of coefficients for the same exponents for p
                        ],
                    "coefficients":
                        [
                            [ "2838.2104843030", "-0.0007019523",  "-0.0007019523", "-0.0007019523" ],
                            [  "425.9069835160", "-0.0054237190",  "-0.0054237190", "-0.0054237190" ],
                            [   "96.6806600316", "-0.0277505669",  "-0.0277505669", "-0.0277505669" ],
                        ],
                    ],
                },
            ]

        :rtype: []
        """

        return self.get_attribute("blocks", [])

    @property
    def n_orbital_functions(self):
        """
        Return the number of orbital functions from this basis set
        """

        norbfuncs = 0

        for block in self.blocks:
            # for each l quantum number we get number of m quantum numbers times number of "shells" MOs
            norbfuncs += sum((2 * lqn + 1) * nshells for lqn, nshells in block["l"])

        return norbfuncs

    @classmethod
    def get(cls, element, name=None, version="latest", match_aliases=True):
        from aiida.orm.querybuilder import QueryBuilder
        from aiida.common.exceptions import NotExistent

        filters = {"attributes.element": {"==": element}}

        if version != "latest":
            filters["attributes.version"] = {"==": version}

        if match_aliases:
            filters["attributes.aliases"] = {"contains": [name]}
        else:
            filters["attributes.name"] = {"==": name}

        query = QueryBuilder()
        query.append(BasisSet)
        query.add_filter(BasisSet, filters)

        # SQLA ORM only solution:
        # query.order_by({BasisSet: [{"attributes.version": {"cast": "i", "order": "desc"}}]})
        # existing = query.first()

        existing = sorted(query.iterall(), key=lambda b: b[0].version, reverse=True)[0] if query.count() else []

        if not existing:
            raise NotExistent(f"No Gaussian Basis Set found for element={element}, name={name}, version={version}")

        return existing[0]

    @classmethod
    def from_cp2k(cls, fhandle, filters=None, duplicate_handling="ignore"):
        """
        Constructs a list with basis set objects from a Basis Set in CP2K format

        :param fhandle: open file handle
        :param filters: a dict with attribute filter functions
        :param duplicate_handling: how to handle duplicates ("ignore", "error", "new" (version))
        :rtype: list
        """

        from aiida.common.exceptions import UniquenessError, NotExistent

        if not filters:
            filters = {}

        def matches_criteria(bset):
            return all(fspec(bset[field]) for field, fspec in filters.items())

        def exists(bset):
            try:
                cls.get(bset["element"], bset["name"], match_aliases=False)
            except NotExistent:
                return False

            return True

        bsets = [bs for bs in cp2k_basisset_file_iter(fhandle) if matches_criteria(bs)]

        if duplicate_handling == "ignore":  # simply filter duplicates
            bsets = [bs for bs in bsets if not exists(bs)]

        elif duplicate_handling == "error":
            for bset in bsets:
                try:
                    latest = cls.get(bset["element"], bset["name"], match_aliases=False)
                except NotExistent:
                    pass
                else:
                    raise UniquenessError(
                        f"Gaussian Basis Set already exists for"
                        f" element={bset['element']}, name={bset['name']}: {latest.uuid}"
                    )

        elif duplicate_handling == "new":
            for bset in bsets:
                try:
                    latest = cls.get(bset["element"], bset["name"], match_aliases=False)
                except NotExistent:
                    pass
                else:
                    bset["version"] = latest.version + 1

        else:
            raise ValueError(f"Specified duplicate handling strategy not recognized: '{duplicate_handling}'")

        return [cls(**bs) for bs in bsets]

    def to_cp2k(self, fhandle):
        """
        Write the Basis Set to the passed file handle in the format expected by CP2K.

        :param fhandle: A valid output file handle
        """

        return write_cp2k_basisset(
            fhandle, self.element, self.name, self.blocks, comment=f"from AiiDA BasisSet<uuid: {self.uuid}>"
        )
