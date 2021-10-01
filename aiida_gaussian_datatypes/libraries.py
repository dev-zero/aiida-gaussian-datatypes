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
import pydriller
from aiida_gaussian_datatypes import utils
from typing import Dict, Generic, List, Optional, Sequence, Type, TypeVar
from icecream import ic
from .basisset.data import BasisSet
from .pseudopotential.data import Pseudopotential, ECPPseudopotential

from aiida.common.exceptions import (
    NotExistent,
)

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
class QmcpackLibrary(_ExternalLibrary):

    _URL = "https://github.com/QMCPACK/pseudopotentiallibrary.git"

    @classmethod
    def fetch(cls):

        elements = {}
        def add_data(p, tempdir, elements = elements):
            element = str(p.parent.parent.name)
            if element not in utils.SYM2NUM: # Check if element is valid
                return
            element_path = p.parent.parent

            typ = str(p.parent.name)
            typ_path = str(p.parent.name)

            tags = ["ECP", typ, ]

            """ Load Pseudopotential first """
            with open(p, "r") as fhandle:
                pseudo, = Pseudopotential.from_gamess(fhandle,
                                                      duplicate_handling = "force-ignore",
                                                      attrs = {"name" : typ })

            commithash = ""
            for commit in pydriller.Repository(str(tempdir), filepath=str(p)).traverse_commits():
                commithash = commit.hash
            if commithash == "": return
            pseudo.extras["commithash"] = commithash

            try:
                latest = ECPPseudopotential.get(pseudo.element,
                                                pseudo.name)
                pseudo.version = latest.version
                if latest.extras["commithash"] != commithash:
                    pseudo.version += 1
            except NotExistent:
                pass

            tags.append(f"q{pseudo.n_el_tot}")
            tags.append(f"c{pseudo.core_electrons}")
            pseudo.tags.extend(tags)

            pseudos = [{"path": p,
                        "obj": pseudo}]

            """ Load Basis sets """
            basis = []
            for r in (p.parent).glob("**/*"):
                if re.match("[A-z]{1,2}\.[A-z\-]*cc-.*\.nwchem", r.name):
                    name = re.match("[A-z]{1,2}\.([A-z\-]*cc-.*)\.nwchem", r.name).group(1)
                    name = f"{typ}-{name}"
                    with open(r, "r") as fhandle:
                        b = BasisSet.from_nwchem(fhandle,
                                                 duplicate_handling = "force-ignore",
                                                 attrs = {"n_el": pseudo.n_el_tot,
                                                          "name": name,
                                                          "tags": tags})
                        if len(b) == 0: continue
                        b, = b

                        commithash = ""
                        for commit in pydriller.Repository(str(tempdir), filepath=str(r)).traverse_commits():
                            commithash = commit.hash
                        if commithash == "": return
                        b.extras["commithash"] = commithash

                        try:
                            latest = BasisSet.get(b.element,
                                                  b.name)
                            b.version = latest.version
                            if latest.extras["commithash"] != commithash:
                                b.version += 1
                        except NotExistent:
                            pass

                    basis.append({"path": r,
                                  "obj": b})


            if element not in elements:
                elements[element] = {"path": element_path,
                                     "types": {}}

            if typ not in elements[element]["types"]:
                elements[element]["types"][typ] = {"path": typ_path,
                                                   "basis": basis,
                                                   "pseudos": pseudos,
                                                   "tags": tags}

        tempdir = pathlib.Path(tempfile.mkdtemp())
        git.Repo.clone_from(cls._URL, tempdir)

        for p in (tempdir/"recipes").glob("**/*"):
            if re.match("[A-z]{1,2}\.ccECP\.gamess", p.name):
                add_data(p, tempdir)

        return elements

