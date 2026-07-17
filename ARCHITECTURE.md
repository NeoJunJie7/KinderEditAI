# System Architecture Document

# KinderEdit AI
### AI-Assisted Multi-Camera Kindergarten Graduation Video Editing Prototype

**Version:** 1.0 Final  
**Architecture Type:** Human-in-the-Loop AI-Assisted Processing Pipeline  
**Technology Stack:** Python, MoviePy, FFmpeg, Pandas, JSON, GitHub  
**Deployment Model:** Local Desktop Application / Local Web Application  
**Target Environment:** Student Laptop (CPU Only)

---

# 1. Architecture Overview

KinderEdit AI follows a lightweight, modular, Human-in-the-Loop architecture designed specifically for a one-week academic prototype.

The system does not perform fully automated AI editing. Instead, it assists users by generating editing recommendations based on predefined event metadata. Human reviewers remain responsible for approving all editing decisions before video rendering.

This architecture prioritizes:

- Simplicity
- Maintainability
- Privacy
- Educational value
- Ethical AI usage
- Low hardware requirements

---

# 2. High-Level Architecture

```text
┌─────────────────┐
│   Camera Video  │
│     Inputs      │
└────────┬────────┘
         │
         ▼

┌─────────────────┐
│ Synchronization │
│ Configuration   │
└────────┬────────┘
         │
         ▼

┌─────────────────┐
│  Event Metadata │
│     Loader      │
└────────┬────────┘
         │
         ▼

┌─────────────────┐
│ AI Recommendation│
│     Engine      │
└────────┬────────┘
         │
         ▼

┌─────────────────┐
│ EDL Generator   │
└────────┬────────┘
         │
         ▼

=================================
        HUMAN REVIEW
=================================

         │
         ▼

┌─────────────────┐
│ Video Renderer  │
└────────┬────────┘
         │
         ▼

┌─────────────────┐
│ Final MP4 Video │
└─────────────────┘
```

---

# 3. Architectural Principles

## Human-in-the-Loop

The system never makes final editing decisions automatically.

All AI-generated recommendations must be reviewed and approved by a human editor before rendering.

---

## Privacy by Design

The system processes all videos locally.

No cloud processing is required.

No external AI services are used.

---

## Modular Components

Each major function is isolated into an independent module.

Benefits:

- Easier maintenance
- Easier testing
- Faster development
- Better scalability

---

## Low Resource Consumption

The system is optimized for:

- CPU-only execution
- Offline usage
- Student laptops
- Small video datasets

---

# 4. Core Components

## Component 1: Video Input Module

### Purpose

Load camera recordings into the system.

### Responsibilities

- Validate video files
- Read metadata
- Verify supported formats

### Input

```text
camera1.mp4
camera2.mp4
```

### Output

```json
{
  "camera":"camera1",
  "duration":120,
  "resolution":"1280x720"
}
```

---

## Component 2: Synchronization Module

### Purpose

Apply predefined timing offsets.

### Responsibilities

- Read synchronization settings
- Align video timelines

### Input

```json
{
  "camera1_offset_sec": 0,
  "camera2_offset_sec": 1.2
}
```

### Output

```json
{
  "timeline_aligned": true
}
```

### Notes

For this prototype, synchronization values are entered manually.

Automatic audio synchronization is intentionally excluded.

---

## Component 3: Event Metadata Module

### Purpose

Load event information used by recommendation logic.

### Responsibilities

- Read event timeline
- Validate metadata structure

### Input

```json
[
  {
    "start_sec":0,
    "end_sec":15,
    "event_type":"speech"
  },
  {
    "start_sec":15,
    "end_sec":45,
    "event_type":"performance"
  }
]
```

### Output

Structured event objects for processing.

---

## Component 4: AI Recommendation Engine

### Purpose

Generate camera-selection recommendations.

### Responsibilities

- Analyze event types
- Apply decision rules
- Produce recommendations

### Rules

```python
speech      -> camera1
performance -> camera2
applause    -> camera2
```

### Output

```json
{
  "recommended_camera":"camera1",
  "reason":"Speaker visible"
}
```

---

## Component 5: EDL Generator

### Purpose

Convert recommendations into an Editing Decision List.

### Responsibilities

- Create timeline segments
- Assign cameras
- Define transitions
- Generate overlay text

### Output Example

```json
[
  {
    "start_sec":0,
    "end_sec":15,
    "source_camera":"camera1",
    "transition":"fade",
    "overlay_text":"Opening Speech"
  }
]
```

---

## Component 6: Human Review Module

### Purpose

Provide human oversight.

### Responsibilities

- Review generated EDL
- Modify recommendations
- Approve final timeline

### Actions

```text
Approve
Modify
Reject
```

### Output

```text
approved_edl.json
```

---

## Component 7: Video Rendering Module

### Purpose

Produce final video output.

### Responsibilities

- Read approved EDL
- Extract clips
- Apply transitions
- Add subtitles
- Add title screen
- Add credit screen

### Tools

- MoviePy
- FFmpeg

### Output

```text
graduation_highlight.mp4
```

---

# 5. Data Flow Architecture

```text
camera1.mp4
camera2.mp4
       │
       ▼

sync_config.json
       │
       ▼

events.json
       │
       ▼

Recommendation Engine
       │
       ▼

generated_edl.json
       │
       ▼

Human Review
       │
       ▼

approved_edl.json
       │
       ▼

Render Engine
       │
       ▼

graduation_highlight.mp4
```

---

# 6. File Structure

```text
KinderEditAI/
│
├── videos/
│   ├── camera1.mp4
│   └── camera2.mp4
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
│   └── graduation_highlight.mp4
│
├── docs/
│   └── architecture.md
│
├── requirements.txt
│
├── README.md
│
└── .gitignore
```

---

# 7. Technology Architecture

## Frontend (Optional Web Interface)

### Framework

```text
React
Next.js
Tailwind CSS
```

Purpose:

- Teacher dashboard
- EDL review
- File upload
- Video preview

---

## Backend

### Framework

```text
Python
FastAPI
```

Purpose:

- Upload handling
- Recommendation processing
- Rendering coordination

---

## Processing Layer

### Libraries

```text
MoviePy
FFmpeg
Pandas
```

Purpose:

- Video processing
- EDL management
- Final rendering

---

## Storage Layer

### Local Storage

```text
JSON Files
MP4 Files
```

Advantages:

- Simple deployment
- No database required
- Privacy friendly

---

# 8. Security Architecture

## Local Processing

All processing occurs locally.

No video data leaves the device.

---

## Repository Protection

The following must never be uploaded:

```gitignore
videos/
outputs/
*.mp4
```

---

## Access*Control

Only project members*may access:

```text**aw recordings

Generated outputs*
EDL files
*`*

---

# 9* Performance Constraints

To ensur* reliable execution:

```text
Maxi*um Cameras       : 2

Maximum Reso*ution    : 720p

Maximum Input Len*th  : 5 minutes

Output Duration  *    : 60-180 seconds

Execution Pl*tform    : CPU Only
```

---

# 10* Future Architecture Enhancements
*Future versions may introduce:

##* AI Features

- Speech detection
-*Automated event*extraction
- Whisper subtitle gene*ation
- Smart highlight detection
*### UX Features

- Drag-and-drop*timeline editor
- Interactive EDL *ditor
- Real*time preview

### Infrastructure*
- SQLite database
-*User authentication
- Cloud*deployment

---

# *1. Architecture Summary

Kinder*dit AI adopts*a simple,*modular, Human-in-the*Loop architecture specifically opt*mized*for a one-week academic prototype.*
The architecture combines:

- Mul*i-camera video input
- Metadata-dr*ven*recommendations
- Automated E*L generation
- Human approval*workflow
- Automated video renderi*g

while maintaining:

- Low*complexity
- Local processing*- Privacy protection
**Ethical AI practices
* PDPA awareness

This*architecture provides a*realistic and*achievable implementation that sat*sfies both*the technical and ethical*objectives of the project.
````*