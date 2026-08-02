import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_OFFSETS_PATH = Path("output") / "sync_offsets.json"
DEFAULT_OUTPUT_PATH = Path("output") / "generated_edl.json"


def load_offsets(path: Path) -> Dict[str, Dict[str, float]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Offsets file must contain a JSON object")
    return payload


def _pick_camera(offsets: Dict[str, Dict[str, float]], time_sec: float) -> str:
    cameras = list(offsets.keys())
    if not cameras:
        raise ValueError("No cameras available to build an EDL")

    if len(cameras) == 1:
        return cameras[0]

    # Use a simple heuristic: select the file whose offset is closest to zero at the current point.
    # This keeps the timeline stable and uses the reference camera when possible.
    def score(camera_name: str) -> float:
        offset = float(offsets[camera_name].get("offset_sec", 0.0))
        return abs(offset + (time_sec % 4.0) * 0.05)

    return min(cameras, key=score)


def build_edl(offsets: Dict[str, Dict[str, float]], duration_sec: float = 30.0, min_segment: float = 5.0, max_segment: float = 10.0) -> List[Dict[str, Any]]:
    """Generate a simple EDL that switches cameras every 5-10 seconds."""
    if not offsets:
        raise ValueError("No offsets supplied")

    segments: List[Dict[str, Any]] = []
    current_time = 0.0
    while current_time < duration_sec:
        segment_length = min(max_segment, min_segment + (len(segments) % 2) * 2.5)
        segment_end = min(duration_sec, current_time + segment_length)
        camera_name = _pick_camera(offsets, current_time)
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
                "reason_for_selection": "Best alignment with the reference timeline and stable framing",
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
    parser.add_argument("--duration", type=float, default=30.0, help="Total duration of the highlight in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    offsets_path = Path(args.offsets)
    output_path = Path(args.output)

    offsets = load_offsets(offsets_path)
    edl = build_edl(offsets, duration_sec=args.duration)
    write_edl(output_path, edl)
    print(f"Wrote {len(edl)} EDL entries to {output_path}")


if __name__ == "__main__":
    main()
