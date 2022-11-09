# -*- coding: utf-8 -*-

import click
import tabulate
import pydriller
from pathlib import Path
from aiida.cmdline.utils import decorators, echo
from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.orm import load_group
from ..libraries import *
from ..basisset.data import BasisSet
from ..pseudopotential.data import Pseudopotential
#from ..groups import (
#    BasisSetGroup,
#    PseudopotenialGroup,
#)
from ..groups import BasisSetGroup
from ..groups import PseudopotentialGroup

#from ..utils import (
#    click_parse_range,  # pylint: disable=relative-beyond-top-level
#    SYM2NUM,
#)

from ..utils import click_parse_range
from ..utils import SYM2NUM
from aiida.common.exceptions import UniquenessError

def _formatted_table_import(elements):
    """generates a formatted table (using tabulate) for importable basis and PPs"""

    def _boldformater(f):

        def fout(*args, **kwargs):
            if args[1] % 2 == 1:
                return ( f"\033[1m{x}\033[0m" for x in f(*args, **kwargs))
            else:
                return ( x for x in f(*args, **kwargs))
        return fout

    class row():

        num = []
        element = []
        t = []

        @_boldformater
        def __new__(cls, num, element, t, p, tags, b):

            if element in cls.element:
                element = ""
            else:
                cls.element.append(element)
                element = str(element)
                cls.t = []

            if num in cls.num:
                num = ""
            else:
                cls.num.append(num)
                num = str(num)

            if t in cls.t:
                t = ""
            else:
                cls.t.append(t)

            if t == "":
                p = ""
                tags = []

            name = ""
            m = re.match("http:\/\/burkatzki\.com\|([A-z]+)", b)
            if m:
                name = m.group(1)
            m = re.match("[A-z]{1,2}\.(.+).nwchem", b)
            if m:
                name = m.group(1)

            return (
                num,
                element,
                t,
                p,
                " ".join(sorted(tags)),
                name,
                b
            )

    table_content = []
    for ii, (e, d) in enumerate(elements):
        for t in d["types"]:
            if len(d["types"][t]["pseudos"]) == 0:
                continue
            p = d["types"][t]["pseudos"][0]
            for b in d["types"][t]["basis"]:
                name = ""
                if isinstance(b["path"], str):
                    name = b["path"]
                if hasattr(b["path"], "name"):
                    name = b["path"].name
                table_content.append(row(ii, e, t, name,
                                         d["types"][t]["tags"],
                                         name))

    #table_content = [row(n, p, v) for n, (p, v) in enumerate(elements.items())]
    return tabulate.tabulate(table_content, headers=["Nr.", "Element", "Type", "PseudoFile", "Tags", "Basis", "BasisFile"])

@verdi_data.group("gaussian")
def cli():
    """Manage Pseudopotentials for GTO-based codes"""

# fmt: off
@cli.command('fetch')
@click.argument('library',
                type=click.Choice(LibraryBookKeeper.get_library_names()))
@decorators.with_dbenv()
# fmt: on
def install_family(library):
    """
    Installs a family of pseudo potentials from a remote repository
    """

    basissetgname = f"{library}-basis"
    try:
        basisgroup = load_group(basissetgname)
    except:
        echo.echo_info("Creating library basis group ... ", nl = False)
        basisgroup = BasisSetGroup(basissetgname)
        basisgroup.store()
        echo.echo("DONE")

    pseudogname = f"{library}-pseudo"
    try:
        pseudogroup = load_group(pseudogname)
    except:
        echo.echo_info("Creating library pseudo group ... ", nl = False)
        pseudogroup = PseudopotentialGroup(pseudogname)
        pseudogroup.store()
        echo.echo("DONE")

    elements = LibraryBookKeeper.get_library_by_name(library).fetch()

    elements = [ [el, p] for el, p in sorted(elements.items(), key = lambda x: SYM2NUM[x[0]]) ]
    echo.echo_info(f"Found {len(elements)} elements")
    echo.echo(_formatted_table_import(elements))
    echo.echo("")
    indexes = click.prompt(
        "Which Elements do you want to add?"
        " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
        value_proc=lambda v: click_parse_range(v, len(elements)))
    for idx in indexes:
        e, v = elements[idx]
        for t, o in v["types"].items():
            for b in o["basis"]:
                basis = b["obj"]
                echo.echo_info(f"Adding Basis for: ", nl=False)
                echo.echo(f"{basis.element} ({basis.name})...  ", nl=False)
                try:
                    basis.store()
                    basisgroup.add_nodes([basis])
                    echo.echo("Imported")
                except UniquenessError:
                    echo.echo("Skipping (already in)")
                except Exception as e:
                    echo.echo("Skipping (something went wrong)")
            for p in o["pseudos"]:
                pseudo = p["obj"]
                echo.echo_info(f"Adding Pseudopotential for: ", nl=False)
                echo.echo(f"{pseudo.element} ({pseudo.name})...  ", nl=False)
                try:
                    pseudo.store()
                    pseudogroup.add_nodes([pseudo])
                    echo.echo("Imported")
                except UniquenessError:
                    echo.echo("Skipping (already in)")
                except Exception as e:
                    echo.echo("Skipping (something went wrong)")

