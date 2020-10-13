# -*- coding: utf-8 -*-
# Copyright (c), Tiziano Müller
# SPDX-License-Identifier: MIT

"""
Groups for the GTO data classes
"""

from aiida.orm import Group


class BasisSetGroup(Group):
    """Group for Gaussian.Basisset nodes"""


class PseudopotentialGroup(Group):
    """Group for Gaussian.Pseudopotential nodes"""
