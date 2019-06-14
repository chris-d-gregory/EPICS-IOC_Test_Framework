import unittest

from utils.ioc_launcher import get_default_ioc_dir
import os
from parameterized.parameterized import parameterized
from utils.testing import parameterized_list
from common_tests.jaws_manager_utils import JawsManagerBase, MOD_GAP
from time import sleep

# IP address of device
from utils.test_modes import TestModes

GALIL_ADDR = "128.0.0.0"

test_path = os.path.realpath(os.path.join(os.getenv("EPICS_KIT_ROOT"),
                                          "support", "motorExtensions", "master", "settings", "nimrod_jaws"))

# Create 3 Galils
IOCS = [{
            "name": "GALIL_0{}".format(i),
            "directory": get_default_ioc_dir("GALIL", i),
            "pv_for_existence": "AXIS1",
            "macros": {
                "GALILADDR": GALIL_ADDR,
                "MTRCTRL": "0{}".format(i),
                "GALILCONFIGDIR": test_path.replace("\\", "/"),
            }
           } for i in range(1, 4)]

TEST_MODES = [TestModes.RECSIM]


class NimrodJawsManagerTests(JawsManagerBase, unittest.TestCase):
    """
    Tests for the Jaws Manager on Nimrod.
    """
    def get_num_of_jaws(self):
        return 6

    @parameterized.expand(parameterized_list([
        # Numbers taken from the VI
        (100, 10, [70.5, 63.1, 44.8, 29.4, 21.2, 10]),
        (70, 40, [60.2, 57.7, 51.6, 46.5, 43.7, 40]),
        (130, 5, [89, 78.8, 53.4, 31.9, 20.6, 5]),
    ]))
    def test_WHEN_sample_gap_set_THEN_other_jaws_as_expected(self, _, mod_gap, sample_gap, expected):
        self.ca.set_pv_value(MOD_GAP.format("V"), mod_gap)
        sleep(1)  # Setting moderator and sample in quick succession causes issues
        self._test_WHEN_sample_gap_set_THEN_other_jaws_as_expected("V", sample_gap, expected)
