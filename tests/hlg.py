import unittest
from unittest import skipIf

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import IOCRegister
from utils.testing import get_running_lewis_and_ioc

hihi_level = 400
hi_level = 350
low_level = 100
lolo_level = 50

# MACROS to use for the IOC
MACROS = {
    "HIGH_LEVEL_ALARM": hi_level,
    "HIHI_LEVEL_ALARM": hihi_level,
    "LOW_LEVEL_ALARM": low_level,
    "LOLO_LEVEL_ALARM": lolo_level}

DEVICE_PREFIX = "HLG_01"

class HlgTests(unittest.TestCase):
    """
    Tests for the HLG
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("hlg")

        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)
        self._lewis.backdoor_set_on_device("verbosity", 1)
        self._lewis.backdoor_set_on_device("prefix", 1)
        self._set_level(0)

    def _set_level(self, expected_level):
        self._lewis.backdoor_set_on_device("level", expected_level)
        self._ioc.set_simulated_value("SIM:LEVEL", expected_level)

    def test_GIVEN_level_set_WHEN_read_THEN_level_is_as_expected(self):
        expected_level = 123
        self._set_level(expected_level)

        self.ca.assert_that_pv_is("LEVEL", expected_level)
        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_NONE)

    def test_GIVEN_high_level_set_WHEN_read_THEN_minor_alarm(self):
        level = hi_level + 1
        self._set_level(level)

        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_MINOR)

    def test_GIVEN_low_level_set_WHEN_read_THEN_minor_alarm(self):
        level = low_level - 1
        self._set_level(level)

        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_MINOR)

    def test_GIVEN_hihi_level_set_WHEN_read_THEN_major_alarm(self):
        level = hihi_level + 1
        self._set_level(level)

        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_MAJOR)

    def test_GIVEN_lolo_level_set_WHEN_read_THEN_major_alarm(self):
        level = lolo_level - 1
        self._set_level(level)

        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_MAJOR)

    @skipIf(IOCRegister.uses_rec_sim, "Can not disconnect in recsim")
    def test_GIVEN_not_connected_WHEN_read_THEN_alarm_error(self):

        self._set_level(None)

        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_INVALID)

    @skipIf(IOCRegister.uses_rec_sim, "Can not set prefix in recsim")
    def test_GIVEN_prefix_set_incorrectly_WHEN_read_THEN_prefix_is_set_to_none_and_level_is_read(self):
        expected_level = 234
        self._lewis.backdoor_set_on_device("prefix", 4)
        self._set_level(expected_level)

        self.ca.assert_that_pv_is("LEVEL", expected_level)
        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_NONE)

    @skipIf(IOCRegister.uses_rec_sim, "Can not set verbosity in recsim")
    def test_GIVEN_verbosity_set_incorrectly_WHEN_read_THEN_verbosity_is_set_to_1_and_level_is_read(self):
        expected_level = 250
        self._lewis.backdoor_set_on_device("verbosity", 0)
        self._set_level(expected_level)

        self.ca.assert_that_pv_is("LEVEL", expected_level)
        self.ca.assert_pv_alarm_is("LEVEL", ChannelAccess.ALARM_NONE)
