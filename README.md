# AiiDA Gaussian Data Plugin

[![tests](https://github.com/dev-zero/aiida-gaussian-datatypes/workflows/tests/badge.svg)](https://github.com/dev-zero/aiida-gaussian-datatypes/actions) [![codecov](https://codecov.io/gh/dev-zero/aiida-gaussian-datatypes/branch/develop/graph/badge.svg)](https://codecov.io/gh/dev-zero/aiida-gaussian-datatypes) [![PyPI](https://img.shields.io/pypi/pyversions/aiida-gaussian-datatypes)](https://pypi.org/project/aiida-gaussian-datatypes/)


Plugin to handle GTO-based basis sets and pseudopotentials and manage them as first-class citizens in AiiDA.

## Commandline usage

After the installation, you will get new commands in `verdi data`

```console
$ verdi data
Usage: verdi data [OPTIONS] COMMAND [ARGS]...

  Inspect, create and manage data nodes.

Options:
  -h, --help  Show this message and exit.

Commands:
  array              Manipulate ArrayData objects.
  bands              Manipulate BandsData objects.
  cif                Manipulation of CIF data objects.
  parameter          View and manipulate Dict objects.
  plugins            Print a list of registered data plugins or details of
                     a...
  remote             Managing RemoteData objects.
  structure          Manipulation of StructureData objects.
  trajectory         View and manipulate TrajectoryData instances.
  upf                Manipulation of the upf families.
  gaussian.basisset  Manage basis sets for GTO-based codes
  gaussian.pseudo    Manage Pseudopotentials for GTO-based codes

$ verdi data gaussian.basisset
Usage: verdi data gaussian.basisset [OPTIONS] COMMAND [ARGS]...

  Manage basis sets for GTO-based codes

Options:
  -h, --help  Show this message and exit.

Commands:
  dump    Print specified Basis Sets
  import  Add a basis sets from a file to the database
  list    List Gaussian Basis Sets

$ verdi data gaussian.pseudo
Usage: verdi data gaussian.pseudo [OPTIONS] COMMAND [ARGS]...

  Manage Pseudopotentials for GTO-based codes

Options:
  -h, --help  Show this message and exit.

Commands:
  dump    Print specified Pseudopotential
  import  Add a pseudopotential from a file to the database
  list    List Gaussian Pseudopotentials
```

## Examples

### Import and use Basis Set from CP2K

To import a specific basis set from a file with basis sets in CP2K's native format, simply use:

```console
$ verdi data gaussian.basisset import --sym He data/BASIS_MOLOPT
Info: 2 Gaussian Basis Sets found:

  Nr.  Sym    Names                                      Tags                         # Val. e⁻    Version
-----  -----  -----------------------------------------  -------------------------  -----------  ---------
    1  He     SZV-MOLOPT-SR-GTH-q2, SZV-MOLOPT-SR-GTH    SZV, MOLOPT, SR, GTH, q2             2          1
    2  He     DZVP-MOLOPT-SR-GTH-q2, DZVP-MOLOPT-SR-GTH  DZVP, MOLOPT, SR, GTH, q2            2          1

Which Gaussian Basis Set do you want to add? ('n' for none, 'a' for all, comma-seperated list or range of numbers): 2
Info: Adding Gaussian Basis Set for: He (DZVP-MOLOPT-SR-GTH-q2)... DONE

$ verdi data gaussian.basisset list
Info: 1 Gaussian Basis Sets found:

ID                                    Sym    Names                                      Tags                       # Val. e⁻      Version
------------------------------------  -----  -----------------------------------------  -------------------------  -----------  ---------
4a173d43-b022-4e1e-aca9-c4db51da223b  He     DZVP-MOLOPT-SR-GTH-q2, DZVP-MOLOPT-SR-GTH  DZVP, MOLOPT, SR, GTH, q2  2                    1
```

Notes:

* The command line argument `--sym He` is optional (leaving it away will simply show all available entries)
* The plugin automatically filters already imported basis sets

To reference this in a `verdi` script, you can use the following snippet:

```python
from aiida.plugins import DataFactory

BasisSet = DataFactory('gaussian.basisset')

basis_He = BasisSet.get(element="He", name="DZVP-MOLOPT-SR-GTH")

# the generic way using BasisSet.objects.find(...) works too, of course
```

Notes:

* You don't have to specify the full name (`DZVP-MOLOPT-SR-GTH-q2`), the shorter name (`DZVP-MOLOPT-SR-GTH`) also works

### Import and use Pseudopotential from CP2K

To import a specific pseudopotential from a file with pseudopotentials in CP2K's native format, simply use:

```console
$ verdi data gaussian.pseudo import --sym He data/GTH_POTENTIALS
Info: 4 Gaussian Pseudopotentials found:

  Nr.  Sym    Names                                       Tags           Val. e⁻ (s, p, d)      Version
-----  -----  ------------------------------------------  -------------  -------------------  ---------
    1  He     GTH-BLYP-q2, GTH-BLYP                       GTH, BLYP, q2  2, 0, 0                      1
    2  He     GTH-BP-q2, GTH-BP                           GTH, BP, q2    2, 0, 0                      1
    3  He     GTH-PADE-q2, GTH-LDA-q2, GTH-PADE, GTH-LDA  GTH, PADE, q2  2, 0, 0                      1
    4  He     GTH-PBE-q2, GTH-PBE                         GTH, PBE, q2   2, 0, 0                      1

Which Gaussian Pseudopotentials do you want to add? ('n' for none, 'a' for all, comma-seperated list or range of numbers): 4
Info: Adding Gaussian Pseudopotentials for: He (GTH-PBE-q2)... DONE

$ verdi data gaussian.pseudo list
Info: 1 Gaussian Pseudopotential found:

ID                                    Sym    Names                                         Tags            Val. e⁻ (s, p, d)      Version
------------------------------------  -----  --------------------------------------------  --------------  -------------------  ---------
5838b0b7-336a-4b97-b76a-e5c42a4e98ac  He     GTH-PBE-q2, GTH-PBE                           GTH, PBE, q2    2, 0, 0                      1
```

Notes:

* The command line argument `--sym He` is optional (leaving it away will simply show all available entries)
* The plugin automatically filters already imported basis sets

To reference this in a `verdi` script, you can use the following snippet:

```python
from aiida.plugins import DataFactory

Pseudopotential = DataFactory('gaussian.pseudo')

pseudo_He = Pseudopotential.get(element="He", name="GTH-PBE")

# the generic way using Pseudopotential.objects.find(...) works too, of course
```

Notes:

* You don't have to specify the full name (`GTH-PBE-q2`), the shorter name (`GTH-PBE`) also works
