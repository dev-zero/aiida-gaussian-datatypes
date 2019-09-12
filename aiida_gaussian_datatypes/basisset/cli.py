# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Basis Set verdi command line interface
"""

import sys

import click
import tabulate

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.utils import decorators, echo
from aiida.cmdline.params import arguments
from aiida.cmdline.params.types import DataParamType

from ..utils import click_parse_range


def _names_column(name, aliases):
    return ", ".join(["\033[1m{}\033[0m".format(name), *[a for a in aliases if a != name]])


def _formatted_table_import(bsets):
    """generates a formatted table (using tabulate) for the given list of basis sets, shows a sequencial number"""

    def row(num, bset):
        return (
            num + 1,
            bset.element,
            _names_column(bset.name, bset.aliases),
            ", ".join(bset.tags),
            bset.n_el if bset.n_el else "<unknown>",
            bset.version,
        )

    table_content = [row(n, b) for n, b in enumerate(bsets)]
    return tabulate.tabulate(table_content, headers=["Nr.", "Sym", "Names", "Tags", "# Val. e⁻", "Version"])


def _formatted_table_list(bsets):
    """generates a formatted table (using tabulate) for the given list of basis sets, shows the UUID"""

    def row(bset):
        return (
            bset.uuid,
            bset.element,
            _names_column(bset.name, bset.aliases),
            ", ".join(bset.tags),
            bset.n_el if bset.n_el else "<unknown>",
            bset.version,
        )

    table_content = [row(b) for b in bsets]
    return tabulate.tabulate(table_content, headers=["ID", "Sym", "Names", "Tags", "# Val. e⁻", "Version"])


@verdi_data.group("gaussian.basisset")
def cli():
    """Manage basis sets for GTO-based codes"""


# fmt: off
@cli.command('import')
@click.argument('basisset_file', type=click.File(mode='r'))
@click.option('--sym', '-s', help="filter by atomic symbol")
@click.option(
    'tags', '--tag', '-t',
    multiple=True,
    help="filter by a tag (all tags must be present if specified multiple times)")
@click.option(
    'fformat', '-f', '--format', type=click.Choice(['cp2k']), default='cp2k',
    help="the format of the basis set file")
@click.option(
    '--duplicates',
    type=click.Choice(['ignore', 'error', 'new']), default='ignore',
    help="Whether duplicates should be ignored, produce an error or uploaded as new version")
# fmt: on
@decorators.with_dbenv()
def import_basisset(basisset_file, fformat, sym, tags, duplicates):
    """
    Add a basis sets from a file to the database
    """

    from aiida_gaussian_datatypes.basisset.data import BasisSet

    loaders = {
        "cp2k": BasisSet.from_cp2k,
    }

    filters = {
        'element': lambda x: not sym or x == sym,
        'tags': lambda x: not tags or set(tags).issubset(x),
    }

    bsets = loaders[fformat](basisset_file, filters, duplicates)

    if not bsets:
        echo.echo_info("No valid Gaussian Basis Sets found in the given file matching the given criteria")
        return

    if len(bsets) == 1:
        bset = bsets[0]
        click.confirm("Add a Gaussian Basis Set for '{b.element}' from '{b.name}'?".format(b=bset), abort=True)
        bset.store()
        return

    echo.echo_info("{} Gaussian Basis Sets found:\n".format(len(bsets)))
    echo.echo(_formatted_table_import(bsets))
    echo.echo("")

    indexes = click.prompt(
        "Which Gaussian Basis Set do you want to add?"
        " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
        value_proc=lambda v: click_parse_range(v, len(bsets)))

    for idx in indexes:
        echo.echo_info("Adding Gaussian Basis Set for: {b.element} ({b.name})... ".format(b=bsets[idx]), nl=False)
        bsets[idx].store()
        echo.echo("DONE")


@cli.command('list')
@click.option('-s', '--sym', type=str, default=None, help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None, help="filter by name")
@click.option(
    'tags', '--tag', '-t', multiple=True, help="filter by a tag (all tags must be present if specified multiple times)")
@decorators.with_dbenv()
def list_basisset(sym, name, tags):
    """
    List Gaussian Basis Sets
    """

    from aiida_gaussian_datatypes.basisset.data import BasisSet
    from aiida.orm.querybuilder import QueryBuilder

    query = QueryBuilder()
    query.append(BasisSet)

    if sym:
        query.add_filter(BasisSet, {'attributes.element': {'==': sym}})

    if name:
        query.add_filter(BasisSet, {'attributes.aliases': {'contains': [name]}})

    if tags:
        query.add_filter(BasisSet, {'attributes.tags': {'contains': tags}})

    if not query.count():
        echo.echo("No Gaussian Basis Sets found.")
        return

    echo.echo_info("{} Gaussian Basis Sets found:\n".format(query.count()))
    echo.echo(_formatted_table_list(bs for [bs] in query.iterall()))
    echo.echo("")


# fmt: off
@cli.command('dump')
@arguments.DATA(type=DataParamType(sub_classes=("aiida.data:gaussian.basisset",)))
@click.option('-s', '--sym', type=str, default=None,
              help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None,
              help="filter by name")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@click.option('output_format', '-f', '--format', type=click.Choice(['cp2k', ]), default='cp2k',
              help="Chose the output format for the basiset: " + ', '.join(['cp2k', ]))
# fmt: on
@decorators.with_dbenv()
def dump_basisset(sym, name, tags, output_format, data):
    """
    Print specified Basis Sets
    """

    from aiida_gaussian_datatypes.basisset.data import BasisSet
    from aiida.orm.querybuilder import QueryBuilder

    writers = {
        "cp2k": BasisSet.to_cp2k,
    }

    if data:
        # if explicit nodes where given the only thing left is to make sure no filters are present
        if sym or name or tags:
            raise click.UsageError("can not specify node IDs and filters at the same time")
    else:
        query = QueryBuilder()
        query.append(BasisSet, project=['*'])

        if sym:
            query.add_filter(BasisSet, {'attributes.element': {'==': sym}})

        if name:
            query.add_filter(BasisSet, {'attributes.aliases': {'contains': [name]}})

        if tags:
            query.add_filter(BasisSet, {'attributes.tags': {'contains': tags}})

        if not query.count():
            echo.echo_warning("No Gaussian Basis Sets found.", err=echo.is_stdout_redirected())
            return

        data = [bset for bset, in query.iterall()]  # query always returns a tuple, unpack it here

    for bset in data:
        if echo.is_stdout_redirected():
            echo.echo_info("Dumping {}/{} ({})...".format(bset.name, bset.element, bset.uuid), err=True)

        writers[output_format](bset, sys.stdout)
