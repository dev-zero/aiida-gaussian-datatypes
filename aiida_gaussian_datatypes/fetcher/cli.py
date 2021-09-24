# -*- coding: utf-8 -*-

import click
import tabulate
from aiida.cmdline.utils import decorators, echo
from aiida.cmdline.commands.cmd_data import verdi_data
from ..libraries import *

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
    return tabulate.tabulate(table_content, headers=["Nr.", "Element", "Type", "Pseudo", "Basis"])

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


