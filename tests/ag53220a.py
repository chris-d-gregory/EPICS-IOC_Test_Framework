import unittest

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, skip_if_recsim


DEVICE_PREFIX = "AG53220A_01"


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("AG53220A"),
        "emulator": "Ag53220A",
    },
]


TEST_MODES = [TestModes.RECSIM]


class Ag53220ATests(unittest.TestCase):
    """
    Tests for the Ag53220A IOC.
    """
    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("Ag53220A", DEVICE_PREFIX)
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)
        self.ca.wait_for("DISABLE", timeout=30)

    def test_WHEN_ioc_is_started_THEN_ioc_is_not_disabled(self):
        self.ca.assert_that_pv_is("DISABLE", "COMMS ENABLED")

    def test_WHEN_start_set_THEN_start_readback_set(self):
        self.ca.assert_setting_setpoint_sets_readback(0, "START", "START:SP", 0)
        self.ca.assert_setting_setpoint_sets_readback(1, "START", "START:SP", 1)