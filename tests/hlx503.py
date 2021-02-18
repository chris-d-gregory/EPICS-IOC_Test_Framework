import unittest
from dataclasses import dataclass

from parameterized import parameterized
from itertools import product
from enum import Enum

from utils.test_modes import TestModes
from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.testing import get_running_lewis_and_ioc, parameterized_list

# Device prefix
DEVICE_PREFIX = "HLX503_01"

# Emulator name
emulator_name = "hlx503"


class Version(Enum):
    ITC503 = 503
    ITC502 = 502
    ITC601 = 601


@dataclass
class ITC:
    name: str
    version: Version
    channel : int
    isobus_address: int


# ITC503 ISOBUS addresses and channels
# Must match those in emulator device
itcs = [
    ITC("1KPOT", Version.ITC502, 0, 0), ITC("HE3POT_LOWT", Version.ITC503, 1, 1),
    ITC("HE3POT_HIGHT", Version.ITC503, 2, 2), ITC("SORB", Version.ITC601, 3, 3)
]
itcs_non_601 = [itc for itc in itcs if itc.version != Version.ITC601]
itcs_non_502 = [itc for itc in itcs if itc.version != Version.ITC502]
itcs_601 = [itc for itc in itcs if itc.version == Version.ITC601]
itcs_502 = [itc for itc in itcs if itc.version == Version.ITC502]
itcs_503 = [itc for itc in itcs if itc.version == Version.ITC503]
isobus_addresses = {f"{itc.name}_ISOBUS": itc.isobus_address for itc in itcs}
versions = {f"{itc.name}_VERSION": itc.version.value for itc in itcs}
channels = {f"{itc.name}_CHANNEL": itc.channel for itc in itcs}

# Properties obtained from the get_status protocol and values to set them with
status_properties_non_601 = [
    "status", "autoheat", "autoneedlevalve", "initneedlevalve", "remote",
    "locked", "sweeping", "ctrlchannel", "autopid", "tuning"
]
status_set_values_non_601 = [
    8, True, True, True, True,
    True, 1, 5, True, True
]
status_expected_values_non_601 = [
    8, "Auto", "Auto", "YES", "YES",
    "YES", "YES", 5, "ON", "YES"
]
status_properties_and_values_non_601 = zip(status_properties_non_601, status_set_values_non_601, status_expected_values_non_601)
isobus_status_properties_and_values_503 = product(itcs_503, status_properties_and_values_non_601)
combo_one = [("autoheat", "autoneedlevalve", "initneedlevalve")]
combo_one_set_values = [
    (True, True, True),
    (True, False, True),
    (False, False, False),
    (True, True, False),
    (False, True, True),
]
combo_one_expected_values = [
    ("Auto", "Auto", "YES"),
    ("Auto", "Manual", "YES"),
    ("Manual", "Manual", "NO"),
    ("Auto", "Auto", "NO"),
    ("Manual", "Auto", "YES"),
]
combo_two = [("remote", "locked")]
combo_two_set_values = [
    (True, True),
    (False, False),
    (True, False),
    (False, True)
]
combo_two_expected_values = [
    ("YES", "YES"),
    ("NO", "NO"),
    ("YES", "NO"),
    ("NO", "YES")
]
combo_three = [("ctrlchannel", "autopid", "tuning")]
combo_three_set_values = [
    #
    (None, True, True),
    (None, False, True),
    (None, True, False),
    (None, False, False),
    #
    (None, None, None),
    (None, None, True),
    (None, None, False),
    (None, False, None),
    (None, True, None),
    #
    (5, True, True),
    (5, False, True),
    (5, True, False),
    (5, False, False),
    #
    (5, None, None),
    (5, None, True),
    (5, None, False),
    (5, False, None),
    (5, True, None),
]
combo_three_expected_values = [
    #
    (0, "ON", "YES"),
    (0, "OFF", "YES"),
    (0, "ON", "NO"),
    (0, "OFF", "NO"),
    #
    (0, "OFF", "NO"),
    (0, "OFF", "YES"),
    (0, "OFF", "NO"),
    (0, "OFF", "NO"),
    (0, "ON", "NO"),
    #
    (5, "ON", "YES"),
    (5, "OFF", "YES"),
    (5, "ON", "NO"),
    (5, "OFF", "NO"),
    #
    (5, "OFF", "NO"),
    (5, "OFF", "YES"),
    (5, "OFF", "NO"),
    (5, "OFF", "NO"),
    (5, "ON", "NO"),
]

status_combos_non_601 = list(product(combo_one, zip(combo_one_set_values, combo_one_expected_values)))
itc_status_combos_non_601 = list(product(itcs_non_601, status_combos_non_601))
status_combos_non_502 = list(product(combo_three, zip(combo_three_set_values, combo_three_expected_values)))
itc_status_combos_non_502 = list(product(itcs_non_502, status_combos_non_502))
status_combos_all = list(product(combo_two, zip(combo_two_set_values, combo_two_expected_values)))
itc_status_combos_all = list(product(itcs, status_combos_all))
itc_status_combos = itc_status_combos_non_601 + itc_status_combos_non_502 + itc_status_combos_all


IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("HLX503"),
        "emulator": emulator_name,
        "macros": {**isobus_addresses, **channels, **versions}
    },
]


TEST_MODES = [TestModes.DEVSIM]


class HLX503Tests(unittest.TestCase):
    """
    Tests for the ISOBUS503/Heliox 3He Refrigerator.
    """

    def setUp(self):
        self._lewis, self._ioc = get_running_lewis_and_ioc(emulator_name, DEVICE_PREFIX)
        self.assertIsNotNone(self._lewis)
        self.assertIsNotNone(self._ioc)

        self.ca = ChannelAccess(device_prefix=DEVICE_PREFIX)
        for itc in itcs:
            self._lewis.backdoor_run_function_on_device("reset_status", arguments=[itc.isobus_address])

    def test_WHEN_ioc_started_THEN_ioc_connected(self):
        self.ca.get_pv_value("DISABLE")

    @parameterized.expand(parameterized_list(itcs))
    def test_WHEN_ioc_set_up_with_ISOBUS_numbers_THEN_ISOBUS_numbers_are_correct(self, _, itc):
        self.ca.assert_that_pv_is(f"{itc.name}_ISOBUS", itc.isobus_address)

    @parameterized.expand(parameterized_list(itcs))
    def test_WHEN_set_temp_via_backdoor_THEN_get_temp_value_correct(self, _, itc):
        temp = 20.0
        self._lewis.backdoor_run_function_on_device("set_temp", arguments=(itc.isobus_address, itc.channel, temp))
        self.ca.assert_that_pv_is(f"{itc.name}:TEMP", temp)

    @parameterized.expand(parameterized_list(isobus_status_properties_and_values_503))
    def test_WHEN_status_properties_set_via_backdoor_THEN_status_values_correct(self, _, itc, status_property_and_vals):
        status_property, status_set_val, status_expected_val = status_property_and_vals
        self._lewis.backdoor_run_function_on_device(f"set_{status_property}", arguments=[itc.isobus_address, status_set_val])
        self.ca.assert_that_pv_is(f"{itc.name}:{status_property.upper()}", status_expected_val)

    @parameterized.expand(parameterized_list(itc_status_combos))
    def test_WHEN_status_properties_set_in_combination_via_backdoor_THEN_status_values_correct(self, _, itc, status_property_and_vals):
        # Unpack status property and values
        properties = status_property_and_vals[0]
        set_vals = status_property_and_vals[1][0]
        expected_vals = status_property_and_vals[1][1]
        num_of_properties = len(properties)
        for i in range(num_of_properties):
            self._lewis.backdoor_run_function_on_device(f"set_{properties[i]}", arguments=[itc.isobus_address, set_vals[i]])
        for i in range(num_of_properties):
            self.ca.assert_that_pv_is(f"{itc.name}:{properties[i].upper()}", expected_vals[i])

    @parameterized.expand(parameterized_list(product(itcs, ["Auto", "Manual"])))
    def test_WHEN_set_autoheat_THEN_autoheat_set(self, _, itc, value):
        self.ca.assert_setting_setpoint_sets_readback(value, f"{itc.name}:AUTOHEAT", timeout=20)

    @parameterized.expand(parameterized_list(product(itcs_non_601, ["Auto", "Manual"])))
    def test_WHEN_set_autoneedlevalue_AND_NOT_601_THEN_autoneedlevalve_set(self, _, itc_non_601, value):
        self.ca.assert_setting_setpoint_sets_readback(value, f"{itc_non_601.name}:AUTONEEDLEVALVE")

    @parameterized.expand(parameterized_list(product(itcs_601, ["Auto", "Manual"])))
    def test_WHEN_set_autoneedlevalue_AND_NOT_601_THEN_autoneedlevalve_set(self, _, itc_601, value):
        self.ca.set_pv_value(f"{itc_601.name}:AUTONEEDLEVALVE:SP", value)
        self.ca.assert_that_pv_is(f"{itc_601.name}:AUTONEEDLEVALVE", "Manual")

    @parameterized.expand(parameterized_list(product(itcs_non_502, ["ON", "OFF"])))
    def test_WHEN_set_autopid_AND_NOT_502_THEN_autopid_set(self, _, itc_non_502, value):
        self.ca.assert_setting_setpoint_sets_readback(value, f"{itc_non_502.name}:AUTOPID")

    @parameterized.expand(parameterized_list(product(itcs_502, ["ON", "OFF"])))
    def test_WHEN_set_autopid_AND_502_THEN_autopid_not_set(self, _, itc, value):
        self.ca.set_pv_value(f"{itc.name}:AUTOPID:SP", value)
        self.ca.assert_that_pv_is(f"{itc.name}:AUTOPID", "OFF")
