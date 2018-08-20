from parameterized import parameterized
import unittest

from utils.channel_access import ChannelAccess
from utils.testing import parameterized_list
from hamcrest import assert_that, is_, equal_to

DEVICE_PREFIX = "KICKER_01"

# VOLTAGE CALIBRATION CONTSTANTS FOR TESTS
DAQ_MAX_VOLTAGE = 10.0
PSU_MAX_VOLTAGE = 45.0  # This is set as a macro in IOC st.cmd
VOLTAGE_CALIBRATION_RATIO = PSU_MAX_VOLTAGE / DAQ_MAX_VOLTAGE

# CURRENT CALIBRATION CONTSTANTS FOR TESTS
DAQ_MAX_CURRENT = 10.0
PSU_MAX_CURRENT = 15.0  # This is set as a macro in IOC st.cmd
CURRENT_CALIBRATION_RATIO = PSU_MAX_CURRENT / DAQ_MAX_CURRENT


class BaseTests(unittest.TestCase):
    record = None
    calibration = None

    def setUp(self):
        self.ca = ChannelAccess(20, device_prefix=DEVICE_PREFIX)

        pv_root = "DAQ:{}".format(self.record)
        self.ca.set_pv_value("DAQ:{}:SIM".format(self.record), 0)

        value_to_check = self.ca.get_pv_value("{}:_RAW".format(pv_root))[0]
        assert_that(value_to_check, is_(equal_to(0)))

    def simulate_value(self, value):
        pv_root = "DAQ:{}".format(self.record)
        self.ca.set_pv_value("{}:SIM".format(pv_root), value)
        self.ca.assert_that_pv_is("{}:SIM".format(pv_root), value)

        value_to_check = self.ca.get_pv_value("{}:_RAW".format(pv_root))[0]
        assert_that(value_to_check, is_(equal_to(value)))

    @parameterized.expand(
        parameterized_list([4.68, 10, 0, 4e-3])
    )
    def test_that_GIVEN_a_value_THEN_the_calibrated_value_is_read(self, _, value_to_set):
        # Given:
        self.simulate_value(value_to_set)

        # Then:
        expected_calibrated_value = self.calibration * value_to_set
        self.ca.assert_that_pv_is_number(self.record, expected_calibrated_value, 0.01)

    @parameterized.expand(
        parameterized_list([15, -5])
    )
    def test_that_GIVEN_a_value_out_of_range_THEN_pv_is_in_alarm(self, _, value_to_set):
        # Given:
        self.simulate_value(value_to_set)
        self.ca.assert_that_pv_is_number(self.record, value_to_set * self.calibration, 0.01)

        # Then:
        self.ca.assert_that_pv_alarm_is(self.record, self.ca.Alarms.MAJOR)


class VoltageTests(BaseTests):
    record = "VOLT"
    calibration = VOLTAGE_CALIBRATION_RATIO


class CurrentTests(BaseTests):
    record = "CURR"
    calibration = CURRENT_CALIBRATION_RATIO

