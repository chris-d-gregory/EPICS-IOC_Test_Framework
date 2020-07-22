import unittest
import os
from parameterized import parameterized

from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from utils.channel_access import ChannelAccess

test_path = os.path.realpath(
    os.path.join(os.getenv("EPICS_KIT_ROOT"), "support", "motorExtensions", "master", "settings", "sans2d_vac_tank")
)

GALIL_ADDR = "128.0.0.0"

# Create GALIL_04 and GALIL_05
IOCS = [
    {
        "name": "GALIL_0{}".format(i),
        "directory": get_default_ioc_dir("GALIL", i),
        "custom_prefix": "MOT",
        "pv_for_existence": "MTR0{}01".format(i),
        "macros": {
            "GALILADDR": GALIL_ADDR,
            "MTRCTRL": "0{}".format(i),
            "GALILCONFIGDIR": test_path.replace("\\", "/"),
        }
    } for i in [3, 4, 5]
]

TEST_MODES = [TestModes.RECSIM]

AXES_TO_STOP = [
    "FRONTDETZ", "FRONTDETX", "FRONTDETROT", "REARDETZ", "REARDETX", "REARBAFFLEZ", "FRONTBAFFLEZ",
    "BEAMSTOPX", "BEAMSTOP2Y", "BEAMSTOP1Y", "BEAMSTOP3Y", "FRONTBEAMSTOP",
    "JAWRIGHT", "JAWLEFT", "JAWUP", "JAWDOWN", "FRONTSTRIP", "REARSTRIP"
]


class Sans2dVacTankTests(unittest.TestCase):
    """
    Tests for the sans2d vacuum tank motor extensions.
    """

    def setUp(self):
        self.ca = ChannelAccess(device_prefix="MOT")

    def set_axis_moving(self, axis):
        current_position = self.ca.get_pv_value(axis)
        low_limit = self.ca.get_pv_value(axis + ":MTR.LLM")
        high_limit = self.ca.get_pv_value(axis + ":MTR.HLM")
        if current_position - low_limit < high_limit - current_position:
            self.ca.set_pv_value(axis + ":SP", high_limit)
        else:
            self.ca.set_pv_value(axis + ":SP", low_limit)

    def assert_axis_moving(self, axis):
        self.ca.assert_that_pv_is(axis + ":MTR.MOVN", 1)

    def assert_axis_not_moving(self, axis):
        self.ca.assert_that_pv_is(axis + ":MTR.MOVN", 0)

    @parameterized.expand(AXES_TO_STOP)
    def test_GIVEN_axis_moving_WHEN_stop_all_THEN_axis_stopped(self, axis):
        for _ in range(3):
            self.set_axis_moving(axis)
            self.assert_axis_moving(axis)
            self.ca.set_pv_value("SANS2DVAC:STOP_MOTORS:ALL", 1)
            self.assert_axis_not_moving(axis)

    def test_GIVEN_front_beamstop_moving_WHEN_front_detector_angle_goes_out_of_range_THEN_front_beamstop_stops(self):
        self.ca.set_pv_value("FRONTDETROT", 0)
        self.set_axis_moving("FRONTBEAMSTOP")
        self.assert_axis_moving("FRONTBEAMSTOP")
        self.ca.set_pv_value("FRONTDETROT", -3)
        self.ca.assert_that_pv_is("SANS2DVAC:INHIBIT_FRONTBEAMSTOP", 1)
        self.assert_axis_not_moving("FRONTBEAMSTOP")

    def test_GIVEN_front_beamstop_not_moving_AND_front_detector_angle_goes_out_of_range_THEN_front_beamstop_cannot_move(self):
        self.ca.set_pv_value("FRONTDETROT", -3)
        start_position = self.ca.get_pv_value("FRONTBEAMSTOP")
        self.set_axis_moving("FRONTBEAMSTOP")
        self.ca.assert_that_pv_is("SANS2DVAC:INHIBIT_FRONTBEAMSTOP", 1)
        end_position = self.ca.get_pv_value("FRONTBEAMSTOP")
        self.assertEqual(start_position, end_position)

