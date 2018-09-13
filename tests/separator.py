import unittest

from utils.channel_access import ChannelAccess
from utils.ioc_launcher import get_default_ioc_dir
from utils.test_modes import TestModes
from parameterized import parameterized
from time import clock, sleep

import threading

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

# Voltage and current stability limits

VOLT_LOWERLIM = 4.0
VOLT_UPPERLIM = 6.0

VOLT_STEADY = (VOLT_LOWERLIM+VOLT_UPPERLIM)*0.5

CURR_STEADY = 1.0
CURR_LIMIT = 0.5

SAMPLE_LEN = 1000
SAMPLETIME = 1E-3


def stream_data(ca, n_repeat, curr, volt):
    """
    Sends a stream of data over the channel access link. This will perform n_repeat writes per second.
    Args:
        ca: Object, The channel access link
        n_repeat: integer, The maximum number of writes which will be performed per second
        curr: List of float, The current data to be written over CA
        volt: List of float, The voltage data to be written over CA

    Returns:

    """
    while True:
        time1 = clock()

        for i in range(n_repeat):
            ca.set_pv_value("CURR:CALC", curr, wait=True, sleep_after_set=0.0)
            ca.set_pv_value("VOLT:CALC", volt, wait=True, sleep_after_set=0.0)

        #second_counter = clock() - time1
        #if second_counter < 1.0:
        #    sleep(1.0 - second_counter)
        sleep(1.5)


def simulate_current_data():
    """
    Generates a random set of data around the current stability limit

    Returns:
        current_data: Array of floats

    """

    current_data = [CURR_STEADY]*int(0.75*SAMPLE_LEN)

    current_data.extend([CURR_STEADY+2.0*CURR_LIMIT] * int(0.25*SAMPLE_LEN))

    return current_data


def simulate_voltage_data():
    """
    Generates a random set of data around the voltage stability limit

    Returns:
        voltage_data: Array of floats

    """

    voltage_data = [2.0*VOLT_UPPERLIM] * int(0.25*SAMPLE_LEN)

    voltage_data.extend([VOLT_STEADY]*int(0.75*SAMPLE_LEN))

    return voltage_data


CURRENT_DATA = simulate_current_data()
VOLTAGE_DATA = simulate_voltage_data()


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


class SepLogicTests(unittest.TestCase):
    def setUp(self):
        self.ca = ChannelAccess(20, device_prefix=DEVICE_PREFIX)

        self.ca.set_pv_value("VOLT:CALC", [VOLT_STEADY] * SAMPLE_LEN)
        self.ca.set_pv_value("CURR:CALC", [CURR_STEADY] * SAMPLE_LEN)

        #self.ca.set_pv_value("_SAMPLEBUFFER.RES", 1)
        self.ca.set_pv_value("STABILITY", 0)
        self.ca.set_pv_value("RESETWINDOW", 1)
        self.ca.set_pv_value("_ADDCOUNTS", 0)
        #self.ca.set_pv_value("_MOVINGBUFFER.RES", 1)

        # Define a 1ms polling time
        self.ca.set_pv_value("SAMPLETIME", SAMPLETIME)
        self.ca.assert_that_pv_is_number("SAMPLETIME", SAMPLETIME, tolerance=0.05*abs(SAMPLETIME))

        self.ca.set_pv_value("_COUNTERTIMING.SCAN", "1 second")

    def evaluate_current_instability(self, current_values):
        """
        Evaluates the input current values against the stability criterion.

        Args:
            current_values: Array of input currents

        Returns:
            current_instability: Boolean array of len(current_values). True where element is unstable, else False

        """

        current_instability = [curr_measured >= (CURR_STEADY + CURR_LIMIT) for curr_measured in current_values]

        return current_instability

    def evaluate_voltage_instability(self, voltage_values):
        """
        Evaluates the input voltages against the stability criterion.

        Args:
            voltage_values: Array of input voltages

        Returns:
            voltage_instability: Boolean array of len(voltage_values). True where element is unstable, else False

        """

        voltage_instability = [(VOLT_LOWERLIM >= volt_measured) | (volt_measured >= VOLT_UPPERLIM) for volt_measured in voltage_values]

        return voltage_instability

    def get_out_of_range_samples(self, current_values, voltage_values):
        """
        Calculates the number of points which lie out of stability limits for a current and voltage dataset.
        Args:
            current_values: Array of input current values
            voltage_values: Array of input voltage values

        Returns:
            no_out_of_range: Integer, the number of samples in the dataset which are out of range

        """

        current_instability = self.evaluate_current_instability(current_values)
        voltage_instability = self.evaluate_voltage_instability(voltage_values)

        overall_instability = [curr | volt for curr, volt in zip(current_instability, voltage_instability)]

        no_out_of_range = sum(overall_instability)

        return no_out_of_range

    @parameterized.expand([
        ("steady_current_steady_voltage", [CURR_STEADY]*SAMPLE_LEN, [VOLT_STEADY]*SAMPLE_LEN),

        ("steady_current_unsteady_voltage", [CURR_STEADY] * SAMPLE_LEN, VOLTAGE_DATA),

        ("unsteady_current_steady_voltage", CURRENT_DATA, [VOLT_STEADY] * SAMPLE_LEN),

        ("random_noise_current_and_voltage", simulate_current_data(), simulate_voltage_data())
    ])
    def test_GIVEN_current_and_voltage_data_WHEN_limits_are_tested_THEN_number_of_samples_out_of_range_returned(self, _, curr_data, volt_data):
        self.ca.set_pv_value("_ADDCOUNTS", 0)

        self.ca.set_pv_value("CURR:CALC", curr_data, wait=True, sleep_after_set=0.0)
        self.ca.set_pv_value("VOLT:CALC", volt_data, wait=True, sleep_after_set=0.0)

        expected_out_of_range_samples = self.get_out_of_range_samples(curr_data, volt_data)

        self.ca.assert_that_pv_is_number("_ADDCOUNTS", expected_out_of_range_samples, tolerance=0.05*expected_out_of_range_samples)

    @parameterized.expand([
        ("random_current_steady_voltage", simulate_current_data(), [VOLT_STEADY] * SAMPLE_LEN),
        ("steady_current_random_voltage", [CURR_STEADY] * SAMPLE_LEN, simulate_voltage_data())

    ])
    def test_GIVEN_multiple_samples_in_one_second_WHEN_buffer_read_THEN_buffer_reads_all_out_of_range_samples(self, _, curr_data, volt_data):

        # Setting this to 4 as channel access takes ~0.25s. All writes need to occur within 1 second, which is asserted.
        number_of_writes = 4

        expected_out_of_range_samples = self.get_out_of_range_samples(curr_data, volt_data) * number_of_writes

        for i in range(number_of_writes):
            self.ca.set_pv_value("CURR:CALC", CURRENT_DATA, wait=True, sleep_after_set=0.0)
            self.ca.set_pv_value("VOLT:CALC", VOLTAGE_DATA, wait=True, sleep_after_set=0.0)

        #data_supply_thread = threading.Thread(target=SupplyData, args=(self.ca, 4, curr_data, volt_data))

        data_supply_thread = threading.Thread(target=stream_data, args=(self.ca, number_of_writes, curr_data, volt_data))
        data_supply_thread.daemon = True
        data_supply_thread.start()

        time1 = clock()

        processtime = clock() - time1

        self.ca.assert_that_pv_is_number("_ADDCOUNTS", expected_out_of_range_samples, timeout=60.0)
        self.assertLess(processtime, 1.0)

        del data_supply_thread

    def test_GIVEN_buffer_with_data_WHEN_resetwindow_PV_processed_THEN_buffer_is_cleared(self):
        number_of_writes = 50

        expected_out_of_range_samples = self.get_out_of_range_samples(CURRENT_DATA,
                                                                      VOLTAGE_DATA) * number_of_writes * SAMPLETIME

        for i in range(number_of_writes):
            self.ca.set_pv_value("CURR:CALC", CURRENT_DATA, wait=True, sleep_after_set=0.0)
            self.ca.set_pv_value("VOLT:CALC", VOLTAGE_DATA, wait=True, sleep_after_set=0.0)

        self.ca.assert_that_pv_is_number("STABILITY", expected_out_of_range_samples)

        self.ca.set_pv_value("RESETWINDOW", 1.0)

        self.ca.assert_that_pv_is_number("STABILITY", 0)

    def test_GIVEN_full_buffer_WHEN_more_data_added_to_buffer_THEN_oldest_values_overwritten(self):
        length_of_buffer = 600
        testvalue = 50.0

        self.assertNotEqual(testvalue, 1.0)

        self.ca.set_pv_value("_COUNTERTIMING.SCAN", "Passive")

        for i in range(length_of_buffer):
            self.ca.set_pv_value("_ADDCOUNTS", 1.0/SAMPLETIME, wait=True, sleep_after_set=0.0)

            self.ca.set_pv_value("_COUNTERTIMING.PROC", 1, wait=True, sleep_after_set=0.0)

        self.ca.assert_that_pv_is_number("STABILITY", length_of_buffer)

        self.ca.set_pv_value("_ADDCOUNTS", 50.0/SAMPLETIME, wait=True, sleep_after_set=0.0)
        self.ca.set_pv_value("_COUNTERTIMING.PROC", 1, wait=True, sleep_after_set=0.0)

        self.ca.assert_that_pv_is_number("STABILITY", (length_of_buffer-1.)+testvalue)

    def test_GIVEN_input_data_over_several_seconds_WHEN_stability_PV_read_THEN_all_unstable_time_counted(self):
        # This number needs to be large enough to write over several seconds. Writing over multiple seconds is asserted.
        number_of_writes = 50

        time1 = clock()

        expected_out_of_range_samples = self.get_out_of_range_samples(CURRENT_DATA,
                                                                      VOLTAGE_DATA) * number_of_writes * SAMPLETIME

        for i in range(number_of_writes):
            self.ca.set_pv_value("CURR:CALC", CURRENT_DATA, wait=True, sleep_after_set=0.0)
            self.ca.set_pv_value("VOLT:CALC", VOLTAGE_DATA, wait=True, sleep_after_set=0.0)

        processtime = clock() - time1
        self.assertGreater(processtime, 1.)
        self.ca.assert_that_pv_is_number("STABILITY", expected_out_of_range_samples,
                                         tolerance=0.05*expected_out_of_range_samples)