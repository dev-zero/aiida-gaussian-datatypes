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

from aiida.orm import Data
from aiida.common.exceptions import ValidationError

from .utils import write_cp2k_pseudo_to_file, cp2k_pseudo_file_iter


def _li_round(li, prec=6):
    if isinstance(li, float):
        return round(li, prec)

    if isinstance(li, list):
        return type(li)(_li_round(x, prec) for x in li)

    return li


class Pseudopotential(Data):
    """
    Gaussian Pseudopotential (gpp) class to store gpp's in database and retrieve them.
    fixme: extend to NLCC pseudos.
    """

    def __init__(self, element=None, name=None, aliases=[], tags=[], n_el=[], local=None, non_local=[], version=1,
                 **kwargs):
        """
        TODO
        """

        super(Pseudopotential, self).__init__(**kwargs)

        if 'dbnode' in kwargs:
            return  # node was loaded from database

        self._set_attr('name', name)
        self._set_attr('element', element)
        self._set_attr('tags', tags)
        self._set_attr('aliases', aliases)
        self._set_attr('n_el', n_el)
        self._set_attr('local', local)
        self._set_attr('non_local', non_local)
        self._set_attr('version', version)

    def _validate(self):
        super(Pseudopotential, self)._validate()

        from voluptuous import Schema, MultipleInvalid, ALLOW_EXTRA

        schema = Schema({
            'name': str,
            'element': str,
            'tags': [str],
            'aliases': [str],
            'n_el': list,
            'local': {
                'r': float,
                'coeffs': [float],
                },
            'non_local': [{
                'r': float,
                'nproj': int,
                'coeffs': [float],
                }],
            'version': int,
            }, extra=ALLOW_EXTRA, required=True) 
        try:
            schema(dict(self.iterattrs()))
        except MultipleInvalid as exc:
            raise ValidationError(str(exc))

        for nl in self.non_local:
            if len(nl['coeffs']) != nl['nproj']*(nl['nproj']+1) // 2:
                raise ValidationError("invalid number of coefficients for non-local projection")

    @property
    def element(self):
        """
        the atomic kind/element this pseudopotential is for

        :rtype: str
        """
        return self.get_attr('element', None)

    @property
    def name(self):
        """
        the name for this pseudopotential

        :rtype: str
        """
        return self.get_attr('name', None)

    @property
    def aliases(self):
        """
        a list of alternative names

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
        the version of this pseudopotential

        :rtype: int
        """
        return self.get_attr('version', None)

    @property
    def n_el(self):
        """
        Return the number of electrons per angular momentum
        :rtype:list
        """

        return self.get_attr('n_el', [])

    @property
    def local(self):
        """
        Return the local part in the following format:

            {
                'r': float,
                'coeffs': [float, float, ...],
            }

        :rtype:dict
        """
        return self.get_attr('local', None)


    @property
    def non_local(self):
        """
        Return a list of non-local projectors (for l=0,1...) with each element having the following format:

            {
                'r': float,
                'nprj': int,
                'coeffs': [float, float, ...],  # only the upper-triangular elements
            }

        :rtype:list
        """
        return self.get_attr('non_local', [])


    @classmethod
    def from_cp2k(cls, fhandle):
        """
        Upload a gpp's in CP2K format contained in a single file.
        If a gpp already exists, it is not uploaded.
        If a different gpp exists under the same name or alias, an
        UniquenessError is thrown.
        :return: number of gpp's in file, number of uploaded gpp's.
        Docu of format from GTH_POTENTIALS file of CP2K:
        ------------------------------------------------------------------------
        GTH-potential format:

        Element symbol  Name of the potential  Alias names
        n_el(s)  n_el(p)  n_el(d)  ...
        r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
        nprj
        r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
        r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
         .       .               .
         .       .               .
         .       .               .
        r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
                                                      i=1,nprj_ppnl(nprj))

        n_el   : Number of electrons for each angular momentum quantum number
                   (electronic configuration -> s p d ...)
        r_loc    : Radius for the local part defined by the Gaussian function
                   exponent alpha_erf
        nexp_ppl : Number of the local pseudopotential functions
        cexp_ppl : Coefficients of the local pseudopotential functions
        nprj     : Number of the non-local projectors => nprj = SIZE(nprj_ppnl(:))
        r        : Radius of the non-local part for angular momentum quantum number l
                   defined by the Gaussian function exponents alpha_prj_ppnl
        nprj_ppnl: Number of the non-local projectors for the angular momentum
                   quantum number l
        hprj_ppnl: Coefficients of the non-local projector functions
        ------------------------------------------------------------------------
        Name and Alias of the potentials are required to be of the format
        'type'-'xc'-q'nval' with 'type' some classification (e.g. GTH), 'xc'
        the compatible xc-functional (e.g. PBE) and 'nval' the total number
        of valence electrons.
        """

        return [Pseudopotential(**pseudo_data) for pseudo_data in cp2k_pseudo_file_iter(fhandle)]

    def to_cp2k(self, fhandle):
        """
        Write a gpp instance to file in CP2K format.
        :param filename: open file handle
        :param mode: mode argument of built-in open function ('a' or 'w')
        """
        pseudo_data = dict(self.iterattrs())
        write_cp2k_pseudo_to_file(pseudo_data)
