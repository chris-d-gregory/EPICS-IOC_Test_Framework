import unittest
from contextlib import contextmanager
from time import sleep

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import IOCRegister, get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc, skip_if_recsim


DEVICE_PREFIX = "FERMCHOP_01"


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("FERMCHOP"),
        "emulator": "fermichopper",
    },
]


TEST_MODES = [TestModes.RECSIM, TestModes.DEVSIM]


class FermichopperTests(unittest.TestCase):
    """
    Tests for the Fermi Chopper IOC.
    """

    valid_commands = ["0001", "0002", "0003", "0004", "0005"]

    # Values that will be tested in the parametrized tests.
    test_chopper_speeds = [100, 350, 600]
    test_delay_durations = [0, 2.5, 18]
    test_gatewidth_values = [0, 0.5, 5]
    test_temperature_values = [20.0, 25.0, 37.5, 47.5]
    test_current_values = [0, 1.37, 2.22]
    test_voltage_values = [0, 282.9, 333.3]
    test_autozero_values = [-5.0, -2.22, 0, 1.23, 5]

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc("fermichopper", DEVICE_PREFIX)

        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX, default_timeout=30)
        self.ca.wait_for("SPEED")

        self.ca.set_pv_value("DELAY:SP", 0)
        self.ca.set_pv_value("GATEWIDTH:SP", 0)
        self.ca.assert_that_pv_is_number("DELAY:SP:RBV", 0)
        self.ca.assert_that_pv_is_number("GATEWIDTH", 0)

        if not IOCRegister.uses_rec_sim:
            self._lewis.backdoor_run_function_on_device("reset")

    def is_device_broken(self):
        if IOCRegister.uses_rec_sim:
            return False  # In recsim, assume device is always ok
        else:
            return self._lewis.backdoor_get_from_device("is_broken") != "False"

    def tearDown(self):
        self.assertFalse(self.is_device_broken(), "Device was broken.")

    def _turn_on_bearings_and_run(self):
        self.ca.set_pv_value("COMMAND:SP", 4)  # Switch magnetic bearings on
        self.ca.assert_that_pv_is("STATUS.B3", "1")
        self.ca.set_pv_value("COMMAND:SP", 3)  # Switch drive on and run
        self.ca.assert_that_pv_is("STATUS.B5", "1")

    def test_WHEN_ioc_is_started_THEN_ioc_is_not_disabled(self):
        self.ca.assert_that_pv_is("DISABLE", "COMMS ENABLED")

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_last_command_is_set_via_backdoor_THEN_pv_updates(self):
        for value in self.valid_commands:
            self._lewis.backdoor_set_on_device("last_command", value)
            self.ca.assert_that_pv_is("LASTCOMMAND", value)

    def test_WHEN_speed_setpoint_is_set_THEN_readback_updates(self):
        for speed in self.test_chopper_speeds:
            self.ca.set_pv_value("SPEED:SP", speed)
            self.ca.assert_that_pv_is("SPEED:SP", speed)
            self.ca.assert_pv_alarm_is("SPEED:SP", self.ca.ALARM_NONE)
            self.ca.assert_that_pv_is("SPEED:SP:RBV", speed)
            self.ca.assert_pv_alarm_is("SPEED:SP:RBV", self.ca.ALARM_NONE)

    def test_WHEN_delay_setpoint_is_set_THEN_readback_updates(self):
        for value in self.test_delay_durations:
            self.ca.set_pv_value("DELAY:SP", value)
            self.ca.assert_that_pv_is("DELAY:SP", value)
            self.ca.assert_pv_alarm_is("DELAY:SP", self.ca.ALARM_NONE)
            self.ca.assert_that_pv_is_number("DELAY:SP:RBV", value, tolerance=0.05)
            self.ca.assert_pv_alarm_is("DELAY:SP:RBV", self.ca.ALARM_NONE)

    def test_WHEN_gatewidth_is_set_THEN_readback_updates(self):
        for value in self.test_gatewidth_values:
            self.ca.set_pv_value("GATEWIDTH:SP", value)
            self.ca.assert_that_pv_is("GATEWIDTH:SP", value)
            self.ca.assert_pv_alarm_is("GATEWIDTH:SP", self.ca.ALARM_NONE)
            self.ca.assert_that_pv_is_number("GATEWIDTH", value, tolerance=0.05)
            self.ca.assert_pv_alarm_is("GATEWIDTH", self.ca.ALARM_NONE)

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_autozero_voltages_are_set_via_backdoor_THEN_pvs_update(self):
        for number in ["1", "2"]:
            for boundary in ["upper", "lower"]:
                for value in self.test_autozero_values:
                    self._lewis.backdoor_set_on_device("autozero_{n}_{b}".format(n=number, b=boundary), value)
                    self.ca.assert_that_pv_is_number("AUTOZERO:{n}:{b}".format(n=number, b=boundary.upper()), value, tolerance=0.05)
                    self.ca.assert_pv_alarm_is("AUTOZERO:{n}:{b}".format(n=number, b=boundary.upper()), self.ca.ALARM_NONE)

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_drive_voltage_is_set_via_backdoor_THEN_pv_updates(self):
        for voltage in self.test_voltage_values:
            self._lewis.backdoor_set_on_device("voltage", voltage)
            self.ca.assert_that_pv_is_number("VOLTAGE", voltage, tolerance=0.1)
            self.ca.assert_pv_alarm_is("VOLTAGE", self.ca.ALARM_NONE)

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_drive_current_is_set_via_backdoor_THEN_pv_updates(self):
        for current in self.test_current_values:
            self._lewis.backdoor_set_on_device("current", current)
            self.ca.assert_that_pv_is_number("CURRENT", current, tolerance=0.1)
            self.ca.assert_pv_alarm_is("CURRENT", self.ca.ALARM_NONE)

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_the_electronics_temperature_is_set_via_backdoor_THEN_pv_updates(self):
        for temp in self.test_temperature_values:
            self._lewis.backdoor_set_on_device("electronics_temp", temp)
            self.ca.assert_that_pv_is_number("TEMP:ELECTRONICS", temp, tolerance=0.2)
            self.ca.assert_pv_alarm_is("TEMP:ELECTRONICS", self.ca.ALARM_NONE)

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_the_motor_temperature_is_set_via_backdoor_THEN_pv_updates(self):
        for temp in self.test_temperature_values:
            self._lewis.backdoor_set_on_device("motor_temp", temp)
            self.ca.assert_that_pv_is_number("TEMP:MOTOR", temp, tolerance=0.2)
            self.ca.assert_pv_alarm_is("TEMP:MOTOR", self.ca.ALARM_NONE)

    @skip_if_recsim("In rec sim this test fails")
    def test_GIVEN_a_stopped_chopper_WHEN_start_command_is_sent_THEN_chopper_goes_to_setpoint(self):

        for speed in self.test_chopper_speeds:
            # Setup setpoint speed
            self.ca.set_pv_value("SPEED:SP", speed)
            self.ca.assert_that_pv_is_number("SPEED:SP:RBV", speed)

            self._turn_on_bearings_and_run()

            self.ca.assert_that_pv_is_number("SPEED", speed, tolerance=0.1)

    @skip_if_recsim("In rec sim this test fails")
    def test_GIVEN_a_stopped_chopper_WHEN_start_command_is_sent_without_magnetic_bearings_on_THEN_chopper_does_not_go_to_setpoint(self):

        self.ca.assert_that_pv_is_number("SPEED", 0)

        # Switch OFF magnetic bearings
        self.ca.set_pv_value("COMMAND:SP", 5)
        self.ca.assert_that_pv_is("LASTCOMMAND", "0005")
        self.ca.assert_that_pv_is("STATUS.B3", "0")

        for speed in self.test_chopper_speeds:
            # Setup setpoint speed
            self.ca.set_pv_value("SPEED:SP", speed)
            self.ca.assert_that_pv_is_number("SPEED:SP:RBV", speed)

            # Run mode ON
            self.ca.set_pv_value("COMMAND:SP", 3)
            # Ensure the ON command has been ignored and last command is still "switch off bearings"
            self.ca.assert_that_pv_is("LASTCOMMAND", "0005")

            self.ca.assert_that_pv_is_number("SPEED", 0, tolerance=0.1)

    @skip_if_recsim("In rec sim this test fails")
    def test_GIVEN_a_chopper_at_speed_WHEN_switch_off_magnetic_bearings_command_is_sent_THEN_magnetic_bearings_do_not_switch_off(self):

        speed = 150

        # Setup setpoint speed
        self.ca.set_pv_value("SPEED:SP", speed)
        self.ca.assert_that_pv_is_number("SPEED:SP:RBV", speed)

        # Run mode ON
        self._turn_on_bearings_and_run()

        # Wait for chopper to get up to speed
        self.ca.assert_that_pv_is_number("SPEED", speed, tolerance=0.1)

        # Attempt to switch OFF magnetic bearings
        self.ca.set_pv_value("COMMAND:SP", 5)

        # Assert that bearings did not switch off
        sleep(5)
        self.ca.assert_that_pv_is("LASTCOMMAND", "0003")
        self.ca.assert_that_pv_is("STATUS.B3", "1")
        self.ca.assert_that_pv_is("SPEED", speed)

    @skip_if_recsim("In rec sim this test fails")
    def test_GIVEN_a_stopped_chopper_WHEN_switch_on_and_off_magnetic_bearings_commands_are_sent_THEN_magnetic_bearings_switch_on_and_off(self):

        # Switch ON magnetic bearings
        self.ca.set_pv_value("COMMAND:SP", 4)
        self.ca.assert_that_pv_is("LASTCOMMAND", "0004")
        self.ca.assert_that_pv_is("STATUS.B3", "1")

        # Switch OFF magnetic bearings
        self.ca.set_pv_value("COMMAND:SP", 5)
        self.ca.assert_that_pv_is("LASTCOMMAND", "0005")
        self.ca.assert_that_pv_is("STATUS.B3", "0")

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_chopper_speed_is_too_high_THEN_status_updates(self):

        too_fast = 700

        # Turn on magnetic bearings otherwise device will report it is broken
        self._lewis.backdoor_set_on_device("magneticbearing", True)
        self.ca.assert_that_pv_is("STATUS.B3", "1")

        self._lewis.backdoor_set_on_device("speed", too_fast)
        self.ca.assert_that_pv_is("STATUS.BA", "1")

        self._lewis.backdoor_set_on_device("speed", 0)
        self.ca.assert_that_pv_is("STATUS.BA", "0")

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_chopper_parameters_are_set_THEN_status_updates(self):

        for command_number, b6, b8, b9 in [(6, 1, 0, 0), (7, 0, 1, 0), (8, 0, 0, 1)]:

            # Magnetic bearings should have been turned off in setUp
            self.ca.assert_that_pv_is("STATUS.B3", "0")

            self.ca.set_pv_value("COMMAND:SP", command_number)
            self.ca.assert_that_pv_is("LASTCOMMAND", "000{}".format(command_number))

            self.ca.assert_that_pv_is("STATUS.B6", "{}".format(b6))
            self.ca.assert_that_pv_is("STATUS.B8", "{}".format(b8))
            self.ca.assert_that_pv_is("STATUS.B9", "{}".format(b9))

    @skip_if_recsim("Uses lewis backdoor")
    def test_WHEN_electronics_temperature_is_too_high_THEN_over_temperature_is_true(self):
        self.ca.assert_that_pv_is("TEMP:RANGECHECK", 0)
        self._lewis.backdoor_set_on_device("electronics_temp", 46)
        self.ca.assert_that_pv_is("TEMP:RANGECHECK", 1)

    @skip_if_recsim("Uses lewis backdoor")
    def test_WHEN_motor_temperature_is_too_high_THEN_over_temperature_is_true(self):
        self.ca.assert_that_pv_is("TEMP:RANGECHECK", 0)
        self._lewis.backdoor_set_on_device("motor_temp", 46)
        self.ca.assert_that_pv_is("TEMP:RANGECHECK", 1)

    @skip_if_recsim("Uses lewis backdoor")
    def test_GIVEN_autozero_voltages_are_out_of_range_WHEN_chopper_is_moving_THEN_switch_drive_on_and_stop_is_sent(
            self):
        for number in [1, 2]:
            for position in ["upper", "lower"]:
                self.ca.assert_that_pv_is("AUTOZERO:RANGECHECK", 0)

                # Set autozero voltage too high
                self._lewis.backdoor_set_on_device("autozero_{n}_{p}".format(n=number, p=position), 3.2)

                # Assert
                self.ca.assert_that_pv_is("AUTOZERO:RANGECHECK", 1)

                # Reset relevant autozero voltage back to zero
                self._lewis.backdoor_set_on_device("autozero_{n}_{p}".format(n=number, p=position), 0)
                self.ca.assert_that_pv_is_number("AUTOZERO:{n}:{p}"
                                                 .format(n=number, p=position.upper()), 0, tolerance=0.1)

    @skip_if_recsim("Uses lewis backdoor")
    def test_WHEN_voltage_and_current_are_varied_THEN_power_pv_is_the_product_of_current_and_voltage(self):
        for voltage in self.test_voltage_values:
            for current in self.test_current_values:
                self._lewis.backdoor_set_on_device("voltage", voltage)
                self._lewis.backdoor_set_on_device("current", current)
                self.ca.assert_that_pv_is_number("POWER", current * voltage, tolerance=0.5)

    @contextmanager
    def _lie_about(self, lie):
        if IOCRegister.uses_rec_sim:
            raise IOError("Can't use lewis backdoor in recsim!")

        self._lewis.backdoor_set_on_device("is_lying_about_{}".format(lie), True)
        try:
            yield
        finally:
            self._lewis.backdoor_set_on_device("is_lying_about_{}".format(lie), False)

    def _lie_about_delay_setpoint_readback(self):
        return self._lie_about("delay_sp_rbv")

    def _lie_about_gatewidth(self):
        return self._lie_about("gatewidth")

    @skip_if_recsim("Lying about setpoint readback not possible in recsim")
    def test_GIVEN_device_lies_about_delay_setpoint_WHEN_setting_a_delay_THEN_keeps_trying_until_device_does_not_lie(self):

        test_value = 567.8
        tolerance = 0.05

        self.ca.set_pv_value("DELAY:SP", test_value)
        self.ca.assert_that_pv_is_number("DELAY:SP:RBV", test_value, tolerance=tolerance)

        with self._lie_about_delay_setpoint_readback():
            self.ca.assert_pv_value_causes_func_to_return_true("DELAY:SP:RBV", lambda v: abs(v - test_value) > tolerance)

            # Some time later the driver should resend the setpoint which causes the device to behave properly again:
            self.ca.assert_that_pv_is_number("DELAY:SP:RBV", test_value, tolerance=tolerance)

    @skip_if_recsim("Lying about gate width not possible in recsim")
    def test_GIVEN_device_lies_about_gatewidth_WHEN_setting_a_gatewidth_THEN_keeps_trying_until_device_does_not_lie(self):

        test_value = 567.8
        tolerance = 0.05

        self.ca.set_pv_value("GATEWIDTH:SP", test_value)
        self.ca.assert_that_pv_is_number("GATEWIDTH", test_value, tolerance=tolerance)

        with self._lie_about_gatewidth():
            self.ca.assert_pv_value_causes_func_to_return_true("GATEWIDTH", lambda v: abs(v - test_value) > tolerance)

            # Some time later the driver should resend the setpoint which causes the device to behave properly again:
            self.ca.assert_that_pv_is_number("GATEWIDTH", test_value, tolerance=tolerance)

    @skip_if_recsim("Device breakage not simulated in RECSIM")
    def test_GIVEN_setpoint_is_already_at_600Hz_WHEN_setting_setpoint_to_600Hz_THEN_device_does_not_break(self):

        self._turn_on_bearings_and_run()

        self.ca.set_pv_value("SPEED:SP", 600)
        self.ca.assert_that_pv_is_number("SPEED", 600, tolerance=0.1)

        self.ca.set_pv_value("SPEED:SP", 600)
        self.ca.assert_that_pv_is_number("SPEED", 600, tolerance=0.1)

        # Assertion that device is not broken occurs in tearDown()

    @skip_if_recsim("Device breakage not simulated in RECSIM")
    def test_GIVEN_setpoint_is_at_600Hz_and_device_already_running_WHEN_send_run_command_THEN_device_does_not_break(self):

        self._turn_on_bearings_and_run()

        self.ca.set_pv_value("SPEED:SP", 600)
        self.ca.assert_that_pv_is_number("SPEED", 600, tolerance=0.1)

        self.ca.set_pv_value("COMMAND:SP", 3)  # Switch drive on and run

        # Assertion that device is not broken occurs in tearDown()

    #
    #   Mandatory safety tests
    #
    #   The following behaviours MUST be implemented by the chopper according to the manual
    #

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_chopper_speed_is_too_high_THEN_switch_drive_off_is_sent(self):
        self._lewis.backdoor_set_on_device("magneticbearing", True)
        self.ca.assert_that_pv_is("STATUS.B3", "1")

        # Reset last command so that we can tell that it's changed later on
        self._lewis.backdoor_set_on_device("last_command", "0000")
        self.ca.assert_that_pv_is("LASTCOMMAND", "0000")

        # Speed = 610, this is higher than the maximum allowed speed (606)
        self._lewis.backdoor_set_on_device("speed", 610)

        # Assert that "switch drive off" was sent
        self.ca.assert_that_pv_is("LASTCOMMAND", "0002")

    @skip_if_recsim("In rec sim this test fails")
    def test_GIVEN_magnetic_bearing_is_off_WHEN_chopper_speed_is_moving_THEN_switch_drive_on_and_stop_is_sent(self):

        # Magnetic bearings should have been turned off in setUp
        self.ca.assert_that_pv_is("STATUS.B3", "0")

        # Reset last command so that we can tell that it's changed later on
        self._lewis.backdoor_set_on_device("last_command", "0000")
        self.ca.assert_that_pv_is("LASTCOMMAND", "0000")

        # Speed = 7 because that's higher than the threshold in the IOC (5)
        # but lower than the threshold in the emulator (10)
        self._lewis.backdoor_set_on_device("speed", 7)

        # Assert that "switch drive on and stop" was sent
        self.ca.assert_that_pv_is("LASTCOMMAND", "0001")

    @skip_if_recsim("In rec sim this test fails")
    def test_GIVEN_autozero_voltages_are_out_of_range_WHEN_chopper_is_moving_THEN_switch_drive_on_and_stop_is_sent(self):
        for number in [1, 2]:
            for position in ["upper", "lower"]:

                # Reset last command so that we can tell that it's changed later on
                while not self.ca.get_pv_value("LASTCOMMAND") == "0000":
                    self._lewis.backdoor_set_on_device("last_command", "0000")
                    sleep(0.1)

                # Assert that the last command is zero as expected
                self.ca.assert_that_pv_is("LASTCOMMAND", "0000")
                # Check that the last command is not being set to something else by the IOC
                self.ca.assert_pv_value_is_unchanged("LASTCOMMAND", wait=10)

                # Set autozero voltage too high and set device moving
                self._lewis.backdoor_set_on_device("autozero_{n}_{p}".format(n=number, p=position), 3.2)
                self._lewis.backdoor_set_on_device("speed", 7)

                # Assert that "switch drive on and stop" was sent
                self.ca.assert_that_pv_is("LASTCOMMAND", "0001")

                # Reset relevant autozero voltage back to zero
                self._lewis.backdoor_set_on_device("autozero_{n}_{p}".format(n=number, p=position), 0)
                self.ca.assert_that_pv_is_number("AUTOZERO:{n}:{p}".format(n=number, p=position.upper()), 0, tolerance=0.1)

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_motor_temperature_is_too_high_THEN_switch_drive_off_is_sent(self):

        # Reset last command so that we can tell that it's changed later on
        self._lewis.backdoor_set_on_device("last_command", "0000")
        self.ca.assert_that_pv_is("LASTCOMMAND", "0000")

        # Temperature = 46, this is higher than the allowed value (45)
        self._lewis.backdoor_set_on_device("motor_temp", 46)

        # Assert that "switch drive off" was sent
        self.ca.assert_that_pv_is("LASTCOMMAND", "0002")

    @skip_if_recsim("In rec sim this test fails")
    def test_WHEN_electronics_temperature_is_too_high_THEN_switch_drive_off_is_sent(self):
        # Reset last command so that we can tell that it's changed later on
        self._lewis.backdoor_set_on_device("last_command", "0000")
        self.ca.assert_that_pv_is("LASTCOMMAND", "0000")

        # Temperature = 46, this is higher than the allowed value (45)
        self._lewis.backdoor_set_on_device("electronics_temp", 46)

        # Assert that "switch drive off" was sent
        self.ca.assert_that_pv_is("LASTCOMMAND", "0002")
