# -*- coding: utf-8 -*-
"""
Gaussian Pseudo Potential

Provides a general framework for storing and querying gaussian pseudopotentials (GPP's).
Read and write functionality for CP2K format provided.

Copyright (c), 2017 The Gaussian Datatypes Authors (see AUTHORS.txt)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""


import re
from itertools import chain

from aiida.common.exceptions import ParsingError


EMPTY_LINE_MATCH = re.compile(r'^(\s*|\s*#.*)$')
BLOCK_MATCH = re.compile(r'^\s*(?P<element>[a-zA-Z]{1,3})\s+(?P<family>\S+).*\n')

def cp2k_pseudo_file_iter(fhandle):
    """
    Generates a sequence of dicts, one dict for each pseudopotential found in the given file

    :param fhandle: Open file handle (in text mode) to a basis set file
    """

    # find the beginning of a new pseudopotential entry, then
    # continue until the next one, the iterator chain and Eof marker guarantee
    # that we find a last (empty) one which will not be parsed.

    current_pseudo = []

    for line in chain(fhandle, ['Eof marker\n']):
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
    # the first line contains the element and one or more identifiers/names
    identifiers = lines[0].split()
    element = identifiers.pop(0)

    # put the longest identifier first: some basis sets specify the number of
    # valence electrons using <IDENTIFIER>-qN
    identifiers.sort(key=lambda i: -len(i))

    name = identifiers.pop(0)
    tags = name.split('-')  # should we also parse the other identifiers for tags?
    aliases = [name] + identifiers  # use the remaining identifiers as aliases

    # The second line contains the number of electrons for each angular momentum
    n_el = [int(n) for n in lines[1].split()]

    # The third line contains the local part in the format
    #   <radius> <nfuncs> [<func-coeff-1> [<func-coeff-2> ...]]
    r_loc_s, nexp_ppl_s, *cexp_ppl_s = lines[2].split()

    local = {
        'r': float(r_loc_s),
        'coeffs': [float(f) for f in cexp_ppl_s]
        }

    if int(nexp_ppl_s) != len(local['coeffs']):
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
        ncoeffs = nprj_ppnl*(nprj_ppnl+1) // 2  # number of elements in the upper triangular matrix

        # the matrix may be distributed over multiple lines, add those values as well
        while len(hprj_ppnl) < ncoeffs:
            try:
                hprj_ppnl += lines[nline].split()
            except IndexError:
                raise ParsingError("premature end-of-lines while reading coefficients of non-local projects")
            nline += 1

        if len(hprj_ppnl) > ncoeffs:
            raise ParsingError("unknown format of the non-local projector coefficients")

        prj_ppnl.append({
            'r': float(r_nprj_s),
            'nproj': nprj_ppnl,  # store for convenience
            'coeffs': [float(f) for f in hprj_ppnl],  # upper triangular matrix
            })

    return {
        'element': element,
        'name': name,
        'tags': tags,
        'aliases': aliases,
        'n_el': n_el,
        'local': local,
        'non_local': prj_ppnl,
        }


def write_cp2k_pseudo_to_file(pseudo_data, fhandle):
        """
        Write a gpp instance to file in CP2K format.
        :param filename: open file handle
        :param mode: mode argument of built-in open function ('a' or 'w')
        """

        def format_float(fnum):
            return "{0:.8f}".format(fnum).rjust(15)

        def format_int(inum):
            return str(inum).rjust(5)

        fhandle.write(pseudo_data['element'])

        for p_id in pseudo_data['id']:
            fhandle.write(' ' + p_id)
        fhandle.write('\n')

        for n_el in pseudo_data['n_el']:
            fhandle.write(format_int(n_el))
        fhandle.write('\n')

        fhandle.write(format_float(pseudo_data['r_loc']))
        fhandle.write(format_int(pseudo_data['nexp_ppl']))

        for cexp in pseudo_data['cexp_ppl']:
            fhandle.write(format_float(cexp))
        fhandle.write('\n')

        fhandle.write(format_int(pseudo_data['nprj']))
        if pseudo_data['nprj'] > 0:
            fhandle.write('\n')

        for radius, nproj, hprj in zip(pseudo_data['r'], pseudo_data['nprj_ppnl'], pseudo_data['hprj_ppnl']):
            fhandle.write(format_float(radius) + format_int(nproj))

            hprj_iter = iter(hprj)
            n_indent = 0

            for nwrite in reversed(range(nproj, 0, -1)):
                for _ in range(nwrite):
                    fhandle.write(format_float(hprj_iter.next()))
                fhandle.write('\n')

                n_indent += 1
                if nwrite == 1:
                    fhandle.write(' ' * 20 + ' ' * 15 * n_indent)

        fhandle.write('\n')
