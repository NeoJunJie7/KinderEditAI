# KinderEditAI

**AI-Assisted Multi-Camera Kindergarten Graduation Video Editing Pipeline**

A semi-automated video editing pipeline that synchronizes multi-camera footage, selects the best camera angle per segment based on audio energy, generates an Editing Decision List (EDL), and renders a final highlight video — reducing the manual editing workload typically required to combine multi-camera event footage into one polished video.

> Built for BTIS3053 (Social & Professional Issues), Southern University College, 2026B.

---

## Overview

A kindergarten graduation ceremony (or similar event) is recorded using multiple cameras from different angles. Instead of manually reviewing, synchronizing, and cutting hours of footage, this pipeline automates the process into three stages:

1. **Sync** — aligns multiple camera recordings onto a shared timeline and detects the actual performance window within each (long) source file.
2. **EDL Generation** — builds an Editing Decision List by scoring each camera's audio energy per time segment and selecting the best angle, with rules to avoid overly long single-camera runs.
3. **Render** — assembles the final video from the EDL: trims and stitches camera clips, adds an opening title, closing credits, lower-third camera labels, and transitions.

A human is expected to review the generated EDL and final video before publishing — this pipeline is **semi-automated**, not fully autonomous.

---

## Pipeline Architecture

```
starter-pack/                  Raw camera footage (.mp4)
   ├── camera1_*.mp4
   ├── camera2_*.mp4
   ├── camera3_*.mp4
   └── camera4_*.mp4
        │
        ▼
   src/sync.py            →  output/sync_offsets.json
        │                     (per-camera offset + detected
        │                      performance start/end + confidence)
        ▼
   src/edl_generator.py   →  output/generated_edl.json
        │                     (segment list: camera, start/end,
        │                      reason, transition, lower-third)
        ▼
   src/renderer.py        →  output/final_graduation_video.mp4
```

### 1. `sync.py` — Synchronization & Performance Detection
- Selects a reference camera (defaults to the shortest/most performance-focused clip if named `camera2*`, otherwise the smallest file).
- Uses FFT-based cross-correlation (`scipy.signal.fftconvolve`) between each camera's audio and the reference to estimate alignment offset.
- Falls back to audio-energy onset detection if correlation confidence is low.
- Detects the performance's actual start and end within each (potentially much longer) source file, avoiding processing/syncing on irrelevant footage (setup, other acts, silence).
- Outputs `sync_offsets.json` with per-camera `offset_sec`, `performance_start_sec`, `performance_end_sec`, `confidence`, and method used.

### 2. `edl_generator.py` — EDL Generation
- Reads `sync_offsets.json` and builds a segment-by-segment EDL over a requested highlight duration (60–180s).
- For each segment window, scores every camera's RMS audio energy (accounting for each camera's sync offset and valid coverage window) and selects the highest-scoring camera.
- Forces a camera switch after 3 consecutive segments on the same camera to avoid overly long static shots.
- Cameras without valid coverage for a given segment (e.g. footage that doesn't extend that far) are excluded from selection for that segment.
- Outputs `generated_edl.json`: a list of segments with `start_time`, `end_time`, `selected_camera`, `reason_for_selection`, `transition`, and `lower_third` label data.

### 3. `renderer.py` — Rendering
- Loads each EDL segment's source clip, trims it to the correct in/out points (accounting for sync offset and detected performance window), and concatenates them in order.
- Adds:
  - A 3-second opening title screen
  - A 2-second closing credits screen
  - Lower-third camera labels per segment
  - Transitions between segments
- Outputs a final MP4 and prints a render summary (total duration, distinct cameras used, number of camera switches, audio presence check).

---

## Requirements

- Python 3.12+
- [MoviePy](https://github.com/Zulko/moviepy)
- NumPy, SciPy
- FFmpeg (available on PATH)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Usage

Place your 4 camera source files in `starter-pack/` (e.g. `camera1_center_closeup.mp4`, `camera2_front_right.mp4`, `camera3_center_wide.mp4`, `camera4_front_left.mp4`), then run each stage in order:

```bash
# 1. Synchronize cameras and detect performance window
python src/sync.py --input-dir starter-pack --output output/sync_offsets.json

# 2. Generate the Editing Decision List
python src/edl_generator.py --offsets output/sync_offsets.json --output output/generated_edl.json --highlight-duration 120

# 3. Render the final video
python src/renderer.py --edl output/generated_edl.json --output output/final_graduation_video.mp4 --video-dir starter-pack
```

**Optional flags:**
- `--debug-scores` (edl_generator.py) — prints raw per-camera audio energy scores for each segment, useful for understanding/auditing why a camera was or wasn't selected.
- `--count` (sync.py) — number of camera files to process (default: 4).

---

## Output Files

| File | Description |
|---|---|
| `output/sync_offsets.json` | Per-camera timeline offsets, detected performance window, and sync confidence |
| `output/generated_edl.json` | The full Editing Decision List used to render the final video |
| `output/final_graduation_video.mp4` | The rendered highlight video |

### Sample EDL entry
```json
{
  "start_time": 37.5,
  "end_time": 42.5,
  "selected_camera": "camera1_center_closeup.mp4",
  "reason_for_selection": "Second-highest energy — forced switch after 3 consecutive segments on this camera",
  "transition": "fade",
  "lower_third": {
    "text": "Camera camera1_center_closeup.mp4",
    "position": "top-left",
    "font_size": 24
  }
}
```

---

## Known Limitations

- **Audio-energy-based selection is a proxy, not a full editorial judgment.** A camera positioned farther from the performance (e.g. a wide/back angle) will consistently score lower on RMS energy even if its footage is visually valuable — the current logic will rarely or never select it. This is a deliberate, explainable limitation, not a bug: it reflects a real trade-off between automation and true multi-signal editorial judgment (visual framing, composition, etc. aren't currently considered).
- **Human review is required** before publishing. The pipeline may pick technically "correct" but editorially suboptimal segments, miss visually important moments captured by a quieter camera, or make imperfect sync/performance-boundary estimates on footage with unusual audio characteristics.
- Synchronization accuracy depends on having a usable audio fingerprint across cameras; very short or low-quality reference clips reduce alignment confidence.

---

## Ethics, Privacy & Compliance Notes

This project was built with the following considerations in mind (see full discussion in the accompanying project report):

- **Children's privacy** — real footage of children should only be used with written parental consent; this repository is intended to be used with a starter/simulated footage pack or properly consented footage.
- **Malaysia PDPA 2010 (Act 709)** — identifiable footage (faces, voices, names) may constitute personal data under the Act.
- **Copyright & licensing** — background music, performance audio, and third-party tool licenses should be checked before any public distribution of rendered output.
- **AI responsibility** — this system is semi-automatic. It should not be described or relied upon as a fully autonomous editorial tool; human review of the EDL and final render is required before use.

---

## Project Structure

```
KinderEditAI/
├── src/
│   ├── sync.py
│   ├── edl_generator.py
│   └── renderer.py
├── starter-pack/          # Source camera footage (not committed)
├── output/                # Generated offsets, EDL, and final video (not committed)
├── requirements.txt
└── README.md
```

---

## License

For academic use as part of BTIS3053 coursework. Add a license here if distributing publicly.
