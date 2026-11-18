"""
tests/test_frame_grabber_multi_source.py – Tests for multi-source camera input parsing and low-latency configuration
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from src.frame_grabber import FrameGrabber


class TestFrameGrabberMultiSource(unittest.TestCase):
    def test_parse_stream_source_integer_string(self):
        """'0' or '1' must be parsed to integer for USB webcam support."""
        self.assertEqual(FrameGrabber.parse_stream_source("0"), 0)
        self.assertEqual(FrameGrabber.parse_stream_source("1"), 1)
        self.assertEqual(FrameGrabber.parse_stream_source("  2  "), 2)

    def test_parse_stream_source_integer_direct(self):
        """Direct integer 0 or 1 is preserved."""
        self.assertEqual(FrameGrabber.parse_stream_source(0), 0)

    def test_parse_stream_source_urls(self):
        """RTSP, HLS, HTTP, and RTMP URLs are preserved as strings."""
        rtsp_url = "rtsp://admin:pass@192.168.1.100:554/live"
        hls_url = "https://cctv.dishub.go.id/stream/simpang5.m3u8"
        rtmp_url = "rtmp://live.server.com/app/stream"

        self.assertEqual(FrameGrabber.parse_stream_source(rtsp_url), rtsp_url)
        self.assertEqual(FrameGrabber.parse_stream_source(hls_url), hls_url)
        self.assertEqual(FrameGrabber.parse_stream_source(rtmp_url), rtmp_url)

    @patch("cv2.VideoCapture")
    def test_create_capture_webcam_uses_direct_device_index(self, mock_cv2_capture):
        """When source is '0', VideoCapture is called with integer 0 (not CAP_FFMPEG string)."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cv2_capture.return_value = mock_cap

        grabber = FrameGrabber(camera_id="cam_webcam", stream_url="0")
        cap = grabber._create_capture()

        mock_cv2_capture.assert_called_once_with(0)
        self.assertIsNotNone(cap)

    @patch("cv2.VideoCapture")
    def test_create_capture_hls_uses_ffmpeg(self, mock_cv2_capture):
        """When source is an HLS .m3u8 URL, VideoCapture uses CAP_FFMPEG."""
        import cv2
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cv2_capture.return_value = mock_cap

        hls_url = "https://public-cctv.com/stream.m3u8"
        grabber = FrameGrabber(camera_id="cam_hls", stream_url=hls_url)
        cap = grabber._create_capture()

        mock_cv2_capture.assert_called_once_with(hls_url, cv2.CAP_FFMPEG)
        self.assertIsNotNone(cap)


if __name__ == "__main__":
    unittest.main()

