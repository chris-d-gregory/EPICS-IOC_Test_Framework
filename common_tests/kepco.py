from utils.channel_access import ChannelAccess
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, skip_if_recsim, parameterized_list

from parameterized import parameterized

DEVICE_PREFIX = "KEPCO_01"
emulator_name = "kepco"


TEST_MODES = [TestModes.RECSIM, TestModes.DEVSIM]


class OutputMode(object):
    VOLTAGE = "VOLTAGE"
    CURRENT = "CURRENT"


class Status(object):
    ON = "ON"
    OFF = "OFF"


class UnitFlags(object):
    VOLTAGE = 0
    CURRENT = 1
    ON = 1
    OFF = 0

IDN_LIST = [
    ("KEPCO, BIT 4886 100-2 123456 1.8-", 1.8),
    ("KEPCO, BIT 4886 100-2, 123456, 3.3-", 3.7),
    ("KEPCO,BIT 4886 100-2,123456,", 2.2),
    ("KEPCO,BIT 4886 100-2,123456 ", 1.4),
    # With current and voltage
    ("KEPCO, BIT 4886 100-2, 23.4, 36.8, 123456 3.8-", 3.8),
    ("KEPCO, BIT 4886 100-2 28.9 10.2 123456 1.9-", 1.7),
    ("KEPCO,BIT 4886 100-2, 1.1, 0, 123456,", 2.2),
    ("KEPCO,BIT 4886 100-2, 8.0, 9.0 123456 ", 1.4),
]


class KepcoTests(object):
    """
    Tests for the KEPCO.
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("kepco", DEVICE_PREFIX)
        self.ca = ChannelAccess(default_timeout=30, device_prefix=DEVICE_PREFIX)
        self._lewis.backdoor_run_function_on_device("reset")
        self.ca.assert_that_pv_exists("VOLTAGE", timeout=30)

    def _write_voltage(self, expected_voltage):
        self._lewis.backdoor_set_on_device("voltage", expected_voltage)
        self._ioc.set_simulated_value("SIM:VOLTAGE", expected_voltage)

    def _write_current(self, expected_current):
        self._lewis.backdoor_set_on_device("current", expected_current)
        self._ioc.set_simulated_value("SIM:CURRENT", expected_current)

    def _set_IDN(self, expected_idn_no_firmware, expected_firmware):
        self._lewis.backdoor_set_on_device("idn_no_firmware", expected_idn_no_firmware)
        self._lewis.backdoor_set_on_device("firmware", expected_firmware)
        expected_idn = "{}{}".format(expected_idn_no_firmware, str(expected_firmware))[:39]  # EPICS limited to 40 chars
        self._ioc.set_simulated_value("SIM:IDN", expected_idn)
        self._ioc.set_simulated_value("SIM:FIRMWARE", str(expected_firmware))
        # Both firmware and IDN are passive so must be updated
        self.ca.process_pv("FIRMWARE")
        self.ca.process_pv("IDN")
        return expected_idn

    def _set_output_mode(self, expected_output_mode):
        self._lewis.backdoor_set_on_device("output_mode", expected_output_mode)
        self._ioc.set_simulated_value("SIM:OUTPUTMODE", expected_output_mode)

    def _set_output_status(self, expected_output_status):
        self._lewis.backdoor_set_on_device("output_status", expected_output_status)

    def test_GIVEN_voltage_set_WHEN_read_THEN_voltage_is_as_expected(self):
        expected_voltage = 1.2
        self._write_voltage(expected_voltage)
        self.ca.assert_that_pv_is("VOLTAGE", expected_voltage)

    def test_GIVEN_current_set_WHEN_read_THEN_current_is_as_expected(self):
        expected_current = 1.5
        self._write_current(expected_current)
        self.ca.assert_that_pv_is("CURRENT", expected_current)

    def test_GIVEN_setpoint_voltage_set_WHEN_read_THEN_setpoint_voltage_is_as_expected(self):
        # Get current Voltage
        current_voltage = self.ca.get_pv_value("VOLTAGE")
        # Set new Voltage via SP
        self.ca.set_pv_value("VOLTAGE:SP", current_voltage + 5)
        # Check SP RBV matches new current
        self.ca.assert_that_pv_is("VOLTAGE:SP:RBV", current_voltage + 5)

    def test_GIVEN_setpoint_current_set_WHEN_read_THEN_setpoint_current_is_as_expected(self):
        # Get current current
        current_current = self.ca.get_pv_value("CURRENT")
        # Set new Current via SP
        self.ca.set_pv_value("CURRENT:SP", current_current + 5)
        # Check SP RBV matches new current
        self.ca.assert_that_pv_is("CURRENT:SP:RBV", current_current + 5)

    def test_GIVEN_output_mode_set_WHEN_read_THEN_output_mode_is_as_expected(self):
        expected_output_mode_flag = UnitFlags.CURRENT
        expected_output_mode_str = OutputMode.CURRENT
        self._set_output_mode(expected_output_mode_flag)
        # Check OUTPUT MODE matches new OUTPUT MODE
        self.ca.assert_that_pv_is("OUTPUTMODE", expected_output_mode_str)

    def test_GIVEN_output_status_set_WHEN_read_THEN_output_STATUS_is_as_expected(self):
        expected_output_status_flag = UnitFlags.ON
        expected_output_status_str = Status.ON
        self.ca.set_pv_value("OUTPUTSTATUS:SP", expected_output_status_flag)
        self.ca.assert_that_pv_is("OUTPUTSTATUS:SP:RBV", expected_output_status_str)

    @parameterized.expand(parameterized_list(IDN_LIST))
    def test_GIVEN_idn_set_WHEN_read_THEN_idn_is_as_expected(self, _, idn_no_firmware, firmware):
        expected_idn = self._set_IDN(idn_no_firmware, firmware)
        self.ca.assert_that_pv_is("IDN", expected_idn)

    @skip_if_recsim("In rec sim you can not diconnect the device")
    def test_GIVEN_diconnected_WHEN_read_THEN_alarms_on_readbacks(self):
        self._lewis.backdoor_set_on_device("connected", False)

        self.ca.assert_that_pv_alarm_is("OUTPUTMODE", self.ca.Alarms.INVALID)
        self.ca.assert_that_pv_alarm_is("CURRENT", self.ca.Alarms.INVALID)
        self.ca.assert_that_pv_alarm_is("VOLTAGE", self.ca.Alarms.INVALID)

    @parameterized.expand(parameterized_list(IDN_LIST))
    def test_GIVEN_idn_set_AND_firmware_set_THEN_firmware_pv_correct(self, _, idn_no_firmware, firmware):
        self._set_IDN(idn_no_firmware, firmware)
        self.ca.assert_that_pv_is("FIRMWARE", firmware)
