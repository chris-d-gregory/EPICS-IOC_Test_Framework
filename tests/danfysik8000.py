from utils.test_modes import TestModes
from utils.ioc_launcher import get_default_ioc_dir

from common_tests.danfysik import DanfysikBase, DEVICE_PREFIX, EMULATOR_NAME
from utils.testing import skip_if_recsim

IOCS = [
    {
        "name": DEVICE_PREFIX,
        "directory": get_default_ioc_dir("DFKPS"),
        "macros": {
            "DEV_TYPE": "8000",
            "CALIBRATED": "0",
            "FACTOR_READ_I": "1",
            "FACTOR_READ_V": "1",
            "FACTOR_WRITE_I": "1",
        },
        "emulator": EMULATOR_NAME,
        "emulator_protocol": "model8000",
    },
]


TEST_MODES = [TestModes.RECSIM, TestModes.DEVSIM]


class Danfysik8000Tests(DanfysikBase):
    """
    Tests for danfysik model 8000. Tests inherited from DanfysikBase.
    """
    def test_GIVEN_ioc_THEN_model_is_set_correctly(self):
        self.ca.assert_that_pv_is("DEV_TYPE", "8000")
