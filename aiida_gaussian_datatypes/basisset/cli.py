# -*- coding: utf-8 -*-
"""
Gaussian Basis Set verdi command line interface

Copyright (c), 2018 Tiziano Müller

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys

import click
import tabulate

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.utils import decorators, echo


def _formatted_table(bsets):
    """generates a formatted table (using tabulate) for the given list of basis sets"""

    def names_column(name, aliases):
        return ', '.join(["\033[1m{}\033[0m".format(name), *[a for a in aliases if a != name]])

    table_content = [(n+1, b.element, names_column(b.name, b.aliases), ', '.join(b.tags), b.version)
                     for n, b in enumerate(bsets)]
    return tabulate.tabulate(table_content, headers=['Nr.', 'Sym', 'Names', 'Tags', 'Version'])


@verdi_data.group('gaussian.basisset')
def cli():
    """Manage basis sets for GTO-based codes"""
    pass


@cli.command('import')
@click.argument('basisset_file', type=click.File(mode='r'))
@click.option('--sym', '-s', help="filter by atomic symbol")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@click.option('fformat', '-f', '--format',
              type=click.Choice(['cp2k', ]), default='cp2k',
              help="the format of the basis set file")
@click.option('--duplicates', type=click.Choice(['ignore', 'error', 'new']), default='ignore',
              help="Whether duplicates should be ignored, produce an error or uploaded as new version")
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
    echo.echo(_formatted_table(bsets))
    echo.echo("")

    def parse_range(value):
        """value_proc function to convert the given input to a list of indexes"""
        if value.startswith('a'):
            return range(len(bsets))

        if value.startswith('n'):
            return []

        indexes = []

        try:
            for spec in value.replace(' \t', '').split(','):
                try:
                    begin, end = spec.split('-')
                except ValueError:
                    indexes.append(int(spec) - 1)
                else:
                    indexes += list(range(int(begin) - 1, int(end)))

        except ValueError:
            raise click.BadParameter("Invalid range or value specified", param=value)

        if max(indexes) >= len(bsets):
            raise click.BadParameter("Specified index is out of range", param=max(indexes))

        return sorted(set(indexes))

    indexes = click.prompt("Which Gaussian Basis Set do you want to add?"
                           " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
                           value_proc=parse_range)

    for idx in indexes:
        echo.echo_info("Adding Gaussian Basis Set for: {b.element} ({b.name})... ".format(b=bsets[idx]), nl=False)
        bsets[idx].store()
        echo.echo("DONE")


@cli.command('list')
@click.option('-s', '--sym', type=str, default=None,
              help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None,
              help="filter by name")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@decorators.with_dbenv()
def list_basisset(sym, name, tags):
    """
    List installed gaussian basis sets
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
    echo.echo(_formatted_table([bs for [bs] in query.iterall()]))
    echo.echo("")


@cli.command('dump')
@click.option('-e', '--elements', type=str, default=None,
              help=("Filter the families only to those containing a basis set for each of the specified elements"))
@click.option('output_format', '-f', '--format', type=click.Choice(['cp2k', ]), default='cp2k',
              help="Chose the output format for the basiset: " + ', '.join(['cp2k', ]))
@decorators.with_dbenv()
def dump_basisset(elements, output_format):
    """
    Print specified Basis Sets
    """

    from aiida_gaussian_datatypes.basisset.data import BasisSet
    from aiida.orm.querybuilder import QueryBuilder

    writers = {
        "cp2k": BasisSet.to_cp2k,
        }

    query = QueryBuilder()
    query.append(BasisSet,
                 project=['uuid', 'attributes.id', 'attributes.element', '*'])

    if elements is not None:
        query.add_filter(BasisSet, {'attributes.element': {'in': elements}})

    if not query.count():
        echo.echo_warning("No Gaussian Basis Sets found.", err=echo.is_stdout_redirected())
        return

    for uuid, name, element, bset in query.iterall():
        if echo.is_stdout_redirected():
            echo.echo_info("Dumping {}/{} ({})...".format(name, element, uuid), err=True)

        writers[output_format](bset, sys.stdout)
