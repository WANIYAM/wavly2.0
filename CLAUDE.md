# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wavly is an AI-powered touchless computer control system that uses hand gestures, computer vision, and voice commands to control a computer. The system captures webcam input, processes hand gestures using MediaPipe, classifies gestures using a Random Forest model, listens for voice triggers, and translates inputs into automated system actions using PyAutoGUI.

## Tech Stack

- **Python 3.12+** - Core language
- **OpenCV** - Video capture and image processing
- **MediaPipe** - Hand landmark detection and tracking
- **PyAutoGUI** - System automation (mouse, keyboard control)
- **scikit-learn** - Gesture classification (Random Forest)
- **PyQt6** - GUI framework for transparent overlays and HUD interface
- **NumPy & Pandas** - Numerical operations and dataset handling
- **SpeechRecognition & pyttsx3** - Speech-to-text recognition and text-to-speech feedback

## Development Setup

### Initial Setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
python main.py
```

### Testing & Diagnostics
```bash
# Test raw gesture predictions with live video stream
python test_gestures.py

# Test active application context detection
python test_context.py

# Test microphone integration
python test_voice.py

# Test Text-To-Speech engine
python test_tts.py
```

## Project Architecture

### Module Structure

```
src/
├── ai/                 # Gesture classification and model training
│   ├── data_collector.py  # Script/class to collect and log normalized training data to CSV
│   ├── predictor.py       # Wrapper for the trained ML model predictions
│   └── trainer.py         # Script to train and export the scikit-learn model
├── camera/             # Webcam and computer vision tracking
│   └── hand_tracker.py    # MediaPipe hand detection wrapper
├── control/            # Automation mapping and execution
│   ├── app_profiles.py    # App-specific gesture mapping profiles (Chrome, VLC, PowerPoint)
│   ├── context_detector.py # Identifies the currently active window/application
│   ├── gesture_mapper.py  # Translates confirmed gestures to system automation actions depending on mode
│   ├── mouse_controller.py# Handles PyAutoGUI-based cursor movement and smooth tracking
│   ├── voice_controller.py# Background thread listening and parsing voice commands
│   ├── voice_mapper.py    # Executes PyAutoGUI actions for recognized voice commands
│   └── voice_responder.py # Multi-threaded Text-To-Speech engine using pyttsx3/PowerShell fallback
└── ui/                 # PyQt6 user interface components
    ├── overlay_window.py  # Transparent PyQt6 overlay UI / HUD for drawing, modes, and HUD displays
    └── vision_thread.py   # Background thread handling camera input, prediction filtering, and control signals
```

### Key Design Patterns

1. **Pipeline Architecture**: Webcam → MediaPipe Landmarks → Coordinate Normalization → Random Forest Classifier → Buffer confirmation → Action Execution
2. **Separation of Concerns**: 
   - `src/ai/` and `src/camera/` handle hand tracking and machine learning classification.
   - `src/control/` handles operating system control, mapping, and voice assistance.
   - `src/ui/` handles transparent drawing overlay canvas and cyberpunk HUD.
3. **Multi-Threading**:
   - PyQt6 main thread coordinates overlay rendering and canvas drawing.
   - `VisionThread` processes heavy camera capture and predictions.
   - `VoiceController` handles blocking speech recognition in the background.
   - `VoiceResponder` manages background audio queues to ensure zero lag in frame loops.

### Data Flow

1. Webcam frame is read by the `VisionThread` using OpenCV.
2. `HandTracker` extracts hand landmark objects.
3. Landmark coordinates are normalized relative to the wrist (landmark 0) to support position-invariant predictions.
4. `GesturePredictor` feeds the coordinates into the Random Forest model.
5. `VisionThread` uses a 10-frame buffer (6/10 votes) to confirm predictions.
6. `GestureMapper` maps predictions to PyAutoGUI movements or keys, checking active window context via `ContextDetector`.
7. `OverlayWindow` updates drawing lines or modes and animates the bottom-right HUD overlay.

## Development Guidelines

### Adding New Gestures

1. Open a terminal and run `python record_gestures.py` to capture live normalized landmark coordinates. Numeric keys `0-9` are bound to a fixed set of gesture labels (`fist`, `open_hand`, `point`, `two_fingers`, `three_fingers`, `four_fingers`, `thumbs_up`, `thumbs_down`, `l_shape`, `pinch`) via the `GESTURE_LABELS` dict — edit that dict to add new labels. Press `R` to toggle recording, `Q` to quit. This appends data directly to `data/gestures.csv`.
2. Run `python src/ai/trainer.py` to re-train the Random Forest model and write `data/gesture_model.pkl` to disk.
3. Map the confirmed gesture to system actions in `src/control/gesture_mapper.py` (and add app-specific mappings in `src/control/app_profiles.py` if needed).
4. Launch `python main.py` to verify system behavior.

### System Automation Safety

- PyAutoGUI has a built-in failsafe (slam mouse pointer into any screen corner to immediately abort).
- Test keyboard and click automations in a safe test environment first.

### Gotchas

- **Camera index is hardcoded and inconsistent.** The main app (`src/ui/vision_thread.py`) and `test_gestures.py` use `cv2.VideoCapture(0)`, but `record_gestures.py` uses `cv2.VideoCapture(1)`. If recording fails to open the webcam or grabs the wrong camera, change the index to match your hardware.
- **Windows-only runtime.** `main.py` calls `ctypes.windll.user32.SetProcessDPIAware()` and `context_detector.py`/voice modules rely on `pywin32`/`PyGetWindow`, so the app targets Windows despite the cross-platform venv instructions.

## Data & Models

Data and serialized model files are stored in the `data/` directory:
- `data/gestures.csv` - Labeled hand landmark datasets containing coordinate features.
- `data/gesture_model.pkl` - Serialized scikit-learn Random Forest classifier model.
