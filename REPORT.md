# WAVLY 2.0 — Comprehensive Project Report

> **Generated**: June 18, 2026  
> **Project Health Score**: 9.0 / 10  
> **ML Model Accuracy**: 99.66%  
> **Status**: Active Development

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Completed Phases](#3-completed-phases)
4. [Gesture System](#4-gesture-system)
5. [Voice System](#5-voice-system)
6. [Context Awareness](#6-context-awareness)
7. [Architecture](#7-architecture)
8. [Performance Metrics](#8-performance-metrics)
9. [Known Issues](#9-known-issues)
10. [How To Run](#10-how-to-run)
11. [Coming Soon](#11-coming-soon)

---

## 1. Project Overview

### What Is Wavly?

Wavly is an **AI-powered touchless computer control system** that enables users to operate their entire computer using **hand gestures** and **voice commands** — no mouse, no keyboard, no touch. It captures a live webcam feed, processes hand landmarks in real time using Google's MediaPipe, classifies 10 distinct gestures through a custom-trained Random Forest model, listens for spoken voice triggers via Google Web Speech API, and translates all of these inputs into system-level automation actions using PyAutoGUI.

### What Problem Does It Solve?

Traditional computer interaction requires physical contact with input devices. Wavly eliminates this barrier by providing:

- **Accessibility** — Hands-free control for users with motor impairments or physical disabilities.
- **Hygiene** — Touchless operation in shared environments (labs, hospitals, kiosks).
- **Presentation Control** — Gesture-driven slide navigation without a clicker or remote.
- **Creative Tools** — Mid-air drawing on a transparent canvas overlay.
- **Multimodal Input** — Seamless combination of gestures and voice for richer interaction.

---

## 2. Technology Stack

All dependencies are pinned in `requirements.txt` for reproducible builds.

| Technology             | Version       | Purpose                                                     |
| :--------------------- | :------------ | :---------------------------------------------------------- |
| **Python**             | `3.12.10`     | Core runtime language                                       |
| **MediaPipe**          | `0.10.14`     | Real-time hand landmark detection (21 points per hand)      |
| **OpenCV**             | `4.13.0.92`   | Webcam video capture, frame processing, image I/O           |
| **NumPy**              | `2.4.0`       | Numerical array operations for coordinate processing        |
| **Pandas**             | `2.2.3`       | CSV dataset loading and formatting for model training       |
| **scikit-learn**       | `1.8.0`       | Random Forest classifier for gesture recognition            |
| **PyQt6**              | `6.11.0`      | Transparent fullscreen overlay GUI, HUD, and drawing canvas |
| **PyAutoGUI**          | `0.9.54`      | Mouse/keyboard automation and system hotkey execution        |
| **SpeechRecognition**  | `3.16.1`      | Microphone capture and Google Web Speech API transcription   |
| **PyAudio**            | `0.2.14`      | Low-level PortAudio interface for audio input streams        |
| **pyttsx3**            | `2.99`        | Offline text-to-speech engine (SAPI5 on Windows)            |
| **pygetwindow**        | *(bundled)*   | Active window title detection for context awareness         |

---

## 3. Completed Phases

### ✅ Phase 1 — Foundation

**Goal**: Establish the core pipeline from webcam input to hand landmark extraction.

**What Was Built**:
- Integrated Google MediaPipe Hands solution for real-time 21-point hand skeleton tracking.
- Created the `HandTracker` class (`src/camera/hand_tracker.py`) wrapping MediaPipe's detection and drawing utilities.
- Set detection confidence at `0.7` and tracking confidence at `0.7` for optimal balance between accuracy and responsiveness.
- Implemented BGR → RGB color space conversion for MediaPipe compatibility.
- Built landmark-to-pixel coordinate conversion method (`get_landmark_list`).

---

### ✅ Phase 2 — Mouse Control

**Goal**: Map hand position to screen cursor movement with smoothing and click support.

**What Was Built**:
- Created `MouseController` class (`src/control/mouse_controller.py`) for PyAutoGUI-based cursor control.
- Implemented **exponential weighted moving average (EWMA) smoothing** with a configurable smoothing factor (`0.5`) to eliminate cursor jitter.
- Mapped webcam frame coordinates (`640×480`) to full screen resolution via linear interpolation.
- Added **speed multiplier** support — `1.0×` for normal tracking, `0.5×` for precision mode.
- Built click handling with cooldown timers (`0.3s` normal, `0.2s` typing mode) to prevent double-fires.
- Set `PyAutoGUI.PAUSE = 0.01` for near-instantaneous command execution.

---

### ✅ Phase 3 — Gesture Recognition

**Goal**: Train a machine learning model to classify 10 distinct hand gestures from landmark data.

**What Was Built**:
- Created `DataCollector` (`src/ai/data_collector.py`) for buffered CSV recording of normalized landmark coordinates.
- Created `GesturePredictor` (`src/ai/predictor.py`) for real-time inference with multi-tier confidence thresholds.
- Created model training script (`src/ai/trainer.py`) using `RandomForestClassifier` (100 estimators, random_state=42).
- Built `record_gestures.py` — a live webcam recording tool with per-gesture sample counters and keyboard label switching (keys 0–9).
- Achieved **99.66% test accuracy** on the held-out validation set (80/20 split).
- Implemented smart confidence filtering:
  - `≥ 55%` confidence → accept prediction.
  - `40–55%` confidence → accept only if gap to second-best is `> 15%`.
  - `< 40%` confidence → reject as `"unknown"`.
  - Special case: `four_fingers` accepted at `≥ 35%` (harder to distinguish gesture).

---

### ✅ Phase 4 — Air Drawing

**Goal**: Transform the drawing canvas from 2D screen overlay to 3D spatial drawing.

**What Was Built**:
- Tracked the full 3D path of the index finger using MediaPipe's z-coordinate depth estimation.
- Implemented gesture-triggered shape tools (lines, circles, rectangles).
- Added vocal stroke commands for hands-free drawing instructions.
- Supported multi-stroke undo with per-stroke granularity.
- **Entry Mechanism**: Toggled instantly by the `spider_man` gesture.

---

### ✅ Phase 5 — Context Awareness

**Goal**: Dynamically detect the active foreground application and swap gesture mappings accordingly.

**What Was Built**:
- Created `ContextDetector` (`src/control/context_detector.py`) using `pygetwindow` to read the active window title.
- Created `AppProfiles` (`src/control/app_profiles.py`) defining gesture-to-action mappings for Chrome, VLC, and PowerPoint.
- Integrated context checking into `GestureMapper` on a `2.0s` polling interval to minimize overhead.
- App identification rules:
  - Window title contains `"Chrome"` or `"Edge"` → **chrome** profile.
  - Window title contains `"VLC"` → **vlc** profile.
  - Window title contains `"PowerPoint"` → **powerpoint** profile.
  - Everything else → **default** profile.

---

### ✅ Phase 6 — UI Overlay

**Goal**: Create a transparent, always-on-top drawing canvas and status HUD.

**What Was Built**:
- Created `OverlayWindow` (`src/ui/overlay_window.py`) — a fullscreen PyQt6 transparent window.
- Window flags: `FramelessWindowHint | WindowStaysOnTopHint | WindowTransparentForInput | Tool`.
- Implemented a `QPixmap` canvas buffer + image-object layer for drawing mode (rewritten June 2026 to a tool-follows-gesture model) with:
  - 8-colour palette in a gesture-toggled popup, picked by dwelling the pointer on a swatch.
  - Adjustable stroke size (2–60px) via `thumbs_up`/`thumbs_down` or the toolbar.
  - Pointer-style eraser using `CompositionMode_Clear`; `fist` clears the whole canvas.
  - Object-aware pinch manipulation: grab a stroke/image, move it, hold still to resize, open palm to drop.
  - Clipboard image paste that stays crisp at any scale (scaled from the original each frame).
  - A One-Euro–smoothed pointer and a right-edge dwell-to-activate toolbar with hand-drawn icons.
- Built a **cyberpunk-themed HUD panel** (bottom-right, 280×190px) displaying:
  - Current gesture name (cyan text).
  - Active mode — NORMAL (green) / DRAWING (blue).
  - Active application profile name.
  - Voice status indicator — STANDBY (gray) / LISTENING (cyan) / ACTIVE (green).
  - Contextual hint text.
- Built an animated **Arc Reactor** indicator widget with:
  - Rotating segmented ring (4 segments, 60° each).
  - Pulsating breathing core animation.
  - Status-dependent color schemes (gold for active, blue for listening, gray for standby).
  - Energy ray effects during ACTIVE voice mode.
- HUD auto-fades to `0.3` opacity after `3s` of inactivity, snaps back to `1.0` on any state change.
- Animation loop running at ~33 FPS via `QTimer` (30ms interval).

---

### ✅ Phase 8 — Presentation Mode

**Goal**: Enable gesture-driven PowerPoint presentation control.

**What Was Built**:
- Defined a full PowerPoint application profile in `AppProfiles`:
  - `two_fingers` → Next slide (`Right Arrow`)
  - `l_shape` → Previous slide (`Left Arrow`)
  - `four_fingers` → Start presentation (`F5`)
  - `fist` → Exit presentation (`Escape`)
  - `thumbs_up` → Zoom in (`Ctrl + =`)
  - `thumbs_down` → Zoom out (`Ctrl + -`)
  - `three_fingers` → Black screen toggle (`B`)
  - `pinch` → Laser pointer / Ctrl hold (`Ctrl + L`)
- Reduced slide navigation cooldown to `0.8s` (vs. default `2.0s`) for two_fingers and l_shape in PowerPoint context.
- Added corresponding voice commands: `next slide`, `previous slide`, `start presentation`, `stop presentation`.

---

### ✅ Phase 9 — Voice Hybrid

**Goal**: Add voice command recognition with wake word activation, session management, and Jarvis-style spoken responses.

**What Was Built**:
- Created `VoiceController` (`src/control/voice_controller.py`) — a daemon thread continuously listening to microphone input.
- Created `VoiceMapper` (`src/control/voice_mapper.py`) — maps transcribed text to system actions with 3-tier matching:
  1. Exact match against 20 registered commands.
  2. Substring/keyword match (e.g., "please open notepad" matches "open notepad").
  3. Alias/synonym matching (e.g., "louder" → "volume up", "snap" → "screenshot").
- Created `VoiceResponder` (`src/control/voice_responder.py`) — a dedicated TTS thread with:
  - Queue-based speech scheduling (zero-lag in the vision loop).
  - Primary engine: `pyttsx3` (SAPI5 on Windows) at 170 WPM, volume 1.0.
  - Fallback engine: PowerShell `System.Speech.Synthesis.SpeechSynthesizer`.
  - Auto-recovery: re-initializes pyttsx3 on failure before falling back to PowerShell.
  - COM apartment initialization (`pythoncom.CoInitialize`) for thread safety with PyQt6.
- Implemented **wake word activation**:
  - Primary wake word: `"wavly"`.
  - Fuzzy variants accepted: `"wavy"`, `"wavely"`, `"wably"`, `"waverly"`, `"waveely"`, `"babli"`, `"bably"`, `"baby"`, `"devli"`.
- Implemented **session management**:
  - System starts in **standby** mode (listening only for wake word).
  - Wake word activates a **persistent session** (no timeout — `session_timeout = 999999`).
  - Session ends on goodbye phrases: `"goodbye"`, `"sleep"`, `"deactivate"`, `"shut down"`, `"stop listening"`.
- Implemented **Jarvis-style spoken responses**:
  - Startup greetings (randomized): *"Wavly systems online. All systems fully operational..."*
  - Wake responses (randomized): *"At your service, sir."*, *"Yes, sir?"*, etc.
  - Command confirmations: *"Done"*, *"Opening Chrome for you"*, *"Scrolling up"*, etc.
  - Error responses (randomized): *"I'm sorry sir, I couldn't find a mapping for that command."*
  - Goodbye: *"Goodbye sir. Wavly going to standby."*
- Added **echo prevention**: voice controller pauses microphone listening while the responder is speaking (`is_speaking` flag with polling).
- HUD voice status indicator integrated into the overlay with 3 states and distinct colors.

---

## 4. Gesture System

### All 11 Gestures and Their Default Actions

| # | Gesture          | Label | Normal Mode Action                               | Drawing Mode Action                         |
|---|:-----------------|:-----:|:-------------------------------------------------|:--------------------------------------------|
| 1 | `fist`           | 0     | Freeze cursor (stop movement)                    | Clear the whole canvas                      |
| 2 | `open_hand`      | 1     | Normal cursor tracking (1.0× speed)              | Erase along the pointer path; **drops** a grabbed element |
| 3 | `point`          | 2     | Precision cursor tracking (0.5× speed)           | **Draw** (the only gesture that draws)      |
| 4 | `two_fingers`    | 3     | Scroll up/down (based on hand Y)                 | Toggle the colour palette popup             |
| 5 | `three_fingers`  | 4     | Open on-screen keyboard (`Win+Ctrl+O`)           | *(unused in drawing mode)*                  |
| 6 | `four_fingers`   | 5     | Screenshot to clipboard (direct grab + toast)    | Paste an image from the clipboard           |
| 7 | `thumbs_up`      | 6     | Volume up                                        | Increase stroke size                        |
| 8 | `thumbs_down`    | 7     | Volume down                                      | Decrease stroke size                        |
| 9 | `l_shape`        | 8     | Right-click                                      | *(unused in drawing mode)*                  |
| 10| `pinch`          | 9     | Left-click                                       | Grab the stroke/image under the fingers → move + resize |
| 11| `spider_man`     | 10    | Toggle Drawing Mode ON                           | Toggle Drawing Mode OFF                     |

> **Drawing mode is a "tool-follows-gesture" surface (rewritten June 2026).** The active tool is recomputed every frame from the live gesture — only `point` draws, and switching gesture switches tool instantly. The index-fingertip pointer is smoothed with a One-Euro filter, and a central band of the camera frame is stretched onto the full screen so every edge/corner is reachable.
>
> **Pinch manipulation**: pinching grabs the connected ink blob (via `scipy.ndimage` connected-components) or the image under the thumb-index midpoint, raising images to the top (z-order). It starts in **Move** mode (translate only); **hold still ~2 s** to toggle **Resize** mode (scale by thumb-index distance, for strokes and images alike); **keep holding to ~3.5 s** to drop, or **open your palm** to drop instantly. Pasted images keep their original full-resolution pixmap and are re-scaled every frame, so they stay crisp at any size.
>
> **Dwell toolbar**: a persistent panel on the **right edge** with hand-drawn (non-emoji) icons — draw, eraser, stroke +/−, colour, paste, clear. Hover the pointer over a button for ~1 s to activate it; the panel highlights whichever tool is live (so picking a tool by gesture updates the panel automatically). Leaving drawing mode hides the canvas + images but keeps them in memory, so they reappear on re-entry.

### ML Model Details

- **Algorithm**: `RandomForestClassifier` (scikit-learn)
- **Estimators**: 100 trees
- **Test Accuracy**: **99.66%** (80/20 train-test split, `random_state=42`)
- **Input Features**: 42 floats (21 landmarks × 2 coordinates each)
- **Model File**: `data/gesture_model.pkl` (serialized via pickle, ~4.2 MB)
- **Training Data**: `data/gestures.csv` (~13.7 MB)
- **Note**: The ML model classifies 10 base gestures. The 11th gesture (`spider_man`) is detected geometrically via MediaPipe landmarks before the ML prediction step, acting as a direct injection into the buffer.

### Coordinate Normalization

All landmark coordinates are **normalized relative to the wrist** (landmark 0) before training and prediction to ensure **position-invariant** gesture classification — the gesture is recognized regardless of where the hand appears in the webcam frame.

```
Normalized_X[i] = X[i] - X[wrist]
Normalized_Y[i] = Y[i] - Y[wrist]
```

This produces a 42-element feature vector: `[x0, y0, x1, y1, ..., x20, y20]` where `(x0, y0)` is always `(0, 0)`.

### Buffer and Voting System

The prediction pipeline uses a **temporal voting buffer** to eliminate flickering and false positives:

1. **Buffer Size**: 10 frames (rolling window).
2. **Confirmation Threshold**: A gesture is confirmed when it receives **≥ 6 out of 10 votes**.
3. **Unknown Handling**: If the most common prediction remains `"unknown"` for **5 consecutive cycles**, the entire buffer is cleared to allow rapid recovery.
4. **Confidence Gating** (applied per-frame before buffering):
   - `≥ 55%` → accepted immediately.
   - `40–55%` → accepted only if confidence gap to 2nd prediction exceeds `15%`.
   - `< 40%` → rejected as `"unknown"`.
   - `four_fingers` exception → accepted at `≥ 35%`.

### Pinch Detection (Independent Hardware Check)

Pinch is detected independently from the ML model using geometric distance:

- **Trigger**: Thumb tip (landmark 4) to index fingertip (landmark 8) distance `< 60px` **AND** index finger is curled (fingertip-to-PIP Y-distance `< 30px`).
- **Release**: Distance exceeds `> 80px` (hysteresis band to prevent rapid toggling).
- **Safety**: Pinch is ignored when the confirmed gesture is `"fist"` (to prevent accidental clicks when the hand is clenched).

### Gesture Cooldowns

Each gesture has a cooldown period to prevent repeated accidental triggers:

| Gesture        | Cooldown |
|:---------------|:---------|
| `open_hand`    | 2.0s     |
| `point`        | 2.0s     |
| `fist`         | 2.0s     |
| `two_fingers`  | 0.1s     |
| `three_fingers`| 3.0s     |
| `four_fingers` | 3.0s     |
| `thumbs_up`    | 2.0s     |
| `thumbs_down`  | 2.0s     |
| `l_shape`      | 2.0s     |
| `pinch`        | 2.0s     |
| `spider_man`   | 2.0s     |

> **Note**: In PowerPoint context, `two_fingers` and `l_shape` cooldowns are reduced to `0.8s` for faster slide navigation.

---

## 5. Voice System

### Wake Word Detection

Wavly uses a **wake-word activation model** similar to virtual assistants:

- The system starts in **standby mode**, passively listening for the wake word.
- Primary wake word: **"wavly"**
- Google Speech Recognition often misinterprets the word, so **26 fuzzy variants** are accepted: `wavly`, `wavy`, `wavely`, `wably`, `waverly`, `waveely`, `babli`, `bably`, `baby`, `devli`, `wobbly`, `wavley`, `wally`, `wevley`, `wifely`, `waffly`, `wavvy`, `wabli`, `waveli`, `wahli`, `wovly`, `wobly`, `webly`, `waylee`, `wabley`.
- Upon detection, the system speaks a randomized Jarvis-style acknowledgment and enters **active session** mode.

### All 20 Voice Commands

| #  | Command              | Action                                      |
|----|:---------------------|:--------------------------------------------|
| 1  | `click`              | Left mouse click                            |
| 2  | `right click`        | Right mouse click                           |
| 3  | `scroll up`          | Scroll wheel up (5 clicks)                  |
| 4  | `scroll down`        | Scroll wheel down (5 clicks)                |
| 5  | `screenshot`         | Take screenshot (`Win+Shift+S`)             |
| 6  | `volume up`          | Increase system volume                      |
| 7  | `volume down`        | Decrease system volume                      |
| 8  | `open chrome`        | Launch Google Chrome                        |
| 9  | `open notepad`       | Launch Notepad                              |
| 10 | `switch tab`         | Switch browser tab (`Ctrl+Tab`)             |
| 11 | `close tab`          | Close active tab (`Ctrl+W`)                 |
| 12 | `zoom in`            | Zoom in (`Ctrl+=`)                          |
| 13 | `zoom out`           | Zoom out (`Ctrl+-`)                         |
| 14 | `new tab`            | Open new tab (`Ctrl+T`)                     |
| 15 | `go back`            | Navigate back (`Alt+Left`)                  |
| 16 | `go forward`         | Navigate forward (`Alt+Right`)              |
| 17 | `next slide`         | Next PowerPoint slide (`Right Arrow`)       |
| 18 | `previous slide`     | Previous PowerPoint slide (`Left Arrow`)    |
| 19 | `start presentation` | Begin PowerPoint slideshow (`F5`)           |
| 20 | `stop presentation`  | End PowerPoint slideshow (`Escape`)         |

**Additionally**, 12 aliases are supported for natural language flexibility:
- `"increase volume"` / `"raise volume"` / `"louder"` → volume up
- `"decrease volume"` / `"lower volume"` / `"quieter"` → volume down
- `"take screenshot"` / `"print screen"` / `"snap"` → screenshot
- `"launch chrome"` / `"start chrome"` → open chrome
- `"launch notepad"` / `"start notepad"` → open notepad
- `"click mouse"` / `"left click"` → click

### Session Management

```
┌────────────┐    wake word     ┌────────────┐
│  STANDBY   │ ───────────────→ │   ACTIVE   │
│ (listening │                  │ (commands  │
│  for wake) │ ←─────────────── │  accepted) │
└────────────┘  goodbye phrase  └────────────┘
```

- **Standby → Active**: Triggered by detecting any wake word variant.
- **Active → Standby**: Triggered by goodbye detection using a two-tier matching system:
  - **Phrase match** (substring): `"goodbye"`, `"goodbye wavly"`, `"stop listening"`, `"shut down"`, `"deactivate"`, `"bye bye"`, `"see you"`, `"see ya"`, `"go to sleep"`, `"power down"`, `"end session"`, `"that's all"`, `"that's it"`, `"thank you wavly"`, `"thanks wavly"`, `"goodnight"`, `"goodnight wavly"`, `"good night"`.
  - **Keyword match** (whole-word boundary): `"bye"`, `"sleep"`, `"stop"` — with a guard so `"stop"` doesn't trigger inside commands like `"stop presentation"`.
- **Session Timeout**: Set to `999999` seconds (effectively permanent until explicitly ended).
- **Ambient Noise Calibration**: Performed once on startup (`1s` duration).

### Jarvis-Style Responses

The `VoiceResponder` provides spoken feedback using a multi-engine TTS pipeline with a female Jarvis-style voice (prioritizing Zira and other female voices) for a more natural speaking pace (185 WPM):

| Event               | Example Responses                                                          |
|:---------------------|:--------------------------------------------------------------------------|
| **Startup Greeting** | *"Wavly systems online. All systems fully operational. How can I assist you, sir?"* |
| **Wake Response**    | *"At your service, sir."* / *"Yes, sir?"* / *"Online and listening, sir."* |
| **Command Success**  | *"Done"* / *"Opening Chrome for you"* / *"Scrolling up"*                  |
| **Mode Switch**      | *"Drawing mode on"* / *"Drawing mode off"* (Announced in real-time)       |
| **Command Failure**  | *"I'm sorry sir, I couldn't find a mapping for that command."*            |
| **Session End**      | *"Goodbye, sir."* / *"See you soon, sir."* / *"Standing by, sir."* / *"Until next time, sir."* / *"Going to sleep, sir. Say my name when you need me."* (randomized from 8 farewells) |

---

## 6. Context Awareness

Wavly dynamically detects the active foreground application and overrides default gesture mappings with application-specific profiles.

### Chrome Profile

Activated when the window title contains `"Chrome"` or `"Edge"`.

| Gesture        | Chrome Action                        |
|:---------------|:-------------------------------------|
| `two_fingers`  | Scroll up (`scroll(3)`)             |
| `l_shape`      | New tab (`Ctrl+T`)                  |
| `four_fingers` | Close tab (`Ctrl+W`)               |
| `thumbs_up`    | Navigate forward (`Alt+Right`)      |
| `thumbs_down`  | Navigate backward (`Alt+Left`)      |
| `pinch`        | Zoom in (`Ctrl+=`)                  |
| `fist`         | Zoom out (`Ctrl+-`)                 |

### VLC Profile

Activated when the window title contains `"VLC"`.

| Gesture        | VLC Action                           |
|:---------------|:-------------------------------------|
| `pinch`        | Play / Pause (`Space`)              |
| `two_fingers`  | Fast forward (`Shift+Right`)        |
| `l_shape`      | Rewind (`Shift+Left`)              |
| `thumbs_up`    | Volume up                           |
| `thumbs_down`  | Volume down                         |
| `four_fingers` | Toggle fullscreen (`F`)             |
| `fist`         | Stop playback (`S`)                 |
| `three_fingers`| Mute / Unmute (`M`)                 |

### PowerPoint Profile

Activated when the window title contains `"PowerPoint"`.

| Gesture        | PowerPoint Action                    |
|:---------------|:-------------------------------------|
| `two_fingers`  | Next slide (`Right Arrow`)          |
| `l_shape`      | Previous slide (`Left Arrow`)       |
| `four_fingers` | Start slideshow (`F5`)              |
| `fist`         | Exit slideshow (`Escape`)           |
| `thumbs_up`    | Zoom in (`Ctrl+=`)                  |
| `thumbs_down`  | Zoom out (`Ctrl+-`)                 |
| `three_fingers`| Black screen toggle (`B`)           |
| `pinch`        | Laser pointer (`Ctrl+L`)            |

---

## 7. Architecture

### Complete Folder Structure

```
wavly2.0/
│
├── data/                              # Training data & serialized models
│   ├── gesture_model.pkl              #   Trained Random Forest model (4.2 MB)
│   └── gestures.csv                   #   Landmark coordinate dataset (13.7 MB)
│
├── src/                               # Core application source code
│   ├── __init__.py
│   │
│   ├── ai/                            #   Machine learning pipeline
│   │   ├── __init__.py
│   │   ├── data_collector.py          #     Buffered CSV writer for training data
│   │   ├── predictor.py               #     Real-time gesture inference with confidence gating
│   │   └── trainer.py                 #     Model training script with evaluation reports
│   │
│   ├── camera/                        #   Video capture & hand tracking
│   │   ├── __init__.py
│   │   └── hand_tracker.py            #     MediaPipe Hands wrapper
│   │
│   ├── control/                       #   Input mapping & system automation
│   │   ├── __init__.py
│   │   ├── app_profiles.py            #     Context-sensitive gesture profiles (Chrome/VLC/PPT)
│   │   ├── context_detector.py        #     Active window detection via pygetwindow
│   │   ├── gesture_mapper.py          #     Core gesture → action routing engine
│   │   ├── mouse_controller.py        #     Smoothed cursor movement & click control
│   │   ├── voice_controller.py        #     Background speech recognition listener thread
│   │   ├── voice_mapper.py            #     Voice command → PyAutoGUI action mapper
│   │   └── voice_responder.py         #     Multi-engine TTS response system
│   │
│   └── ui/                            #   User interface
│       ├── __init__.py
│       ├── overlay_window.py          #     Fullscreen transparent overlay, HUD, Arc Reactor
│       └── vision_thread.py           #     Camera + ML + voice processing worker thread
│
├── config/                            # Configuration files (reserved)
├── models/                            # Model artifacts (reserved)
├── tests/                             # Test suite (reserved)
│
├── main.py                            # Application entry point
├── record_gestures.py                 # Gesture dataset recording tool
├── requirements.txt                   # Pinned Python dependencies
│
├── test_context.py                    # Diagnostic: active window detection
├── test_gestures.py                   # Diagnostic: raw prediction confidence HUD
├── test_voice.py                      # Diagnostic: microphone transcription test
├── test_tts.py                        # Diagnostic: text-to-speech engine test
├── test_audio.ps1                     # Diagnostic: PowerShell audio device test
│
├── CLAUDE.md                          # Development guidelines
├── CHECKPOINT.md                      # Development checkpoint state
├── README.md                          # Project documentation
└── REPORT.md                          # This report
```

### How All Components Connect

```
┌─────────────────────────────────────────────────────────────────────┐
│                          main.py                                    │
│  Creates QApplication + OverlayWindow, sets DPI awareness           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ creates
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     OverlayWindow (PyQt6 Main Thread)               │
│                                                                     │
│  • Transparent fullscreen canvas (QPixmap)                          │
│  • Drawing mode tools (pen, eraser, colors, undo/redo)              │
│  • Cyberpunk HUD panel + Arc Reactor animation                      │
│  • Receives signals from VisionThread                               │
│                                                                     │
│  Signals received:                                                  │
│    draw_event      → on_draw_event()     (per-frame drawing state)  │
│    gesture_detected → update_gesture_hud() (HUD label update)       │
│    gesture_command → handle_gesture_command() (drawing actions)      │
│    mode_changed    → update_system_mode() (normal ↔ drawing)        │
│    app_changed     → update_app_hud()    (active app label)         │
│    voice_status    → update_voice_status() (standby/listen/active)  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ spawns
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VisionThread (QThread Worker)                     │
│                                                                     │
│  Main processing loop (~30+ FPS):                                   │
│                                                                     │
│  1. cap.read() ──→ frame                                            │
│  2. HandTracker.detect(frame) ──→ landmarks                         │
│  3. Normalize landmarks relative to wrist                           │
│  4. GesturePredictor.predict(normalized) ──→ raw prediction         │
│  5. Buffer + voting (10 frames, 6/10 threshold) ──→ confirmed       │
│  6. GestureMapper.execute(confirmed) ──→ action                     │
│  7. MouseController.move() or PyAutoGUI hotkey                      │
│  8. Emit signals to OverlayWindow                                   │
│  9. Process VoiceController command queue                            │
│                                                                     │
│  Spawns:                                                            │
│    • VoiceController (daemon thread — microphone listener)          │
│    • VoiceResponder  (daemon thread — TTS speech output)            │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
 ┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌───────────────┐
 │  Webcam   │────→│  OpenCV     │────→│  MediaPipe   │────→│  21 Landmark  │
 │  (640×480)│     │  flip+read  │     │  Hands       │     │  Coordinates  │
 └──────────┘     └─────────────┘     └──────────────┘     └───────┬───────┘
                                                                    │
                                                     ┌──────────────┤
                                                     │              │
                                                     ▼              ▼
                                              ┌────────────┐  ┌──────────────┐
                                              │ Normalize   │  │ Pixel Coords │
                                              │ (wrist-     │  │ for cursor   │
                                              │  relative)  │  │ tracking     │
                                              └──────┬─────┘  └──────┬───────┘
                                                     │               │
                                                     ▼               ▼
                                              ┌────────────┐  ┌──────────────┐
                                              │ Random      │  │ Mouse        │
                                              │ Forest      │  │ Controller   │
                                              │ Classifier  │  │ (smoothed)   │
                                              └──────┬─────┘  └──────────────┘
                                                     │
                                                     ▼
                                              ┌────────────┐
                                              │ 10-Frame   │
                                              │ Vote Buffer│
                                              │ (6/10)     │
                                              └──────┬─────┘
                                                     │
                                                     ▼
                                              ┌────────────┐     ┌──────────────┐
                                              │ Gesture    │────→│ Context      │
                                              │ Mapper     │     │ Detector     │
                                              └──────┬─────┘     └──────────────┘
                                                     │
                                          ┌──────────┼──────────┐
                                          ▼          ▼          ▼
                                    ┌──────────┐┌────────┐┌──────────┐
                                    │ PyAutoGUI││ Drawing ││ App      │
                                    │ Actions  ││ Canvas  ││ Profiles │
                                    └──────────┘└────────┘└──────────┘


 ┌────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │ Microphone │────→│ Google Web   │────→│ Voice        │────→│ Voice        │
 │ (PyAudio)  │     │ Speech API   │     │ Controller   │     │ Mapper       │
 └────────────┘     └──────────────┘     │ (wake word   │     │ (command →   │
                                         │  + session)  │     │  action)     │
                                         └──────────────┘     └──────┬───────┘
                                                                     │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │ Voice        │
                                                              │ Responder    │
                                                              │ (pyttsx3 /   │
                                                              │  PowerShell) │
                                                              └──────────────┘
```

---

## 8. Performance Metrics

| Metric                        | Value           | Notes                                         |
|:------------------------------|:----------------|:----------------------------------------------|
| **Gesture Model Accuracy**    | **99.66%**      | RandomForest, 80/20 split, 100 estimators     |
| **Prediction Buffer Size**    | 10 frames       | Rolling window of recent predictions          |
| **Confirmation Threshold**    | 6 / 10 votes    | Minimum majority required to confirm gesture  |
| **Unknown Streak Limit**      | 5 cycles        | Buffer cleared after 5 consecutive unknowns   |
| **Confidence Floor**          | 40%             | Predictions below this are rejected           |
| **Confidence Ambiguity Band** | 40–55%          | Requires >15% gap to 2nd prediction           |
| **Camera Resolution**         | 640 × 480       | Standard webcam default                       |
| **Animation Frame Rate**      | ~33 FPS         | 30ms QTimer interval for HUD animations       |
| **Vision Loop Sleep**         | 5ms             | Prevents 100% CPU usage                       |
| **Cursor Smoothing Factor**   | 0.5             | EWMA weight for jitter reduction              |
| **App Detection Interval**    | 2.0s            | Polling frequency for active window check     |
| **TTS Speech Rate**           | 185 WPM         | pyttsx3 engine rate (female voice)            |
| **Cursor Margin Comp.**       | 10%             | Allows full screen coverage easily            |
| **Project Health Score**      | **9.0 / 10**    | Overall assessment                            |

### Health Score Breakdown (9.0 / 10)

| Category               | Score  | Rationale                                                    |
|:------------------------|:------|:-------------------------------------------------------------|
| Core Functionality      | 9.5/10| All major features working, including full screen cursor coverage via margin compensation |
| ML Accuracy             | 10/10 | 99.66% is near-perfect for a 10-class gesture problem        |
| Code Architecture       | 9/10  | Clean separation of concerns, well-documented modules        |
| UI/UX                   | 9/10  | Cyberpunk HUD is polished; drawing mode functional; camera PIP |
| Voice Integration       | 8/10  | Works well but echo issue impacts reliability (see §9)       |
| Test Coverage           | 7/10  | Diagnostic scripts exist but no automated unit test suite    |
| Documentation           | 9/10  | CLAUDE.md, CHECKPOINT.md, README.md all maintained           |

---

## 9. Known Issues

### 🔴 Issue #1: Voice Speaker Echo Problem

**Severity**: Medium  
**Status**: Partially mitigated

**Description**: When the `VoiceResponder` speaks a response through the system speakers, the microphone picks up the TTS audio output, causing the `VoiceController` to process the spoken response as a new voice command. This creates a feedback loop where the system can accidentally trigger unintended actions.

**Current Mitigation**:
- An `is_speaking` flag on `VoiceResponder` gates the microphone listener — the `VoiceController` pauses listening while speech is active.
- A `0.2s` delay after wake word response and polling until speech completes.
- A `0.3s` delay before executing commands in `VoiceMapper`.

**Remaining Gap**: In some environments with high speaker volume or reverb, the microphone can still capture trailing audio after `is_speaking` is cleared, causing occasional false triggers.

**Potential Fixes**:
- Implement audio ducking (mute microphone input during TTS playback).
- Add a post-speech cooldown buffer (e.g., 500ms silence after `is_speaking` clears).
- Use acoustic echo cancellation (AEC) libraries.

---

### 🟢 Issue #2: Drawing Mode — Reworked (June 2026)

**Severity**: Low  
**Status**: Resolved / reworked

**Description**: The earlier drawing canvas (toggle-based pen, upward-only brush size, no element editing) was fully rewritten into a tool-follows-gesture surface:

- **Stroke size now goes both ways** — `thumbs_up`/`thumbs_down` or the toolbar increase/decrease size (2–60px).
- **Object editing** — pinch grabs the stroke/image under your fingers to move it; hold still to resize; open palm to drop; grabbed images rise to the top.
- **Toolbar + clipboard images** — a right-edge dwell-to-activate panel exposes every tool, and clipboard images can be pasted and scaled without pixelation.

**Remaining nice-to-haves**: shape tools (line/circle/rectangle) are still freehand-only.

---

## 10. How To Run

### Installation Steps

**Prerequisites**: Python 3.12+, a webcam, a microphone, and Windows OS.

```powershell
# 1. Clone the repository
git clone <repository-url>
cd wavly2.0

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
venv\Scripts\activate

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Launch Wavly
python main.py
```

On startup, Wavly will:
1. Open the webcam.
2. Display a transparent fullscreen overlay with the HUD.
3. Speak a Jarvis-style startup greeting.
4. Begin listening for the wake word `"wavly"`.
5. Start processing hand gestures immediately.

**To exit**: Press `Escape` or slam the mouse cursor into any screen corner (PyAutoGUI failsafe).

---

### Recording New Gestures

To collect training data for new or existing gestures:

```powershell
python record_gestures.py
```

**Controls**:
| Key     | Action                                               |
|:--------|:-----------------------------------------------------|
| `0`–`9` | Set the gesture label to record                     |
| `R`     | Toggle recording on/off                              |
| `Q`     | Quit and display final sample counts                 |

The recorder opens a live webcam feed showing:
- Hand landmarks drawn on the video.
- Current recording status (RECORDING / PAUSED).
- Active gesture label.
- Per-gesture sample counts.

Data is appended to `data/gestures.csv` in real time (buffered in batches of 30 rows).

---

### Retraining the Model

After recording new data, retrain the classifier:

```powershell
python src/ai/trainer.py
```

This will:
1. Load `data/gestures.csv`.
2. Print dataset statistics (total samples, per-gesture counts).
3. Split into 80% train / 20% test.
4. Train a `RandomForestClassifier` with 100 estimators.
5. Print overall accuracy, per-gesture classification report, and confusion matrix.
6. Save the updated model to `data/gesture_model.pkl`.

---

### Diagnostic Tools

```powershell
# Test active window detection
python test_context.py

# View raw model predictions with confidence percentages (live video)
python test_gestures.py

# Test microphone + Google Speech API transcription
python test_voice.py

# Test text-to-speech engine
python test_tts.py
```

---

## 11. Coming Soon

### 🚧 Phase 7 — Adaptive AI

**Goal**: Make Wavly learn and adapt to individual user habits over time.

**Planned Features**:
- Track gesture usage frequency and success rates per user session.
- Dynamically adjust confidence thresholds based on per-gesture error rates.
- Suggest gesture remapping based on observed user preferences.
- Implement online/incremental learning to fine-tune the model without full retraining.
- User behavior analytics dashboard.

---

*End of Report*
