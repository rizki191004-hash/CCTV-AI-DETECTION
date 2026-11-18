import unittest
from unittest.mock import patch
from src.reid_manager import ReIDManager


class TestReIDManagerLoadFailureCaching(unittest.TestCase):
    def test_load_failure_cached_after_first_attempt(self):
        manager = ReIDManager()
        # When torchreid is not present, first call returns False and sets _load_failed
        with patch.dict("sys.modules", {"torchreid": None, "torchreid.utils": None}):
            res1 = manager._load_model()
            self.assertFalse(res1)
            self.assertTrue(getattr(manager, "_load_failed", False))

            # Second call immediately returns False without entering load logic
            res2 = manager._load_model()
            self.assertFalse(res2)


if __name__ == "__main__":
    unittest.main()

