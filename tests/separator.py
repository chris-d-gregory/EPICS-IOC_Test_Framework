import unittest

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes

DEVICE_PREFIX = "SEPRTR_01"
DAQ = "DAQ"
MAX_DAQ_VOLT = 10.
MAX_SEPARATOR_VOLT = 200.
MAX_SEPARATOR_CURR = 2.5
DAQ_VOLT_SCALE_FACTOR = MAX_DAQ_VOLT / MAX_SEPARATOR_VOLT
DAQ_CURR_SCALE_FACTOR = MAX_DAQ_VOLT / MAX_SEPARATOR_CURR

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("SEPRTR"),
        "macros": {"DAQMX": DAQ,
                   },
    },
]


TEST_MODES = [TestModes.RECSIM]

# Note that it is difficult to test the Current readback in Recsim because it is only a readback value, and relates
# closely to the voltage.


class PowerStatusTests(unittest.TestCase):
    def setUp(self):
        self.ca = ChannelAccess(20, device_prefix=DEVICE_PREFIX)
        self.ca.set_pv_value("VOLT:SP", 0)
        self.ca.assert_that_pv_is("VOLT:SP", 0)
        self.ca.assert_that_pv_is("POWER:STAT", "OFF")

    def test_GIVEN_psu_off_WHEN_voltage_setpoint_changed_higher_than_threshold_THEN_psu_status_changes_on(self):
        # GIVEN
        # asserted in setUp
        # WHEN
        self.ca.set_pv_value("VOLT:SP", 100)
        # THEN
        self.ca.assert_that_pv_is("POWER:STAT", "ON")

    def test_GIVEN_psu_on_WHEN_voltage_setpoint_changed_lower_than_threshold_THEN_psu_status_changes_off(self):
        # GIVEN
        self.ca.set_pv_value("VOLT:SP", 10)
        self.ca.assert_that_pv_is("VOLT", 10)
        self.ca.assert_that_pv_is("POWER:STAT", "ON")
        # WHEN
        self.ca.set_pv_value("VOLT:SP", 0)
        # THEN
        self.ca.assert_that_pv_is("POWER:STAT", "OFF")


class VoltageTests(unittest.TestCase):
    def setUp(self):
        self.ca = ChannelAccess(20, device_prefix=DEVICE_PREFIX)
        self.ca.set_pv_value("VOLT:SP", 0)
        self.ca.assert_that_pv_is("VOLT:SP", 0)

    def test_GIVEN_sim_val_0_and_data_0_WHEN_voltage_set_point_changed_THEN_data_changed(self):
        # GIVEN
        self.ca.set_pv_value("{}:VOLT:SIM".format(DAQ), 0)
        self.ca.assert_that_pv_is("{}:VOLT:SP:DATA".format(DAQ), 0)
        # WHEN
        self.ca.set_pv_value("VOLT:SP", 20.)
        # THEN
        self.ca.assert_that_pv_is("{}:VOLT:SP:DATA".format(DAQ), 20. * DAQ_VOLT_SCALE_FACTOR)


    def test_WHEN_set_THEN_the_voltage_changes(self):
        # WHEN
        self.ca.set_pv_value("VOLT:SP", 50.)
        # THEN
        self.ca.assert_that_pv_is("VOLT", 50.)

    def test_GIVEN_voltage_in_range_WHEN_setpoint_goes_above_range_THEN_setpoint_max(self):
        # GIVEN
        self.ca.set_pv_value("VOLT:SP", 30)
        self.ca.assert_that_pv_is("VOLT", 30)
        # WHEN
        self.ca.set_pv_value("VOLT:SP", 215.)
        # THEN
        self.ca.assert_that_pv_is("VOLT", 200)

    def test_GIVEN_voltage_in_range_WHEN_setpoint_goes_above_range_THEN_setpoint_min(self):
        # GIVEN
        self.ca.set_pv_value("VOLT:SP", 30)
        self.ca.assert_that_pv_is("VOLT", 30)
        # WHEN
        self.ca.set_pv_value("VOLT:SP", -50)
        # THEN
        self.ca.assert_that_pv_is("VOLT", 0)