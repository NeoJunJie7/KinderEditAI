import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from moviepy import AudioClip, ColorClip

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.edl_generator import build_edl, write_edl, _pick_camera


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
            for name, amp in [("camera1.mp4", 0.2), ("camera2.mp4", 1.0)]:
                audio = AudioClip(lambda t, amp=amp: (amp * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32), duration=10.0)
                video = ColorClip(size=(64, 64), color=(255, 0, 0), duration=10.0)
                video = video.with_audio(audio)
                video.write_videofile(str(video_dir / name), fps=24, codec="libx264", audio_codec="aac", logger=None)
                video.close()

            offsets = {
                "camera1.mp4": {"offset_sec": 0.0, "performance_start_sec": 0.0, "performance_end_sec": 10.0},
                "camera2.mp4": {"offset_sec": 0.2, "performance_start_sec": 0.0, "performance_end_sec": 10.0},
            }
            edl = build_edl(offsets, duration_sec=10.0, video_dir=video_dir)
            self.assertGreaterEqual(len(edl), 2)
            self.assertTrue(any(item["selected_camera"] == "camera2.mp4" for item in edl))

    def test_build_edl_selects_all_cameras_for_project_offsets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_dir = Path(temp_dir)
            # Write three synthetic camera files with staggered timings matching the project offsets.
            offsets = {
                "camera1_center_closeup.mp4": {
                    "offset_sec": 88.848,
                    "performance_start_sec": 88.848,
                    "performance_end_sec": 288.848,
                },
                "camera3_center_wide.mp4": {
                    "offset_sec": 292.16725,
                    "performance_start_sec": 292.16725,
                    "performance_end_sec": 492.16725,
                },
                "camera4_front_left.mp4": {
                    "offset_sec": 3.675,
                    "performance_start_sec": 3.675,
                    "performance_end_sec": 183.675,
                },
                "performance_window": {
                    "start_sec": 0.0,
                    "end_sec": 120.0,
                    "duration_sec": 120.0,
                },
            }

            def make_audio(filename: str, freq: float, duration: float):
                audio = AudioClip(lambda t: np.sin(2 * np.pi * freq * t).astype(np.float32), duration=duration)
                video = ColorClip(size=(64, 64), color=(255, 0, 0), duration=duration)
                video = video.with_audio(audio)
                video.write_videofile(str(video_dir / filename), fps=24, codec="libx264", audio_codec="aac", logger=None)
                video.close()

            # Patch extract_audio_signal to return deterministic synthetic energy for each camera.
            def fake_extract_audio_signal(path, sample_rate=16000, duration=None, start_time=0.0, end_time=None):
                if end_time is None:
                    end_time = duration if duration is not None else 0.0
                length = max(0, end_time - start_time)
                # Use energy shape based on the requested global timeline window.
                if path.name == "camera4_front_left.mp4":
                    amp = 0.5 if start_time < 40.0 else 0.15
                elif path.name == "camera1_center_closeup.mp4":
                    amp = 0.2 if start_time < 40.0 else 0.5 if start_time < 80.0 else 0.2
                elif path.name == "camera3_center_wide.mp4":
                    amp = 0.15 if start_time < 80.0 else 0.6
                else:
                    amp = 0.1
                samples = int(max(1, length * sample_rate))
                return (amp * np.ones(samples, dtype=np.float32))

            for filename in ["camera1_center_closeup.mp4", "camera3_center_wide.mp4", "camera4_front_left.mp4"]:
                (video_dir / filename).write_bytes(b"dummy")

            with patch("src.edl_generator.extract_audio_signal", side_effect=fake_extract_audio_signal):
                edl = build_edl(offsets, highlight_duration=120.0, video_dir=video_dir)

            self.assertEqual(edl[0]["start_time"], 0.0)
            self.assertEqual(edl[-1]["end_time"], 120.0)
            # Ensure all three cameras are selected at least once in the 120s highlight.
            selected = {item["selected_camera"] for item in edl}
            self.assertTrue({"camera1_center_closeup.mp4", "camera3_center_wide.mp4", "camera4_front_left.mp4"}.issubset(selected))


if __name__ == "__main__":
    unittest.main()
