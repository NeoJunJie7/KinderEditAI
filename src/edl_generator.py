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
    debug_scores: bool = False,
) -> Tuple[str, str]:
    """Select the best camera for a time window by comparing audio energy scores.
    
    This function evaluates all available cameras for a specific timeline segment.
    It applies sync offsets to ensure accurate audio window extraction and enforces
    a rule to switch cameras if the same angle has been used for MAX_CONSECUTIVE_SEGMENTS
    to maintain visual dynamism.
    
    Args:
        offsets: Dictionary containing sync and performance window metadata.
        time_sec: The current timeline position being evaluated.
        previous_camera: The camera selected in the immediately preceding segment.
        consecutive_count: How many times the previous_camera has been used in a row.
        
    Returns:
        A tuple containing the selected camera name and the string reason for selection.
    """
    cameras = [name for name in offsets.keys() if name != "performance_window"]
    if not cameras:
        raise ValueError("No cameras available to build an EDL")

    if len(cameras) == 1:
        return cameras[0], "Only camera available"

    video_dir = video_dir or DEFAULT_VIDEO_DIR
    start_time = max(0.0, start_time if start_time is not None else time_sec)
    end_time = max(start_time, end_time if end_time is not None else start_time + 5.0)

    energies: Dict[str, float] = {}
    valid_cameras: List[str] = []
    for camera_name in cameras:
        candidate_path = video_dir / camera_name
        if not candidate_path.exists() and not camera_name.endswith(".mp4"):
            candidate_path = video_dir / f"{camera_name}.mp4"
        if not candidate_path.exists():
            energies[camera_name] = 0.0
            if debug_scores:
                print(f"DEBUG {camera_name}: missing source file, scored 0")
            continue

        camera_info = offsets.get(camera_name, {})
        camera_source_start = float(camera_info.get("performance_start_sec", 0.0))
        camera_source_end = float(camera_info.get("performance_end_sec", float("inf")))
        offset_sec = float(camera_info.get("offset_sec", 0.0))
        camera_timeline_start = 0.0
        camera_timeline_end = max(0.0, camera_source_end - camera_source_start)
        if start_time < camera_timeline_start or end_time > camera_timeline_end:
            energies[camera_name] = 0.0
            if debug_scores:
                print(
                    f"DEBUG {camera_name}: segment [{start_time:.3f},{end_time:.3f}] not fully covered by timeline "
                    f"[{camera_timeline_start:.3f},{camera_timeline_end:.3f}], scored 0"
                )
            continue

        valid_cameras.append(camera_name)
        energy = compute_camera_energy(candidate_path, start_time, end_time, offset_sec)
        energies[camera_name] = energy
        if debug_scores:
            print(
                f"DEBUG {camera_name}: segment [{start_time:.3f},{end_time:.3f}], "
                f"offset={offset_sec:.3f}, energy={energy:.6f}"
            )

    ranked = sorted(energies.items(), key=lambda item: item[1], reverse=True)
    if not valid_cameras:
        fallback_camera = cameras[round_robin_index % len(cameras)]
        return fallback_camera, "No camera has valid coverage for this segment — deterministic round-robin"

    if all(score < MIN_ENERGY_THRESHOLD for camera, score in ranked if camera in valid_cameras):
        candidate_name = next((camera for camera, _ in ranked if camera in valid_cameras), valid_cameras[0])
        return candidate_name, "Low energy across valid cameras — selected highest valid energy"

    ranked_valid = [(camera, score) for camera, score in ranked if camera in valid_cameras]
    if ranked_valid:
        top_score = ranked_valid[0][1]
        tied = [camera for camera, score in ranked_valid if abs(score - top_score) < 1e-9]
        candidate_name = tied[round_robin_index % len(tied)] if len(tied) > 1 else ranked_valid[0][0]
    else:
        candidate_name = ranked[0][0]

    if previous_camera and previous_camera == candidate_name and consecutive_count >= MAX_CONSECUTIVE_SEGMENTS:
        if len(ranked_valid) > 1:
            candidate_name = ranked_valid[1][0]
            return candidate_name, "Second-highest energy — forced switch after 3 consecutive segments on this camera"

    if debug_scores:
        scored = ", ".join(f"{name}={value:.6f}" for name, value in ranked)
        print(f"DEBUG segment [{start_time:.3f},{end_time:.3f}] scores: {scored}")
    return candidate_name, "Highest audio energy in segment window"


def build_edl(
    offsets: Dict[str, Dict[str, float]],
    duration_sec: Optional[float] = None,
    highlight_duration: Optional[float] = None,
    min_segment: float = 5.0,
    max_segment: float = 10.0,
    video_dir: Optional[Path] = None,
    debug_scores: bool = False,
) -> List[Dict[str, Any]]:
    """Generate an EDL that switches cameras based on segment audio energy and sync offsets."""
    if not offsets:
        raise ValueError("No offsets supplied")

    performance_window = offsets.get("performance_window")
    if performance_window:
        performance_start = float(performance_window["start_sec"])
        performance_end = float(performance_window["end_sec"])
    else:
        camera_windows = [
            (float(info.get("performance_start_sec", 0.0)), float(info.get("performance_end_sec", 0.0)))
            for name, info in offsets.items()
            if name != "performance_window"
        ]
        if camera_windows and any(end > start for start, end in camera_windows):
            performance_start = min(start for start, end in camera_windows if end > start)
            performance_end = max(end for start, end in camera_windows if end > start)
        else:
            performance_start = 0.0
            if duration_sec is not None and duration_sec > 0:
                performance_end = performance_start + float(duration_sec)
            else:
                performance_end = performance_start + DEFAULT_HIGHLIGHT_DURATION

    if highlight_duration is None:
        request_duration = float(duration_sec) if duration_sec is not None else DEFAULT_HIGHLIGHT_DURATION
    else:
        request_duration = float(highlight_duration)
        request_duration = max(MIN_HIGHLIGHT_DURATION, min(MAX_HIGHLIGHT_DURATION, request_duration))
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
            debug_scores=debug_scores,
        )

        camera_info = offsets.get(camera_name, {})
        camera_source_start = float(camera_info.get("performance_start_sec", performance_start))
        camera_source_end = float(camera_info.get("performance_end_sec", performance_end))
        camera_timeline_start = 0.0
        camera_timeline_end = max(0.0, camera_source_end - camera_source_start)
        if segment_end > camera_timeline_end:
            segment_end = camera_timeline_end
        if current_time < camera_timeline_start:
            current_time = camera_timeline_start
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
    parser.add_argument(
        "--debug-scores",
        action="store_true",
        help="Print raw energy scores for each camera and segment during EDL generation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    offsets_path = Path(args.offsets)
    output_path = Path(args.output)

    offsets = load_offsets(offsets_path)
    edl = build_edl(
        offsets,
        highlight_duration=args.highlight_duration,
        video_dir=DEFAULT_VIDEO_DIR,
        debug_scores=args.debug_scores,
    )
    write_edl(output_path, edl)
    print(f"Wrote {len(edl)} EDL entries to {output_path}")


if __name__ == "__main__":
    main()
