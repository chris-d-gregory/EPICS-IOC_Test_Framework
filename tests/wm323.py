import unittest

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, skip_if_recsim, skip_if_devsim

DEVICE_PREFIX = "WM323_01"


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("WM323"),
        "emulator": "wm323",
    },
]


TEST_MODES = [TestModes.DEVSIM, TestModes.RECSIM]
SPEED_LOW_LIMIT = 3
SPEED_HIGH_LIMIT = 400


class Itc503Tests(unittest.TestCase):
    """
    Tests for the wm323 IOC.
    """
    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("wm323", DEVICE_PREFIX)
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_timeout=20)
        self.ca.assert_that_pv_exists("DISABLE")

    def test_WHEN_ioc_is_started_THEN_it_is_not_disabled(self):
        self.ca.assert_that_pv_is("DISABLE", "COMMS ENABLED")

    def test_WHEN_speed_setpoint_is_sent_THEN_readback_updates(self):
        self.ca.assert_setting_setpoint_sets_readback(42, 'SPEED')

    def test_WHEN_speed_setpoint_is_set_outside_max_limits_THEN_setpoint_within(self):
        self.ca.set_pv_value("SPEED:SP", SPEED_LOW_LIMIT - 1)
        self.ca.assert_that_pv_is("SPEED:SP", SPEED_LOW_LIMIT)
        self.ca.set_pv_value("SPEED:SP", SPEED_HIGH_LIMIT + 1)
        self.ca.assert_that_pv_is("SPEED:SP", SPEED_HIGH_LIMIT)

    def test_WHEN_direction_setpoint_is_sent_THEN_readback_updates(self):
        for mode in ["Clockwise", "Anti-clockwise"]:
            self.ca.assert_setting_setpoint_sets_readback(mode, "DIRECTION")

    def test_WHEN_running_setpoint_is_sent_THEN_readback_updates(self):
        for mode in ["Running", "Stopped"]:
            self.ca.assert_setting_setpoint_sets_readback(mode, "RUNNING")
