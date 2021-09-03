# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from typing import Dict, Generic, List, Optional, Sequence, Type, TypeVar

class _ExternalLibrary:

    def fetch(self):
        pass

class MitasLibrary(_ExternalLibrary):
    pass
