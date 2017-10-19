import click
import sys

@click.group()
def cli():
    """Command line interface for template plugin"""
    pass

@cli.command()
def list():
    """Display all MultiplyParameters nodes"""
    from aiida import is_dbenv_loaded, load_dbenv
    if not is_dbenv_loaded():
        load_dbenv()

    from aiida.orm.querybuilder import QueryBuilder
    from aiida.orm import DataFactory
    MultiplyParameters = DataFactory('template.factors')

    qb = QueryBuilder()
    qb.append(MultiplyParameters)
    results = qb.all()

    vsep = '\t'

    s = ""
    for result in results:
        obj = result[0]
        s += "{}, pk: {}\n".format(str(obj), obj.pk)
    sys.stdout.write(s)
