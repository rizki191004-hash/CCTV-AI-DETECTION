import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.auth import PinAuthManager

class TestDashboardPinGate(unittest.TestCase):
    def test_verify_pin_success_and_failure(self):
        auth = PinAuthManager(pin="123456")
        self.assertTrue(auth.verify_pin("123456"))
        self.assertFalse(auth.verify_pin("wrong"))
        self.assertFalse(auth.verify_pin(""))

    def test_session_token_validation(self):
        auth = PinAuthManager(pin="123456")
        token = auth.create_session()
        self.assertTrue(auth.is_valid_session(token))
        self.assertFalse(auth.is_valid_session("invalid-token-xyz"))
        self.assertFalse(auth.is_valid_session(None))

    def test_rate_limiting_after_consecutive_failures(self):
        auth = PinAuthManager(pin="123456", max_attempts=3)
        client_ip = "192.168.1.50"
        
        self.assertFalse(auth.verify_pin("wrong", client_ip=client_ip))
        self.assertFalse(auth.verify_pin("wrong", client_ip=client_ip))
        self.assertFalse(auth.verify_pin("wrong", client_ip=client_ip))
        
        # 4th attempt should be blocked by rate limiter even if correct
        is_blocked = auth.is_rate_limited(client_ip)
        self.assertTrue(is_blocked)

if __name__ == "__main__":
    unittest.main()

