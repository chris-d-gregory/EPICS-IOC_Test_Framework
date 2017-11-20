import unittest
from unittest import skipIf

import datetime

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import IOCRegister
from utils.testing import get_running_lewis_and_ioc

# MACROS to use for the IOC
MACROS = {}

# Device prefix
DEVICE_PREFIX = "FZJDDFCH_01"


class Fzj_dd_fermi_chopperTests(unittest.TestCase):
    """
    Tests for the FZJ Digital Drive Fermi Chopper Controller
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("fzj_dd_fermi_chopper")

        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)
        # self._lewis.backdoor_set_on_device("address", ADDRESS)

    def _set_value(self, expected_value):
        self._lewis.backdoor_set_on_device("magnetic_bearing_status", expected_value)
        self._ioc.set_simulated_value("SIM:MB:STATUS", expected_value)

    def _set_all_status(self, frequency_reference=10, frequency_setpoint=10, frequency=10, phase_setpoint=10,
                        phase=10, phase_status="NOK", magnetic_bearing="OFF", magnetic_bearing_status="NOK",
                        magnetic_bearing_integrator=10):

        start = datetime.datetime.now()

        self._lewis.backdoor_set_on_device("frequency_reference", frequency_reference)
        self._lewis.backdoor_set_on_device("frequency_setpoint", frequency_setpoint)
        self._lewis.backdoor_set_on_device("frequency", frequency)
        self._lewis.backdoor_set_on_device("phase_setpoint", phase_setpoint)
        self._lewis.backdoor_set_on_device("phase", phase)
        self._lewis.backdoor_set_on_device("phase_status", phase_status)
        self._lewis.backdoor_set_on_device("magnetic_bearing", magnetic_bearing)
        self._lewis.backdoor_set_on_device("magnetic_bearing_status", magnetic_bearing_status)
        self._lewis.backdoor_set_on_device("magnetic_bearing_integrator", magnetic_bearing_integrator)

        self._ioc.set_simulated_value("SIM:FREQ:REF", frequency_reference)
        self._ioc.set_simulated_value("SIM:FREQ:SP:RBV", frequency_setpoint)
        self._ioc.set_simulated_value("SIM:FREQ", frequency)
        self._ioc.set_simulated_value("SIM:PHAS:SP:RBV", phase_setpoint)
        self._ioc.set_simulated_value("SIM:PHAS", phase)
        self._ioc.set_simulated_value("SIM:PHAS:STATUS", phase_status)
        self._ioc.set_simulated_value("SIM:MB", magnetic_bearing)
        self._ioc.set_simulated_value("SIM:MB:STATUS", magnetic_bearing_status)
        self._ioc.set_simulated_value("SIM:MB:INT", magnetic_bearing_integrator)

        print "elapsed {}".format(datetime.datetime.now() - start)

    def test_GIVEN_frequency_reference_WHEN_read_all_status_THEN_value_is_as_expected(self):
        expected_value = 50
        self._set_all_status(frequency_reference=expected_value)

        self.ca.assert_that_pv_is("FREQ:REF", expected_value)
        self.ca.assert_pv_alarm_is("FREQ:REF", ChannelAccess.ALARM_NONE)

    def test_GIVEN_frequency_setpoint_WHEN_read_all_status_THEN_value_is_as_expected(self):
        expected_value = 60
        self._set_all_status(frequency_setpoint=expected_value)

        self.ca.assert_that_pv_is("FREQ:SP:RBV", expected_value)
        self.ca.assert_pv_alarm_is("FREQ:SP:RBV", ChannelAccess.ALARM_NONE)

    def test_GIVEN_frequency_WHEN_read_all_status_THEN_value_is_as_expected(self):
        expected_value = 35
        self._set_all_status(frequency=expected_value)

        self.ca.assert_that_pv_is("FREQ", expected_value)
        self.ca.assert_pv_alarm_is("FREQ", ChannelAccess.ALARM_NONE)

    def test_GIVEN_phase_setpoint_WHEN_read_all_status_THEN_value_is_as_expected(self):
        expected_value = 45
        self._set_all_status(phase_setpoint=expected_value)

        self.ca.assert_that_pv_is("PHAS:SP:RBV", expected_value)
        self.ca.assert_pv_alarm_is("PHAS:SP:RBV", ChannelAccess.ALARM_NONE)

    def test_GIVEN_phase_WHEN_read_all_status_THEN_value_is_as_expected(self):
        expected_value = 65
        self._set_all_status(phase=expected_value)

        self.ca.assert_that_pv_is("PHAS", expected_value)
        self.ca.assert_pv_alarm_is("PHAS", ChannelAccess.ALARM_NONE)

    def test_GIVEN_phase_status_WHEN_read_all_status_THEN_status_is_as_expected(self):
        expected_value = "OK"
        self._set_all_status(phase_status=expected_value)

        self.ca.assert_that_pv_is("PHAS:STATUS", expected_value)
        self.ca.assert_pv_alarm_is("PHAS:STATUS", ChannelAccess.ALARM_NONE)

    def test_GIVEN_magnetic_bearing_WHEN_read_all_status_THEN_status_is_as_expected(self):
        expected_value = "ON"
        self._set_all_status(magnetic_bearing=expected_value)

        self.ca.assert_that_pv_is("MB", expected_value)
        self.ca.assert_pv_alarm_is("MB", ChannelAccess.ALARM_NONE)

    def test_GIVEN_magnetic_bearing_status_WHEN_read_all_status_THEN_status_is_as_expected(self):
        expected_value = "OK"
        self._set_all_status(magnetic_bearing_status=expected_value)

        self.ca.assert_that_pv_is("MB:STATUS", expected_value)
        self.ca.assert_pv_alarm_is("MB:STATUS", ChannelAccess.ALARM_NONE)

    def test_GIVEN_magnetic_bearing_integrator_WHEN_read_all_status_THEN_value_is_as_expected(self):
        expected_value = -27
        self._set_all_status(magnetic_bearing_integrator=expected_value)

        self.ca.assert_that_pv_is("MB:INT", expected_value)
        self.ca.assert_pv_alarm_is("MB:INT", ChannelAccess.ALARM_NONE)
