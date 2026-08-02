# GitHub Copilot Instructions for KinderEditAI

## Project Context
This is an academic project to design a semi-automated multi-camera video editing pipeline in Python[cite: 1].
- Input: 4 camera MP4 video files (~2 mins, 720p, 30fps)[cite: 1].
- Stack: Python 3.10+, MoviePy, Audalign/FFmpeg, OpenCV, JSON[cite: 1].

## Coding Standards & Guidelines
1. **Pipeline Architecture:** Follow a modular approach (`sync.py`, `edl_generator.py`, `renderer.py`)[cite: 1].
2. **EDL Specification:** Any generated Editing Decision List must be structured as JSON containing `start_time`, `end_time`, `selected_camera`, `reason_for_selection`, and `transition` keys[cite: 1].
3. **Video Requirements:** The rendering pipeline must support overlaying lower-third text/labels, opening title clips, closing credit screens, and simple transitions[cite: 1].
4. **Performance Constraint:** Keep implementations lightweight so scripts can execute on low-spec CPUs without requiring heavy GPU rendering[cite: 1].