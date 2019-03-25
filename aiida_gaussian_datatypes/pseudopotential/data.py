# -*- coding: utf-8 -*-
"""
Gaussian Pseudopotential Data class

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

from aiida.orm import Data
from aiida.common.exceptions import ValidationError

from .utils import write_cp2k_pseudo, cp2k_pseudo_file_iter


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

        self.set_attribute('name', name)
        self.set_attribute('element', element)
        self.set_attribute('tags', tags)
        self.set_attribute('aliases', aliases)
        self.set_attribute('n_el', n_el)
        self.set_attribute('local', local)
        self.set_attribute('non_local', non_local)
        self.set_attribute('version', version)

    def store(self, *args, **kwargs):
        """
        Store the node, ensuring that the combination (element,name,version) is unique.
        """
        # TODO: this uniqueness check is not race-condition free.

        from aiida.common.exceptions import UniquenessError, NotExistent

        try:
            existing = self.get(self.element, self.name, self.version, match_aliases=False)
        except NotExistent:
            pass
        else:
            raise UniquenessError("Gaussian Pseudopotential already exists for"
                                  " element={b.element}, name={b.name}, version={b.version}: {uuid}"
                                  .format(uuid=existing.uuid, b=self))

        return super(Pseudopotential, self).store(*args, **kwargs)

    def _validate(self):
        super(Pseudopotential, self)._validate()

        from voluptuous import Schema, MultipleInvalid, ALLOW_EXTRA

        schema = Schema({
            'name': str,
            'element': str,
            'tags': [str],
            'aliases': [str],
            'n_el': [int],
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
            schema(self.attributes)
        except MultipleInvalid as exc:
            raise ValidationError(str(exc))

        for nlocal in self.attributes['non_local']:
            if len(nlocal['coeffs']) != nlocal['nproj']*(nlocal['nproj']+1) // 2:
                raise ValidationError("invalid number of coefficients for non-local projection")

    @property
    def element(self):
        """
        the atomic kind/element this pseudopotential is for

        :rtype: str
        """
        return self.get_attribute('element', None)

    @property
    def name(self):
        """
        the name for this pseudopotential

        :rtype: str
        """
        return self.get_attribute('name', None)

    @property
    def aliases(self):
        """
        a list of alternative names

        :rtype: []
        """
        return self.get_attribute('aliases', [])

    @property
    def tags(self):
        """
        a list of tags

        :rtype: []
        """
        return self.get_attribute('tags', [])

    @property
    def version(self):
        """
        the version of this pseudopotential

        :rtype: int
        """
        return self.get_attribute('version', None)

    @property
    def n_el(self):
        """
        Return the number of electrons per angular momentum
        :rtype:list
        """

        return self.get_attribute('n_el', [])

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
        return self.get_attribute('local', None)

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
        return self.get_attribute('non_local', [])

    @classmethod
    def get(cls, element, name=None, version='latest', match_aliases=True):
        """
        Get the first matching Pseudopotential for the given parameters.

        :param element: The atomic symbol
        :param name: The name of the pseudo
        :param version: A specific version (if more than one in the database and not the highest/latest)
        :param match_aliases: Whether to look in the list of of aliases for a matching name
        """
        from aiida.orm.querybuilder import QueryBuilder
        from aiida.common.exceptions import NotExistent

        filters = {
            'attributes.element': {'==': element},
            }

        if version != 'latest':
            filters['attributes.version'] = {'==': version}

        if match_aliases:
            filters['attributes.aliases'] = {'contains': [name]}
        else:
            filters['attributes.name'] = {'==': name}

        query = QueryBuilder()
        query.append(Pseudopotential)
        query.add_filter(Pseudopotential, filters)
        query.order_by({Pseudopotential: [{'attributes.version': {'cast': 'i', 'order': 'desc'}}]})

        existing = query.first()

        if not existing:
            raise NotExistent("No Gaussian Pseudopotential found for"
                              " element={element}, name={name}, version={version}"
                              .format(element=element, name=name, version=version))

        return existing[0]

    @classmethod
    def from_cp2k(cls, fhandle, filters, duplicate_handling='ignore'):
        """
        Constructs a list with pseudopotential objects from a Pseudopotential in CP2K format

        :param fhandle: open file handle
        :param filters: a dict with attribute filter functions
        :param duplicate_handling: how to handle duplicates ("ignore", "error", "new" (version))
        :rtype: list
        """

        from aiida.common.exceptions import UniquenessError, NotExistent

        def matches_criteria(pseudo):
            return all(fspec(pseudo[field]) for field, fspec in filters.items())

        def exists(pseudo):
            try:
                cls.get(pseudo['element'], pseudo['name'], match_aliases=False)
            except NotExistent:
                return False

            return True

        pseudos = [p for p in cp2k_pseudo_file_iter(fhandle) if matches_criteria(p)]

        if duplicate_handling == 'ignore':  # simply filter duplicates
            pseudos = [p for p in pseudos if not exists(p)]

        elif duplicate_handling == 'error':
            for pseudo in pseudos:
                try:
                    latest = cls.get(pseudo['element'], pseudo['name'], match_aliases=False)
                except NotExistent:
                    pass
                else:
                    raise UniquenessError("Gaussian Pseudopotential already exists for"
                                          " element={element}, name={name}: {uuid}"
                                          .format(uuid=latest.uuid, **pseudo))

        elif duplicate_handling == 'new':
            for pseudo in pseudos:
                try:
                    latest = cls.get(pseudo['element'], pseudo['name'], match_aliases=False)
                except NotExistent:
                    pass
                else:
                    pseudo['version'] = latest.version + 1

        else:
            raise ValueError("Specified duplicate handling strategy not recognized: '{}'".format(duplicate_handling))

        return [cls(**p) for p in pseudos]

    def to_cp2k(self, fhandle):
        """
        Write this Pseudopotential instance to a file in CP2K format.

        :param fhandle: open file handle
        """
        write_cp2k_pseudo(fhandle, self.element, self.name, self.n_el, self.local, self.non_local)
