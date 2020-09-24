import unittest
from time import sleep

from utils.emulator_launcher import DAQMxEmulatorLauncher
from utils.test_modes import TestModes
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import EPICS_TOP
from utils.testing import get_running_lewis_and_ioc, assert_log_messages

import os


# Device prefix
DEVICE_PREFIX = "DAQMXTEST"

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": os.path.join(EPICS_TOP, "support", "DAQmxBase", "master", "iocBoot",  "iocDAQmx"),
        "emulator": DEVICE_PREFIX,
        "emulator_launcher_class": DAQMxEmulatorLauncher,
        "pv_for_existence": "ACQUIRE",
    },
]


TEST_MODES = [TestModes.DEVSIM]


class DAQmxTests(unittest.TestCase):
    """
    General tests for the DAQmx.
    """
    def setUp(self):
        self.emulator, self._ioc = get_running_lewis_and_ioc(DEVICE_PREFIX, DEVICE_PREFIX)

        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)

    def test_WHEN_acquire_called_THEN_data_gathered_and_is_changing(self):
        self.ca.set_pv_value("ACQUIRE", 1)

        def non_zero_data(data):
            return all([d != 0.0 for d in data])
        self.ca.assert_that_pv_value_causes_func_to_return_true("DATA", non_zero_data)
        self.ca.assert_that_pv_value_is_changing("DATA", 1)

    def test_WHEN_emulator_disconnected_THEN_data_in_alarm_and_valid_on_reconnect(self):
        self.ca.assert_that_pv_alarm_is_not("DATA", ChannelAccess.Alarms.INVALID)
        self.emulator.disconnect_device()
        self.ca.assert_that_pv_alarm_is("DATA", ChannelAccess.Alarms.INVALID)

        # Check we don't get excessive numbers of messages if we stay disconnected for 15s (up to 15 messages seems
        # reasonable - 1 per second on average)
        with assert_log_messages(self._ioc, number_of_messages=15):
            sleep(15)
            # Double-check we are still in alarm
            self.ca.assert_that_pv_alarm_is("DATA", ChannelAccess.Alarms.INVALID)

        self.emulator.reconnect_device()
        self.ca.assert_that_pv_alarm_is_not("DATA", ChannelAccess.Alarms.INVALID, timeout=5)
        self.ca.assert_that_pv_value_is_changing("DATA", 1)


