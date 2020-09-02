import unittest

from six.moves import cStringIO as StringIO

from aiida_gaussian_datatypes.basisset.utils import parse_single_cp2k_basisset, write_cp2k_basisset

from . import TEST_DIR


class CP2KBasisSetParsingTest(unittest.TestCase):
    def test_single_parse(self):
        content = """\
 H  DZVP-MOLOPT-GTH DZVP-MOLOPT-GTH-q1
 1
 2 0 1 7 2 1
     11.478000339908  0.024916243200 -0.012512421400  0.024510918200
      3.700758562763  0.079825490000 -0.056449071100  0.058140794100
      1.446884268432  0.128862675300  0.011242684700  0.444709498500
      0.716814589696  0.379448894600 -0.418587548300  0.646207973100
      0.247918564176  0.324552432600  0.590363216700  0.803385018200
      0.066918004004  0.037148121400  0.438703133000  0.892971208700
      0.021708243634 -0.001125195500 -0.059693171300  0.120101316500
"""

        parsed = parse_single_cp2k_basisset(content.splitlines())

        result = {
            "name": "DZVP-MOLOPT-GTH-q1",
            "element": "H",
            "n_el": 1,
            "tags": ["DZVP", "MOLOPT", "GTH", "q1"],
            "aliases": ["DZVP-MOLOPT-GTH-q1", "DZVP-MOLOPT-GTH"],
            "blocks": [
                {
                    "n": 2,
                    "l": [(0, 2), (1, 1)],
                    "coefficients": [
                        [11.478000339908, 0.024916243200, -0.012512421400, 0.024510918200],
                        [3.700758562763, 0.079825490000, -0.056449071100, 0.058140794100],
                        [1.446884268432, 0.128862675300, 0.011242684700, 0.444709498500],
                        [0.716814589696, 0.379448894600, -0.418587548300, 0.646207973100],
                        [0.247918564176, 0.324552432600, 0.590363216700, 0.803385018200],
                        [0.066918004004, 0.037148121400, 0.438703133000, 0.892971208700],
                        [0.021708243634, -0.001125195500, -0.059693171300, 0.120101316500],
                    ],
                }
            ],
        }

        self.maxDiff = None
        # compare everything except the blocks
        self.assertEqual(parsed, result)

    def test_roundtrip_single(self):

        with open(TEST_DIR.joinpath("BASIS_MOLOPT.H"), "r") as fhandle:
            content = fhandle.read()

        parsed = parse_single_cp2k_basisset(content.splitlines())

        output = StringIO()
        write_cp2k_basisset(output, **{k: v for k, v in parsed.items() if k in ["element", "name", "blocks"]})

        # ignore the first element since the family name might contain aliases we are not going to write
        self.assertEqual(
            [line.strip() for line in content.splitlines()[1:]],  # do not compare the name
            [line.lstrip() for line in output.getvalue().splitlines()[2:]],  # do not compare the comment or the name
        )

    def test_roundtrip_multi_shell(self):

        with open(TEST_DIR.joinpath("BASIS_pob-TZVP.H"), "r") as fhandle:
            content = fhandle.read()

        parsed = parse_single_cp2k_basisset(content.splitlines())

        output = StringIO()
        write_cp2k_basisset(
            output,
            **{k: v for k, v in parsed.items() if k in ["element", "name", "blocks"]},
            fmts=(" > #12.9f", " > #12.9f"),  # this basis uses a shorter format
        )

        # ignore the first element since the family name might contain aliases we are not going to write
        self.assertEqual(
            [line.strip() for line in content.splitlines()[1:]],  # do not compare the name
            [line.lstrip() for line in output.getvalue().splitlines()[2:]],  # do not compare the comment or the name
        )
