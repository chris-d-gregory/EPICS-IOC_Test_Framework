import unittest
from parameterized import parameterized

from utils.test_modes import TestModes
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.testing import skip_if_recsim, skip_if_devsim, parameterized_list

# Device prefix
DEVICE_PREFIX = "ASTRIUM_01"

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("ASTRIUM")
    },
]


TEST_MODES = [TestModes.RECSIM, TestModes.DEVSIM]


class AstriumTests(unittest.TestCase):
    """
    Tests for the Astrium Chopper.
    """

    def setUp(self):
        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)

    def test_WHEN_phase_set_to_10_p_5_THEN_phase_readback_is_10_p_5(self):
        expected_phase = 10.5
        self.ca.set_pv_value("CH1:PHASE:SP", expected_phase)
        self.ca.assert_that_pv_is("CH1:PHASE", expected_phase)

    # Can only be set in values of 10
    @parameterized.expand(
        parameterized_list([
            20,
            140,
            280,
            0
        ])
    )
    def test_that_WHEN_setting_the_frequency_setpoint_THEN_it_is_set(self, _, value):
        self.ca.set_pv_value("CH1:FREQ:SP", value)
        self.ca.assert_that_pv_is("CH1:FREQ", value)

    def test_WHEN_frequency_set_to_180_THEN_actual_setpoint_not_updated(self):
        sent_frequency = 180
        self.ca.set_pv_value("CH1:FREQ:SP", sent_frequency)
        self.ca.assert_that_pv_is_not("CH1:FREQ:SP_ACTUAL", sent_frequency)
        self.ca.assert_that_pv_is_not("CH1:FREQ", sent_frequency)

    @skip_if_recsim("No state changes in recsim")
    def test_WHEN_brake_called_THEN_state_is_BRAKE(self):
        self.ca.set_pv_value("CH1:BRAKE", 1)
        self.ca.assert_that_pv_is("CH1:STATE", "BRAKE")

    @skip_if_recsim("No state changes in recsim")
    def test_WHEN_speed_set_THEN_state_is_POSITION(self):
        self.ca.set_pv_value("CH1:FREQ:SP", 10)
        self.ca.assert_that_pv_is("CH1:STATE", "POSITION")

    @skip_if_devsim("No backdoor to state in devsim")
    def test_WHEN_one_channel_state_not_ESTOP_THEN_calibration_disabled(self):
        self.ca.set_pv_value("CH1:SIM:STATE", "NOT_ESTOP")
        self.ca.set_pv_value("CH2:SIM:STATE", "E_STOP")
        # Need to process to update disabled status.
        # We don't want the db to process when disabled changes as this will write to the device.
        self.ca.process_pv("CALIB")
        self.ca.assert_that_pv_is("CALIB.STAT", self.ca.Alarms.DISABLE, timeout=1)

    @skip_if_devsim("No backdoor to state in devsim")
    def test_WHEN_both_channels_state_ESTOP_THEN_calibration_enabled(self):
        self.ca.set_pv_value("CH1:SIM:STATE", "E_STOP")
        self.ca.set_pv_value("CH2:SIM:STATE", "E_STOP")
        # Need to process to update disabled status.
        # We don't want the db to process when disabled changes as this will write to the device.
        self.ca.process_pv("CALIB")
        self.ca.assert_that_pv_is_not("CALIB.STAT", self.ca.Alarms.DISABLE, timeout=1)