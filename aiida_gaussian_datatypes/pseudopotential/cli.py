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

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.utils import decorators, echo


SUPPORTED_OUTPUT_FORMATS = ['cp2k', ]  # other candidates: 'Abinit', ...


@verdi_data.group('gaussian.pseudo')
def cli():
    """Manage pseudopotentials for GTO-based codes"""
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

    from aiida_gaussian_datatypes.basisset.data import PseudoPotential

    loaders = {
        "cp2k": PseudoPotential.from_cp2k,
        }

    pseudo = loaders[fformat](basisset_file)

    click.confirm("Add a Pseudopotential for '{b.element}' from '{b.id}'?".format(b=pseudo), abort=True)

    pseudo.store()



@cli.command()
@decorators.with_dbenv()
@click.argument('filename', type=click.Path(exists=True))
def upload(filename):
    """
    Upload all pseudopotentials in a file.
    If a pseudo already exists, it is not uploaded.
    Returns the number of pseudos found and the number of uploaded pseudos.
    """

    from aiida_gaussian_datatypes.data.pseudopotential import PseudoPotential as gpp
    n_gpp, n_uploaded = gpp.upload_cp2k_gpp_file(filename)
    echo.echo("Number of pseudos found: {}. Number of new pseudos uploaded: {}".format(n_gpp, n_uploaded))


@cli.command()
@decorators.with_dbenv()
@click.option('-e', '--element', type=str, default=None, help="Element (e.g. H)")
@click.option('ptype', '-t', '--type', type=str, default=None, help="Name or classification (e.g. GTH)")
@click.option('-x', '--xcfct', type=str, default=None, help="Associated xc functional (e.g. PBE)")
@click.option('-n', '--nval', type=int, default=None, help="Number of valence electrons (e.g. 1)")
@click.option('-v', '--version', type=int, default=None, help="specific version")
@click.option('-d', '--default', type=bool, default=True,
              help="show only default pseudos (newest version)", show_default=True)
def list(element, ptype, xcfct, nval, version, default):
    """
    List AiiDa Gaussian pseudopotentials filtered with optional criteria.
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

    row_format_header = "  {:<10} {:<15} {:<20} {:<10} {:<40} {:<10}"
    row_format = '* {:<10} {:<15} {:<20} {:<10} {:<40} {:<10}'
    echo.echo(row_format_header.format("atom type", "pseudo type", "xc functional", "num. el.", "ID", "version"))
    for pseudo in pseudos:
        pseudo_data = dict(pseudo.iterattrs())

        echo.echo(row_format.format(
            pseudo_data['element'],
            pseudo_data['gpp_type'],
            pseudo_data['xc'][0] if pseudo_data['xc'] else '',
            pseudo_data['n_val'],
            pseudo_data['id'][0],
            pseudo_data['version'][0]))

        for i in range(1, len(pseudo_data['id'])):
            echo.echo(row_format.format(
                '',
                '(alias)',
                pseudo_data['xc'][i] if pseudo_data['xc'] else '',
                '',
                pseudo_data['id'][i],
                pseudo_data['version'][i]))


@cli.command()
@decorators.with_dbenv()
@click.argument('filename', type=click.Path(exists=False), required=True)
@click.option('-e', '--element', type=str, default=None, help="Element (e.g. H)")
@click.option('ptype', '-t', '--type', type=str, default=None, help="Name or classification (e.g. GTH)")
@click.option('-x', '--xcfct', type=str, default=None, help="Associated xc functional (e.g. PBE)")
@click.option('-n', '--nval', type=int, default=None, help="Number of valence electrons (e.g. 1)")
@click.option('-v', '--version', type=int, default=None, help="specific version")
@click.option('-d', '--default', type=bool, default=True,
              help="show only default pseudos (newest version)", show_default=True)
def dump(filename, element, ptype, xcfct, nval, version, default):
    """
    Export AiiDa Gaussian pseudopotentials filtered with optional criteria to file.
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
