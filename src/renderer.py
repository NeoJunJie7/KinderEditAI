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


def build_clips(edl: List[Dict[str, Any]], video_map: Dict[str, Path]) -> List[Tuple[VideoFileClip, Dict[str, Any]]]:
    clips: List[Tuple[VideoFileClip, Dict[str, Any]]] = []
    for entry in edl:
        camera_name = entry.get("selected_camera")
        if not camera_name:
            continue
        video_path = video_map.get(camera_name)
        if not video_path:
            continue
        try:
            clip = VideoFileClip(str(video_path))
        except FileNotFoundError:
            continue

        start_time = float(entry.get("start_time", 0.0))
        end_time = float(entry.get("end_time", clip.duration))
        if start_time >= clip.duration:
            clip.close()
            continue

        start_time = max(0.0, min(start_time, clip.duration))
        end_time = max(start_time, min(end_time, clip.duration))
        clip = clip.subclipped(start_time, end_time)
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


def render_video(edl_path: Path, output_path: Path, video_dir: Path = DEFAULT_VIDEO_DIR) -> Path:
    edl = load_edl(edl_path)
    video_map = {path.name: path for path in video_dir.glob("*.mp4")}
    clips_with_meta = build_clips(edl, video_map)

    if not clips_with_meta:
        raise ValueError("No clips were generated from the EDL")

    rendered_clips = []
    for clip, entry in clips_with_meta:
        lower_third = entry.get("lower_third", {})
        overlay_text = lower_third.get("text", "Graduation Moment")
        overlay = (
            TextClip(text=overlay_text, font_size=22, color="white")
            .with_position(("left", "top"))
            .with_duration(clip.duration)
        )
        clip = clip.with_position("center")
        clip = CompositeVideoClip([clip, overlay])
        if clip.duration > 1.0:
            clip = fx.CrossFadeIn(1.0).apply(clip)
        rendered_clips.append(clip)

    final_clip = concatenate_videoclips(rendered_clips, method="compose")
    title_screen = add_title_screen(3.0, final_clip.size)
    closing_screen = (
        TextClip(text="Thank you!", font_size=40, color="white")
        .with_position(("center", "center"))
        .with_duration(2.0)
    )
    final_video = CompositeVideoClip([title_screen, final_clip.with_start(3.0), closing_screen.with_start(final_clip.duration + 3.0)])
    final_video = final_video.with_duration(final_clip.duration + 5.0)
    final_video.write_videofile(str(output_path), codec="libx264", fps=24, audio_codec="aac")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a graduation highlight video from an EDL")
    parser.add_argument("--edl", default=str(DEFAULT_EDL_PATH), help="Path to the EDL JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Where to save the final MP4")
    parser.add_argument("--video-dir", default=str(DEFAULT_VIDEO_DIR), help="Directory containing the source MP4 videos")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = render_video(Path(args.edl), Path(args.output), Path(args.video_dir))
    print(f"Wrote video to {output_path}")


if __name__ == "__main__":
    main()
