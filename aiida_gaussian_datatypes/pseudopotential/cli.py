# -*- coding: utf-8 -*-
"""
Gaussian Pseudopotential verdi command line interface

Copyright (c), Tiziano Müller

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

from ..utils import click_parse_range


def _formatted_table(pseudos):
    """generates a formatted table (using tabulate) for the given list of Pseudopotentials"""

    def names_column(name, aliases):
        return ', '.join(["\033[1m{}\033[0m".format(name), *[a for a in aliases if a != name]])

    def row(num, pseudo):
        return (
            num+1,
            pseudo.element,
            names_column(pseudo.name, pseudo.aliases),
            ', '.join(pseudo.tags),
            ', '.join(f"{n}" for n in pseudo.n_el + (3-len(pseudo.n_el))*[0]),
            pseudo.version,
            )

    table_content = [row(n, p) for n, p in enumerate(pseudos)]
    return tabulate.tabulate(table_content, headers=['Nr.', 'Sym', 'Names', 'Tags', 'Val. e⁻ (s, p, d)', 'Version'])


@verdi_data.group('gaussian.pseudo')
def cli():
    """Manage Pseudopotentials for GTO-based codes"""
    pass


@cli.command('import')
@click.argument('pseudopotential_file', type=click.File(mode='r'))
@click.option('--sym', '-s', help="filter by atomic symbol")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@click.option('fformat', '-f', '--format',
              type=click.Choice(['cp2k', ]), default='cp2k',
              help="the format of the pseudopotential file")
@click.option('--duplicates', type=click.Choice(['ignore', 'error', 'new']), default='ignore',
              help="Whether duplicates should be ignored, produce an error or uploaded as new version")
@decorators.with_dbenv()
def import_pseudopotential(pseudopotential_file, fformat, sym, tags, duplicates):
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
    echo.echo(_formatted_table(pseudos))
    echo.echo("")

    indexes = click.prompt("Which Gaussian Pseudopotentials do you want to add?"
                           " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
                           value_proc=lambda v: click_parse_range(v, len(pseudos)))

    for idx in indexes:
        echo.echo_info("Adding Gaussian Pseudopotentials for: {p.element} ({p.name})... ".format(p=pseudos[idx]),
                       nl=False)
        pseudos[idx].store()
        echo.echo("DONE")


@cli.command('list')
@click.option('-s', '--sym', type=str, default=None,
              help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None,
              help="filter by name")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@decorators.with_dbenv()
def list_pseudos(sym, name, tags):
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

    echo.echo_info("{} Gaussian Pseudopotential founds:\n".format(query.count()))
    echo.echo(_formatted_table([pseudo for [pseudo] in query.iterall()]))
    echo.echo("")


@cli.command('dump')
@click.option('-s', '--sym', type=str, default=None,
              help="filter by a specific element")
@click.option('-n', '--name', type=str, default=None,
              help="filter by name")
@click.option('tags', '--tag', '-t', multiple=True,
              help="filter by a tag (all tags must be present if specified multiple times)")
@click.option('output_format', '-f', '--format', type=click.Choice(['cp2k', ]), default='cp2k',
              help="Chose the output format for the pseudopotentials: " + ', '.join(['cp2k', ]))
@decorators.with_dbenv()
def dump_pseudo(sym, name, tags, output_format):
    """
    Print specified Pseudopotential
    """

    from aiida_gaussian_datatypes.pseudopotential.data import Pseudopotential
    from aiida.orm.querybuilder import QueryBuilder

    writers = {
        "cp2k": Pseudopotential.to_cp2k,
        }

    query = QueryBuilder()
    query.append(Pseudopotential,
                 project=['uuid', 'attributes.id', 'attributes.element', '*'])

    if sym:
        query.add_filter(Pseudopotential, {'attributes.element': {'==': sym}})

    if name:
        query.add_filter(Pseudopotential, {'attributes.aliases': {'contains': [name]}})

    if tags:
        query.add_filter(Pseudopotential, {'attributes.tags': {'contains': tags}})

    if not query.count():
        echo.echo_warning("No Gaussian Pseudopotential found.", err=echo.is_stdout_redirected())
        return

    for uuid, name, element, pseudo in query.iterall():
        if echo.is_stdout_redirected():
            echo.echo_info("Dumping {}/{} ({})...".format(name, element, uuid), err=True)

        writers[output_format](pseudo, sys.stdout)
