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

from __future__ import absolute_import

import re

from aiida.orm.data import Data

from .utils import write_cp2k_basisset, parse_single_cp2k_basisset

EMPTY_LINE_MATCH = re.compile(r'^(\s*|\s*#.*)$')
BLOCK_MATCH = re.compile(r'^\s*(?P<element>[a-zA-Z]{1,3})\s+(?P<family>\S+).*\n')


class BasisSet(Data):
    """
    Provide a general way to store GTO basis sets from different codes within the AiiDA framework.
    """

    def __init__(self, element=None, aliases=[], tags=[], blocks=[], **kwargs):
        """
        :param element: string containing the name of the element
        :param aliases: alternative IDs
        :param tags: additional tags
        :param orbital_quantum_numbers: see :py:attr:`~orbitalquantumnumbers`
        :param coefficients: see :py:attr:`~coefficients`

        **Important**: The `orbital_quantum_numbers` and the `coefficients` lists must be consistent
        """

        super(BasisSet, self).__init__(**kwargs)

        if 'dbnode' in kwargs:
            return  # node was loaded from database

        # TODO: check format
        # TODO: finalize version information
        # TODO: check for duplicate

        self._set_attr('id', "-".join(tags))
        self._set_attr('element', element)
        self._set_attr('tags', tags)
        self._set_attr('aliases', aliases)
        self._set_attr('blocks', blocks)
        self._set_attr('version', 1)

    @classmethod
    def from_cp2k(cls, data):
        """
        Construct a basis set object from a Basis Set in CP2K format

        :param data: file handle or list of lines
        """

        # TODO: implement filtering

        current_basis = []

        for line in data:
            if EMPTY_LINE_MATCH.match(line):
                # ignore empty and comment lines
                continue

            match = BLOCK_MATCH.match(line)

            if match and current_basis:
                return cls(**parse_single_cp2k_basisset(current_basis))

            current_basis.append(line.strip())
        
        if current_basis:
            return cls(**parse_single_cp2k_basisset(current_basis))

        return cls()

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
    def blocks(self):
        """
        Return the shells/blocks in the following format::

            [
                {
                    "n": 2,
                    "l": [
                        (0, 2),  # 2 sets of coefficients for the same exponents for s
                        (1, 1),  # 1 set of coefficients for the same exponents for p
                        ],
                    "blocks": numpy.array(
                        [
                            [ "2838.2104843030", "-0.0007019523",  "-0.0007019523", "-0.0007019523" ],
                            [  "425.9069835160", "-0.0054237190",  "-0.0054237190", "-0.0054237190" ],
                            [   "96.6806600316", "-0.0277505669",  "-0.0277505669", "-0.0277505669" ],
                        ],
                    ],
                },
            ]

        :rtype: []
        """

        return self.get_attr('blocks', [])

    def to_cp2k(self, fhandle):
        """
        Write the Basis Set to the passed file handle in the format expected by CP2K.

        :param fhandle: A valid output file handle
        """

        return write_cp2k_basisset(fhandle, self.element, self.id, self.blocks)
