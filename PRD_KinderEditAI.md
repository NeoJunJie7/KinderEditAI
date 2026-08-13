# Product Requirements Document (PRD)

# KinderEdit AI
### AI-Assisted Multi-Camera Kindergarten Graduation Video Editing Prototype

**Version:** 1.0 Final  
**Course:** BTIS3053 – Social & Professional Issues  
**Project Duration:** 1 Week  
**Development Environment:** Visual Studio Code + GitHub Copilot  
**Technology Stack:** Python, MoviePy, FFmpeg, Pandas, GitHub  
**Prototype Type:** Human-in-the-Loop AI-Assisted Video Editing System

---

# 1. Project Overview

KinderEdit AI is a lightweight video editing prototype designed to assist kindergarten teachers in producing graduation highlight videos from multiple camera recordings.

The system uses predefined event metadata and rule-based decision logic to recommend camera selections, generate an Editing Decision List (EDL), and render a final highlight video. Rather than fully automating the editing process, all editing recommendations must be reviewed and approved by a human before video production. This ensures transparency, accountability, and responsible AI usage. 【1-86c561】

---

# 2. Problem Statement

Kindergarten graduation ceremonies are commonly recorded using multiple cameras positioned around the venue.

Teachers often spend significant time:

- Reviewing recordings
- Synchronizing footage
- Choosing camera angles
- Creating transitions
- Producing final videos

This manual workflow is time-consuming and may lead to inconsistent editing decisions. Furthermore, children's recordings require careful handling to protect privacy and comply with legal and ethical responsibilities. 【1-86c561】

---

# 3. Project Goal

Develop a one-week prototype that demonstrates a responsible AI-assisted editing workflow capable of:

- Combining recordings from multiple cameras
- Generating camera-selection recommendations
- Producing an Editing Decision List (EDL)
- Supporting human review
- Creating a 60–180 second graduation highlight video

---

# 4. Project Objectives

### O1 – Video Synchronization

Support synchronization of two camera recordings using manually defined timing offsets.

### O2 – Camera Recommendation

Generate camera recommendations using event metadata and predefined rules.

### O3 – EDL Generation

Produce a structured Editing Decision List (EDL) in JSON format.

### O4 – Video Rendering

Render an MP4 graduation highlight video using the approved EDL.

### O5 – Human Review

Require human approval before final video generation.

### O6 – Ethical Compliance

Demonstrate compliance with privacy, consent, copyright, licensing, and professional responsibility requirements. 【1-86c561】

---

# 5. Project Scope

## In Scope

- Two camera video inputs
- Manual synchronization offsets
- Event metadata input
- Rule-based camera recommendations
- Automatic EDL generation
- Human review workflow
- Opening title
- Subtitle or lower-third
- Basic transition effect
- Closing credits
- MP4 video export

## Out of Scope

- Facial recognition
- Speech recognition
- OpenCV object detection
- Whisper transcription
- Real-time editing
- Cloud AI services
- Social media publishing
- Commercial deployment

---

# 6. System Workflow

```text
camera1.mp4
camera2.mp4
events.json
sync_config.json
        │
        ▼
Camera Recommendation Engine
        │
        ▼
Generated EDL
        │
        ▼
Human Review
        │
        ▼
Render Video
        │
        ▼
graduation_highlight.mp4
```

---

# 7. Functional Requirements

## FR1 – Video Import

The system shall import two MP4 video files.

### Example

```text
camera1.mp4
camera2.mp4
```

---

## FR2 – Synchronization Configuration

The system shall accept manually supplied synchronization offsets.

### Example

```json
{
  "camera1_offset_sec": 0.0,
  "camera2_offset_sec": 1.2
}
```

The prototype will not perform automatic synchronization.

---

## FR3 – Event Metadata Input

The system shall accept an event timeline file.

### Example

```json
[
  {
    "start_sec": 0,
    "end_sec": 15,
    "event_type": "speech"
  },
  {
    "start_sec": 15,
    "end_sec": 45,
    "event_type": "performance"
  }
]
```

---

## FR4 – Camera Recommendation

The system shall recommend camera angles using predefined rules.

### Rules

```python
speech      → camera1
performance → camera2
applause    → camera2
```

### Recommendation Example

```json
{
  "event_type": "speech",
  "recommended_camera": "camera1",
  "reason": "Speaker clearly visible"
}
```

---

## FR5 – EDL Generation

The system shall generate an Editing Decision List (EDL).

### Example

```json
[
  {
    "start_sec": 0,
    "end_sec": 15,
    "source_camera": "camera1",
    "transition": "fade",
    "overlay_text": "Opening Speech"
  },
  {
    "start_sec": 15,
    "end_sec": 45,
    "source_camera": "camera2",
    "transition": "cut",
    "overlay_text": "Graduation Performance"
  }
]
```

---

## FR6 – Human Review

The generated EDL must be reviewed and approved by a human editor before rendering.

Users may:

- Accept recommendations
- Modify recommendations
- Reject recommendations

---

## FR7 – Video Rendering

The system shall:

- Read the approved EDL
- Extract clips from source videos
- Apply transitions
- Add title screen
- Add subtitle or label
- Add closing credits
- Export MP4 video

### Output

```text
graduation_highlight.mp4
```

---

# 8. Non-Functional Requirements

## Performance

The system should support:

```text
Maximum Cameras      : 2
Maximum Resolution   : 720p
Maximum Input Length : 5 minutes
Output Length        : 60–180 seconds
```

Target rendering time:

```text
Less than 5 minutes
```

---

## Reliability

The system should:

- Validate input files
- Validate EDL format
- Handle missing data gracefully

---

## Maintainability

The solution shall:

- Use modular Python scripts
- Include comments and documentation
- Be managed using GitHub

---

## Security

The system shall:

- Process videos locally
- Avoid cloud uploads
- Restrict access to video files

---

# 9. AI Strategy

KinderEdit AI uses **AI-assisted recommendations** rather than fully autonomous editing.

### Workflow

```text
Event Metadata
        ↓
Rule-Based Recommendation
        ↓
EDL Generation
        ↓
Human Review
        ↓
Final Rendering
```

This approach improves transparency, reduces implementation complexity, and aligns with responsible AI principles. 【1-86c561】

---

# 10. Technology Stack

### Development Tools

- Visual Studio Code
- GitHub Copilot

### Programming Language

- Python 3.x

### Video Processing

- MoviePy
- FFmpeg

### Data Processing

- Pandas
- JSON

### Version Control

- GitHub

---

# 11. Repository Structure

```text
KinderEditAI/
│
├── videos/
│
├── config/
│   ├── events.json
│   └── sync_config.json
│
├── edl/
│   ├── generated_edl.json
│   └── approved_edl.json
│
├── source/
│   ├── camera_selector.py
│   ├── generate_edl.py
│   ├── render_video.py
│   └── utils.py
│
├── outputs/
│
├── docs/
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# 12. Ethical, Legal and Professional Considerations

## Children's Privacy

- Process recordings locally
- Restrict access to video files
- Delete files after project completion

## Parental Consent

Consent should cover:

- Recording
- Editing
- Distribution of final video

## Malaysia PDPA 2010

Children's recordings may contain identifiable personal data such as faces, names, voices, and school uniforms. Appropriate safeguards must be applied when storing and processing recordings. 【1-86c561】(https://www.pdp.gov.my/ppdpv1/en/akta/pdp-act-2010-en/)

## Copyright

Use only:

- Original recordings
- Royalty-free music
- Properly licensed assets

## Professional Responsibility

- Human approval is mandatory: Teachers, administrators, or approved school staff must review and approve AI-generated edits before the video is exported, shared, or published.
- AI recommendations must remain transparent: The system should clearly explain which clips, transitions, or timing choices were suggested and why, so users understand the basis for recommendations rather than blindly accepting them.
- Do not claim full automation: Kid-safe or educational video creation must not be presented as fully autonomous. The AI should be positioned as an assistant that accelerates decision-making, not a replacement for professional oversight.
- Keep humans responsible for final decisions: Final choices about inclusion, sequence, wording, privacy, consent, and distribution remain with the educator or designated human reviewer. The AI supports the workflow but does not make final publishing decisions.

---

# 13. GitHub Privacy Policy

To prevent accidental exposure of children's recordings, video files must not be uploaded to GitHub.

### .gitignore

```gitignore
videos/
outputs/
*.mp4
```

This reduces privacy risks and supports responsible data handling.

---

# 14. One-Week Development Plan

### Day 1
Project setup, GitHub repository, dependency installation.

### Day 2
Synchronization configuration and event metadata setup.

### Day 3
Camera recommendation module.

### Day 4
EDL generation module.

### Day 5
Video rendering pipeline.

### Day 6
Testing, screenshots, and documentation.

### Day 7
Final video generation, report completion, and presentation preparation.

---

# 15. Success Criteria

The prototype is considered successful if it:

- Supports 2 camera inputs
- Generates an EDL automatically
- Includes at least 3 camera switches
- Produces a video between 60–180 seconds
- Includes opening title, subtitle, transition, and closing credits
- Requires human review
- Processes videos locally
- Demonstrates privacy and ethical compliance

---

# 16. Conclusion

KinderEdit AI is a practical one-week AI-assisted video editing prototype that demonstrates synchronization, camera recommendation, EDL generation, human review, and automated video rendering. The project balances technical feasibility with ethical responsibility, making it suitable for the BTIS3053 assignment while remaining achievable within the available timeline and resources. 【1-86c561】
