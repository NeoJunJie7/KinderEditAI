import argparse
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from moviepy.audio.io.AudioFileClip import AudioFileClip


DEFAULT_INPUT_DIR = Path("starter-pack")
DEFAULT_OUTPUT_PATH = Path("output") / "sync_offsets.json"


def select_video_files(input_dir: Path, count: int = 4) -> List[Path]:
    """Select up to ``count`` MP4 files from the input directory."""
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    videos = sorted(input_dir.glob("*.mp4"))
    if len(videos) < count:
        raise ValueError(f"Expected at least {count} MP4 files in {input_dir}, found {len(videos)}")

    return videos[:count]


def extract_audio_signal(
    video_path: Path,
    sample_rate: int = 16000,
    duration: Optional[float] = None,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
) -> np.ndarray:
    """Extract a mono audio waveform from a video file window."""
    clip = AudioFileClip(str(video_path))
    try:
        if duration is not None:
            end_time = start_time + duration
        if end_time is None:
            end_time = clip.duration
        window_start = max(0.0, min(float(start_time), clip.duration))
        window_end = max(window_start, min(float(end_time), clip.duration))
        if window_end <= window_start:
            return np.zeros(0, dtype=np.float32)
        audio = clip.subclipped(window_start, window_end)
        waveform = audio.to_soundarray(fps=sample_rate, buffersize=sample_rate)
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        return waveform.astype(np.float32)
    finally:
        clip.close()


def estimate_offset(reference: np.ndarray, target: np.ndarray) -> float:
    """Estimate the offset in seconds between two audio signals using correlation."""
    if len(reference) == 0 or len(target) == 0:
        return 0.0

    if len(reference) > len(target):
        reference = reference[: len(target)]
    else:
        target = target[: len(reference)]

    reference = reference - np.mean(reference)
    target = target - np.mean(target)

    corr = np.correlate(reference, target, mode="full")
    lag = np.argmax(corr) - (len(reference) - 1)
    lag_seconds = lag / 16000.0
    return float(lag_seconds)


def compute_offsets(video_paths: List[Path]) -> Dict[str, Dict[str, float]]:
    """Compute offsets for each video relative to the first video."""
    if len(video_paths) < 2:
        raise ValueError("At least two videos are required to compute offsets")

    reference_path = video_paths[0]
    reference_audio = extract_audio_signal(reference_path)

    offsets: Dict[str, Dict[str, float]] = {
        reference_path.name: {"offset_sec": 0.0, "reference": reference_path.name}
    }
    for video_path in video_paths[1:]:
        target_audio = extract_audio_signal(video_path)
        lag = estimate_offset(reference_audio, target_audio)
        offsets[video_path.name] = {"offset_sec": lag, "reference": reference_path.name}

    return offsets


def write_offsets(output_path: Path, offsets: Dict[str, Dict[str, float]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(offsets, handle, indent=2)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate audio sync offsets for videos")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory containing the MP4 files")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Where to write the JSON offsets")
    parser.add_argument("--count", type=int, default=4, help="Number of videos to process")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    video_paths = select_video_files(input_dir, count=args.count)
    offsets = compute_offsets(video_paths)
    write_offsets(output_path, offsets)
    print(f"Wrote {len(offsets)} offsets to {output_path}")
    for name, payload in offsets.items():
        print(f"{name}: {payload['offset_sec']:.3f}s")


if __name__ == "__main__":
    main()
