# -*- coding: utf-8 -*-

import click
import tabulate
from aiida.cmdline.utils import decorators, echo
from aiida.cmdline.commands.cmd_data import verdi_data
from ..libraries import *
from ..basisset.data import BasisSet
from ..pseudopotential.data import Pseudopotential

from ..utils import click_parse_range  # pylint: disable=relative-beyond-top-level

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
        def __new__(cls, num, element, t, p, b):

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

            return (
                num,
                element,
                t,
                p,
                re.match("[A-z]{1,2}\.(.+).nwchem", b).group(1),
                b
            )

    table_content = []
    for ii, (e, d) in enumerate(elements.items()):
        for t in d["types"]:
            if len(d["types"][t]["pseudos"]) == 0:
                continue
            p = d["types"][t]["pseudos"][0]
            for b in d["types"][t]["basis"]:
                table_content.append(row(ii, e, t, p.name, b.name))

    #table_content = [row(n, p, v) for n, (p, v) in enumerate(elements.items())]
    return tabulate.tabulate(table_content, headers=["Nr.", "Element", "Type", "PseudoFile", "Basis", "BasisFile"])

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
    elements = LibraryBookKeeper.get_library_by_name(library).fetch()
    echo.echo_info(f"Found {len(elements)} elements")
    echo.echo(_formatted_table_import(elements))
    echo.echo("")
    indexes = click.prompt(
        "Which Elements do you want to add?"
        " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
        value_proc=lambda v: click_parse_range(v, len(elements)))
    ic(elements)
    ic(indexes)
    for idx in indexes:
        e = elements[{1: "H"}[idx+1]]
        for t, o in e["types"].items():
            for b in o["basis"]:
                with open(str(b), "r") as fhandle:
                    basis, = BasisSet.from_nwchem(fhandle)
                    echo.echo(f"Adding Basis for: {basis.element} ({basis.name})...  ", nl=False)
                    echo.echo("DONE")
            for p in o["pseudos"]:
                with open(str(p), "r") as fhandle:
                    pseudo, = Pseudopotential.from_gamess(fhandle)
                    echo.echo(f"Adding Pseudo for: {pseudo.element} ({pseudo.name})... ", nl=False)
                    echo.echo("DONE")


    #    echo.echo_info(
    #        "Adding Objects for: {p.element} ({p.name})... ".format(p=pseudos[idx]), nl=False)
    #    pseudos[idx].store()
    #    echo.echo("DONE")


