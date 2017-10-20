import click

from aiida.cmdline.commands import data_plug


SUPPORTED_OUTPUT_FORMATS = ['cp2k', ]  # other candidates: 'gaussian', 'gamess', 'nwchem'


@data_plug.group('gaussian-basisset')
def cli():
    """Command line interface for managing gaussian basissets"""
    pass


@cli.command()
@cli.argument('filename', type=click.Path(exists=True))
def upload(filename):
    """
    Upload all pseudopotentials in a file.
    If a pseudo already exists, it is not uploaded.
    Returns the number of pseudos found and the number of uploaded pseudos.
    """

    from aiida import try_load_dbenv
    try_load_dbenv()

    from aiida_gaussian_datatypes.data.pseudopotential import PseudoPotential as gpp
    n_gpp, n_uploaded = gpp.upload_cp2k_gpp_file(filename)
    click.echo("Number of pseudos found: {}. Number of new pseudos uploaded: {}".format(n_gpp, n_uploaded))


@cli.command()
@cli.option('-e', '--element', type=str, default=None, help="Element (e.g. H)")
@cli.option('ptype', '-t', '--type', type=str, default=None, help="Name or classification (e.g. GTH)")
@cli.option('-x', '--xcfct', type=str, default=None, help="Associated xc functional (e.g. PBE)")
@cli.option('-n', '--nval', type=int, default=None, help="Number of valence electrons (e.g. 1)")
@cli.option('-v', '--version', type=int, default=None, help="specific version")
@cli.option('-d', '--default', type=bool, default=True,
            help="show only default pseudos (newest version)", show_defaults=True)
def list(element, ptype, xcfct, nval, version, default):
    """
    List AiiDa Gaussian pseudopotentials filtered with optional criteria.
    """
    from aiida import try_load_dbenv
    try_load_dbenv()

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
    click.echo(row_format_header.format("atom type", "pseudo type", "xc functional", "num. el.", "ID", "version"))
    for pseudo in pseudos:
        pseudo_data = dict(pseudo.iterattrs())

        click.echo(row_format.format(
            pseudo_data['element'],
            pseudo_data['gpp_type'],
            pseudo_data['xc'][0] if pseudo_data['xc'] else '',
            pseudo_data['n_val'],
            pseudo_data['id'][0],
            pseudo_data['version'][0]))

        for i in range(1, len(pseudo_data['id'])):
            click.echo(row_format.format(
                '',
                '(alias)',
                pseudo_data['xc'][i] if pseudo_data['xc'] else '',
                '',
                pseudo_data['id'][i],
                pseudo_data['version'][i]))


@cli.command()
@cli.argument('filename', type=click.Path(exists=False), required=True)
@cli.option('-e', '--element', type=str, default=None, help="Element (e.g. H)")
@cli.option('ptype', '-t', '--type', type=str, default=None, help="Name or classification (e.g. GTH)")
@cli.option('-x', '--xcfct', type=str, default=None, help="Associated xc functional (e.g. PBE)")
@cli.option('-n', '--nval', type=int, default=None, help="Number of valence electrons (e.g. 1)")
@cli.option('-v', '--version', type=int, default=None, help="specific version")
@cli.option('-d', '--default', type=bool, default=True,
            help="show only default pseudos (newest version)", show_defaults=True)
def dump(filename, element, ptype, xcfct, nval, version, default):
    """
    Export AiiDa Gaussian pseudopotentials filtered with optional criteria to file.
    """
    from aiida import try_load_dbenv
    try_load_dbenv()

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
