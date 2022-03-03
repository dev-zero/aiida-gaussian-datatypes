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
            for version, commit in enumerate(pydriller.Repository(str(tempdir), filepath=str(p)).traverse_commits()):
                commithash = commit.hash
            if commithash == "": return
            pseudo.extras["commithash"] = commithash
            pseudo.attributes["version"] = version + 1

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
                        for version, commit in enumerate(pydriller.Repository(str(tempdir), filepath=str(r)).traverse_commits()):
                            commithash = commit.hash
                        if commithash == "": return
                        b.extras["commithash"] = commithash
                        b.attributes["version"] = version + 1

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

@LibraryBookKeeper.register_library
class BFDLibrary(_ExternalLibrary):

    _URL = "http://burkatzki.com/pseudos/step4.2.php?format=gaussian&element={e}&basis={b}"

    @classmethod
    def fetch(cls):

        from ase.data import chemical_symbols
        from ase.data import atomic_numbers
        from urllib.request import urlopen
        from time import sleep
        import io

        elements = {}
        def add_data(source, e, b):

            source = str(source)
            pat=re.compile("^.*?(" + e + "\s0.*$)",re.M|re.DOTALL)
            x = pat.sub("\g<1>", source)
            x = re.sub("\<br\s*/\>", "\n", x)
            x = re.sub("\&nbsp", "", x)
            x = re.sub("\&nbsp", "", x)
            x = re.sub(".*html.*$", "", x)
            pat=re.compile("^.*?(" + e + "\s0.*)("+e+" 0.*)$",re.M|re.DOTALL)
            m = pat.match(x)
            if(m):
                bas = m.group(1)
                ecp = m.group(2)
                if len(bas) < 15: return
                typ = "BFD"
                pseudo, = Pseudopotential.from_gaussian(io.StringIO(ecp),
                                                        duplicate_handling = "force-ignore",
                                                        attrs = {"name" : f"{typ}" })

                basisset, = BasisSet.from_gaussian(io.StringIO(f"\n{bas}"),
                                                   duplicate_handling = "force-ignore",
                                                   attrs = {"name" : f"{typ}-{b}" })
                pseudos = [{"path": "",
                            "obj": pseudo}]
                version = 1
                pseudo.attributes["version"] = version

                tags = []
                tags.append(f"q{pseudo.n_el_tot}")
                tags.append(f"c{pseudo.core_electrons}")
                pseudo.tags.extend(tags)

                if e not in elements:
                    elements[e] = {"path": "",
                                   "types": {}}

                if typ not in elements[e]["types"]:
                    elements[e]["types"][typ] = {"path": "",
                                                 "basis": [],
                                                 "pseudos": pseudos,
                                                 "tags": []}
                elements[e]["types"][typ]["tags"].extend(tags)
                elements[e]["types"][typ]["basis"].append({"path" : f"http://burkatzki.com|{b}",
                                                           "obj"  : basisset})
                elements[e]["types"][typ]["tags"].append("BFD")
                tt = set(elements[e]["types"][typ]["tags"])
                elements[e]["types"][typ]["tags"] = list(tt)


        list_of_basis  =[ f"v{s}z" for s in "dtq56" ]
        list_of_basis += [ f"{x}_ano" for x in list_of_basis ]

        for b in list_of_basis:
            for ie in range(1, 87):
                l = cls._URL.format(b = b, e = chemical_symbols[ie])
                add_data(urlopen(l).read(), chemical_symbols[ie], b)
                """ Cool down """
                sleep(0.5)

        return elements
