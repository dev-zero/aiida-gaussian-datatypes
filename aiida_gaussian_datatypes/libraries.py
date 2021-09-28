# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
#
# Was there really a fish
# That grants you that kind of wish
#
import os
import re
import git
import tempfile
import pathlib
from aiida_gaussian_datatypes import utils
from typing import Dict, Generic, List, Optional, Sequence, Type, TypeVar
from icecream import ic
from .basisset.data import BasisSet
from .pseudopotential.data import Pseudopotential

class LibraryBookKeeper:

    classes = []

    @classmethod
    def register_library(cls, cls_):
        cls.classes.append(cls_)

    @classmethod
    def get_libraries(cls):
        return cls.classes

    @classmethod
    def get_library_names(cls):
        return [ re.match("<class '[0-9A-z_\.]*\.([A-z]+)'>", str(x)).group(1) for x in cls.classes ]

    @classmethod
    def get_library_by_name(cls, name):
        for cls_ in cls.get_libraries():
            if re.match(f"<class '[0-9A-z_\.]*\.({name})'>", str(cls_)) is not None:
                return cls_
        return None

class _ExternalLibrary:

    @classmethod
    def fetch(cls):
        pass

@LibraryBookKeeper.register_library
class EmptyLibrary(_ExternalLibrary):
    pass

@LibraryBookKeeper.register_library
class MitasLibrary(_ExternalLibrary):

    _URL = "https://github.com/QMCPACK/pseudopotentiallibrary.git"

    @classmethod
    def fetch(cls):

        elements = {}
        def add_row(p, elements = elements):
            element = str(p.parent.parent.name)
            if element not in utils.SYM2NUM: # Check if element is valid
                return
            element_path = p.parent.parent

            typ = str(p.parent.name)
            typ_path = str(p.parent.name)

            if re.match("[A-z]{1,2}\.[A-z\-]*cc-.*\.nwchem", p.name):
                nature = "basis"
            elif re.match("[A-z]{1,2}\.ccECP\.gamess", p.name):
                nature = "pseudos"
            else:
                """
                If does not match these regexes do nothing
                """
                return

            if element not in elements:
                elements[element] = {"path": element_path,
                                     "types": {}}

            if typ not in elements[element]["types"]:
                elements[element]["types"][typ] = {"path": typ_path,
                                                   "basis": [],
                                                   "pseudos": [],
                                                   "tags": ["ECP", typ, ]}
            val = {}
            val["path"] = p
            with open(p, "r") as fhandle:
                if nature == "basis":
                    try:
                        obj, = BasisSet.from_nwchem(fhandle,
                                                   duplicate_handling = "new")
                    except:
                        """
                        Something went wrong in the import, continuing ...
                        """
                        return
                    tags = ["aug"]
                elif nature == "pseudos":
                    try:
                        obj, = Pseudopotential.from_gamess(fhandle,
                                                          duplicate_handling = "new")
                    except:
                        """
                        Something went wrong in the import, continuing ...
                        """
                        return
                    tags = []
                else:
                    raise # TODO give here an error
            obj.tags.extend(tags)
            val["obj"] = obj
            val["tags"] = tags
            elements[element]["types"][typ][nature].append(val)


        tempdir = pathlib.Path(tempfile.mkdtemp())
        git.Repo.clone_from(cls._URL, tempdir)

        for p in (tempdir/"recipes").glob("**/*"):
            if str(p.name).lower().endswith(".gamess") or str(p.name).lower().endswith(".nwchem"):
                add_row(p)

        """ Update valence electrons """
        for e in elements:
            for t in elements[e]["types"]:
                if len(elements[e]["types"][t]["pseudos"]) == 1:
                    tags = [f'q{elements[e]["types"][t]["pseudos"][0]["obj"].n_el_tot}',
                            f'c{elements[e]["types"][t]["pseudos"][0]["obj"].core_electrons}'
                           ]
                    elements[e]["types"][t]["tags"].extend(tags)
                    for ii, b in enumerate(elements[e]["types"][t]["basis"]):
                        elements[e]["types"][t]["basis"][ii]["obj"].n_el = elements[e]["types"][t]["pseudos"][0]["obj"].n_el_tot


        return elements

