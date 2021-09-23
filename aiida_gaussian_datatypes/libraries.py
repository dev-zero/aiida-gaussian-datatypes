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
        tempdir = pathlib.Path(tempfile.mkdtemp())
        git.Repo.clone_from(cls._URL, tempdir)
        elements = { str(sub.name): {"file" : sub} for sub in (tempdir/"recipes").iterdir() if sub.is_dir() }
        # Add types
        elements = {el: {**data,
                         "types" : {x.name: {"path": x,
                                             "basis": [ b for b in x.iterdir() if re.match("[A-z]{1,2}\.[A-z\-]*cc-.*\.gamess", b.name)],
                                             "pseudo": [ b for b in x.iterdir() if re.match("[A-z]{1,2}\.ccECP\.gamess", b.name)]} for x in data["file"].iterdir() if x.is_dir()}} for el, data in elements.items()}
        return elements




