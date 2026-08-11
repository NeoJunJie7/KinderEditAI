import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from moviepy import CompositeVideoClip, ColorClip, TextClip, VideoFileClip, concatenate_videoclips
from moviepy.video import fx


DEFAULT_EDL_PATH = Path("output") / "generated_edl.json"
DEFAULT_OUTPUT_PATH = Path("output") / "final_graduation_video.mp4"
DEFAULT_VIDEO_DIR = Path("starter-pack")


def load_edl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("EDL file must contain a JSON array")
    return payload


def resolve_video_path(video_name: str, video_dir: Path) -> Path:
    candidates = [video_dir / video_name, video_dir / f"{video_name}.mp4", Path(video_name)]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find video: {video_name}")


def build_clips(edl: List[Dict[str, Any]], video_map: Dict[str, Path], offsets: Optional[Dict[str, Dict[str, float]]] = None) -> List[Tuple[VideoFileClip, Dict[str, Any]]]:
    clips: List[Tuple[VideoFileClip, Dict[str, Any]]] = []
    for entry in edl:
        camera_name = entry.get("selected_camera")
        if not camera_name:
            continue
        video_path = video_map.get(camera_name)
        if not video_path:
            print(f"Warning: missing camera source '{camera_name}' for segment {len(clips)}")
            continue
        try:
            clip = VideoFileClip(str(video_path))
        except FileNotFoundError as exc:
            print(f"Warning: failed to load '{camera_name}': {exc}")
            continue

        start_time = float(entry.get("start_time", 0.0))
        end_time = float(entry.get("end_time", clip.duration))
        offset_sec = 0.0
        performance_start = 0.0
        performance_end = clip.duration
        if offsets and camera_name in offsets:
            offset_sec = float(offsets[camera_name].get("offset_sec", 0.0))
            performance_start = float(offsets[camera_name].get("performance_start_sec", 0.0))
            performance_end = float(offsets[camera_name].get("performance_end_sec", clip.duration))

        clip_start = max(0.0, min(start_time - offset_sec, clip.duration))
        clip_end = max(clip_start, min(end_time - offset_sec, clip.duration))
        clip_start = max(performance_start, clip_start)
        clip_end = min(performance_end, clip_end)

        if clip_start >= clip_end:
            clip.close()
            continue

        clip = clip.subclipped(clip_start, clip_end)
        clips.append((clip, entry))
    return clips


def add_title_screen(duration: float, output_size: Tuple[int, int]) -> CompositeVideoClip:
    title = (
        TextClip(text="KinderEdit AI\nGraduation Highlights", font_size=40, color="white")
        .with_position(("center", "center"))
        .with_duration(duration)
    )
    background = ColorClip(size=output_size, color=(0, 0, 0), duration=duration)
    return CompositeVideoClip([background, title])


def render_video(edl_path: Path, output_path: Path, video_dir: Path = DEFAULT_VIDEO_DIR, offsets: Optional[Dict[str, Dict[str, float]]] = None) -> Path:
    edl = load_edl(edl_path)
    video_map = {path.name: path for path in video_dir.glob("*.mp4")}
    clips_with_meta = build_clips(edl, video_map, offsets=offsets)

    if not clips_with_meta:
        raise ValueError("No clips were generated from the EDL")

    rendered_clips = []
    for clip_index, (clip, entry) in enumerate(clips_with_meta):
        try:
            lower_third = entry.get("lower_third", {})
            overlay_text = lower_third.get("text", "Graduation Moment")
            overlay = (
                TextClip(text=overlay_text, font_size=22, color="white")
                .with_position(("left", "top"))
                .with_duration(clip.duration)
            )
            segment_audio = clip.audio
            clip = clip.with_position("center")
            composite_clip = CompositeVideoClip([clip, overlay])
            if segment_audio is not None:
                composite_clip = composite_clip.with_audio(segment_audio)
            if composite_clip.duration > 1.0:
                composite_clip = fx.CrossFadeIn(1.0).apply(composite_clip)
            rendered_clips.append(composite_clip)
        except Exception as exc:  # pragma: no cover - defensive logging for real rendering failures
            print(f"Warning: failed to render segment {clip_index} for camera {entry.get('selected_camera')}: {exc}")
            continue

    final_clip = concatenate_videoclips(rendered_clips, method="compose")
    title_screen = add_title_screen(3.0, final_clip.size)
    closing_screen = (
        TextClip(text="Thank you!", font_size=40, color="white")
        .with_position(("center", "center"))
        .with_duration(2.0)
    )
    shifted_final_clip = final_clip.with_start(3.0)
    final_audio = shifted_final_clip.audio
    final_video = CompositeVideoClip([title_screen, shifted_final_clip, closing_screen])
    if final_audio is not None:
        final_video = final_video.with_audio(final_audio)
    final_video = final_video.with_duration(final_clip.duration + 5.0)
    final_video.write_videofile(str(output_path), codec="libx264", fps=24, audio_codec="aac")

    distinct_cameras = {entry.get("selected_camera") for _, entry in clips_with_meta if entry.get("selected_camera")}
    camera_switches = sum(
        1 for index in range(1, len(clips_with_meta)) if clips_with_meta[index - 1][1].get("selected_camera") != clips_with_meta[index][1].get("selected_camera")
    )
    print(f"Render summary: total_duration={final_video.duration:.2f}s, distinct_cameras={len(distinct_cameras)}, camera_switches={camera_switches}, has_audio={final_video.audio is not None}")
    if final_video.audio is None:
        raise AssertionError("Rendered video has no audio track")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a graduation highlight video from an EDL")
    parser.add_argument("--edl", default=str(DEFAULT_EDL_PATH), help="Path to the EDL JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Where to save the final MP4")
    parser.add_argument("--video-dir", default=str(DEFAULT_VIDEO_DIR), help="Directory containing the source MP4 videos")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    offsets_path = Path("output") / "sync_offsets.json"
    offsets = None
    if offsets_path.exists():
        try:
            with offsets_path.open("r", encoding="utf-8") as handle:
                offsets = json.load(handle)
        except Exception:
            offsets = None
    output_path = render_video(Path(args.edl), Path(args.output), Path(args.video_dir), offsets=offsets)
    print(f"Wrote video to {output_path}")


if __name__ == "__main__":
    main()
