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

from aiida.orm.data import Data
from aiida.common.exceptions import ParsingError


EMPTY_LINE_MATCH = re.compile(r'^(\s*|\s*#.*)$')
BLOCK_MATCH = re.compile(r'^\s*(?P<element>[a-zA-Z]{1,2})\s+(?P<family>\S+).*\n')


class BasisSet(Data):
    """
    Provide a general way to store GTO basis sets from different codes within the AiiDA framework.
    """

    def __init__(self, atomkind=None, aliases=[], tags=[], orbital_quantum_numbers=[], coefficients=[], **kwargs):
        """
        :param atomkind: string containing the name of the element
        :param aliases: alternative IDs
        :param tags: additional tags
        :param orbital_quantum_numbers: see :py:attr:`~orbitalquantumnumbers`
        :param coefficients: see :py:attr:`~coefficients`

        **Important**: The `orbital_quantum_numbers` and the `coefficients` lists must be consistent
        """

        super(BasisSet, self).__init__(**kwargs)

        if 'dbnode' in kwargs:
            return  # node was loaded from database

        if len(orbital_quantum_numbers) != len(coefficients):
            raise ParsingError("The array with quantum numbers and the array with exponents have different size!")

        if not all(isinstance(entry, tuple) and (len(entry) == 2) for bset in coefficients for entry in bset):
            raise ParsingError("Coefficients must be a list of a list of tuples")

        # TODO: finalize version information
        # TODO: check for duplicate

        self._set_attr('id', "-".join(tags))
        self._set_attr('element', atomkind)
        self._set_attr('tags', tags)
        self._set_attr('aliases', aliases)
        self._set_attr('exponent_contraction_coefficients', coefficients)
        self._set_attr('orbital_quantum_numbers', orbital_quantum_numbers)
        self._set_attr('version', 1)

    @classmethod
    def from_cp2k(cls, data):
        """
        Construct a basis set object from a Basis Set in CP2K format

        :param data: file handle or list of lines
        """

        # TODO: implement filtering
        # TODO: proper return

        current_basis = []

        for line in data:
            if EMPTY_LINE_MATCH.match(line):
                # ignore empty and comment lines
                continue

            match = BLOCK_MATCH.match(line)

            if match and current_basis:
                return cls(**parse_single_cp2k_basiset(current_basis))

            current_basis.append(line.strip())

    @property
    def element(self):
        """
        the atomic kind/element this basis set is for

        :rtype: str
        """
        return self.get_attr('element', None)

    @property
    def id(self):
        """
        the ID for this basis set

        :rtype: str
        """
        return self.get_attr('id', None)

    @property
    def aliases(self):
        """
        a list of alternative IDs

        :rtype: []
        """
        return self.get_attr('aliases', [])

    @property
    def tags(self):
        """
        a list of tags

        :rtype: []
        """
        return self.get_attr('tags', [])

    @property
    def version(self):
        """
        the version of this basis set

        :rtype: int
        """
        return self.get_attr('version', None)

    @property
    def norbitals(self):
        """
        the number of orbitals stored in the basis set

        :rtype: int
        """
        return len(self.orbitalquantumnumbers)

    @property
    def orbitalquantumnumbers(self):
        """
        Return a list of quantum numbers for each orbital::

            [
                ( N, l, m ),
            ]

        Where:

        N
            principle quantum number
        l
            angular momentum
        m
            magnetic quantum number

        :rtype: []
        """

        return self.get_attr('orbital_quantum_numbers', [])

    @property
    def coefficients(self):
        """
        Return a list of exponents and contraction coefficient tuples for each orbital
        in the following format::

            [
               [
                   ( "2838.2104843030",  "-0.0007019523" ),
                   (  "425.9069835160",  "-0.0054237190" ),
                   (   "96.6806600316",  "-0.0277505669" ),
               ],
            ]

        :rtype: []

        The numbers are intentionally stored as strings to allow for bit-wise reproduction.
        """

        self.get_attr('exponent_contraction_coefficients', [])

    def get_orbital(self, n_qn, l_qn='*', m_qn='*'):
        """
        Return a tuple of two lists:
            * List of orbital quantum numbers
            * List of exponents and contraction coefficients

        :param    n_qn: principle quantum number
        :param    l_qn: angular momentum
        :param    m_qn: magnetic quantum number

        :rtype: ([], [])
        """

        return_oqn = []
        return_ecc = []

        for qnumbers, coeffs in zip(self.orbitalquantumnumbers, self.coefficients):
            n, l, m, s = qnumbers

            if (n == n_qn) and (l_qn in ['*', l]) and (m_qn in ['*', m]):
                return_oqn.append((n, l, m, s))
                return_ecc.append(coeffs)

        return return_oqn, return_ecc

    def to_cp2k(self, fhandle):
        """
        Write the Basis Set to the passed file handle in the format expected by CP2K.

        :param fhandle: A valid output file handle
        """

        return write_cp2k_basisset(fhandle, self.element, self.id, self.orbitalquantumnumbers, self.coefficients)


def write_cp2k_basisset(fhandle, atomkind, name, orbital_quantum_numbers, exponent_contraction_coefficients):
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
                1,  # the number of contractions for l_min
                ],
            exponent_contraction_coefficients[0],  # the respective contraction coefficients
            ]
        ]

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
                    1,
                    ],
                exponent_contraction_coefficients[i],
                ])

        elif exponent_contraction_coefficients[i] != exponent_contraction_coefficients[i - 1]:
            # if the current set contains a different set of exponents for the same primary quantum number,
            # add as a separate basis set (can't merge coefficients for those with the previous one)
            to_print.append([
                [
                    orbital_quantum_numbers[i][0],
                    orbital_quantum_numbers[i][1],
                    orbital_quantum_numbers[i][1],  # will be increment if more coefficients are available
                    1,
                    ],
                exponent_contraction_coefficients[i],
                ])

        elif orbital_quantum_numbers[i][1] != orbital_quantum_numbers[i - 1][1]:
            # in case the primary quantum number and the contraction coefficients are the same as for the previous,
            # but the orbital quantum number is different, add these contraction coefficients to the previous set
            to_print[-1][0][2] += 1  # increment the maximum angular momentum contained in this set
            to_print[-1][0].append(1)  # initialize the number of contractions for this l quantum number
            to_print[-1].append(exponent_contraction_coefficients[i])

        elif exponent_contraction_coefficients[i] != exponent_contraction_coefficients[i - 1]:
            # now, if we got different contraction coefficients for the same n and l quantum numbers and exponents
            to_print[-1][0][-1] += 1  # increment the number of contractions for this l quantum number
            to_print[-1].append(exponent_contraction_coefficients[i])

    fhandle.write("{} {}\n".format(atomkind, name))
    fhandle.write("{}\n".format(len(to_print)))  # the number of sets this basis set contains

    for bset in to_print:
        for out in bset[0]:  # n, l_min, l_max, n_exp, n_cont_l0, n_cont_l1, ...
            fhandle.write("{} ".format(out))

        fhandle.write("\n")

        for i in range(len(bset[1])):  # go through all expontents
            # print the exponent:
            fhandle.write("\t{}".format(bset[1][i][0]))

            for j in range(sum(bset[0][3:])):
                # print all contraction coefficients for this exponent:
                fhandle.write(" {}".format(bset[1 + j][i][1]))

            fhandle.write("\n")


def parse_single_cp2k_basiset(basis):
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

    nae = identifiers.pop(0)
    tags = name.split('-')
    aliases = identifiers  # use the remaining identifiers as aliases

    # The second line contains the number of sets, conversion to int ignores any whitespace
    n_blocks = int(basis[1])

    nline = 2
    exponent_contractioncoefficient = []
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

                # loop over all possible magnetic quantum numbers
                for m_qn in range(-(qnumbers[1] + l_qn_idx), qnumbers[1] + l_qn_idx + 1):

                    orbital_quantum_numbers.append([qnumbers[0], qnumbers[1] + l_qn_idx, m_qn])

                    # loop over all exponents.
                    # Do NOT convert the values to float to preserve bit-correct reproduction of the values.
                    exponent_contractioncoefficient.append([
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
            'coefficients': exponent_contractioncoefficient,
            }
