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


_CP2KGPP_REGEX = re.compile(r"""
    # Element symbol  Name of the potential  Alias names
        (?P<element>
            [A-Z][a-z]{0,1}
        )
        (?P<name>
            ([ \t\r\f\v]+[-\w]+)+
        )
        [ \t\r\f\v]*[\n]
    # n_elec(s)  n_elec(p)  n_elec(d)  ...
        (?P<el_config>
            ([ \t\r\f\v]*[0-9]+)+
        )
        [ \t\r\f\v]*[\n]
    # r_loc   nexp_ppl        cexp_ppl(1) ... cexp_ppl(nexp_ppl)
        (?P<body_loc>
            [ \t\r\f\v]*[\d\.]+[ \t\r\f\v]*[\d]+([ \t\r\f\v]+-?[\d]+.[\d]+)*
        )
        [ \t\r\f\v]*[\n]
    # nprj
        (?P<nproj_nonloc>
            [ \t\r\f\v]*[\d]+
        )
        [ \t\r\f\v]*[\n]
    # r(1)    nprj_ppnl(1)    ((hprj_ppnl(1,i,j),j=i,nprj_ppnl(1)),i=1,nprj_ppnl(1))
    # r(2)    nprj_ppnl(2)    ((hprj_ppnl(2,i,j),j=i,nprj_ppnl(2)),i=1,nprj_ppnl(2))
    #  .       .               .
    #  .       .               .
    #  .       .               .
    # r(nprj) nprj_ppnl(nprj) ((hprj_ppnl(nprj,i,j),j=i,nprj_ppnl(nprj)),
        (?P<body_nonloc>
            ([ \t\r\f\v]*[\d\.]+[ \t\r\f\v]*[\d]+(([ \t\r\f\v]+-?[\d]+.[\d]+)+
                [ \t\r\f\v]*[\n])*)*
        )
    """, re.VERBOSE | re.MULTILINE)


def parse_single_cp2k_gpp(match):
    element = match.group('element').strip(' \t\r\f\v\n')
    names = match.group('name').strip(' \t\r\f\v\n').split()

    n_elec = [int(el) for el in (match.group('el_config').strip(
        ' \t\r\f\v\n').split())]
    body_loc = match.group('body_loc').strip(' \t\r\f\v\n').split()
    nprj = int(match.group('nproj_nonloc').strip(' \t\r\f\v\n'))
    body_nonloc = match.group('body_nonloc').strip(' \t\r\f\v\n')

    r_loc = float(body_loc[0])
    nexp_ppl = int(body_loc[1])
    cexp_ppl = []
    for val in body_loc[2:]:
        cexp_ppl.append(float(val))
    next_proj = True
    n = 0
    r = []
    nprj_ppnl = []
    hprj_ppnl = []
    for line in body_nonloc.splitlines():
        line = line.split()
        offset = 0
        if next_proj:
            hprj_ppnl.append([])
            r.append(float(line[offset]))
            nprj_ppnl.append(int(line[offset + 1]))
            nhproj = nprj_ppnl[-1] * (nprj_ppnl[-1] + 1) / 2
            offset = 2
        for data in line[offset:]:
            hprj_ppnl[n].append(float(data))
        next_proj = len(hprj_ppnl[n]) == nhproj
        if next_proj:
            n = n + 1

    namessp = [_.split('-') for _ in names]

    parse_name = any(len(_) > 1 for _ in namessp)

    gpp_type = [_[0] for _ in namessp if len(_) >= 1]
    xc = [_[1] for _ in namessp if len(_) >= 2]
    n_val = [_[2] for _ in namessp if len(_) >= 3]

    xc = list(set(xc))
    unique_type = list(set(gpp_type))
    if not n_val:
        n_val = [str(sum(n_elec))]
    unique_n_val = list(set(n_val))

    data_to_store = ('element', 'gpp_type', 'xc', 'n_elec', 'r_loc',
                     'nexp_ppl', 'cexp_ppl', 'nprj', 'r', 'nprj_ppnl',
                     'hprj_ppnl')
    gpp_data = {}
    for _ in data_to_store:
        gpp_data[_] = locals()[_]

    if parse_name:
        if len(unique_type) == 1 and len(unique_n_val) == 1:
            gpp_type = unique_type[0]
            n_val = unique_n_val[0]
        else:
            raise ParsingError(
                'gpp_type and n_val in pseudo name gpp_type-xc-n_val must be '
                'unique')

        try:
            n_val = int(n_val.lstrip('q'))
        except ValueError:
            raise ValueError(
                'pseudo potential name should be "type-xc-q<nval>" with nval the number of valence electrons.')

        gpp_data['id'] = ['{}-{}-q{}'.format(gpp_type, _, n_val)
                          for _ in gpp_data['xc']]
        gpp_data['gpp_type'] = gpp_type
        gpp_data['n_val'] = n_val
        gpp_data['xc'] = xc

        if n_val != sum(n_elec):
            raise ParsingError(
                'number of valence electron must be sum of occupancy')

    else:
        gpp_data['id'] = names
        gpp_data['gpp_type'] = ''
        gpp_data['n_val'] = ''
        gpp_data['xc'] = []

    return gpp_data


def cp2k_gpp_file_iter(fhandle):
    for match in _CP2KGPP_REGEX.finditer(fhandle):
        yield _parse_single_cp2k_gpp(match)


def write_cp2k_gpp_to_file(gpp_data, fhandle):
        """
        Write a gpp instance to file in CP2K format.
        :param filename: open file handle
        :param mode: mode argument of built-in open function ('a' or 'w')
        """

        def format_float(fnum):
            return "{0:.8f}".format(fp).rjust(15)

        def format_int(inum):
            return str(inum).rjust(5)

        fhandle.write(gpp_data['element'])

        for p_id in gpp_data['id']:
            fhandle.write(' ' + p_id)
        fhandle.write('\n')

        for n_elec in gpp_data['n_elec']:
            fhandle.write(format_int(n_elec))
        fhandle.write('\n')

        fhandle.write(format_float(gpp_data['r_loc']))
        fhandle.write(format_int(gpp_data['nexp_ppl']))

        for cexp in gpp_data['cexp_ppl']:
            fhandle.write(format_float(cexp))
        fhandle.write('\n')

        fhandle.write(format_int(gpp_data['nprj']))
        if gpp_data['nprj'] > 0:
            fhandle.write('\n')

        for radius, nproj, hprj in zip(gpp_data['r'], gpp_data['nprj_ppnl'], gpp_data['hprj_ppnl']):
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
