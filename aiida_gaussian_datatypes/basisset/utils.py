# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Gaussian Basis Set helper functions
"""

import re

from ..utils import SYM2NUM


EMPTY_LINE_MATCH = re.compile(r"^(\s*|\s*#.*)$")
BLOCK_MATCH = re.compile(r"^\s*(?P<element>[a-zA-Z]{1,3})\s+(?P<family>\S+).*\n")
N_VAL_EL_MATCH = re.compile(r"^q(\d+)$")


def write_cp2k_basisset(
    fhandle, element, name, blocks, fmts=(">#18.12f", "> #14.12f"), comment=""
):  # pylint: disable=too-many-arguments
    """
    Write the Basis Set to the passed file handle in the format expected by CP2K.

    :param fhandle: A valid output file handle
    :param element: Atomic symbol of the passed-in data
    :param name: Name for this entry
    :param blocks: The actual basis set data
    :param fmts: Tuple of Python format strings, the first one for the exponents, the second for the coefficients
    """

    fhandle.write(f"# {comment}\n")

    fhandle.write(f"{element} {name}\n" f"{len(blocks)}\n")  # the number of sets this basis set contains

    e_fmt, c_fmt = fmts

    for block in blocks:
        fhandle.write(
            "{n} {lmin} {lmax} {nexp} ".format(
                n=block["n"], lmin=block["l"][0][0], lmax=block["l"][-1][0], nexp=len(block["coefficients"])
            )
        )
        fhandle.write(" ".join(str(lqn[1]) for lqn in block["l"]))
        fhandle.write("\n")

        for row in block["coefficients"]:
            fhandle.write(f"{row[0]:{e_fmt}}")
            fhandle.write(" ")
            fhandle.write(" ".join(f"{f:{c_fmt}}" for f in row[1:]))
            fhandle.write("\n")


def cp2k_basisset_file_iter(fhandle):
    """
    Generates a sequence of dicts, one dict for each basis set found in the given file

    :param fhandle: Open file handle (in text mode) to a basis set file
    """

    # find the beginning of a new basis set entry, then
    # continue until the next one or the EOF

    current_basis = []

    for line in fhandle:
        if EMPTY_LINE_MATCH.match(line):
            # ignore empty and comment lines
            continue

        match = BLOCK_MATCH.match(line)

        if match and current_basis:
            yield parse_single_cp2k_basisset(current_basis)
            current_basis = []

        current_basis.append(line.strip())

    # EOF and we still have lines belonging to a basis set
    if current_basis:
        yield parse_single_cp2k_basisset(current_basis)


def parse_single_cp2k_basisset(basis):
    """
    :param basis: A list of strings, where each string contains a line read from the basis set file.
                  The list must one single basis set.
    :return:      A dictionary containing the element, name, tags, aliases, orbital_quantum_numbers, coefficients
    """

    # pylint: disable=too-many-locals

    # the first line contains the element and one or more identifiers/names
    identifiers = basis[0].split()
    element = identifiers.pop(0)

    # put the longest identifier first: some basis sets specify the number of
    # valence electrons using <IDENTIFIER>-qN
    identifiers.sort(key=lambda i: -len(i))

    name = identifiers.pop(0)
    tags = name.split("-")
    aliases = [name] + identifiers  # use the remaining identifiers as aliases

    n_el = None

    for tag in tags:
        match = N_VAL_EL_MATCH.match(tag)

        if not match:
            continue

        if not n_el:
            n_el = int(match.group(1))
            continue  # go to next to check for multiple tags

        if n_el != int(match.group(1)):
            # found multiple different #(Val.El.) tags, ignore all of them
            n_el = None
            break  # and terminate the loop

    # the ALL* tags indicate an all-electron basis set, but they might be ambigious,
    # ignore them if we found an explicit #(val.el.) spec already
    if not n_el and any(kw in tags for kw in ["ALL", "ALLELECTRON"]):
        n_el = SYM2NUM[element]

    # The second line contains the number of sets, conversion to int ignores any whitespace
    n_blocks = int(basis[1])

    nline = 2

    blocks = []

    # go through all blocks containing different sets of orbitals
    for _ in range(n_blocks):
        # get the quantum numbers for this set, formatted as follows:
        # n lmin lmax nexp nshell(lmin) nshell(lmin+1) ... nshell(lmax-1) nshell(lmax)
        qn_n, qn_lmin, qn_lmax, nexp, *ncoeffs = [int(qn) for qn in basis[nline].split()]

        nline += 1

        blocks.append(
            {
                "n": qn_n,
                "l": [(lqn, nl) for lqn, nl in zip(range(qn_lmin, qn_lmax + 1), ncoeffs)],
                "coefficients": [[float(c) for c in basis[nline + n].split()] for n in range(nexp)],
            }
        )

        # advance by the number of exponents
        nline += nexp

    return {"element": element, "name": name, "tags": tags, "aliases": aliases, "n_el": n_el, "blocks": blocks}
