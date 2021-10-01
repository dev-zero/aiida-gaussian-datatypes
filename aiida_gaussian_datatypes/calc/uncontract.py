# -*- coding: utf-8 -*-

from aiida.plugins import DataFactory
from aiida.engine import calcfunction
from icecream import ic
"""

"""

BasisSet = DataFactory("gaussian.basisset")
BasisSetFree = DataFactory("gaussian.basissetfree")

@calcfunction
def uncontract(basisset):
    """

    """
    def disassemble(block):
        n = block["n"]
        l = block["l"]
        for exp, cont in block["coefficients"]:
            yield {"n" : n,
                   "l" : l,
                   "coefficients": [[exp, 1.0]]}
    attr = basisset.attributes
    blocks = []
    for block in attr["blocks"]:
        blocks.extend([ b for b in disassemble(block) ])
    attr["blocks"] = blocks
    attr["name"] += "-uncont"
    ret = BasisSetFree(**attr)
    return ret

