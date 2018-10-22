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

from __future__ import print_function

from aiida.orm import Data
from aiida.common.exceptions import PluginInternalError, ValidationError, ParsingError

from .utils import write_cp2k_gpp_to_file, cp2k_gpp_file_iter

def _li_round(li, prec=6):
    if isinstance(li, float):
        return round(li, prec)

    if isinstance(li, list):
        return type(li)(_li_round(x, prec) for x in li)

    return li


class GaussianpseudoData(Data):
    """
    Gaussian Pseudopotential (gpp) class to store gpp's in database and
    retrieve them.
    fixme: extend to NLCC pseudos.
    """

    def _init_internal_params(self):
        self._updatable_attributes = ['default']

    def __init__(self, gpp_data):
        """
        Create a gpp from dictionary and store it in database if does not exist.
        If user tries to store a new gpp under an already existing id, a
        UniquenessError is thrown. The correctness of the created gpp is
        validated (keys, types, lengths).
        Currently does not support NLCC pseudopotentials.
        :param gpp_data: a dictionary that must contain the following keys
          and data types:
          * element:     string
                         (e.g. 'H')
          * gpp_type:    string,
                         some classification of the gpp (e.g. 'GTH'),
                         must be unique for a given element and a given xc
                         functional
                         and a given number of valence electrons
          * xc:          list of strings,
                         defining compatibility with xc-functionals (e.g. 'PBE')
          * n_elec:      list of ints,
                         number of electrons for each angular momentum quantum
                         number (electronic configuration -> s p d ...)
          * r_loc:       float,
                         radius for the local part defined by the Gaussian
                         function exponent alpha_erf
          * nexp_ppl:    int,
                         number of the local pseudopotential functions
          * cexp_ppl:    list of floats of length nexp_ppl,
                         coefficients of the local pseudopotential functions
          * nprj:        int,
                         number of the non-local projectors
                         => nprj = len(nprj_ppnl)
          * r:           list of floats of length nprj,
                         radius of the non-local part for angular momentum
                         quantum number l
                         defined by the Gaussian function exponents
                         alpha_prj_ppnl
          * nprj_ppnl:   list of ints of length nprj,
                         number of the non-local projectors for the angular
                         momentum quantum number l
          * hprj_ppnl:   list of list of floats of length
                         nprj, nprj_ppnl[iprj]*(nprj_ppnl[iprj]+1)/2,
                         coefficients of the non-local projector functions
        :return: the created gpp instance.
        """

        gpp_data['n_val'] = sum(gpp_data['n_elec'])
        is_new = True
        version = []
        # query for element and id to check if gpp with same name exists
        for pid in gpp_data['id']:
            q = models.DbNode.objects.filter(
                type__startswith=cls._query_type_string)
            qtmp = models.DbAttribute.objects.filter(
                key='element', tval=gpp_data['element'])
            q = q.filter(dbattributes__in=qtmp)
            qtmp = models.DbAttribute.objects.filter(
                key__startswith='id.', tval=pid)
            q = q.filter(dbattributes__in=qtmp)

            version.append(len(q) + 1)
            pseudos_with_same_id = [_.get_aiida_class() for _ in q]
            for pseudo in pseudos_with_same_id:
                if pseudo == gpp_data:
                    is_new = False
                elif pseudo.get_attr('default', None):
                    pseudo._set_attr('default', False)

        gpp_data['version'] = version

        if is_new:
            do_upload = True
            if any(_ > 1 for _ in gpp_data['version']):
                print("pseudo with same id but different coefficients already exists, do you want to upload a new version? [y/N]")
                do_upload = raw_input().strip().lower() == 'y'
            if do_upload:
                print("uploading to db")
                instance = cls()
                for k, v in gpp_data.iteritems():
                    instance._set_attr(k, v)
                instance._set_attr('default', True)
                instance._validate()
                instance.store()
                return instance
            else:
                print("no upload")
                return None
        else:
            print("pseudo already exists")
            print("no upload")
            return None

    @classmethod
    def get_pseudos(cls, element=None, gpp_type=None, xc=None, n_val=None, version=None, default=True):
        """
        Return all instances stored in DB that match a number of optional
        parameters.
        Specification of all parameters is guaranteed to give a unique (or no)
        match.
        :param element: the element
        :param gpp_type: the name/classification of the gpp
        :param xc: the xc functional
        :param n_val: the number of valence electrons (sum of n_elec)
        :return: generator for found gpp's
        """

        q = models.DbNode.objects.filter(
            type__startswith=cls._query_type_string)

        notnone = 0
        if element is not None:
            qtmp = models.DbAttribute.objects.filter(key='element',
                                                     tval=element)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if gpp_type is not None:
            qtmp = models.DbAttribute.objects.filter(key='gpp_type',
                                                     tval=gpp_type)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if xc is not None:
            qtmp = models.DbAttribute.objects.filter(key__startswith='xc.',
                                                     tval=xc)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if n_val is not None:
            qtmp = models.DbAttribute.objects.filter(key='n_val',
                                                     ival=n_val)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1
        if version is not None:
            qtmp = models.DbAttribute.objects.filter(key__startswith='version.',
                                                     ival=version)
            q = q.filter(dbattributes__in=qtmp)
            notnone += 1

        q = q.distinct()

        if notnone == 5 and len(q) > 1:
            raise PluginInternalError('found gpp is not unique.')

        for _ in q:
            pseudo = _.get_aiida_class()
            if (not default) or pseudo.get_attr('default', None):
                yield pseudo

    def _validate(self):

        super(GaussianpseudoData, self)._validate()

        gpp_dict = dict(self.iterattrs())

        keys = ['element', 'id', 'gpp_type', 'xc', 'n_val',
                'n_elec', 'r_loc', 'nexp_ppl', 'cexp_ppl', 'nprj',
                'r', 'nprj_ppnl', 'hprj_ppnl']

        types = [[str], [list, str], [str], [list, str], [int],
                 [list, int], [float], [int], [list, float], [int],
                 [list, float], [list, int], [list, list, float]]

        lengths = [None, None, None, None, None,
                   None, None, None, 'nexp_ppl', None,
                   'nprj', 'nprj', 'nprj']

        try:
            for k, t, l in zip(keys, types, lengths):
                if k in gpp_dict.keys():
                    if not isinstance(gpp_dict[k], t[0]):
                        raise ValidationError('{} must be {}'.format(k, t))
                    if len(t) > 1:
                        if not all(isinstance(_, t[1]) for _ in gpp_dict[k]):
                            raise ValidationError('{} must be {}'.format(k, t))
                    if len(t) > 2:
                        if not all(all(isinstance(__, t[2]) for __ in _)
                                   for _ in gpp_dict[k]):
                            raise ValidationError('{} must be {}'.format(k, t))
                    if l is not None and len(gpp_dict[k]) != gpp_dict[l]:
                        raise ValidationError(
                            'length of {} must be equal to {}'.format(k, l))
                else:
                    raise ValidationError('{} missing'.format(k))

            if sum(gpp_dict['n_elec']) != gpp_dict['n_val']:
                raise ValidationError(
                    'number of valence electrons is not sum of occupancy')

            # check size of upper triangular part of hprj_ppnl matrices
            for iprj in range(0, len(gpp_dict['nprj_ppnl'])):
                nprj = gpp_dict['nprj_ppnl'][iprj]
                if len(gpp_dict['hprj_ppnl'][iprj]) != nprj * (nprj + 1) / 2:
                    raise ValidationError(
                        'Incorrect number of hprj_ppnl coefficients')
        except ValidationError as e:
            raise ValidationError('invalid format for {} {}: {}'.format(
                gpp_dict['element'],
                ' '.join(gpp_dict['id']),
                e.message))

    def __eq__(self, other):
        if isinstance(other, GaussianpseudoData):
            other_dict = dict(other.iterattrs())
        elif isinstance(other, dict):
            other_dict = other
        else:
            return False
        self_dict = dict(self.iterattrs())
        self_dict.pop('version', None)
        self_dict.pop('default', None)
        other_dict.pop('version', None)
        other_dict.pop('default', None)
        self_vals = _li_round(sorted(self_dict.items()))
        other_vals = _li_round(sorted(other_dict.items()))
        return self_vals == other_vals

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
        n_elec(s)  n_elec(p)  n_elec(d)  ...
        r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
        nprj
        r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
        r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
         .       .               .
         .       .               .
         .       .               .
        r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
                                                      i=1,nprj_ppnl(nprj))

        n_elec   : Number of electrons for each angular momentum quantum number
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
        
        uploaded = [cls.create_if_not_existing(gpp) for gpp in cp2k_gpp_file_iter(fhandle)]
        n_gpp = len(uploaded)
        n_uploaded = n_gpp - uploaded.count(None)
        return n_gpp, n_uploaded

    def to_cp2k(self, fhandle):
        """
        Write a gpp instance to file in CP2K format.
        :param filename: open file handle
        :param mode: mode argument of built-in open function ('a' or 'w')
        """
        gpp_data = dict(self.iterattrs())
        write_cp2k_gpp_to_file(gpp_data)
