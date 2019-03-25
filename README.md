# AiiDA Gaussian Data Plugin

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
