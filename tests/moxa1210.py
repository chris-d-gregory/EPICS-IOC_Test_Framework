from __future__ import division
import unittest
from time import sleep

from utils.test_modes import TestModes
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.testing import get_running_lewis_and_ioc
from parameterized import parameterized


# Device prefix
DEVICE_PREFIX = "MOXA1210_01"

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("MOXA1210"),
        "emulator": "moxa1210",
        "emulator_protocol": "modbus",
        "macros": {
            "IEOS": r"\\r\\n",
            "OEOS": r"\\r\\n",
        }
    },
]

TEST_MODES = [TestModes.DEVSIM, ]
CHANNELS = range(16)


class Moxa1210Tests(unittest.TestCase):
    """
    Tests for the Moxa ioLogik e1210
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("moxa1210", DEVICE_PREFIX)

        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)

        # Sends a backdoor command to the device to set a discrete input (DI) value

        self._lewis.backdoor_run_function_on_device("set_di", (0, [False]*16))

    def resetDICounters(self):
        """
        Reset the counters for each DI (channel)

        We typically want to preserve our counter values for each channel even upon restart. For testing purposes
        this function will reset the counter values to 0. 
        """
        for channel_counter_pv in CHANNELS:
            self.ca.set_pv_value("CH{:02d}:DI:CNT".format(channel_counter_pv), 0)

    @parameterized.expand([
        ("CH{:02d}".format(channel), channel) for channel in CHANNELS
    ])
    def test_WHEN_DI_input_is_switched_on_THEN_only_that_channel_readback_changes_to_state_just_set(self, _, channel):
        self._lewis.backdoor_run_function_on_device("set_di", (channel, (True,)))
        self.ca.assert_that_pv_is("CH{:02d}:DI".format(channel), "High")

        # Test that all other channels are still off
        for test_channel in CHANNELS:
            if test_channel == channel:
                continue

            self.ca.assert_that_pv_is("CH{:02d}:DI".format(test_channel), "Low")

    @parameterized.expand([
        ("CH{:02d}:DI:CNT".format(channel), channel) for channel in CHANNELS
    ])
    def test_WHEN_di_input_is_triggered_THEN_di_counter_increases(self, channel_pv, channel):
        self.resetDICounters()
        self._lewis.backdoor_run_function_on_device("set_di", (channel, (True,)))

        self.ca.assert_that_pv_is(channel_pv, 1)
