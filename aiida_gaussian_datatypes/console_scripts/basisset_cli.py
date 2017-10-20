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
    Upload basis sets from a file
    """

    from aiida import try_load_dbenv
    try_load_dbenv()

    from aiida_gaussian_datatypes.data.basisset import upload_cp2k_basissetfile
    upload_cp2k_basissetfile(filename)


@cli.command()
@cli.argument('tags', type=str, nargs=-1, required=True)
@cli.option('-e', '--element', type=str, default=None,
            help=("Filter the families only to those containing a basis set for each of the specified elements"))
def list(tags, element):
    """
    Print on screen the list of gaussian basissets installed
    """

    from aiida import try_load_dbenv
    try_load_dbenv()

    from aiida_gaussian_datatypes.data.basisset import BasisSet
    basissets = BasisSet.get_basis_sets(filter_elements=element, filter_tags=tags)

    for basisset in basissets:
        click.echo("Found a basis set for the element {} of type {}".format(basisset.element, ", ".join(basisset.tags)))


@cli.command()
@cli.argument('tags', type=str, nargs=-1, required=True)
@cli.option('-e', '--element', type=str, default=None,
            help=("Filter the families only to those containing a basis set for each of the specified elements"))
@cli.optino('output_format', '-f', '--format', type=click.Choice(SUPPORTED_OUTPUT_FORMATS), default='cp2k',
            help="Chose the output format for the basiset: " + ', '.join(SUPPORTED_OUTPUT_FORMATS))
def dump(tags, element, output_format):
    """
    Print on screen a given basiset
    """
    from aiida import try_load_dbenv
    try_load_dbenv()

    from aiida_gaussian_datatypes.data.basisset import BasisSet
    basissets = BasisSet.get_basis_sets(filter_elements=element, filter_tags=tags)

    for basisset in basissets:
        if output_format == 'cp2k':
            basisset.print_cp2k()
