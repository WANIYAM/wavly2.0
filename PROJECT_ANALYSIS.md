# WAVLY 2.0 — Project Analysis

## 1. Executive Summary

Wavly 2.0 is a Windows-focused Python application for touchless computer control using webcam-based hand gestures and optional voice commands. It combines MediaPipe hand landmark tracking, a scikit-learn Random Forest gesture classifier, PyAutoGUI automation, and a PyQt6 transparent overlay with a drawing canvas and status HUD.

Current state:
- The core runtime pipeline is implemented and appears functional for gesture detection, cursor movement, click/keyboard macros, and voice command execution.
- The codebase includes data collection and model training utilities for the gesture classifier.
- Several documentation files claim broader functionality than the actual code implements; those mismatches are documented below.
- The repository includes empty placeholder directories (`config/`, `models/`, `tests/`) and a Python virtual environment in `venv/` / `.venv/`.

Overall health assessment:
- The codebase is mostly complete for a gesture-and-voice proof-of-concept.
- There are a few reliability and logic issues that should be fixed before production use, notably pinch-click duplication, voice session lifecycle gaps, and some documentation mismatches.
- The app is tightly coupled to Windows-specific automation and voice fallback via PowerShell.

## 2. Complete File Inventory

### Root files and directories
- `CHECKPOINT.md` — project checkpoint summary describing current code purpose and feature state.
- `CLAUDE.md` — repository guidance and architecture notes for the code assistant.
- `README.md` — user-facing project documentation and feature list; includes some claims not fully matched by code.
- `REPORT.md` — an extended project report with status, architecture, and metrics; includes several overstatements compared to the code.
- `PROJECT_SUMMARY.md` — short summary of the project and file structure.
- `requirements.txt` — pinned Python package dependencies.
- `main.py` — application entry point that initializes Qt, sets DPI/runtime environment variables, and launches the overlay.
- `record_gestures.py` — gesture dataset recording utility using OpenCV and MediaPipe landmarks.
- `test_gestures.py` — debug utility to display raw model predictions and confidence percentages on a webcam feed.
- `test_voice.py` — microphone recognition diagnostic script using SpeechRecognition.
- `test_context.py` — active window context detection diagnostic script.
- `test_tts.py` — threaded pyttsx3 text-to-speech test script.
- `test_audio.ps1` — PowerShell speech synthesis test script.

### Data and model artifacts
- `data/gestures.csv` — collected gesture training dataset.
- `data/gesture_model.pkl` — serialized `RandomForestClassifier` model used by runtime prediction.

### Source tree
- `src/__init__.py` — package version metadata.
- `src/ai/__init__.py` — empty package initializer.
- `src/ai/data_collector.py` — buffered helper for writing normalized landmark rows to CSV.
- `src/ai/predictor.py` — runtime gesture prediction wrapper for the serialized classifier.
- `src/ai/trainer.py` — model training script using scikit-learn.
- `src/camera/__init__.py` — empty package initializer.
- `src/camera/hand_tracker.py` — MediaPipe hand detection wrapper.
- `src/control/__init__.py` — empty package initializer.
- `src/control/app_profiles.py` — context-aware gesture mappings for Chrome, VLC, and PowerPoint.
- `src/control/context_detector.py` — foreground window title detection and app classification.
- `src/control/gesture_mapper.py` — maps confirmed gestures into modes and actions.
- `src/control/mouse_controller.py` — screen movement smoothing and click cooldown helper.
- `src/control/voice_controller.py` — background speech recognition/wake-word listener.
- `src/control/voice_mapper.py` — maps recognized voice text to system actions.
- `src/control/voice_responder.py` — queued text-to-speech responder using pyttsx3 and PowerShell fallback.
- `src/ui/__init__.py` — empty package initializer.
- `src/ui/overlay_window.py` — full-screen transparent overlay window and drawing HUD.
- `src/ui/vision_thread.py` — camera/gesture/voice worker thread that drives the app.

### Other directories
- `config/` — present but empty.
- `models/` — present but empty.
- `tests/` — present but empty.
- `.gitignore` — git ignore patterns for Python artifacts and environment files.
- `.venv/`, `venv/` — local Python virtual environments present in the workspace but not part of application logic.

## 3. Each Module Deep Dive

### `main.py`
- Purpose: Launch the Qt overlay application and configure environment settings.
- Imports: `os`, `sys`, `warnings`, `QApplication`, `qInstallMessageHandler`, `OverlayWindow`.
- Behavior:
  - Disables Qt debug logging and high DPI scaling via environment variables.
  - Defines a Qt message handler that drops all Qt logs.
  - Calls `ctypes.windll.user32.SetProcessDPIAware()` on Windows for DPI handling.
  - Instantiates and shows `OverlayWindow`; executes the Qt event loop.
- Hardcoded values: no user-configurable timeout or app arguments.
- Notes: it assumes the application runs on Windows because it calls `ctypes.windll`.

### `record_gestures.py`
- Purpose: Capture webcam frames and save normalized landmark data to `data/gestures.csv` for model training.
- Imports: `cv2`, `HandTracker`, `DataCollector`.
- Behavior:
  - Opens default webcam `VideoCapture(0)`.
  - Detects hand landmarks and draws them on-screen.
  - When recording is enabled, saves normalized landmarks labeled by the current key selection.
  - Displays recording state, gesture name, sample counts, and hand detection indicator.
  - Keyboard control: `0-9` set gesture label, `R` toggle recording, `Q` quit.
- Issues:
  - No alternative camera index support.
  - Cannot choose output data file at runtime.

### `test_gestures.py`
- Purpose: Diagnostics mode showing raw predictions and probability bars from the trained model.
- Imports: `cv2`, `numpy`, `HandTracker`, `GesturePredictor`.
- Behavior:
  - Loads the model using `GesturePredictor()`.
  - Reads webcam frames, detects hands, draws landmarks.
  - Computes normalized coordinates relative to the wrist and passes them directly to the classifier.
  - Displays top-3 class probabilities and raw prediction confidence.
- Dependencies: requires `data/gesture_model.pkl`.
- Notes: This tool bypasses the main app's smoothing, buffering, and gesture mapping.

### `test_voice.py`
- Purpose: Microphone voice recognition health check.
- Imports: `speech_recognition as sr`.
- Behavior:
  - Initializes microphone and ambient noise adjustment.
  - Performs three listen-and-recognize iterations with 5-second timeouts.
  - Prints recognized text or errors.
- Notes: It does not exercise the app's wake word or voice mapping.

### `test_context.py`
- Purpose: Validate active window detection.
- Imports: `time`, `ContextDetector`.
- Behavior:
  - Runs a 30-second loop printing the active window title and app classification each second.
- Notes: useful for verifying `pygetwindow` behavior on Windows.

### `test_tts.py`
- Purpose: Validate threaded `pyttsx3` text-to-speech and COM initialization.
- Imports: `threading`, `time`, `pyttsx3`, optional `pythoncom`.
- Behavior:
  - Executes a TTS test on the main thread.
  - Executes a background-thread TTS test like `VoiceResponder` would.
- Notes: does not integrate with the actual application state.

### `src/ai/data_collector.py`
- Purpose: Persist normalized hand landmark vectors to CSV.
- Imports: `csv`, `Path`.
- Class: `DataCollector`
  - `__init__(data_dir='data', filename='gestures.csv')`: sets path and buffer size of `30` rows.
  - `save(landmark_list, gesture_name)`: normalizes landmarks relative to wrist coordinates, flattens to 42 features, buffers rows.
  - `flush()`: appends buffered rows to `data/gestures.csv`.
- Hardcoded values: output directory `data`, buffer size `30`.
- Notes:
  - `__del__` attempts a cleanup flush, but relying on destructor semantics is fragile.

### `src/ai/predictor.py`
- Purpose: Use a trained RandomForest model to classify gestures.
- Imports: `pickle`, `numpy as np`, `warnings`, `Path`.
- Class: `GesturePredictor`
  - `__init__()`: loads `data/gesture_model.pkl` from repo root.
  - `predict(landmark_list)`: returns a gesture or `unknown`.
- Prediction logic:
  - Input is expected as 21 normalized `(x, y)` pairs.
  - Flattens to a 42-element feature vector.
  - Uses `predict_proba` and selects top two classes.
  - Special handling:
    - `four_fingers` accepted at `>= 0.35` confidence.
    - `>= 0.55`: accept top prediction.
    - `0.40 <= top_confidence < 0.55`: accept only if gap to second best > `0.15`.
    - `< 0.40`: return `unknown`.
- Hardcoded values:
  - Paths: model located at `data/gesture_model.pkl` relative to repository root.
  - Confidence thresholds: `0.40`, `0.55`, `0.15`, `0.35` for `four_fingers`.
- Issues:
  - If the model is missing, the app still runs in collection-only mode.

### `src/ai/trainer.py`
- Purpose: Train a gesture classification model from `data/gestures.csv`.
- Imports: `pandas`, `pickle`, `RandomForestClassifier`, `train_test_split`, `accuracy_score`, `classification_report`, `confusion_matrix`.
- Behavior:
  - Reads `data/gestures.csv` without header.
  - Defines columns `gesture`, `feature_0`, ... `feature_N`.
  - Splits data with `test_size=0.2`, `random_state=42`.
  - Trains `RandomForestClassifier(n_estimators=100, random_state=42)`.
  - Prints overall accuracy, classification report, confusion matrix.
  - Saves the trained model to `data/gesture_model.pkl`.
- Notes:
  - No exception handling for missing or malformed CSV.
  - No hyperparameter search or cross-validation.

### `src/camera/hand_tracker.py`
- Purpose: Wrap MediaPipe hand landmark detection and drawing.
- Imports: `cv2`, `mediapipe as mp`.
- Class: `HandTracker`
  - `__init__(max_hands=1, detection_confidence=0.5, tracking_confidence=0.5)`: initializes MediaPipe Hands.
  - `detect(frame)`: returns the first detected hand landmarks or `None`.
  - `get_landmark_list(landmarks, frame_width, frame_height)`: converts normalized landmarks to pixel coordinates.
  - `draw(frame, landmarks)`: renders hand skeletons on the frame.
  - `close()`: closes MediaPipe resources.
- Hardcoded values: default detection/tracking confidences `0.5`.

### `src/control/context_detector.py`
- Purpose: Detect the active foreground application using window title.
- Imports: `pygetwindow`.
- Class: `ContextDetector`
  - `get_active_title()`: returns the active window title or `None`.
  - `get_active_app()`: returns application identifier `chrome`, `vlc`, `powerpoint`, or `default`.
- Hardcoded rules:
  - `"Chrome"` or `"Edge"` → `chrome`.
  - `"VLC"` → `vlc`.
  - `"PowerPoint"` → `powerpoint`.
  - Otherwise `default`.
- Issues:
  - Title matching is case-sensitive and narrow.

### `src/control/app_profiles.py`
- Purpose: Provide app-specific gesture-to-action mappings.
- Imports: `pyautogui`.
- Class: `AppProfiles`
  - `self.profiles` contains gesture mappings for `chrome`, `vlc`, and `powerpoint`.
  - `get_profile(app_name)` returns the dictionary or empty map.
- Supported app gestures include browser tab control, media playback, and PowerPoint navigation.
- Notes: no fallback behavior when actions fail.

### `src/control/gesture_mapper.py`
- Purpose: Map confirmed gestures into application states and actions.
- Imports: `pyautogui`, `time`, `ContextDetector`, `AppProfiles`.
- Class: `GestureMapper`
  - Maintains `current_mode`, `drawing_mode`, `last_confirmed_gesture`, and gesture cooldown timers.
  - Polls app context every `2.0` seconds.
- Methods:
  - `_can_execute(gesture_name)`: implements gesture cooldown enforcement and PowerPoint overrides.
  - `execute(gesture_name)`: performs action dispatch.
  - `get_current_mode()`, `is_drawing_mode()`, `update_hand_position(y)`.
- Normal mode mapping:
  - `fist` → freeze cursor.
  - `open_hand` → move mode.
  - `point` → precision mode.
  - `two_fingers` → scroll based on hand Y position.
  - `three_fingers` → open on-screen keyboard.
  - `four_fingers` → screenshot (captured directly to the clipboard, no Snipping Tool).
  - `thumbs_up` / `thumbs_down` → volume control.
  - `l_shape` → right click.
  - `pinch` → left click.
- Drawing mode mapping (`_execute_drawing`) — discrete commands only; continuous tools (point=draw, open_hand=erase, pinch=grab/move/resize) are applied per-frame by the overlay:
  - `spider_man` → exit drawing (pinch no longer exits).
  - `fist` → clear canvas (`clear_canvas`).
  - `thumbs_up` / `thumbs_down` → stroke size up / down (`size_up` / `size_down`).
  - `two_fingers` → toggle colour palette (`toggle_palette`).
  - `four_fingers` → paste clipboard image (`paste_image`).
  - `point` / `open_hand` / `pinch` → return `None` (handled continuously by the overlay).
- Hardcoded values:
  - gesture cooldowns: `0.1` to `3.0` seconds; drawing-mode discrete cooldowns `0.45`s (size) / `0.8`s (toggles).
- Notes: app profile actions use `pyautogui` directly and return `"executed"`.

### `src/control/mouse_controller.py`
- Purpose: Smooth cursor movement and manage click cooldowns.
- Imports: `pyautogui`, `time`.
- Class: `MouseController`
  - `__init__(smoothing_factor=0.3)`: sets screen dimensions and PyAutoGUI parameters.
  - `move(x, y, frame_width, frame_height, speed_multiplier=1.0)`: maps webcam coordinates to screen coordinates, applies a 10% margin, clamps values, smooths via EWMA, and moves the cursor.
  - `click(typing_mode=False)`: enforces click cooldowns.
- Hardcoded values:
  - margin: `0.1`.
  - smoothing factor: `0.3`.
  - click cooldown: `0.3`s normal, `0.2`s typing.

### `src/control/voice_controller.py`
- Purpose: Run continuous speech recognition and wake-word detection.
- Imports: `queue`, `threading`, `time`, `speech_recognition as sr`.
- Class: `VoiceController`
  - `__init__()`: sets up recognizer, microphone, wake word, and session flags.
  - `start()`, `stop()`: manage the background listener thread.
  - `_run_loop()`: listens for audio, performs ambient noise adjustment, and detects wake words.
- Behavior:
  - `activated` remains false until a wake word is heard.
  - After activation, commands are queued and goodbye phrases reset the session.
- Hardcoded values:
  - wake words list.
  - goodbye phrases list.
  - listening timeout: `3` seconds.
  - `session_timeout` exists but is unused.
- Issues:
  - no timeout or auto-deactivate feature.
  - uses cloud speech via `recognize_google` rather than local offline recognition.

### `src/control/voice_mapper.py`
- Purpose: Map recognized voice text to actions and spoken feedback.
- Imports: `os`, `pyautogui`, `VoiceResponder`.
- Class: `VoiceMapper`
  - `self.commands` holds exact voice-to-action mappings.
  - `self.responses` holds speech feedback text.
  - `execute(command)`: normalizes input and searches exact, substring, and alias mappings.
- Supported commands: 20 standard voice commands covering mouse, volume, browser, and presentation control.
- Alias support: map natural phrases like `louder`, `take screenshot`, `start notepad`.
- Issues:
  - command normalization is basic and may fail with complex transcripts.
  - uses Windows-specific `start` shell invocation.

### `src/control/voice_responder.py`
- Purpose: Queue and play synthesized speech in a separate thread.
- Imports: `queue`, `threading`, `pyttsx3`.
- Class: `VoiceResponder`
  - `start()`, `stop()`: manage the speech thread.
  - `speak(text)`: queue spoken text.
  - `greet()`, `speak_wake_response()`: queue randomized responses.
  - `_run_loop()`: initializes `pyttsx3`, chooses a voice, and speaks queued text.
- Fallback:
  - If `pyttsx3` fails, uses PowerShell `System.Speech.Synthesis.SpeechSynthesizer`.
- Hardcoded values:
  - rate: `185`.
  - volume: `1.0`.
- Issues:
  - fallback speech escaping is fragile.
  - no explicit thread-safe shutdown order for the speech engine.

### `src/ui/overlay_window.py`
- Purpose: Display the transparent full-screen overlay, drawing canvas, and status HUD.
- Imports: `os`, `time`, `math`, `datetime`, `QMainWindow`, `QApplication`, `Qt`, `QPoint`, `QTimer`, `QStandardPaths`, `QRectF`, `QPainter`, `QPen`, `QColor`, `QPixmap`, `QFont`, `VisionThread`.
- Class: `OverlayWindow` (drawing surface rewritten June 2026 to tool-follows-gesture)
  - Window flags: frameless, stay-on-top, transparent input, tool.
  - Creates a full-screen raster stroke `QPixmap` plus an image-object layer; manages colour, stroke size, the active tool, pinch manipulation, and HUD state.
  - One-Euro pointer smoothing (`OneEuroFilter`) and full-screen edge mapping (`_to_screen` with `draw_margin`).
  - Connects `VisionThread` signals (`draw_event`, gesture, mode, app, voice).
- Behaviors:
  - `on_draw_event()`: per-frame entry point — routes to draw/erase/grab, palette selection, or the toolbar panel.
  - `_update_manip()` / `_drop_manip()`: pinch grab → move → hold-still Resize → drop; `open_hand` drops instantly.
  - `_lift_ink_component()`: cuts the connected ink blob under the pinch out of the canvas (`scipy.ndimage.label`, numpy flood-fill fallback).
  - `_paint_panel()` / `_draw_panel_icon()`: right-edge dwell toolbar with hand-drawn vector icons.
  - `paintEvent()`: renders canvas, images, panel, palette, cursor, and HUD.
  - `draw_hud()` / `draw_arc_reactor()`: cyberpunk HUD and animated ring.
  - `keyPressEvent()`: `C` clears canvas, `Esc` closes app.
- Hardcoded values:
  - HUD dimensions: `280x190`; colour palette: 8 colours; stroke size range: 2–60.
  - Manipulation dwell: ~2s (Move/Resize toggle), ~3.5s (drop); panel dwell ~1s.
- Issues:
  - Connected-component grab does a full-screen QImage round-trip per pinch (a brief one-off cost).

### `src/ui/vision_thread.py`
- Purpose: Main worker thread for camera, gesture recognition, mode execution, and voice command processing.
- Imports: `cv2`, `time`, `math`, `warnings`, `Counter`, `QThread`, `pyqtSignal`, `HandTracker`, `MouseController`, `GestureMapper`, `GesturePredictor`, `VoiceController`, `VoiceMapper`, `VoiceResponder`.
- Signals:
  - `draw_event(dict)` — per-frame drawing state (position, thumb, tool, pinch, gesture); replaces the old `point_detected`
  - `gesture_detected(str)`
  - `gesture_command(str)`
  - `mode_changed(str)`
  - `app_changed(str)`
  - `voice_status_changed(str)`
  - `frame_ready(object)` — camera preview frame for the HUD PiP
- Initialization:
  - Creates `HandTracker` with detection/tracking confidence `0.7`.
  - Initializes mouse, gesture mapper, predictor, voice responder, voice listener, and voice mapper.
  - Starts the voice responder and controller.
- Run loop:
  - Opens default webcam.
  - Greets via voice responder.
  - Emits initial active app and starts voice control.
  - Captures frames in a loop, flips horizontally.
  - Every 2 seconds checks app context.
  - On each frame, detects landmarks and emits fingertip coordinates.
  - Normalizes landmarks relative to the wrist and predicts gestures.
  - Buffers predictions in a rolling window of 10.
  - Confirms gestures if `>= 6` votes and `not unknown`.
  - Clears buffer after `5` consecutive unknown majority votes.
  - Detects pinch geometry and clicks via `MouseController`.
  - Executes gesture actions and emits drawing commands to the overlay.
  - Moves the cursor for `open_hand` and `point` gestures.
  - Shows a small OpenCV camera preview.
  - Processes queued voice commands using `VoiceMapper`.
  - Emits voice status changes for HUD updates.
- Issues:
  - `pinch` click duplication and independent click triggers.
  - preview window appears even though the app is meant to be touchless.

### `src/__init__.py`
- Contains version metadata: `__version__ = "0.1.0"`.

### Empty package initializers
- `src/ai/__init__.py`, `src/camera/__init__.py`, `src/control/__init__.py`, `src/ui/__init__.py` are empty.

### `.gitignore`
- Excludes Python artifacts, caches, and virtual environment folders.

## 4. Data Flow

### Gesture pipeline
1. `src/ui/vision_thread.py` captures webcam frames with OpenCV.
2. `HandTracker.detect(frame)` returns MediaPipe hand landmarks.
3. `HandTracker.get_landmark_list()` converts normalized hand landmarks into pixel positions.
4. The fingertip position is emitted to the overlay for drawing.
5. Landmarks are normalized relative to the wrist and passed into `GesturePredictor.predict()`.
6. Predictions are buffered in a 10-frame rolling window.
7. The most common gesture is confirmed if it has `>= 6` votes and is not `unknown`.
8. `GestureMapper.execute()` converts confirmed gestures into actions or mode changes.
9. The cursor is moved by `MouseController.move()` for `open_hand` and `point`.
10. Drawing mode commands are emitted to `OverlayWindow` via `gesture_command`.

### Voice pipeline
1. `VoiceController` listens continuously on a microphone thread.
2. If a wake word is recognized, the system activates and speaks a wake response.
3. Subsequent speech is enqueued as commands.
4. `VisionThread` polls `VoiceController.command_queue` each frame.
5. Commands are passed to `VoiceMapper.execute()`.
6. Recognized command actions execute via PyAutoGUI or OS shell.
7. `VoiceResponder` synthesizes speech feedback in a separate thread.
8. The overlay HUD updates voice status from standby to listening to active.

## 5. All Known Bugs & Issues

### Gesture issues
- **Pinch duplication**: `src/ui/vision_thread.py` calls `self.mouse_controller.click()` for geometric pinch and `GestureMapper.execute('pinch')` also performs `pyautogui.click()` (normal mode only — drawing mode no longer clicks).
- **Pinch without classifier confirmation**: geometric pinch detection triggers independently of prediction buffer results.
- **~~Fixed 640x480 overlay mapping~~** (resolved June 2026): the drawing overlay now maps using the frame dimensions carried in each `draw_event`, and stretches a central band to the full screen for edge reachability.

### Voice issues
- **Unused voice timeout**: `VoiceController.session_timeout` is defined but never used.
- **Persistent active session**: voice remains active until a goodbye phrase is spoken.
- **Weak wake-word matching**: close-sounding words may misactivate the system.
- **PowerShell TTS fallback quote escaping is fragile**, and may fail for special characters.

### Context issues
- **Case-sensitive active app detection** may miss window titles.
- **Browser detection limited to Chrome/Edge/VLC/PowerPoint**.

### Reliability issues
- **Unreliable destructor flush** in `DataCollector.__del__()`.
- **No CSV validation in `trainer.py`**.
- **`pyttsx3` failures are only printed**.

## 6. Inconsistencies

### Documentation vs code
- `REPORT.md` still lists an "Air Drawing" phase with 3D path tools that are not implemented (2D only).
- Documented module structure includes non-existent packages such as `src/automation/`.
- Drawing mode is now a full 2D editor (draw/erase/clear, object move/resize, image paste, dwell toolbar) — the earlier "basic 2D drawing only" note is outdated.

### Mismatched claims
- Voice documentation claims wake-word activation and spoken session management; the actual implementation is partial and cloud-based.
- The model accuracy claim appears in docs but is not verified by runtime code.

## 7. Missing Pieces

### Missing from implementation
- No actual `src/automation/` module.
- Empty `config/`, `models/`, and `tests/` directories.
- No offline speech recognition engine.
- No camera selection UI.

### Useful missing features
- Emergency overlay close hotkey.
- Explicit GUI error messages for missing webcam or mic.
- Config-driven thresholds.

## 8. Dependencies Map

### Runtime dependency graph
- `main.py` → `src/ui/overlay_window.py`
- `src/ui/overlay_window.py` → `src/ui/vision_thread.py`
- `src/ui/vision_thread.py` → `src/camera/hand_tracker.py`, `src/control/mouse_controller.py`, `src/control/gesture_mapper.py`, `src/ai/predictor.py`, `src/control/voice_controller.py`, `src/control/voice_mapper.py`, `src/control/voice_responder.py`
- `src/control/gesture_mapper.py` → `src/control/context_detector.py`, `src/control/app_profiles.py`
- `record_gestures.py` → `src/camera/hand_tracker.py`, `src/ai/data_collector.py`
- `test_gestures.py` → `src/camera/hand_tracker.py`, `src/ai/predictor.py`
- `test_context.py` → `src/control/context_detector.py`

### Breakage points
- Removing `src/ui/vision_thread.py` or `src/ui/overlay_window.py` breaks the app.
- Removing `src/camera/hand_tracker.py` disables gesture input.
- Removing `data/gesture_model.pkl` disables runtime gesture prediction.
- Removing `src/control/gesture_mapper.py` disables gesture actions.
- Removing voice modules disables voice.

## 9. Configuration Reference

### Hardcoded thresholds and constants
- Gesture buffer size: `10` frames.
- Gesture confirmation threshold: `6` votes.
- Unknown streak reset: `5` frames.
- Drawing mode hold time: `2.0` seconds.
- `GestureMapper` cooldowns: `open_hand=2.0`, `point=2.0`, `fist=2.0`, `two_fingers=0.1`, `three_fingers=3.0`, `four_fingers=3.0`, `thumbs_up=2.0`, `thumbs_down=2.0`, `l_shape=2.0`, `pinch=2.0`.
- PowerPoint override: `0.8` seconds for `two_fingers` and `l_shape`.
- Pinch trigger: `< 60` px.
- Pinch release: `> 80` px.
- Index curl threshold: `< 30` px.
- Mouse smoothing factor: `0.3`.
- Screen margin: `0.1`.
- PyAutoGUI pause: `0.01`.
- Voice listen timeout: `3` seconds.
- Voice phrase time limit: `3` seconds.
- Voice responder rate: `185`.
- `VoiceController.session_timeout`: `999999` (unused).
- Runtime hand tracker confidence: `0.7`.

### `requirements.txt` versions
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

## 10. Recommendations

### High priority
1. Fix pinch click duplication and choose one reliable pinch mechanism.
2. Implement voice session auto-deactivation or timeout.
3. Improve app detection to be case-insensitive and support more titles.
4. Add missing error handling for absent data/model files.

### Medium priority
5. Centralize configuration values in a config module or file.
6. Hide or optionally disable the OpenCV preview window for production.
7. Harden voice text normalization and alias logic.
8. Improve TTS fallback escaping.
9. Add camera selection support.

### Low priority
10. Add automated tests in `tests/`.
11. Clean up docs to match implemented behavior.
12. Populate or remove empty placeholder directories.

---

## Line references for key issues
- `src/ui/vision_thread.py` lines ~171-173: duplicate click path for pinch.
- `src/control/voice_controller.py` line ~16: `session_timeout` defined but unused.
- `src/control/context_detector.py` line ~20: case-sensitive app matching.
- `src/ui/vision_thread.py` lines ~138-150: buffer confirmation and unknown streak logic.
- `src/control/mouse_controller.py` line ~58: click cooldown logic.
- `src/ui/overlay_window.py` `_to_screen()`: frame→screen mapping with full-screen edge band (replaced the old fixed 640x480 mapping).
