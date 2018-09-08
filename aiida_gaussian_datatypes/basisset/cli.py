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
from collections import OrderedDict

import click
import tabulate

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.utils import decorators, echo

@verdi_data.group('gaussian.basisset')
def cli():
    """Manage basis sets for GTO-based codes"""
    pass


@cli.command('import')
@click.argument('basisset_file', type=click.File(mode='r'))
@click.option('fformat', '-f', '--format',
              type=click.Choice(['cp2k', ]), default='cp2k',
              help="the format of the basis set file")
@decorators.with_dbenv()
def import_basisset(basisset_file, fformat):
    """
    Add a basis sets from a file to the database
    """

    from aiida_gaussian_datatypes.basisset.data import BasisSet

    loaders = {
        "cp2k": BasisSet.from_cp2k,
        }

    bset = loaders[fformat](basisset_file)

    click.confirm("Add a Basis Set for '{b.element}' from '{b.id}'?".format(b=bset), abort=True)

    bset.store()


@cli.command('list')
@click.argument('tags', metavar='[TAG] [TAG] [...]', type=str, nargs=-1)
@click.option('-e', '--elements', type=str, default=None,
              help="Filter the families only to those containing a basis set for each of the specified elements")
@decorators.with_dbenv()
def list_basisset(tags, elements):
    """
    List installed gaussian basis sets
    """

    from aiida_gaussian_datatypes.basisset.data import BasisSet
    from aiida.orm.querybuilder import QueryBuilder

    columns = OrderedDict([
            ('ID', 'uuid'),  # the header of the table, the respective property from the DB
            ('Element', 'attributes.element'),
            ('Name', 'attributes.id'),
            ('Aliases', 'attributes.aliases'),
            ('Tags', 'attributes.tags'),
            ])

    query = QueryBuilder()
    query.append(BasisSet, project=list(columns.values()))

    if elements is not None:
        query.add_filter(BasisSet, {'attributes.element': {'in': elements}})

    if not query.count():
        echo.echo("No Gaussian Basis Sets found.")
        return

    def stringify_list(entry):
        if isinstance(entry, list):
            return ", ".join(entry)
        return entry

    entries = [[stringify_list(e) for e in line] for line in query.all()]

    echo.echo_info("{} Gaussian Basis Sets found:\n".format(query.count()))
    echo.echo(tabulate.tabulate(entries, headers=columns.keys()))


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
