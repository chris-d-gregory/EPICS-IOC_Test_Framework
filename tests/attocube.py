import unittest

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.testing import get_running_lewis_and_ioc

DEVICE_PREFIX = "ATTOCUBE_01"
EMULATOR = "attocube_anc350"

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "custom_prefix": "MOT",
        "pv_for_existence": "MTR0101",
        "directory": get_default_ioc_dir("ATTOCUBE"),
        "macros": {
            "MTRCTRL": 1
        },
        "emulator": EMULATOR,
    },
]

TEST_MODES = [TestModes.DEVSIM]

MOTOR_PV = "MTR0101"
MOTOR_RBV = MOTOR_PV + ".RBV"


class AttocubeTests(unittest.TestCase):
    """
    Tests for the Attocube IOC.
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc(EMULATOR, DEVICE_PREFIX)
        self.ca = self._ioc.ca
        self.ca.assert_that_pv_exists(MOTOR_RBV)
        self._lewis.backdoor_set_on_device('connected', True)
        self.ca.assert_that_pv_alarm_is(MOTOR_PV, ChannelAccess.Alarms.NONE, timeout=30)

        self.ca.set_pv_value(MOTOR_PV + ".RTRY", 0)
        self.ca.set_pv_value(MOTOR_PV + ".VBAS", 20)
        self.ca.set_pv_value(MOTOR_PV + ".VMAX", 20)
        self.ca.set_pv_value(MOTOR_PV + ".VELO", 20)

        self.ca.set_pv_value(MOTOR_PV, 0)
        self.ca.assert_that_pv_is(MOTOR_PV + ".RBV", 0, timeout=30)
        self.ca.assert_that_pv_is(MOTOR_PV + ".DMOV", 1, timeout=30)

        self._lewis.backdoor_set_on_device('axis_on', True)
        self._lewis.assert_that_emulator_value_is('axis_on', "True")

    def test_WHEN_moved_to_position_THEN_position_reached(self):
        position_setpoint = 2
        self.ca.set_pv_value(MOTOR_PV, position_setpoint)
        self.ca.assert_that_pv_value_is_increasing(MOTOR_RBV, 1)
        self.ca.assert_that_pv_is_number(MOTOR_RBV, position_setpoint, timeout=30)

    @unittest.skip("This test is broken and is difficult to fix because the test passes consistently on dev machines, "
                   "but fails consistently on RENO. On connecting a debugger, it appears that the motor record may be "
                   "deadlocked, however, this is hard to diagnose with only the remote tools.")
    def test_GIVEN_device_not_connected_THEN_pv_in_alarm(self):
        self._lewis.backdoor_set_on_device('connected', False)
        self.ca.assert_that_pv_alarm_is(MOTOR_PV, ChannelAccess.Alarms.INVALID, timeout=30)
        self._lewis.backdoor_set_on_device('connected', True)
        self.ca.assert_that_pv_alarm_is(MOTOR_PV, ChannelAccess.Alarms.NONE, timeout=30)

    @unittest.skip("This test is broken and is difficult to fix because the test passes consistently on dev machines, "
                   "but fails consistently on RENO. On connecting a debugger, it appears that the motor record may be "
                   "deadlocked, however, this is hard to diagnose with only the remote tools.")
    def test_GIVEN_device_not_connected_WHEN_motor_val_set_THEN_pv_returns_to_alarm(self):
        self._lewis.backdoor_set_on_device('connected', False)
        self.ca.assert_that_pv_alarm_is(MOTOR_PV, ChannelAccess.Alarms.INVALID, timeout=30)
        position_setpoint = 4
        self.ca.set_pv_value(MOTOR_PV, position_setpoint)
        self.ca.assert_that_pv_alarm_is(MOTOR_PV, ChannelAccess.Alarms.INVALID, timeout=30)
        self._lewis.backdoor_set_on_device('connected', True)
        self.ca.assert_that_pv_alarm_is(MOTOR_PV, ChannelAccess.Alarms.NONE, timeout=30)

    def test_GIVEN_axis_not_on_WHEN_motor_moved_THEN_axis_turned_on_and_moves(self):
        self._lewis.backdoor_set_on_device('axis_on', False)
        position_setpoint = 6
        self.ca.set_pv_value(MOTOR_PV, position_setpoint)
        self.ca.assert_that_pv_value_is_increasing(MOTOR_RBV, 1)
        self.ca.assert_that_pv_is_number(MOTOR_RBV, position_setpoint, timeout=30)

        self._lewis.assert_that_emulator_value_is('axis_on', "True")
