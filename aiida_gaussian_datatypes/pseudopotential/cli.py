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

import click
import tabulate

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.utils import decorators, echo

from ..utils import click_parse_range


SUPPORTED_OUTPUT_FORMATS = ['cp2k', ]  # other candidates: 'Abinit', ...


def _formatted_table(pseudos):
    """generates a formatted table (using tabulate) for the given list of Pseudopotentials"""

    def names_column(name, aliases):
        return ', '.join(["\033[1m{}\033[0m".format(name), *[a for a in aliases if a != name]])

    table_content = [(n+1, p.element, names_column(p.name, p.aliases), ', '.join(p.tags), ', '.join(str(n) for n in p.n_el), p.version)
                     for n, p in enumerate(pseudos)]
    return tabulate.tabulate(table_content, headers=['Nr.', 'Sym', 'Names', 'Tags', 'Valence e⁻ (s, p, d)', 'Version'])


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

    pseudos = loaders[fformat](pseudopotential_file)

    if not pseudos:
        echo.echo_info("No valid Gaussian Pseudopotentials found in the given file matching the given criteria")
        return

    if len(pseudos) == 1:
        pseudo = pseudos[0]
        click.confirm("Add a Gaussian '{p.gpp_type}' Pseudopotential for '{p.element}'?".format(p=pseudo), abort=True)
        pseudo.store()
        return

    echo.echo_info("{} Gaussian Pseudopotentials found:\n".format(len(pseudos)))
    echo.echo(_formatted_table(pseudos))
    echo.echo("")

    indexes = click.prompt("Which Gaussian Pseudopotentials do you want to add?"
                           " ('n' for none, 'a' for all, comma-seperated list or range of numbers)",
                           value_proc=lambda v: click_parse_range(v, len(pseudos)))

    for idx in indexes:
        echo.echo_info("Adding Gaussian Pseudopotentials for: {p.element} ({p.name})... ".format(p=pseudos[idx]), nl=False)
        pseudos[idx].store()
        echo.echo("DONE")


@cli.command('list')
@decorators.with_dbenv()
@click.option('-s', '--sym', type=str, default=None, help="filter by atomic symbol")
@click.option('ptype', '-t', '--type', type=str, default=None, help="Name or classification (e.g. GTH)")
@click.option('-x', '--xcfunc', type=str, default=None, help="Associated XC functional (e.g. PBE)")
@click.option('-n', '--nval', type=int, default=None, help="Number of valence electrons (e.g. 1)")
@click.option('-v', '--version', type=int, default=None, help="Specific version")
@click.option('-d', '--default', type=bool, default=True,
              help="show only default pseudos (newest version)", show_default=True)
def list_pseudos(sym, ptype, xcfunc, nval, version, default):
    """
    List Gaussian Pseudopotentials
    """
    from aiida_gaussian_datatypes.pseudopotential.data import Pseudopotential
    from aiida.orm.querybuilder import QueryBuilder

    query = QueryBuilder()
    query.append(Pseudopotential)

    if sym:
        query.add_filter(Pseudopotential, {'attributes.element': {'==': sym}})

    if ptype:
        query.add_filter(Pseudopotential, {'attributes.gpp_ptype': {'==': ptype}})

    if xcfunc:
        pass
        #query.add_filter(Pseudopotential, {'attributes.element': {'startswith': ptype}})

    if nval:
        pass

    if version:
        pass

    if not query.count():
        echo.echo("No Gaussian Pseudopotential found.")
        return

    echo.echo_info("{} Gaussian Pseudopotential found:\n".format(query.count()))
    echo.echo(_formatted_table([pseudo for [pseudo] in query.iterall()]))
    echo.echo("")


@cli.command('dump')
@decorators.with_dbenv()
@click.argument('filename', type=click.Path(exists=False), required=True)
@click.option('-e', '--element', type=str, default=None, help="Element (e.g. H)")
@click.option('ptype', '-t', '--type', type=str, default=None, help="Name or classification (e.g. GTH)")
@click.option('-x', '--xcfct', type=str, default=None, help="Associated xc functional (e.g. PBE)")
@click.option('-n', '--nval', type=int, default=None, help="Number of valence electrons (e.g. 1)")
@click.option('-v', '--version', type=int, default=None, help="specific version")
@click.option('-d', '--default', type=bool, default=True,
              help="show only default pseudos (newest version)", show_default=True)
def dump_pseudo(filename, element, ptype, xcfct, nval, version, default):
    """
    Export AiiDa Gaussian Pseudopotential filtered with optional criteria to file.
    """

    from aiida.orm import DataFactory

    pseudo = DataFactory('gaussian.pseudo')
    pseudos = pseudo.get_pseudos(
        element=element,
        gpp_type=ptype,
        xc=xcfct,
        n_val=nval,
        version=version,
        default=default)

    for pseudo in pseudos:
        pseudo.write_cp2k_gpp_to_file(filename, mode='a')
