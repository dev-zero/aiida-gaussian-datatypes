# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Pseudopotential Data class
"""

import dataclasses
from ..utils import SYM2NUM
from decimal import Decimal
from icecream import ic
import numpy as np

from aiida.common.exceptions import (
    MultipleObjectsError,
    NotExistent,
    UniquenessError,
    ValidationError,
)
from aiida.orm import Data, Group


class Pseudopotential(Data):
    """
    Gaussian Pseudopotential (gpp) class to store gpp's in database and retrieve them.
    fixme: extend to NLCC pseudos.
    """

    __name__ = "Pseudopotential"

    def __init__(
        self,
        element=None,
        name=None,
        aliases=None,
        tags=None,
        n_el=None,
        n_el_tot=None,
        version=1,
        **kwargs,
    ):
        """
        :param element: string containing the name of the element
        :param name: identifier for this basis set, usually something like <name>-<size>[-q<nvalence>]
        :param aliases: alternative names
        :param tags: additional tags
        :param n_el: number of valence electrons covered by this basis set
        """

        if not aliases:
            aliases = []

        if not tags:
            tags = []

        if not n_el:
            n_el = []
        else:
            if not n_el_tot:
                n_el_tot = sum(n_el)
            else:
                raise #TODO a propiate error here

        if "label" not in kwargs:
            kwargs["label"] = name

        super().__init__(**kwargs)

        for attr in ("name", "element", "tags", "aliases", "n_el", "n_el_tot", "version"):
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

            assert isinstance(self.name, str) and self.name
            assert (
                isinstance(self.aliases, list)
                and all(isinstance(alias, str) for alias in self.aliases)
                and self.aliases
            )
            assert isinstance(self.tags, list) and all(isinstance(tag, str) for tag in self.tags)
            assert isinstance(self.version, int) and self.version > 0
            if len(self.n_el) != 0:
                assert(sum(self.n_el) == self.n_el_tot)
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
    def n_el_tot(self):
        """
        Return the number of electrons per angular momentum
        :rtype:int
        """

        return self.get_attribute("n_el_tot", [])

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

        query.append(cls, **params)

        filters = {"attributes.element": {"==": element}}

        if version != "latest":
            filters["attributes.version"] = {"==": version}

        if name:
            if match_aliases:
                filters["attributes.aliases"] = {"contains": [name]}
            else:
                filters["attributes.name"] = {"==": name}

        query.add_filter(cls, filters)

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

        def dict_fact(data):
            """
            Convert the list of tuples to a dict with:
            * Decimals replaced by strings
            * the required attrs set on the root
            * the key "coefficients" replaced with "coeffs"
            """

            def decimal2str(val):
                if isinstance(val, Decimal):
                    return str(val)

                if isinstance(val, list) and val and isinstance(val[0], Decimal):
                    return [str(v) for v in val]

                return val

            pseudo_dict = {k if k != "coefficients" else "coeffs": decimal2str(v) for k, v in data}

            if "identifiers" in pseudo_dict:  # if this is the root dict, replace 'identifiers'
                pseudo_dict["aliases"] = sorted(pseudo_dict.pop("identifiers"), key=lambda i: -len(i))
                pseudo_dict["name"] = pseudo_dict["aliases"][0]
                pseudo_dict["tags"] = pseudo_dict["name"].split("-")

            return pseudo_dict

        pseudos = [
            p
            for p in (
                dataclasses.asdict(p, dict_factory=dict_fact)
                for p in PseudopotentialData.datafile_iter(fhandle, keep_going=ignore_invalid)
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

        return [GTHPseudopotential(**p) for p in pseudos]

    @classmethod
    def from_gaussian(cls, fhandle, filters=None, duplicate_handling="ignore", ignore_invalid=False, attrs = None):
        """
        Constructs a list with pseudopotential objects from a Pseudopotential in Gaussian format

        :param fhandle: open file handle
        :param filters: a dict with attribute filter functions
        :param duplicate_handling: how to handle duplicates ("ignore", "error", "new" (version))
        :param ignore_invalid: whether to ignore invalid entries silently
        :rtype: list
        """

        def exists(pseudo):
            try:
                cls.get(pseudo["element"], pseudo["name"], match_aliases=False)
            except NotExistent:
                return False

            return True

        if not attrs:
            attrs = {}

        """
        Parser for Gaussian format
        """

        was_comment_line = 2
        functions = []
        functions.append({"prefactors" : [],
                          "polynoms"   : [],
                          "exponents"  : []})
        for ii, line in enumerate(fhandle):
            ic(line.strip())
            if ii == 0:
                element, n, = line.split()
                continue
            if ii == 1:
                qmc, n, core_electrons, = line.split()
                continue
            if ii == 2:
                continue
            if was_comment_line == -1:
                was_comment_line = int(line.strip())
            else:
                was_comment_line -= 1
                functions[-1]["exponents"].append(int(line.strip()[0]))
                functions[-1]["polynoms"].append(float(line.strip()[1]))
                functions[-1]["prefactors"].append(float(line.strip()[2]))

        """
        Change the order of functions so they match orbital momentum

        In Gaussian format first block represents upper most lmax
        and then the rest s, p, d, ...
        """
        functions = functions[1:] + [functions[0]]

        """
        TODO properly extract name
        """

        lmax = len(functions) - 1
        core_electrons = int(core_electrons)

        data = {"functions"      : functions,
                "element"        : element,
                "aliases"        : [qmc],
                "name"           : qmc,
                "core_electrons" : core_electrons,
                "lmax"           : lmax,
                "version"        : 1,
                "n_el"           : None,
                "n_el_tot"       : SYM2NUM[element] - core_electrons}

        if "name" in attrs:
            data["aliases"].append(data["name"])
            data["name"] = attrs["name"]

        if duplicate_handling == "force-ignore":  # This will be checked at the store stage
            pass

        elif duplicate_handling == "ignore":  # simply filter duplicates
            if exists(data):
                return []

        elif duplicate_handling == "error":
            if exists(data):
                raise UniquenessError(
                    f"Gaussian Pseudopotential already exists for"
                    f" element={data['element']}, name={data['name']}: {latest.uuid}"
                )

        elif duplicate_handling == "new":
            if exists(data):
                latest = cls.get(data["element"], data["name"], match_aliases=False)
                data["version"] = latest.version + 1

        else:
            raise ValueError(f"Specified duplicate handling strategy not recognized: '{duplicate_handling}'")

        return [ECPPseudopotential(**data)]

    @classmethod
    def from_gamess(cls, fhandle, filters=None, duplicate_handling="ignore", ignore_invalid=False, attrs = None):
        """
        Constructs a list with pseudopotential objects from a Pseudopotential in GAMESS format

        :param fhandle: open file handle
        :param filters: a dict with attribute filter functions
        :param duplicate_handling: how to handle duplicates ("ignore", "error", "new" (version))
        :param ignore_invalid: whether to ignore invalid entries silently
        :rtype: list
        """

        def exists(pseudo):
            try:
                cls.get(pseudo["element"], pseudo["name"], match_aliases=False)
            except NotExistent:
                return False

            return True

        if not attrs:
            attrs = {}

        """
        Parser for Gamess format
        """

        functions = []
        ns = 0
        for ii, line in enumerate(fhandle):
            if len(line.strip()) == 0: continue
            if ii == 0:
                name, gen, core_electrons, lmax = line.split()
                continue
            if ns == 0:
                ns = int(line)
                functions.append({"prefactors" : [],
                                  "polynoms"   : [],
                                  "exponents"  : []})
            else:
                for key, value in zip(("prefactors", "polynoms", "exponents"), map(float, line.split())):
                    functions[-1][key].append(value)
                ns -= 1

                """
                Cast polynoms to Integers
                """
                functions[-1]["polynoms"] = [ int(x) for x in functions[-1]["polynoms"] ]

        """
        Change the order of functions so they match orbital momentum

        In GAMESS format first block represents upper most lmax
        and then the rest s, p, d, ...
        """
        functions = functions[1:] + [functions[0]]

        """
        TODO properly extract name
        """

        element = name.split("-")[0]
        lmax = int(lmax)
        core_electrons = int(core_electrons)


        data = {"functions"      : functions,
                "element"        : element,
                "aliases"        : [name],
                "name"           : name,
                "core_electrons" : core_electrons,
                "lmax"           : lmax,
                "version"        : 1,
                "n_el"           : None,
                "n_el_tot"       : SYM2NUM[element] - core_electrons}

        if "name" in attrs:
            data["aliases"].append(data["name"])
            data["name"] = attrs["name"]

        if duplicate_handling == "force-ignore":  # This will be checked at the store stage
            pass

        elif duplicate_handling == "ignore":  # simply filter duplicates
            if exists(data):
                return []

        elif duplicate_handling == "error":
            if exists(data):
                raise UniquenessError(
                    f"Gaussian Pseudopotential already exists for"
                    f" element={data['element']}, name={data['name']}: {latest.uuid}"
                )

        elif duplicate_handling == "new":
            if exists(data):
                latest = cls.get(data["element"], data["name"], match_aliases=False)
                data["version"] = latest.version + 1

        else:
            raise ValueError(f"Specified duplicate handling strategy not recognized: '{duplicate_handling}'")

        return [ECPPseudopotential(**data)]

    @classmethod
    def from_turborvb(cls, fhandle, filters=None, duplicate_handling="ignore", ignore_invalid=False, attrs = None, name = None):
        """
        Constructs a list with pseudopotential objects from a Pseudopotential in TurboRVB format

        :param fhandle: open file handle
        :param filters: a dict with attribute filter functions
        :param duplicate_handling: how to handle duplicates ("ignore", "error", "new" (version))
        :param ignore_invalid: whether to ignore invalid entries silently
        :rtype: list
        """

        if hasattr(fhandle, "name"):
            import re
            if re.match("Z[0-9]{1,2}\_atomnumber[0-9]{1,2}\.[A-z]+",
                        fhandle.name):
                ret = re.match("Z[0-9]{1,2}\_atomnumber([0-9]{1,2})\.[A-z]+",
                               fhandle.name)
                atnum = int(ret.group(1))
                element = list(SYM2NUM.keys())[list(SYM2NUM.values()).index(atnum)]
                name = fhandle.name


        def exists(pseudo):
            try:
                cls.get(pseudo["element"], pseudo["name"], match_aliases=False)
            except NotExistent:
                return False

            return True

        if not attrs:
            attrs = {}

        """
        Parser for TurboRVB format
        """

        functions = []
        ns = 0
        for ii, line in enumerate(fhandle):
            if ii == 0: continue
            if ii == 1:
                num, r0, lmax = [float(x) for x in line.split()]
                continue
            if ii == 2:
                numf = [float(x) for x in line.split()]
                for jj in range(len(numf)):
                    functions.append({"prefactors" : [],
                                      "polynoms"   : [],
                                      "exponents"  : []})
                continue
            for jj in range(len(numf)):
                if numf[jj] < 1: continue
                numf[jj] -= 1
                for key, value in zip(("prefactors", "polynoms", "exponents"), map(float, line.split())):
                    functions[jj][key].append(value)

                functions[jj]["polynoms"] = [ int(x) for x in functions[jj]["polynoms"] ]
                break

        """
        TODO properly extract name
        """

        lmax = int(lmax)

        data = {"functions"      : functions,
                "element"        : element,
                "aliases"        : [name],
                "name"           : name,
                "core_electrons" : 0,
                "lmax"           : lmax,
                "version"        : 1,
                "n_el"           : None,
                "n_el_tot"       : 0}

        if "name" in attrs:
            data["aliases"].append(data["name"])
            data["name"] = attrs["name"]

        if duplicate_handling == "force-ignore":  # This will be checked at the store stage
            pass

        elif duplicate_handling == "ignore":  # simply filter duplicates
            if exists(data):
                return []

        elif duplicate_handling == "error":
            if exists(data):
                raise UniquenessError(
                    f"Gaussian Pseudopotential already exists for"
                    f" element={data['element']}, name={data['name']}: {latest.uuid}"
                )

        elif duplicate_handling == "new":
            if exists(data):
                latest = cls.get(data["element"], data["name"], match_aliases=False)
                data["version"] = latest.version + 1

        else:
            raise ValueError(f"Specified duplicate handling strategy not recognized: '{duplicate_handling}'")

        pp = ECPPseudopotential(**data)
        pp.set_extra("r0", r0)
        return [pp]

    def to_cp2k(self, fhandle, **kwargs):
        """
        Write this Pseudopotential instance to a file in CP2K format.

        :param fhandle: open file handle
        """

        if isinstance(self, GTHPseudopotential):

            fhandle.write(f"# from AiiDA Pseudopotential<uuid: {self.uuid}>\n")
            for line in _dict2pseudodata(self.attributes).cp2k_format_line_iter():
                fhandle.write(line)
                fhandle.write("\n")

        else:
            """
            make an error
            """
            pass

    def to_gamess(self, fhandle, **kwargs):
        """
        Write this Pseudopotential instance to a file in Gamess format.

        :param fhandle: open file handle
        """

        if isinstance(self, ECPPseudopotential):
            fhandle.write(f"{self.name} GEN {self.core_electrons} {self.lmax}\n")
            functions = [self.functions[-1]] + self.functions[:-1]
            for fun in functions:
                fhandle.write(f"{len(fun['polynoms'])}\n")
                for prefactor, polynom, exponent in zip(*[ fun[k] for k in ("prefactors", "polynoms", "exponents")]):
                    fhandle.write(f"{prefactor:12.7f} {polynom:4d} {exponent:12.7f}\n")


        else:
            """
            make an error
            """
            pass

    def to_turborvb(self, fhandle, tolerance = 1.0e-5, index = 1, **kwargs):
        """
        Write this Pseudopotential instance to a file in TurboRVB format.

        :param fhandle: open file handle
        :param tolerance: tolerance for pseudopotential
        """
        def f(r, block):
            nmax = len(block)
            psip = np.zeros(nmax)
            fun = 0.0
            if r < 1.0e-9: r = 1.0e-9

            for i in range(nmax):
                psip[i] = np.exp(-block[i][2]*r*r + np.log(r)*block[i][1])

            for i in range(nmax):
                fun += psip[i] * block[i][0]

            return fun/r/r

        if isinstance(self, ECPPseudopotential):
            fhandle.write(f"ECP\n")
            r0 = 0.0
            if "r0" in self.extras:
                r0 = self.extras["r0"]
            r0s = []
            for fun in self.functions:
                X = [ ii for ii in np.arange(0,10,0.01) ]
                block = [ [prefactor, polynom, exponent] for prefactor, polynom, exponent in zip(*[ fun[k] for k in ("prefactors", "polynoms", "exponents")])]
                Y = [ f(x, block) for x in X ]
                for ii in reversed(range(len(X))):
                    if Y[ii] > tolerance:
                        r0s.append(X[ii])
                        break
            r0 = max(r0s)

            fhandle.write(f"{index} {r0:4.2f} {len(self.functions)}\n")
            fhandle.write(" ".join([ f"{len(x['polynoms'])}" for x in self.functions ]))
            fhandle.write("\n")
            for fun in self.functions:
                for prefactor, polynom, exponent in zip(*[ fun[k] for k in ("prefactors", "polynoms", "exponents")]):
                    fhandle.write(f"{prefactor:12.7f} {polynom:4d} {exponent:12.7f}\n")


        else:
            """
            make an error
            """
            pass

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


class GTHPseudopotential(Pseudopotential):

    __name__ = "GTHPseudopotential"

    def __init__(
        self,
        local=None,
        non_local=None,
        nlcc=None,
        **kwargs):
        """
        :param local: see :py:attr:`~local`
        :param local: see :py:attr:`~non_local`
        """

        if not non_local:
            non_local = []

        if not nlcc:
            nlcc = []

        super().__init__(**kwargs)

        for attr in ("local", "non_local", "nlcc"):
            self.set_attribute(attr, locals()[attr])

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

    def _validate(self):
        super()._validate()

        try:
            _dict2pseudodata(self.attributes)
        except Exception as exc:
            raise ValidationError("One or more invalid fields found") from exc


class ECPPseudopotential(Pseudopotential):

    __name__ = "ECPPseudopotential"

    def __init__(
        self,
        functions=None,
        lmax=1,
        core_electrons=0,
        **kwargs):
        """
        :param functions:
        :param lmax: maximum angular momentum
        """

        if not functions:
            functions = []

        super().__init__(**kwargs)

        for attr in ("functions", "lmax", "core_electrons"):
            self.set_attribute(attr, locals()[attr])

    @property
    def lmax(self):
        """
        Return maximum angular momentum

        :rtype:int
        """
        return self.get_attribute("lmax", [])

    @property
    def core_electrons(self):
        """
        Returns number of core electrons

        :rtype:int
        """
        return self.get_attribute("core_electrons", [])

    @property
    def functions(self):
        """
        Returns list of basis functions

        :rtype:list
        """
        return self.get_attribute("functions", [])


def _dict2pseudodata(data):
    from cp2k_input_tools.pseudopotentials import (
        PseudopotentialData,
        PseudopotentialDataLocal,
        PseudopotentialDataNonLocal,
    )

    type_hooks = {
        PseudopotentialDataLocal: lambda d: {"coefficients": d["coeffs"], **d},
        PseudopotentialDataNonLocal: lambda d: {"coefficients": d["coeffs"], **d},
    }

    return PseudopotentialData.from_dict({"identifiers": data["aliases"], **data}, type_hooks=type_hooks)
