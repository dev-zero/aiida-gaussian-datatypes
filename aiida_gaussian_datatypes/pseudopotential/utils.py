# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Pseudopotential helper functions
"""


import re
from itertools import chain

from aiida.common.exceptions import ParsingError


EMPTY_LINE_MATCH = re.compile(r"^(\s*|\s*#.*)$")
BLOCK_MATCH = re.compile(r"^\s*(?P<element>[a-zA-Z]{1,3})\s+(?P<family>\S+).*\n")


def cp2k_pseudo_file_iter(fhandle):
    """
    Generates a sequence of dicts, one dict for each pseudopotential found in the given file

    :param fhandle: Open file handle (in text mode) to a pseudopotential file
    """

    # find the beginning of a new pseudopotential entry, then
    # continue until the next one, the iterator chain and Eof marker guarantee
    # that we find a last (empty) one which will not be parsed.

    current_pseudo = []

    for line in chain(fhandle, ["Eof marker\n"]):
        if EMPTY_LINE_MATCH.match(line):
            # ignore empty and comment lines
            continue

        match = BLOCK_MATCH.match(line)

        if match and current_pseudo:
            try:
                pseudo_data = parse_single_cp2k_pseudo(current_pseudo)
            except Exception as exc:
                raise ParsingError("failed to parse block for '{}': {}".format(current_pseudo[0], exc)) from exc
            yield pseudo_data
            current_pseudo = []

        current_pseudo.append(line.strip())


def parse_single_cp2k_pseudo(lines):
    """
    Parse a single CP2K pseudopotential entry

    :param lines: List of strings where each string is a line from the original file
    :return:      A dictionary containing the element, name, tags, aliases, n_el, local, non_local attributes
    """

    # pylint: disable=too-many-locals

    # the first line contains the element and one or more identifiers/names
    identifiers = lines[0].split()
    element = identifiers.pop(0)

    # put the longest identifier first: some pseudopotential specify the number of
    # valence electrons using <IDENTIFIER>-qN
    identifiers.sort(key=lambda i: -len(i))

    name = identifiers.pop(0)
    tags = name.split("-")  # should we also parse the other identifiers for tags?
    aliases = [name] + identifiers  # use the remaining identifiers as aliases

    # The second line contains the number of electrons for each angular momentum
    n_el = [int(n) for n in lines[1].split()]

    # The third line contains the local part in the format
    #   <radius> <nfuncs> [<func-coeff-1> [<func-coeff-2> ...]]
    r_loc_s, nexp_ppl_s, *cexp_ppl_s = lines[2].split()

    local = {"r": float(r_loc_s), "coeffs": [float(f) for f in cexp_ppl_s]}

    if int(nexp_ppl_s) != len(local["coeffs"]):
        raise ParsingError("less coefficients found than expected while parsing the block")

    nprj = int(lines[3])
    prj_ppnl = []
    nline = 4  # start processing the non-local function blocks (if any) at this line
    while len(prj_ppnl) < nprj:
        try:
            r_nprj_s, nprj_ppnl_s, *hprj_ppnl = lines[nline].split()
        except IndexError:
            raise ParsingError("premature end-of-lines while reading a block of non-local projectors")

        nline += 1

        nprj_ppnl = int(nprj_ppnl_s)
        ncoeffs = nprj_ppnl * (nprj_ppnl + 1) // 2  # number of elements in the upper triangular matrix

        # the matrix may be distributed over multiple lines, add those values as well
        while len(hprj_ppnl) < ncoeffs:
            try:
                hprj_ppnl += lines[nline].split()
            except IndexError:
                raise ParsingError("premature end-of-lines while reading coefficients of non-local projects")
            nline += 1

        if len(hprj_ppnl) > ncoeffs:
            raise ParsingError("unknown format of the non-local projector coefficients")

        prj_ppnl.append(
            {
                "r": float(r_nprj_s),
                "nproj": nprj_ppnl,  # store for convenience
                "coeffs": [float(f) for f in hprj_ppnl],  # upper triangular matrix
            }
        )

    return {
        "element": element,
        "name": name,
        "tags": tags,
        "aliases": aliases,
        "n_el": n_el,
        "local": local,
        "non_local": prj_ppnl,
    }


def write_cp2k_pseudo(
    fhandle, element, name, n_el, local, non_local, fmts=(">#4d", ">#14.8f", "> #14.8f"), comment=""
):  # pylint: disable=too-many-arguments
    """
    Write a Gaussian Pseudopotential to file in CP2K format.

    :param fhandle: A valid output file handle
    :param element: Atomic symbol of the passed-in data
    :param name: Name for this entry
    :param n_el: List of number of valence electrons per angular momentum

    :param fmts: Tuple of Python format strings: (integers, radii, coefficients)
    """

    # pylint: disable=too-many-locals

    i_fmt, r_fmt, c_fmt = fmts

    fhandle.write(f"# {comment}\n")

    fhandle.write(f"{element} {name}\n")
    fhandle.write(" ".join(f"{i:{i_fmt}}" for i in n_el))
    fhandle.write("\n")

    fhandle.write(f"{local['r']:{r_fmt}} {len(local['coeffs']):{i_fmt}} ")
    fhandle.write(" ".join(f"{c:{c_fmt}}" for c in local["coeffs"]))
    fhandle.write("\n")

    fhandle.write(f"{len(non_local):{i_fmt}}\n")

    single_c_len = len("{0:{c_fmt}}".format(0, c_fmt=c_fmt))

    for nonl in non_local:
        r_nproj = f"{nonl['r']:{r_fmt}} {nonl['nproj']:{i_fmt}} "
        fhandle.write(r_nproj)

        nlcoeffs = nonl["coeffs"]
        nproj = nonl["nproj"]

        # print the first N (=nproj) coefficients (first row of the matrix)
        fhandle.write(" ".join(f"{c:{c_fmt}}" for c in nlcoeffs[:nproj]))
        fhandle.write("\n")

        # for a non-scalar non-empty matrix, print the rest of the coefficients
        for nrow in range(1, nonl["nproj"]):
            fhandle.write(" " * (len(r_nproj) + nrow * (1 + single_c_len)))
            scol = nrow * nproj - nrow * (nrow - 1) // 2
            ecol = scol + nproj - nrow
            fhandle.write(" ".join(f"{c:{c_fmt}}" for c in nlcoeffs[scol:ecol]))
            fhandle.write("\n")
