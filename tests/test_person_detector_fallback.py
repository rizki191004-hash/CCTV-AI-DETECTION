import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock external heavy dependencies if not present
if "supervision" not in sys.modules:
    mock_sv = MagicMock()
    sys.modules["supervision"] = mock_sv
if "ultralytics" not in sys.modules:
    mock_ultra = MagicMock()
    sys.modules["ultralytics"] = mock_ultra

from src.person_detector import PersonDetector

class TestPersonDetectorFallback(unittest.TestCase):
    @patch("src.person_detector.YOLO")
    def test_warmup_fallback_to_cpu_on_kernel_error(self, mock_yolo_cls):
        mock_model = MagicMock()
        mock_yolo_cls.return_value = mock_model
        
        # Simulate OpenVINO CISA / GPU JIT kernel failure on first predict call
        mock_model.predict.side_effect = RuntimeError("Error in CISA routine with name: kernel: Input V38 intersects with V37")
        
        detector = PersonDetector(model_name="yolov8n-pose.pt", device_mode="intel:gpu")
        # Assert device was gracefully downgraded to cpu
        self.assertEqual(detector.device, "cpu")

if __name__ == "__main__":
    unittest.main()
