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

            if re.match("[A-z]{1,2}\.[A-z\-]*cc-.*\.gamess", p.name):
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
                                                   "pseudos": []}

            elements[element]["types"][typ][nature].append(p)


        tempdir = pathlib.Path(tempfile.mkdtemp())
        git.Repo.clone_from(cls._URL, tempdir)

        for p in (tempdir/"recipes").glob("**/*"):
            if str(p.name).lower().endswith(".gamess"):
                add_row(p)

        return elements
#                        elements = {el: {**data,
#-                         "types" : {x.name: {"path": x,
#-                                             "basis": [ b for b in x.iterdir() if re.match("[A-z]{1,2}\.[A-z\-]*cc-.*\.gamess", b.name)],
#-                                             "pseudo": [ b for b in x.iterdir() if re.match(, b.name)]} for x in data["file"].iterdir() if x.is_dir()}} for el, data in elements.items()}
#-        return elements





