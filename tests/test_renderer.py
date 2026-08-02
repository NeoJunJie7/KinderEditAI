import json
import sys
import tempfile
import unittest
from pathlib import Path

from moviepy import ColorClip

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.renderer import build_clips, load_edl


class RendererTests(unittest.TestCase):
    def test_load_edl_reads_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "edl.json"
            path.write_text(json.dumps([{"start_time": 0, "end_time": 2, "selected_camera": "cam1"}]), encoding="utf-8")
            self.assertEqual(len(load_edl(path)), 1)

    def test_build_clips_returns_expected_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "cam1.mp4"
            clip = ColorClip(size=(64, 64), color=(255, 0, 0), duration=2)
            clip.write_videofile(str(video_path), fps=24, codec="libx264", audio=False)
            clip.close()

            edl = [{"start_time": 0, "end_time": 2, "selected_camera": "cam1", "transition": "cut", "lower_third": {"text": "Hi"}}]
            clips = build_clips(edl, {"cam1": video_path})
            self.assertEqual(len(clips), 1)
            for clip, _ in clips:
                clip.close()


if __name__ == "__main__":
    unittest.main()
