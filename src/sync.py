import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from moviepy.audio.io.AudioFileClip import AudioFileClip
from scipy.signal import fftconvolve


DEFAULT_INPUT_DIR = Path("starter-pack")
DEFAULT_OUTPUT_PATH = Path("output") / "sync_offsets.json"
DEFAULT_ALIGNMENT_SAMPLE_RATE = 4000
DEFAULT_ONSET_WINDOW_SEC = 1.0
DEFAULT_ONSET_STEP_SEC = 0.5
DEFAULT_ONSET_THRESHOLD_FACTOR = 4.0
DEFAULT_ONSET_SUSTAIN_SEC = 3.0
DEFAULT_ALIGNMENT_CONFIDENCE_THRESHOLD = 8.0
DEFAULT_PERFORMANCE_DURATION = 220.0
DEFAULT_PERFORMANCE_BUFFER = 10.0
MIN_PERFORMANCE_DURATION = 180.0
MAX_PERFORMANCE_DURATION = DEFAULT_PERFORMANCE_DURATION + DEFAULT_PERFORMANCE_BUFFER


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


def format_time(seconds: float) -> str:
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def _find_reference_video(video_paths: List[Path]) -> Path:
    for path in video_paths:
        stem = path.stem.lower()
        if "camera2" in stem or "cam2" in stem:
            return path
    return min(video_paths, key=lambda p: p.stat().st_size)


def detect_energy_window(
    waveform: np.ndarray,
    sample_rate: int = DEFAULT_ALIGNMENT_SAMPLE_RATE,
    window_sec: float = DEFAULT_ONSET_WINDOW_SEC,
    step_sec: float = DEFAULT_ONSET_STEP_SEC,
    threshold_factor: float = DEFAULT_ONSET_THRESHOLD_FACTOR,
    min_sustain_sec: float = DEFAULT_ONSET_SUSTAIN_SEC,
) -> Tuple[float, float]:
    if waveform.size == 0:
        return 0.0, 0.0

    window = max(1, int(window_sec * sample_rate))
    step = max(1, int(step_sec * sample_rate))
    energy = []
    positions = []
    for start in range(0, max(1, waveform.shape[0] - window + 1), step):
        segment = waveform[start : start + window]
        energy.append(float(np.sqrt(np.mean(np.square(segment)))))
        positions.append(start)

    if not energy:
        return 0.0, float(waveform.shape[0]) / sample_rate

    energy = np.array(energy, dtype=np.float64)
    baseline = float(np.median(energy[: max(1, len(energy) // 10)]))
    threshold = max(baseline * threshold_factor, 1e-4)
    sustain_slots = max(1, int(math.ceil(min_sustain_sec / step_sec)))

    for idx in range(0, len(energy) - sustain_slots + 1):
        if np.all(energy[idx : idx + sustain_slots] >= threshold):
            start_sec = positions[idx] / sample_rate
            end_idx = idx + sustain_slots
            while end_idx < len(energy) and energy[end_idx] >= threshold:
                end_idx += 1
            end_sec = min((positions[min(end_idx, len(positions) - 1)] + window) / sample_rate, waveform.shape[0] / sample_rate)
            return float(start_sec), float(end_sec)

    return 0.0, float(waveform.shape[0]) / sample_rate


def detect_performance_end(
    waveform: np.ndarray,
    performance_start: float,
    sample_rate: int = DEFAULT_ALIGNMENT_SAMPLE_RATE,
    window_sec: float = DEFAULT_ONSET_WINDOW_SEC,
    step_sec: float = DEFAULT_ONSET_STEP_SEC,
    quiet_factor: float = 1.5,
    end_sustain_sec: float = 5.0,
) -> float:
    if waveform.size == 0 or performance_start >= float(waveform.shape[0]) / sample_rate:
        return performance_start

    window = max(1, int(window_sec * sample_rate))
    step = max(1, int(step_sec * sample_rate))
    energy = []
    positions = []
    for start in range(0, max(1, waveform.shape[0] - window + 1), step):
        segment = waveform[start : start + window]
        energy.append(float(np.sqrt(np.mean(np.square(segment)))))
        positions.append(start)

    if not energy:
        return min(performance_start + DEFAULT_PERFORMANCE_DURATION + DEFAULT_PERFORMANCE_BUFFER, float(waveform.shape[0]) / sample_rate)

    energy = np.array(energy, dtype=np.float64)
    baseline = float(np.median(energy[: max(1, len(energy) // 10)]))
    quiet_threshold = max(baseline * quiet_factor, 1e-4)
    start_index = next((i for i, pos in enumerate(positions) if pos / sample_rate >= performance_start), 0)
    sustain_slots = max(1, int(math.ceil(end_sustain_sec / step_sec)))

    for idx in range(start_index, len(energy) - sustain_slots + 1):
        if np.all(energy[idx : idx + sustain_slots] <= quiet_threshold):
            end_sec = min((positions[idx] + window) / sample_rate, float(waveform.shape[0]) / sample_rate)
            if end_sec > performance_start + MIN_PERFORMANCE_DURATION:
                return float(end_sec)

    return min(performance_start + DEFAULT_PERFORMANCE_DURATION + DEFAULT_PERFORMANCE_BUFFER, float(waveform.shape[0]) / sample_rate)


def estimate_alignment(reference: np.ndarray, target: np.ndarray, sample_rate: int = DEFAULT_ALIGNMENT_SAMPLE_RATE) -> Tuple[float, float]:
    if len(reference) == 0 or len(target) == 0 or len(target) < len(reference):
        return 0.0, 0.0

    reference = reference.astype(np.float64)
    target = target.astype(np.float64)
    reference -= np.mean(reference)
    target -= np.mean(target)
    reference_std = float(np.std(reference))
    target_std = float(np.std(target))
    if reference_std < 1e-8 or target_std < 1e-8:
        return 0.0, 0.0

    reference /= reference_std
    target /= target_std
    corr = fftconvolve(target, reference[::-1], mode="valid")
    peak_index = int(np.argmax(corr))
    peak_value = float(corr[peak_index])
    noise_floor = float(np.median(np.abs(corr))) + 1e-8
    confidence = peak_value / noise_floor
    return float(peak_index / sample_rate), float(confidence)


def compute_offsets(video_paths: List[Path]) -> Dict[str, Dict[str, float]]:
    if len(video_paths) < 2:
        raise ValueError("At least two videos are required to compute offsets")

    reference_path = _find_reference_video(video_paths)
    print(f"Using reference fingerprint video: {reference_path.name}")
    reference_audio = extract_audio_signal(reference_path, sample_rate=DEFAULT_ALIGNMENT_SAMPLE_RATE)
    reference_onset_start, reference_onset_end = detect_energy_window(reference_audio)

    temp_results: Dict[str, Dict[str, float]] = {}
    for video_path in video_paths:
        target_audio = extract_audio_signal(video_path, sample_rate=DEFAULT_ALIGNMENT_SAMPLE_RATE)
        onset_start, onset_end = detect_energy_window(target_audio)
        aligned_start, confidence = estimate_alignment(reference_audio, target_audio)
        if confidence < DEFAULT_ALIGNMENT_CONFIDENCE_THRESHOLD:
            method = "energy onset fallback"
            performance_start = onset_start if onset_start > 0 else aligned_start
        else:
            method = "correlation alignment"
            performance_start = onset_start if onset_start > 0 else aligned_start

        if video_path == reference_path:
            performance_start = reference_onset_start
            method = "reference"
            confidence = 1.0

        # Determine performance end using eventual energy decay or fixed duration.
        performance_end = detect_performance_end(
            target_audio,
            performance_start,
            sample_rate=DEFAULT_ALIGNMENT_SAMPLE_RATE,
        )

        temp_results[video_path.name] = {
            "global_offset_sec": float(performance_start),
            "performance_start_sec": float(performance_start),
            "performance_end_sec": float(performance_end),
            "confidence": float(confidence),
            "method": method,
            "reference": reference_path.name,
        }
        print(
            f"{video_path.name}: performance_start={format_time(performance_start)}, "
            f"performance_end={format_time(performance_end)}, confidence={confidence:.1f}, method={method}"
        )

    global_start = min(item["performance_start_sec"] for item in temp_results.values())
    global_end = max(item["performance_end_sec"] for item in temp_results.values())

    offsets: Dict[str, Dict[str, float]] = {}
    for camera_name, result in temp_results.items():
        offsets[camera_name] = {
            "offset_sec": float(result["performance_start_sec"] - global_start),
            **result,
        }

    offsets["performance_window"] = {
        "start_sec": float(global_start),
        "end_sec": float(global_end),
        "duration_sec": float(max(0.0, global_end - global_start)),
    }
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
        if name == "performance_window":
            continue
        print(f"{name}: {payload['offset_sec']:.3f}s")


if __name__ == "__main__":
    main()
