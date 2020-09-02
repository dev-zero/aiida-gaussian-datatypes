# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Pseudopotential verdi command line interface
"""

import sys

import click
import tabulate

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.utils import decorators, echo
from aiida.cmdline.params import arguments
from aiida.cmdline.params.types import DataParamType

from ..utils import click_parse_range  # pylint: disable=relative-beyond-top-level


def _names_column(name, aliases):
    return ", ".join(["\033[1m{}\033[0m".format(name), *[a for a in aliases if a != name]])


def _formatted_table_import(pseudos):
    """generates a formatted table (using tabulate) for the given list of pseudopotentials, shows a sequencial number"""

    def row(num, pseudo):
        return (
            num + 1,
            pseudo.element,
            _names_column(pseudo.name, pseudo.aliases),
            ", ".join(pseudo.tags),
            ", ".join(f"{n}" for n in pseudo.n_el + (3 - len(pseudo.n_el)) * [0]),
            pseudo.version,
        )

    table_content = [row(n, p) for n, p in enumerate(pseudos)]
    return tabulate.tabulate(table_content, headers=["Nr.", "Sym", "Names", "Tags", "Val. e⁻ (s, p, d)", "Version"])


def _formatted_table_list(pseudos):
    """generates a formatted table (using tabulate) for the given list of pseudopotentials, shows the UUIID"""

    def row(pseudo):
        return (
            pseudo.uuid,
            pseudo.element,
            _names_column(pseudo.name, pseudo.aliases),
            ", ".join(pseudo.tags),
            ", ".join(f"{n}" for n in pseudo.n_el + (3 - len(pseudo.n_el)) * [0]),
            pseudo.version,
        )

    table_content = [row(p) for p in pseudos]
    return tabulate.tabulate(table_content, headers=["ID", "Sym", "Names", "Tags", "Val. e⁻ (s, p, d)", "Version"])


@verdi_data.group("gaussian.pseudo")
def cli():
    """Manage Pseudopotentials for GTO-based codes"""


# fmt: off
@cli.command('import')
@click.argument('pseudopotential_file', type=click.File(mode='r'))
@click.option('--sym', '-s', help="filter by atomic symbol")
@click.option(
    'tags', '--tag', '-t',
    multiple=True,
    help="filter by a tag (all tags must be present if specified multiple times)")
@click.option(
    'fformat', '-f', '--format',
    type=click.Choice(['cp2k', ]), default='cp2k',
    help="the format of the pseudopotential file")
@click.option(
    '--duplicates',
    type=click.Choice(['ignore', 'error', 'new']), default='ignore',
    help="Whether duplicates should be ignored, produce an error or uploaded as new version")
# fmt: on
@decorators.with_dbenv()
def import_pseudo(pseudopotential_file, fformat, sym, tags, duplicates):
    """
    Add a pseudopotential from a file to the database
    """

    from aiida_gaussian_datatypes.pseudopotential.data import Pseudopotential

    loaders = {
        "cp2k": Pseudopotential.from_cp2k,
    }

    filters = {
        'element': lambda x: not sym or x == sym,
        'tags': lambda x: not tags or set(tags).issubset(x),
    }

    pseudos = loaders[fformat](pseudopotential_file, filters, duplicates)

    if not pseudos:
        echo.echo_info("No valid Gaussian Pseudopotentials found in the given file matching the given criteria")
        return

    if len(pseudos) == 1:
        pseudo = pseudos[0]
        click.confirm("Add a Gaussian '{p.name}' Pseudopotential for '{p.element}'?".format(p=pseudo), abort=True)
        pseudo.store()
        return

    echo.echo_info("{} Gaussian Pseudopotentials found:\n".format(len(pseudos)))
    echo.echo(_formatted_table_import(pseudos))
    echo.echo("")

    indexes = click.prompt(
        "Which Gaussian Pseudopotentials do you want to add?"
        " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
        value_proc=lambda v: click_parse_range(v, len(pseudos)))

    for idx in indexes:
        echo.echo_info(
            "Adding Gaussian Pseudopotentials for: {p.element} ({p.name})... ".format(p=pseudos[idx]), nl=False)
        pseudos[idx].store()
        echo.echo("DONE")


@cli.command('list')
@click.option('-s', '--sym', type=str, default=None, help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None, help="filter by name")
@click.option(
    'tags', '--tag', '-t', multiple=True, help="filter by a tag (all tags must be present if specified multiple times)")
@decorators.with_dbenv()
def list_pseudo(sym, name, tags):
    """
    List Gaussian Pseudopotentials
    """
    from aiida_gaussian_datatypes.pseudopotential.data import Pseudopotential
    from aiida.orm.querybuilder import QueryBuilder

    query = QueryBuilder()
    query.append(Pseudopotential)

    if sym:
        query.add_filter(Pseudopotential, {'attributes.element': {'==': sym}})

    if name:
        query.add_filter(Pseudopotential, {'attributes.aliases': {'contains': [name]}})

    if tags:
        query.add_filter(Pseudopotential, {'attributes.tags': {'contains': tags}})

    if not query.count():
        echo.echo("No Gaussian Pseudopotentials found.")
        return

    echo.echo_info("{} Gaussian Pseudopotentials found:\n".format(query.count()))
    echo.echo(_formatted_table_list(pseudo for [pseudo] in query.iterall()))
    echo.echo("")


# fmt: off
@cli.command('dump')
@arguments.DATA(type=DataParamType(sub_classes=("aiida.data:gaussian.pseudo",)))
@click.option('-s', '--sym', type=str, default=None,
              help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None,
              help="filter by name")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@click.option('output_format', '-f', '--format', type=click.Choice(['cp2k', ]), default='cp2k',
              help="Chose the output format for the pseudopotentials: " + ', '.join(['cp2k', ]))
@decorators.with_dbenv()
# fmt: on
def dump_pseudo(sym, name, tags, output_format, data):
    """
    Print specified Pseudopotentials
    """

    from aiida_gaussian_datatypes.pseudopotential.data import Pseudopotential
    from aiida.orm.querybuilder import QueryBuilder

    writers = {
        "cp2k": Pseudopotential.to_cp2k,
    }

    if data:
        # if explicit nodes where given the only thing left is to make sure no filters are present
        if sym or name or tags:
            raise click.UsageError("can not specify node IDs and filters at the same time")
    else:
        query = QueryBuilder()
        query.append(Pseudopotential, project=["*"])

        if sym:
            query.add_filter(Pseudopotential, {"attributes.element": {"==": sym}})

        if name:
            query.add_filter(Pseudopotential, {"attributes.aliases": {"contains": [name]}})

        if tags:
            query.add_filter(Pseudopotential, {"attributes.tags": {"contains": tags}})

        if not query.count():
            echo.echo_warning("No Gaussian Pseudopotential found.", err=echo.is_stdout_redirected())
            return

        data = [pseudo for pseudo, in query.iterall()]  # query always returns a tuple, unpack it here

    for pseudo in data:
        if echo.is_stdout_redirected():
            echo.echo_info("Dumping {}/{} ({})...".format(pseudo.name, pseudo.element, pseudo.uuid), err=True)

        writers[output_format](pseudo, sys.stdout)
