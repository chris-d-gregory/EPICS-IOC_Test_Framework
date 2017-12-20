import unittest
from unittest import skipIf

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import IOCRegister
from utils.testing import get_running_lewis_and_ioc

MACROS = {"MTRCTRL": "01", "AXIS1": "yes"}


class Sm300Tests(unittest.TestCase):
    """
    Tests for the Samsm300 IOC.
    """
    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("sm300")
        self.ca = ChannelAccess(device_prefix="MOT")
        self._lewis.backdoor_run_function_on_device("reset")

    def set_starting_position(self, starting_pos):
        """
        Set the starting position of the motor and check it is there.
        :param starting_pos: position to start at
        """
        self._lewis.backdoor_set_on_device("x_axis_rbv", starting_pos)
        self._lewis.backdoor_set_on_device("x_axis_sp", starting_pos)
        self.ca.assert_that_pv_is("MTR0101.RBV", starting_pos)

    def test_GIVEN_motor_at_position_WHEN_get_axis_x_ioc_position_THEN_position_is_as_expected(self):
        expected_value = 100
        self._lewis.backdoor_set_on_device("x_axis_rbv", expected_value)
        self._lewis.backdoor_set_on_device("x_axis_sp", expected_value)

        self.ca.assert_that_pv_is("MTR0101.RBV", expected_value)

    def test_GIVEN_motor_at_position_WHEN_get_axis_y_ioc_position_THEN_position_is_as_expected(self):
        expected_value = 100
        self._lewis.backdoor_set_on_device("y_axis_rbv", expected_value)
        self._lewis.backdoor_set_on_device("y_axis_sp", expected_value)

        self.ca.assert_that_pv_is("MTR0102.RBV", expected_value)

    def test_GIVEN_incorrect_axis_WHEN_get_axis_x_THEN_error_returned(self):
        self._lewis.backdoor_set_on_device("x_axis_rbv_error", "B10")

        # It doesn't appear that the motor can be made to go into an invlaid state so major alarm will have to do
        self.ca.assert_pv_alarm_is("MTR0101", ChannelAccess.ALARM_MAJOR)

    def test_GIVEN_malformed_motor_position_WHEN_get_axis_x_THEN_error_returned(self):
        self._lewis.backdoor_set_on_device("x_axis_rbv_error", "Xrubbish")

        # It doesn't appear that the motor can be made to go into an invlaid state so major alarm will have to do
        self.ca.assert_pv_alarm_is("MTR0101", ChannelAccess.ALARM_MAJOR)

    def test_GIVEN_a_motor_is_moving_WHEN_get_moving_THEN_both_axis_are_moving(self):

        expected_value = 0
        self._lewis.backdoor_set_on_device("is_moving", True)

        self.ca.assert_that_pv_is("MTR0101.DMOV", expected_value)
        self.ca.assert_that_pv_is("MTR0102.DMOV", expected_value)

    def test_GIVEN_a_motor_is_not_moving_WHEN_get_moving_THEN_both_axis_are_not_moving(self):
        expected_value = 1
        self._lewis.backdoor_set_on_device("is_moving", False)

        self.ca.assert_that_pv_is("MTR0101.DMOV", expected_value)
        self.ca.assert_that_pv_is("MTR0102.DMOV", expected_value)

    def test_GIVEN_a_motor_is_in_error_WHEN_get_moving_THEN_both_axis_are_in_error(self):
        self._lewis.backdoor_set_on_device("is_moving_error", True)

        self.ca.assert_pv_alarm_is("MTR0101", ChannelAccess.ALARM_MAJOR)
        self.ca.assert_pv_alarm_is("MTR0102", ChannelAccess.ALARM_MAJOR)

    def test_GIVEN_motor_at_position_WHEN_set_postion_THEN_motor_moves_to_the_position(self):
        expected_value = 10
        self.set_starting_position(0)
        self.ca.set_pv_value("MTR0101", expected_value)

        self.ca.assert_that_pv_is("MTR0101.RBV", expected_value)

    def test_GIVEN_a_motor_WHEN_homed_THEN_motor_moves_to_home(self):
        expected_home = 0
        self.set_starting_position(10)
        self.ca.set_pv_value("MTR0101.HOMF", 1)

        self.ca.assert_that_pv_is("MTR0101.RBV", expected_home)

    def test_GIVEN_a_motor_WHEN_homed_in_reverseTHEN_motor_moves_to_home(self):
        expected_home = 0
        self.set_starting_position(10)
        self.ca.set_pv_value("MTR0101.HOMR", 1)

        self.ca.assert_that_pv_is("MTR0101.RBV", expected_home)
