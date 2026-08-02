import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.sync import select_video_files


class SyncTests(unittest.TestCase):
    def test_select_video_files_returns_four_files(self):
        files = select_video_files(Path("starter-pack"), count=4)
        self.assertEqual(len(files), 4)


if __name__ == "__main__":
    unittest.main()
