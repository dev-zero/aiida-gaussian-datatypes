# -*- coding: utf-8 -*-
"""
Gaussian Basis Set data object

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

import re

EMPTY_LINE_MATCH = re.compile(r'^(\s*|\s*#.*)$')
BLOCK_MATCH = re.compile(r'^\s*(?P<element>[a-zA-Z]{1,2})\s+(?P<family>\S+).*\n')


def write_cp2k_basisset(fhandle, atomkind, name, orbital_quantum_numbers, coefficients):
    """
    Write the Basis Set to the passed file handle in the format expected by CP2K.

    :param fhandle: A valid output file handle
    """

    # we can safely assume to have always at least one set of coefficients
    to_print = [
        [
            [
                orbital_quantum_numbers[0][0],  # principal quantum number
                orbital_quantum_numbers[0][1],  # minimal angular quantum number l_min
                orbital_quantum_numbers[0][1],  # maximal angular quantum number l_max
                len(coefficients[0]),  # number of exponents
                1,  # the number of contractions for l_min
                ],
            coefficients[0],  # the respective contraction coefficients
            ]
        ]

    total_width = 0
    n_decimals = 0

    for i in range(1, len(orbital_quantum_numbers)):
        # go through all stored coefficients for (n,l,m,s)

        if orbital_quantum_numbers[i][0] != orbital_quantum_numbers[i - 1][0]:
            # if the current set is NOT for the same primary quantum number as the previous one,
            # add a new set (can't merge with the previous one)
            to_print.append([
                [
                    orbital_quantum_numbers[i][0],
                    orbital_quantum_numbers[i][1],
                    orbital_quantum_numbers[i][1],  # will be increment if more coefficients are available
                    len(coefficients[i]),
                    1,
                    ],
                coefficients[i],
                ])

        elif coefficients[i] != coefficients[i - 1]:
            # if the current set contains a different set of exponents for the same primary quantum number,
            # add as a separate basis set (can't merge coefficients for those with the previous one)
            to_print.append([
                [
                    orbital_quantum_numbers[i][0],
                    orbital_quantum_numbers[i][1],
                    orbital_quantum_numbers[i][1],  # will be increment if more coefficients are available
                    len(coefficients[i]),
                    1,
                    ],
                coefficients[i],
                ])

        elif orbital_quantum_numbers[i][1] != orbital_quantum_numbers[i - 1][1]:
            # in case the primary quantum number and the contraction coefficients are the same as for the previous,
            # but the orbital quantum number is different, add these contraction coefficients to the previous set
            to_print[-1][0][2] += 1  # increment the maximum angular momentum contained in this set
            to_print[-1][0].append(1)  # initialize the number of contractions for this l quantum number
            to_print[-1].append(coefficients[i])

        elif coefficients[i] != coefficients[i - 1]:
            # now, if we got different contraction coefficients for the same n and l quantum numbers and exponents
            to_print[-1][0][-1] += 1  # increment the number of contractions for this l quantum number
            to_print[-1].append(coefficients[i])

    max_width = max(len(coeff) for shell in coefficients for exp_coeff in shell for coeff in exp_coeff)

    fhandle.write("{} {}\n".format(atomkind, name))
    fhandle.write("{}\n".format(len(to_print)))  # the number of sets this basis set contains

    for bset in to_print:
        fhandle.write(" ".join(str(n) for n in bset[0]))  # n, l_min, l_max, n_exp, n_cont_l0, n_cont_l1, ...
        fhandle.write("\n")

        for i in range(len(bset[1])):  # go through all exponents
            # print the exponent:
            fhandle.write("{num:>{width}s}".format(num=bset[1][i][0], width=max_width))

            for j in range(sum(bset[0][4:])):
                # print all contraction coefficients for this exponent:
                fhandle.write(" {num:>{width}s}".format(num=bset[1 + j][i][1], width=max_width))

            fhandle.write("\n")


def parse_single_cp2k_basisset(basis):
    """
    :param basis: A list of strings, where each string contains a line read from the basis set file.
                  The list must one single basis set.
    :return:      A dictionary containing the atomkind, tags, aliases, orbital_quantum_numbers, coefficients
    """

    # the first line contains the element and one or more idientifiers/names
    identifiers = basis[0].split()
    atomkind = identifiers.pop(0)

    # put the longest identifier first: some basis sets specify the number of
    # valence electrons using <IDENTIFIER>-qN
    identifiers.sort(key=lambda i: -len(i))

    name = identifiers.pop(0)
    tags = name.split('-')
    aliases = identifiers  # use the remaining identifiers as aliases

    # The second line contains the number of sets, conversion to int ignores any whitespace
    n_blocks = int(basis[1])

    nline = 2
    coefficients = []
    orbital_quantum_numbers = []

    # go through all blocks containing different sets of orbitals
    for _ in range(n_blocks):
        # get the quantum numbers for this set, formatted as follows:
        # n lmin lmax nexp nshell(lmin) nshell(lmin+1) ... nshell(lmax-1) nshell(lmax)
        qnumbers = [int(qn) for qn in basis[nline].split()]

        # n_different_l is how many DIFFERENT angular momenta we have
        n_different_l = (qnumbers[2]) - (qnumbers[1])

        nline += 1
        current_column = 1

        # loop over all different angular momenta: l_min =< l <= l_max
        for l_qn_idx in range(n_different_l+1):
            # loop over different shells of a given momentum
            for _ in range(qnumbers[4 + l_qn_idx]):

                orbital_quantum_numbers.append([qnumbers[0], qnumbers[1] + l_qn_idx])

                # loop over all exponents.
                coefficients.append([
                    (basis[nline + exp_number].split()[0], basis[nline + exp_number].split()[current_column])
                    for exp_number in range(qnumbers[3])
                    ])

                current_column += 1

        # advance by the number of exponents
        nline += qnumbers[3]

    return {
            'atomkind': atomkind,
            'name': name,
            'tags': tags,
            'aliases': aliases,
            'orbital_quantum_numbers': orbital_quantum_numbers,
            'coefficients': coefficients,
            }
