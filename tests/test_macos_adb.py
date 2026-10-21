import os
import subprocess
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from core.adb import client
from core.input import create_backend
from core.screencap import CaptureMethod, ScreenCapturer


class MacOSAdbPortTests(unittest.TestCase):
    def test_adb_path_honors_environment_override(self):
        with patch.dict(os.environ, {"CZN_ADB_PATH": "/tmp/test-adb"}):
            self.assertEqual(client.adb_path(), "/tmp/test-adb")

    def test_run_does_not_pass_windows_creationflags_on_macos(self):
        completed = subprocess.CompletedProcess(["adb"], 0, b"ok", b"")
        with patch.object(client, "adb_path", return_value="adb"), \
             patch.object(client.subprocess, "run", return_value=completed) as mocked:
            result = client.run(["devices"])
        self.assertIs(result, completed)
        self.assertNotIn("creationflags", mocked.call_args.kwargs)

    def test_screen_capturer_defaults_to_adb(self):
        if os.name == "nt":
            self.skipTest("macOS-only assertion")
        capturer = ScreenCapturer()
        self.assertEqual(CaptureMethod.DEFAULT.value, "adb")
        self.assertEqual(capturer.backend.name, "adb")
        self.assertTrue(capturer.backend.is_device)

    def test_non_adb_input_is_forced_to_adb_on_macos(self):
        if os.name == "nt":
            self.skipTest("macOS-only assertion")
        self.assertEqual(create_backend("postmessage").name, "adb")

    def test_adb_screencap_decodes_bgr_frame(self):
        image = np.zeros((4, 6, 3), dtype=np.uint8)
        image[1, 2] = (10, 20, 30)
        ok, encoded = cv2.imencode(".png", image)
        self.assertTrue(ok)
        completed = subprocess.CompletedProcess([], 0, encoded.tobytes(), b"")
        with patch.object(client, "run", return_value=completed):
            frame = client.screencap("emulator-5554")
        self.assertEqual(frame.shape, image.shape)
        self.assertEqual(frame[1, 2].tolist(), [10, 20, 30])

    def test_adb_tap_uses_selected_serial(self):
        with patch.object(client, "run") as mocked:
            client.tap("emulator-5554", 123, 456)
        mocked.assert_called_once_with(
            ["shell", "input", "tap", "123", "456"],
            serial="emulator-5554",
            timeout=10,
        )


if __name__ == "__main__":
    unittest.main()
