import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from src.sync import extract_audio_signal
except ModuleNotFoundError:  # pragma: no cover - allows direct script execution from src/
    from sync import extract_audio_signal


DEFAULT_OFFSETS_PATH = Path("output") / "sync_offsets.json"
DEFAULT_OUTPUT_PATH = Path("output") / "generated_edl.json"
DEFAULT_VIDEO_DIR = Path("starter-pack")
MIN_ENERGY_THRESHOLD = 0.02
MAX_CONSECUTIVE_SEGMENTS = 3
DEFAULT_HIGHLIGHT_DURATION = 90.0
MIN_HIGHLIGHT_DURATION = 60.0
MAX_HIGHLIGHT_DURATION = 180.0


def load_offsets(path: Path) -> Dict[str, Dict[str, float]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Offsets file must contain a JSON object")
    return payload


def compute_camera_energy(video_path: Path, start_time: float, end_time: float, offset_sec: float, sample_rate: int = 16000) -> float:
    """Return the RMS audio energy of a camera window after applying its sync offset."""
    waveform = extract_audio_signal(video_path, sample_rate=sample_rate, start_time=start_time + offset_sec, end_time=end_time + offset_sec)
    if waveform.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(waveform))))


def _pick_camera(
    offsets: Dict[str, Dict[str, float]],
    time_sec: float,
    video_dir: Optional[Path] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    previous_camera: Optional[str] = None,
    consecutive_count: int = 0,
    round_robin_index: int = 0,
) -> Tuple[str, str]:
    """Select the best camera for a time window by comparing audio energy scores."""
    cameras = [name for name in offsets.keys() if name != "performance_window"]
    if not cameras:
        raise ValueError("No cameras available to build an EDL")

    if len(cameras) == 1:
        return cameras[0], "Only camera available"

    video_dir = video_dir or DEFAULT_VIDEO_DIR
    start_time = max(0.0, start_time if start_time is not None else time_sec)
    end_time = max(start_time, end_time if end_time is not None else start_time + 5.0)

    energies: Dict[str, float] = {}
    for camera_name in cameras:
        candidate_path = video_dir / camera_name
        if not candidate_path.exists() and not camera_name.endswith(".mp4"):
            candidate_path = video_dir / f"{camera_name}.mp4"
        if not candidate_path.exists():
            energies[camera_name] = 0.0
            continue

        offset_sec = float(offsets[camera_name].get("offset_sec", 0.0))
        energies[camera_name] = compute_camera_energy(candidate_path, start_time, end_time, offset_sec)

    ranked = sorted(energies.items(), key=lambda item: item[1], reverse=True)
    if all(score < MIN_ENERGY_THRESHOLD for _, score in ranked):
        fallback_camera = cameras[round_robin_index % len(cameras)]
        return fallback_camera, "Low energy across cameras — deterministic round-robin"

    candidate_name = ranked[0][0]
    if previous_camera and previous_camera == candidate_name and consecutive_count >= MAX_CONSECUTIVE_SEGMENTS:
        if len(ranked) > 1:
            candidate_name = ranked[1][0]
            return candidate_name, "Second-highest energy — forced switch after 3 consecutive segments on this camera"

    return candidate_name, "Highest audio energy in segment window"


def build_edl(
    offsets: Dict[str, Dict[str, float]],
    duration_sec: Optional[float] = None,
    highlight_duration: Optional[float] = None,
    min_segment: float = 5.0,
    max_segment: float = 10.0,
    video_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Generate an EDL that switches cameras based on segment audio energy and sync offsets."""
    if not offsets:
        raise ValueError("No offsets supplied")

    performance_window = offsets.get("performance_window")
    if not performance_window:
        raise ValueError("Offsets JSON must include a performance_window")

    highlight_duration = highlight_duration if highlight_duration is not None else duration_sec
    if highlight_duration is None:
        highlight_duration = DEFAULT_HIGHLIGHT_DURATION

    highlight_duration = max(MIN_HIGHLIGHT_DURATION, min(MAX_HIGHLIGHT_DURATION, highlight_duration))
    request_duration = float(highlight_duration)
    performance_start = float(performance_window["start_sec"])
    performance_end = float(performance_window["end_sec"])
    performance_duration = performance_end - performance_start
    if performance_duration <= 0:
        raise ValueError("Detected performance window has non-positive duration")

    if request_duration > performance_duration:
        request_duration = performance_duration

    segments: List[Dict[str, Any]] = []
    current_time = performance_start
    end_target = performance_start + request_duration
    previous_camera: Optional[str] = None
    previous_streak = 0
    round_robin_index = 0

    while current_time < end_target:
        segment_length = min(max_segment, min_segment + (len(segments) % 2) * 2.5)
        segment_end = min(end_target, current_time + segment_length)
        camera_name, reason = _pick_camera(
            offsets,
            current_time,
            video_dir=video_dir,
            start_time=current_time,
            end_time=segment_end,
            previous_camera=previous_camera,
            consecutive_count=previous_streak,
            round_robin_index=round_robin_index,
        )

        camera_info = offsets.get(camera_name, {})
        camera_start = camera_info.get("performance_start_sec", performance_start)
        camera_end = camera_info.get("performance_end_sec", performance_end)
        if segment_end > camera_end:
            segment_end = camera_end
        if current_time < camera_start:
            current_time = camera_start
            continue
        if segment_end <= current_time:
            break

        if camera_name == previous_camera:
            previous_streak += 1
        else:
            previous_streak = 1
        previous_camera = camera_name
        camera_count = max(1, len([k for k in offsets.keys() if k != "performance_window"]))
        round_robin_index = (round_robin_index + 1) % camera_count

        lower_third = {
            "text": f"Camera {camera_name}",
            "position": "top-left",
            "font_size": 24,
        }
        segments.append(
            {
                "start_time": round(current_time, 3),
                "end_time": round(segment_end, 3),
                "selected_camera": camera_name,
                "reason_for_selection": reason,
                "transition": "fade" if len(segments) % 2 == 0 else "cut",
                "lower_third": lower_third,
            }
        )
        current_time = segment_end

    return segments


def write_edl(output_path: Path, edl: List[Dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(edl, handle, indent=2)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an EDL JSON file from sync offsets")
    parser.add_argument("--offsets", default=str(DEFAULT_OFFSETS_PATH), help="Path to the sync offsets JSON file")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path to write the generated EDL JSON")
    parser.add_argument(
        "--highlight-duration",
        type=float,
        default=DEFAULT_HIGHLIGHT_DURATION,
        help="Duration of the selected highlight in seconds (60-180)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    offsets_path = Path(args.offsets)
    output_path = Path(args.output)

    offsets = load_offsets(offsets_path)
    edl = build_edl(offsets, highlight_duration=args.highlight_duration, video_dir=DEFAULT_VIDEO_DIR)
    write_edl(output_path, edl)
    print(f"Wrote {len(edl)} EDL entries to {output_path}")


if __name__ == "__main__":
    main()
