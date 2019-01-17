"""
Testing using channel access.
"""
import os
import time
import operator
import ctypes
from contextlib import contextmanager
from genie_python.genie_cachannel_wrapper import CaChannelWrapper, UnableToConnectToPVException

from functools import partial

from utils.formatters import format_value

try:
    # Python 3
    from functools import partialmethod
except ImportError:
    # Workaround for Python 2
    # noinspection PyPep8Naming
    class partialmethod(partial):
        """
        Create a method based on another method by filling in arguments.
        """
        def __get__(self, instance, owner):
            return partial(self.func, instance, *(self.args or ()), **(self.keywords or {}))


class _MonitorAssertion:
    """
    Set the value of a pv when a monitor is triggered
    """
    def __init__(self, channel_access, pv):
        """
        Initilise.
        Args:
            channel_access: channel_access to set up monitor
            pv: name of pv to monitor
        """
        self._full_pv_name = channel_access._create_pv_with_prefix(pv)
        self._value = None
        CaChannelWrapper.add_monitor(channel_access._create_pv_with_prefix(pv), self._set_val)

    def _set_val(self, value, alarm_severity, alarm_status):
        self._value = value

    @property
    def value(self):
        """
        Returns: value monitor set
        """
        CaChannelWrapper.poll()
        return self._value


class ChannelAccess(object):
    """
    Provides the required channel access commands.
    """

    class Alarms(object):
        """
        Possible alarm states that a PV can be in.
        """
        NONE = "NO_ALARM"  # Alarm value if there is no alarm
        MAJOR = "MAJOR"  # Alarm value if the record is in major alarm
        MINOR = "MINOR"  # Alarm value if the record is in minor alarm
        INVALID = "INVALID"  # Alarm value if the record has a calc alarm
        DISABLE = "DISABLE"  # Alarm stat value if the record has been disabled

    def __init__(self, default_timeout=5, device_prefix=None):
        """
        Args:
            device_prefix: the device prefix which will be added to the start of all pvs
            default_timeout: the default time out to wait for
        """
        self.ca = CaChannelWrapper()

        # Silence CA errors
        CaChannelWrapper.errorLogFunc = lambda *a, **kw: None
        try:
            hcom = ctypes.cdll.LoadLibrary("COM.DLL")
            hcom.eltc(ctypes.c_int(0))
        except Exception as e:
            print("Unable to disable CA errors: ", e)

        self.prefix = os.environ["testing_prefix"]
        self._default_timeout = default_timeout
        if not self.prefix.endswith(':'):
            self.prefix += ':'
        if device_prefix is not None:
            self.prefix += "{}:".format(device_prefix)

    def set_pv_value(self, pv, value, wait=False, sleep_after_set=1.0):
        """
        Sets the specified PV to the supplied value.

        Args:
            pv: the EPICS PV name
            value: the value to set
            wait: wait for completion callback (default: False)
            sleep_after_set: before a sleep after setting pv value
        """
        # Wait for the PV to exist before writing to it. If this is not here sometimes the tests try to jump the gun
        # and attempt to write to a PV that doesn't exist yet
        self.assert_that_pv_exists(pv)

        # Don't use wait=True because it will cause an infinite wait if the value never gets set successfully
        # In that case the test should fail (because the correct value is not set)
        # but it should not hold up all the other tests
        self.ca.set_pv_value(self._create_pv_with_prefix(pv), value, wait=wait, timeout=self._default_timeout)
        # Give lewis time to process
        time.sleep(sleep_after_set)

    def get_pv_value(self, pv):
        """
        Gets the current value for the specified PV.

        Args:
            pv: the EPICS PV name
        Returns:
            the current value
        """
        return self.ca.get_pv_value(self._create_pv_with_prefix(pv))

    def process_pv(self, pv):
        """
        Makes the pv process once.

        Args:
            pv: the EPICS PV name
        """
        pv_proc = "{}.PROC".format(self._create_pv_with_prefix(pv))
        return self.ca.set_pv_value(pv_proc, 1)

    @contextmanager
    def put_simulated_record_into_alarm(self, pv, alarm):
        """
        Put a simulated record into alarm. Using a context manager to put PVs into alarm means they don't accidentally
        get left in alarm if the test fails.

        Args:
             pv: pv to put into alarm
             alarm: type of alarm
        Raises:
            AssertionError if the simulated alarm status could not be set.
        """
        def _set_and_check_simulated_alarm(set_check_pv, set_check_alarm):
            self.set_pv_value("{}.SIMS".format(set_check_pv), set_check_alarm)
            self.assert_that_pv_alarm_is("{}".format(set_check_pv), set_check_alarm)

        try:
            _set_and_check_simulated_alarm(pv, alarm)
            yield
        finally:
            _set_and_check_simulated_alarm(pv, self.Alarms.NONE)

    def _create_pv_with_prefix(self, pv):
        """
        Create the full pv name with instrument prefix.

        Args:
            pv: pv name without prefix
        Returns:
            pv name with prefix
        """
        return "{prefix}{pv}".format(prefix=self.prefix, pv=pv)

    def _wait_for_pv_lambda(self, wait_for_lambda, timeout):
        """
        Wait for a lambda containing a pv to become None; return value or timeout and return actual value.

        Args:
            wait_for_lambda: lambda we expect to be None
            timeout: time out period
        Returns:
            final value of lambda
        """
        start_time = time.time()
        current_time = start_time

        if timeout is None:
            timeout = self._default_timeout

        while current_time - start_time < timeout:
            try:
                lambda_value = wait_for_lambda()
                if lambda_value is None:
                    return lambda_value
            except UnableToConnectToPVException:
                pass  # try again next loop maybe the PV will be up

            time.sleep(0.5)
            current_time = time.time()

        # last try
        return wait_for_lambda()

    def assert_that_pv_value_causes_func_to_return_true(self, pv, func, timeout=None, message=None, value_from=None):
        """
        Check that a PV satisfies a given function within some timeout.

        Args:
            pv: the PV to check
            func: a function that takes one argument, the PV value, and returns True if the value is valid.
            timeout: time to wait for the PV to satisfy the function
            message: custom message to print on failure
            value_from: place to get value from; None from pv get; otherwise attribute value will be used
        Raises:
            AssertionError: If the function does not evaluate to true within the given timeout
        """
        def _wrapper(message):
            if value_from is None:
                value = self.get_pv_value(pv)
            else:
                value = value_from.value
            try:
                return_value = func(value)
            except Exception as e:
                return "Exception was thrown while evaluating function '{}' on pv value {}. Exception was: {} {}"\
                    .format(func.__name__, format_value(value), e.__class__.__name__, e.message)
            if return_value:
                return None
            else:
                return "{}{}{}".format(message, os.linesep, "Final PV value was {}".format(format_value(value)))

        if message is None:
            message = "Expected function '{}' to evaluate to True when reading PV '{}'." \
                .format(func.__name__, self._create_pv_with_prefix(pv))

        err = self._wait_for_pv_lambda(partial(_wrapper, message), timeout)

        if err is not None:
            raise AssertionError(err)

    def assert_that_pv_is(self, pv, expected_value, timeout=None, msg=None, value_from=None):
        """
        Assert that the pv has the expected value or that it becomes the expected value within the timeout.

        Args:
            pv: pv name
            expected_value: expected value
            timeout: if it hasn't changed within this time raise assertion error
            msg: Extra message to print
            value_from: place to get value from; None from pv get; otherwise attribute value will be used
        Raises:
            AssertionError: if value does not become requested value
            UnableToConnectToPVException: if pv does not exist within timeout
        """

        if msg is None:
            msg = "Expected PV, '{}' to have value {}.".format(self._create_pv_with_prefix(pv),
                                                               format_value(expected_value))

        return self.assert_that_pv_value_causes_func_to_return_true(
            pv, lambda val: val == expected_value, timeout=timeout, message=msg, value_from=value_from)

    def assert_that_pv_after_processing_is(self, pv, expected_value, timeout=None, msg=None):
        """
        Assert that the pv has the expected value after the pv is processed
        or that it becomes the expected value within the timeout.

        Args:
            pv: pv name
            expected_value: expected value
            timeout: if it hasn't changed within this time raise assertion error
            msg: Extra message to print
        Raises:
            AssertionError: if value does not become requested value
            UnableToConnectToPVException: if pv does not exist within timeout
        """

        self.process_pv(pv)
        return self.assert_that_pv_is(pv, expected_value, timeout=None, msg=None)

    def assert_that_pv_is_not(self, pv, restricted_value, timeout=None, msg=""):
        """
        Assert that the pv does not have a particular value and optionally it does not become that value within the
        timeout.

        Args:
            pv: pv name
            restricted_value: value the PV shouldn't become
            timeout: if it becomes the value within this time, raise an assertion error
            msg: Extra message to print
        Raises:
            AssertionError: if value has the restricted value
            UnableToConnectToPVException: if pv does not exist within timeout
        """
        if msg is None:
            msg = "Expected PV to not have value {}.".format(format_value(restricted_value))

        return self.assert_that_pv_value_causes_func_to_return_true(
            pv, lambda val: val != restricted_value, timeout, message=msg)

    def _within_tolerance_condition(self, val, expected, tolerance):
        """
        Condition to tell whether a number is equal to another within a tolerance.

        Args:
            val: The actual value
            expected: The expected value
            tolerance:
        Returns:
            True if within tolerance, False otherwise.
        """
        try:
            val = float(val)
        except (ValueError, TypeError):
            return False
        return abs(val - expected) <= tolerance

    def assert_that_pv_is_number(self, pv, expected, tolerance=0.0, timeout=None, value_from=None):
        """
        Assert that the pv has the expected value or that it becomes the expected value within the timeout
        
        Args:
            pv: pv name
            expected: expected value
            tolerance: the allowable deviation from the expected value
            timeout: if it hasn't changed within this time raise assertion error
            value_from: where to get the value from, None for caget from pv
        Raises:
            AssertionError: if value does not become requested value
            UnableToConnectToPVException: if pv does not exist within timeout
        """
        message = "Expected PV value to be equal to {} (tolerance: {})"\
            .format(format_value(expected), format_value(tolerance))

        return self.assert_that_pv_value_causes_func_to_return_true(
            pv, lambda val: self._within_tolerance_condition(val, expected, tolerance), timeout, message=message,
            value_from=value_from)

    def assert_that_pv_is_not_number(self, pv, restricted, tolerance=0, timeout=None):
        """
        Assert that the pv is at least tolerance from the restricted value within the timeout

        Args:
             pv: pv name
             restricted: the value we don't want the PV to have
             tolerance: the minimal deviation from the expected value
             timeout: if it hasn't changed within this time raise assertion error
        Raises:
             AssertionError: if value does not enter the desired range
             UnableToConnectToPVException: if pv does not exist within timeout
        """
        message = "Expected PV value to be not equal to {} (tolerance: {})"\
            .format(format_value(restricted), format_value(tolerance))

        return self.assert_that_pv_value_causes_func_to_return_true(
            pv, lambda val: not self._within_tolerance_condition(val, restricted, tolerance), timeout, message=message)

    def assert_that_pv_is_one_of(self, pv, expected_values, timeout=None):
        """
        Assert that the pv has one of the expected values or that it becomes one of the expected value within the
        timeout.

        Args:
             pv: pv name
             expected_values: expected values
             timeout: if it hasn't changed within this time raise assertion error
        Raises:
             AssertionError: if value does not become requested value
             UnableToConnectToPVException: if pv does not exist within timeout
        """
        def _condition(val):
            return val in expected_values

        message = "Expected PV value to be in {}".format(expected_values)
        return self.assert_that_pv_value_causes_func_to_return_true(pv, _condition, timeout, message)

    def assert_that_pv_is_an_integer_between(self, pv, min_value, max_value, timeout=None):
        """
        Assert that the pv has one of the expected values or that it becomes one of the expected value within the
        timeout

        Args:
             pv: pv name
             min_value: minimum value (inclusive)
             max_value: maximum value (inclusive)
             timeout: if it hasn't changed within this time raise assertion error
        Raises:
             AssertionError: if value does not become requested value
             UnableToConnectToPVException: if pv does not exist within timeout
        """
        def _condition(val):
            try:
                int_pv_value = int(val)
            except ValueError:
                return False

            return min_value <= int_pv_value <= max_value

        message = "Expected PV value to be an integer between {} and {}".format(min_value, max_value)
        return self.assert_that_pv_value_causes_func_to_return_true(pv, _condition, timeout, message)

    def assert_that_pv_exists(self, pv, timeout=None):
        """
        Wait for pv to be available or timeout and throw UnableToConnectToPVException.

        Args:
             pv: pv to wait for
             timeout: time to wait for
        Raises:
             UnableToConnectToPVException: if pv can not be connected to after given time
        """
        if timeout is None:
            timeout = self._default_timeout

        if not self.ca.pv_exists(self._create_pv_with_prefix(pv), timeout=timeout):
            raise AssertionError("PV {pv} does not exist".format(pv=self._create_pv_with_prefix(pv)))

    def assert_that_pv_does_not_exist(self, pv, timeout=2):
        """
        Asserts that a pv does not exist.

        Args:
             pv: pv to wait for
             timeout: amount of time to wait for
        Raises:
             AssertionError: if pv exists
        """

        pv_name = self._create_pv_with_prefix(pv)
        if self.ca.pv_exists(pv_name, timeout):
            raise AssertionError("PV {pv} exists".format(pv=self._create_pv_with_prefix(pv)))

    def assert_that_pv_alarm_is_not(self, pv, alarm, timeout=None):
        """
        Assert that a pv is not in alarm state given or timeout.

        Args:
             pv: pv name
             alarm: alarm state (see constants ALARM_X)
             timeout: length of time to wait for change
        Raises:
             AssertionError: if alarm is requested value
             UnableToConnectToPVException: if pv does not exist within timeout
        """
        return self.assert_that_pv_is_not("{}.SEVR".format(pv), alarm, timeout=timeout)

    def assert_that_pv_alarm_is(self, pv, alarm, timeout=None):
        """
        Assert that a pv is in alarm state given or timeout.

        Args:
             pv: pv name
             alarm: alarm state (see constants ALARM_X)
             timeout: length of time to wait for change
        Raises:
             AssertionError: if alarm does not become requested value
             UnableToConnectToPVException: if pv does not exist within timeout
        """
        return self.assert_that_pv_is("{}.SEVR".format(pv), alarm, timeout=timeout)

    def assert_setting_setpoint_sets_readback(self, value, readback_pv, set_point_pv=None, expected_value=None,
                                              expected_alarm=Alarms.NONE, timeout=None):
        """
        Set a pv to a value and check that the readback has the expected value and alarm state.

        Args:
             value: value to set
             readback_pv: the pv for the read back (e.g. IN:INST:TEMP)
             set_point_pv: the pv to check has the correct value;
            if None use the readback with SP  (e.g. IN:INST:TEMP:SP)
             expected_value: the expected return value; if None use the value
             expected_alarm: the expected alarm status, None don't check; defaults to ALARM_NONE
             timeout: timeout for the pv and alarm to become the expected values
        Raises:
             AssertionError: if setback does not become expected value or has incorrect alarm state
             UnableToConnectToPVException: if a pv does not exist within timeout
        """
        if set_point_pv is None:
            set_point_pv = "{}:SP".format(readback_pv)
        if expected_value is None:
            expected_value = value

        self.set_pv_value(set_point_pv, value)
        self.assert_that_pv_is(readback_pv, expected_value, timeout=timeout)
        if expected_alarm is not None:
            self.assert_that_pv_alarm_is(readback_pv, expected_alarm, timeout=timeout)

    def assert_that_pv_value_over_time_satisfies_comparator(self, pv, wait, comparator):
        """
        Check that a PV satisfies a given function over time. The initial value is compared to the final value after
        a given time using the comparator.

        Args:
             pv: the PV to check
             wait: the number of seconds to wait
             comparator: a function taking two arguments; the initial and final values, which should return a boolean
        Raises:
             AssertionError: if the value of the pv did not satisfy the comparator
        """
        initial_value = self.get_pv_value(pv)
        time.sleep(wait)

        message = "Expected value trend to satisfy comparator '{}'. Initial value was {}."\
            .format(comparator.__name__, format_value(initial_value))

        def _condition(val):
            return comparator(val, initial_value)

        return self.assert_that_pv_value_causes_func_to_return_true(pv, _condition, message=message)

    # Special cases of assert_that_pv_value_over_time_satisfies_comparator
    assert_that_pv_value_is_increasing = \
        partialmethod(assert_that_pv_value_over_time_satisfies_comparator, comparator=operator.gt)

    assert_that_pv_value_is_decreasing = \
        partialmethod(assert_that_pv_value_over_time_satisfies_comparator, comparator=operator.lt)

    assert_that_pv_value_is_unchanged = \
        partialmethod(assert_that_pv_value_over_time_satisfies_comparator, comparator=operator.eq)

    def assert_that_pv_monitor_is(self, pv, expected_value):
        """
        Assert that a pv has a given value set by a monitor event
        Args:
            pv: the pv name
            expected_value: the expected value

        Raises:
            AssertionError: if the value of the pv did not satisfy the comparator
        """
        self.assert_that_pv_is(pv, expected_value, value_from=_MonitorAssertion(self, pv))

    def assert_that_pv_monitor_is_number(self, pv, expected_value, tolerance=0.0):
        """
        Assert that a pv value is set by a monitor event and is within a tolerance
        Args:
            pv: the pv name
            expected_value: the expected value
            tolerance: tolerance

        Raises:
             AssertionError: if the value of the pv did not satisfy the comparator
        """
        channel_access = self

        self.assert_that_pv_is_number(pv, expected_value, tolerance=tolerance, value_from=_MonitorAssertion(self, pv))
