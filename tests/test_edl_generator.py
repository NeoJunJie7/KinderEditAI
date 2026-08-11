import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from moviepy import AudioClip, ColorClip

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.edl_generator import build_edl, write_edl


class EdlGeneratorTests(unittest.TestCase):
    def test_build_edl_contains_required_fields(self):
        offsets = {
            "camera1.mp4": {"offset_sec": 0.0, "reference": "camera1.mp4"},
            "camera2.mp4": {"offset_sec": 0.4, "reference": "camera1.mp4"},
            "camera3.mp4": {"offset_sec": -0.6, "reference": "camera1.mp4"},
            "camera4.mp4": {"offset_sec": 1.2, "reference": "camera1.mp4"},
        }

        edl = build_edl(offsets, duration_sec=20.0)
        self.assertGreaterEqual(len(edl), 2)
        for item in edl:
            self.assertIn("start_time", item)
            self.assertIn("end_time", item)
            self.assertIn("selected_camera", item)
            self.assertIn("reason_for_selection", item)
            self.assertIn("transition", item)
            self.assertIn("lower_third", item)

    def test_write_edl_writes_json_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "generated_edl.json"
            write_edl(output_path, [{"start_time": 0, "end_time": 5, "selected_camera": "camera1"}])
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list)

    def test_build_edl_uses_video_directory_for_camera_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = Path(temp_dir)
            for name, freq in [("camera1.mp4", 220.0), ("camera2.mp4", 660.0)]:
                audio = AudioClip(lambda t: np.sin(2 * np.pi * freq * t).astype(np.float32), duration=4)
                video = ColorClip(size=(64, 64), color=(255, 0, 0), duration=4)
                video = video.with_audio(audio)
                video.write_videofile(str(video_dir / name), fps=24, codec="libx264", audio_codec="aac", logger=None)
                video.close()

            offsets = {
                "camera1.mp4": {"offset_sec": 0.0, "reference": "camera1.mp4"},
                "camera2.mp4": {"offset_sec": 0.2, "reference": "camera1.mp4"},
            }
            edl = build_edl(offsets, duration_sec=10.0, video_dir=video_dir)
            self.assertGreaterEqual(len(edl), 2)
            self.assertTrue(any(item["selected_camera"] == "camera2.mp4" for item in edl))


if __name__ == "__main__":
    unittest.main()
