# Wavly Project Summary

## Project Overview

Wavly is an AI-powered touchless computer control system built in Python. It uses webcam-based hand tracking, a gesture classification model, voice recognition, and a transparent PyQt6 overlay to translate physical gestures and spoken commands into mouse, keyboard, and application control actions.

Key capabilities:
- Real-time hand gesture recognition using MediaPipe and a Random Forest model
- Adaptive cursor movement with smoothing and margin compensation
- Hand gesture-based click, scroll, and application control
- Context-aware app profiles for Chrome, VLC, and PowerPoint
- Voice command listening with wake-word activation and spoken responses
- Drawing mode overlay (tool-follows-gesture): gesture-driven draw/erase/clear, pinch to move & resize strokes and images, clipboard image paste, and a dwell-activated on-screen toolbar
- Data collection and model training utilities

---

## Repository Layout

Root files:
- `README.md` — project description, usage, and high-level features
- `main.py` — entry point launching the PyQt6 overlay window and application
- `requirements.txt` — Python package dependencies
- `record_gestures.py` — gesture dataset collection tool
- `REPORT.md` — existing report file in workspace
- `CHECKPOINT.md` — repository checkpoint metadata
- `CLAUDE.md` — additional project notes and architecture overview
- `test_gestures.py`, `test_voice.py`, `test_context.py`, `test_tts.py` — diagnostics and hardware tests
- `test_audio.ps1` — PowerShell audio test utility

Directories:
- `src/` — main application source code
- `data/` — gesture dataset and serialized model
- `config/` — currently empty
- `models/` — currently empty
- `.git/` — Git repository metadata
- `.venv/` and `venv/` — local Python virtual environment folders

---

## Core Application Files

### `main.py`
- Sets environment variables for Qt and protobuf
- Initializes a PyQt6 `QApplication`
- Enables Windows DPI awareness
- Creates and shows `OverlayWindow`
- Runs the Qt event loop

### `requirements.txt`
Contains explicit pinned dependencies:
- `mediapipe==0.10.14`
- `opencv-python==4.13.0.92`
- `numpy==2.4.0`
- `pandas==2.2.3`
- `scikit-learn==1.8.0`
- `PyQt6==6.11.0`
- `PyAutoGUI==0.9.54`
- `SpeechRecognition==3.16.1`
- `PyAudio==0.2.14`
- `pyttsx3==2.99`
- `PyGetWindow==0.0.9`
- `pywin32==311`

---

## Data & Model Assets

### `data/gestures.csv`
- Collected gesture training dataset
- Each row is: `gesture_name, x1, y1, x2, y2, ..., x21, y21`
- Coordinates are normalized relative to the wrist landmark before saving

### `data/gesture_model.pkl`
- Serialized scikit-learn `RandomForestClassifier`
- Used by the runtime predictor to classify hand gestures

---

## Source Code Breakdown

### `src/ai/`
- `data_collector.py`
  - `DataCollector.save()` records normalized hand landmarks to CSV
  - Buffers rows and flushes to disk in batches
- `trainer.py`
  - Trains a `RandomForestClassifier` from `data/gestures.csv`
  - Prints dataset stats, per-gesture accuracy, and confusion matrix
  - Saves model to `data/gesture_model.pkl`
- `predictor.py`
  - `GesturePredictor` loads the serialized model
  - `predict()` returns a gesture name or `unknown` based on confidence thresholds
  - Applies confidence heuristics and special handling for `four_fingers`

### `src/camera/`
- `hand_tracker.py`
  - Wraps MediaPipe hand detection
  - Converts landmarks to pixel coordinates
  - Draws landmarks and hand connections on video frames

### `src/control/`
- `context_detector.py`
  - Uses `pygetwindow` to inspect the active foreground window title
  - Maps titles to application contexts: `chrome`, `vlc`, `powerpoint`, or `default`
- `app_profiles.py`
  - Defines app-specific gesture-action mappings for Chrome, VLC, and PowerPoint
  - Uses `pyautogui` hotkeys and presses for application control
- `gesture_mapper.py`
  - Central gesture-to-action manager
  - Supports two modes: `normal` and `drawing`
  - Implements gesture cooldowns and deduplication
  - In normal mode, maps gestures to cursor mode, click, scroll, screenshots, keyboard shortcuts, and volume
  - In drawing mode (`_execute_drawing`), resolves discrete commands — clear (`fist`), stroke size +/- (`thumbs_up`/`thumbs_down`), palette toggle (`two_fingers`), image paste (`four_fingers`), exit (`spider_man`) — while the continuous tools (point=draw, open_hand=erase, pinch=grab/move/resize) are applied per-frame by the overlay
- `mouse_controller.py`
  - Smooths cursor movement using exponential moving average
  - Normalizes hand position to screen coordinates with margin compensation
  - Executes clicks with cooldown protection
- `voice_controller.py`
  - Background thread listens through microphone using `speech_recognition`
  - Recognizes a wake word like `wavly` before accepting commands
  - Queues recognized voice commands for later execution
- `voice_mapper.py`
  - Maps recognized voice text into actions
  - Supports exact matches, keyword substring matching, and alias normalization
  - Executes actions via `pyautogui` and OS commands
- `voice_responder.py`
  - Threaded text-to-speech engine using `pyttsx3`
  - Provides wake response, greetings, and fallback speech via PowerShell
  - Maintains queue and speaking state

### `src/ui/`
- `overlay_window.py`
  - Main transparent fullscreen PyQt6 overlay window
  - Owns the drawing surface: a raster stroke canvas + image-object layer, One-Euro pointer smoothing, and full-screen edge mapping
  - `on_draw_event` turns each per-frame draw event into draw/erase/grab actions; supports clear, stroke sizing, colour palette, clipboard image paste, object move/resize (`_update_manip`), and a right-edge dwell toolbar (`_paint_panel`)
  - Renders a cyberpunk-style status HUD with gesture, mode, active app, and voice status
  - Handles key presses: `C` to clear, `Esc` to close
- `vision_thread.py`
  - Background QThread that captures webcam frames from `cv2.VideoCapture(0)`
  - Detects landmarks, predicts gestures, and confirms gestures using a 10-frame voting buffer
  - Emits Qt signals: a per-frame `draw_event` dict (drawing state), gestures, mode changes, app changes, and voice status
  - Manages voice controller/responder lifecycle
  - Performs hand gesture-based motion, pinch click detection, and execution of mapped actions

---

## Gesture Recognition Details

Recognized gesture labels:
- `fist`
- `open_hand`
- `point`
- `two_fingers`
- `three_fingers`
- `four_fingers`
- `thumbs_up`
- `thumbs_down`
- `l_shape`
- `pinch`
- `spider_man`

Gesture behavior includes:
- `open_hand` → normal cursor movement mode
- `point` → precision cursor movement mode
- `fist` → freeze cursor
- `two_fingers` → scroll
<<<<<<< HEAD
- `pinch` → left click (in drawing mode: grab + move/resize a stroke or image)
=======
- `pinch` → left click or exit drawing mode
>>>>>>> fix/drawing-mode
- `l_shape` → right click
- `thumbs_up` / `thumbs_down` → volume control (in drawing mode: stroke size +/-)
- `three_fingers` → launch on-screen keyboard
<<<<<<< HEAD
- `four_fingers` → screenshot to clipboard (in drawing mode: paste image from clipboard)
- `spider_man` → toggle drawing mode ON/OFF

In **drawing mode** the per-frame tool follows the gesture: `point` draws, `open_hand` erases (and drops a grabbed element), `fist` clears, `two_fingers` toggles the colour palette.
=======
- `four_fingers` → screenshot
- `spider_man` → toggle drawing mode ON/OFF
>>>>>>> fix/drawing-mode

---

## Voice Command Support

Supported voice commands include:
- `click`, `right click`
- `scroll up`, `scroll down`
- `screenshot`
- `volume up`, `volume down`
- `open chrome`, `open notepad`
- `switch tab`, `close tab`
- `zoom in`, `zoom out`
- `new tab`
- `go back`, `go forward`
- `next slide`, `previous slide`
- `start presentation`, `stop presentation`

Wake-word activation flows through `VoiceController`, and spoken feedback is produced by `VoiceResponder`.

---

## Utility Scripts

### `record_gestures.py`
- Webcam-based data collection tool
- Press `0-9` to choose gesture label
- Press `R` to toggle recording
- Press `Q` to quit
- Appends normalized landmark rows into `data/gestures.csv`

### `src/ai/trainer.py`
- Trains `RandomForestClassifier` from `data/gestures.csv`
- Saves `data/gesture_model.pkl`
- Prints dataset size, class counts, accuracy, and confusion matrix

---

## Diagnostics & Tests

### `test_gestures.py`
- Launches webcam and displays raw gesture predictions
- Shows prediction probabilities and top 3 gestures
- Helps validate model accuracy and confidence

### `test_voice.py`
- Listens for 3 voice phrases and prints recognized text
- Validates microphone and speech recognition

### `test_context.py`
- Prints active window title and mapped app context once per second
- Validates foreground application detection

### `test_tts.py`
- Exercises `pyttsx3` speech synthesis in main and background threads
- Prints available voices and confirms TTS behavior

---

## How to Run the Project

1. Create and activate a Python virtual environment:
```powershell
python -m venv venv
venv\Scripts\activate
```
2. Install dependencies:
```powershell
pip install -r requirements.txt
```
3. Start the application:
```powershell
python main.py
```

Optional workflows:
- Collect gesture data: `python record_gestures.py`
- Train a new model: `python src/ai/trainer.py`
- Validate gesture model: `python test_gestures.py`
- Validate voice input: `python test_voice.py`
- Validate active window detection: `python test_context.py`
- Validate TTS: `python test_tts.py`

---

## Notes

- `config/` is present but currently empty
- `models/` is present but currently empty
- `data/` contains both gesture training data and the trained model
- The project is designed for Windows, with PowerShell and Windows-specific voice fallbacks present in `voice_responder.py`

---

## Complete File Reference

Root:
- `main.py`
- `README.md`
- `requirements.txt`
- `REPORT.md`
- `CLAUDE.md`
- `CHECKPOINT.md`
- `record_gestures.py`
- `test_gestures.py`
- `test_voice.py`
- `test_context.py`
- `test_tts.py`
- `test_audio.ps1`

Source:
- `src/ai/data_collector.py`
- `src/ai/predictor.py`
- `src/ai/trainer.py`
- `src/camera/hand_tracker.py`
- `src/control/context_detector.py`
- `src/control/app_profiles.py`
- `src/control/gesture_mapper.py`
- `src/control/mouse_controller.py`
- `src/control/voice_controller.py`
- `src/control/voice_mapper.py`
- `src/control/voice_responder.py`
- `src/ui/overlay_window.py`
- `src/ui/vision_thread.py`

Data:
- `data/gestures.csv`
- `data/gesture_model.pkl`

Empty directories:
- `config/`
- `models/`
