# Checkpoint: Current Working State

This document outlines the current status, configurations, structures, and implementation details of the Wavly 2.0 gesture control system.

## Project Structure

```
wavly2.0/
├── data/
│   ├── gesture_model.pkl      # Trained Random Forest classifier model
│   └── gestures.csv           # Dataset containing hand landmark coordinate features with labels
├── src/
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── data_collector.py  # Script/class to collect and log normalized training data to CSV
│   │   ├── predictor.py       # Wrapper for the trained ML model predictions
│   │   └── trainer.py         # Script to train and export the scikit-learn model
│   ├── automation/
│   │   └── __init__.py        # Empty init/placeholder module
│   ├── camera/
│   │   ├── __init__.py
│   │   └── hand_tracker.py    # MediaPipe hand detection wrapper
│   ├── control/
│   │   ├── __init__.py
│   │   ├── gesture_mapper.py  # Translates confirmed gestures to system automation actions depending on mode
│   │   └── mouse_controller.py# Handles PyAutoGUI-based cursor movement and click operations
│   ├── gesture_recognition/
│   │   └── __init__.py        # Empty init/placeholder module
│   ├── gestures/
│   │   └── __init__.py        # Empty init/placeholder module
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── overlay_window.py  # Transparent PyQt6 overlay UI / HUD for drawing, modes, and HUD displays
│   │   └── vision_thread.py   # Background thread handling camera input, prediction filtering, and control signals
│   └── utils/
│       └── __init__.py        # Empty init/placeholder module
├── CLAUDE.md                  # Claude Code guide and instructions
├── main.py                    # Entry point to launch the Wavly transparent overlay application
├── record_gestures.py         # Utility tool to record live landmarks and build the training dataset
├── requirements.txt           # Python dependency file
└── test_gestures.py           # Diagnostic/testing utility for live prediction visualization
```

## Files and Current Purpose

| File Path | Description / Purpose |
| :--- | :--- |
| `main.py` | Launches the PyQt6 overlay window application, configures DPI awareness, sets up logging overrides, and handles startup/shutdown processes. |
| `record_gestures.py` | Opens a live OpenCV webcam feed, runs hand tracking, and lets the user capture and save normalized coordinates mapped to target gesture labels for training datasets. |
| `test_gestures.py` | Diagnostic tool to display raw classifier prediction confidence percentages directly on a live video stream without gesture buffering or mapping. |
| `src/ui/vision_thread.py` | Spawns a background thread capturing camera frames, running landmark extraction, accumulating predicted gestures, validating coordinates for click events, and emitting signal events to the UI thread. |
| `src/ui/overlay_window.py` | Provides a transparent, full-screen canvas window using PyQt6, implements drawing behaviors (changing colors, pen size, canvas clearing, saving canvas to image), and displays gesture/mode status feedback. |
| `src/control/gesture_mapper.py` | Maps confirmed gestures to specific PyAutoGUI inputs (keyboard shortcut hotkeys, clicks) or tracking modes (move, freeze, drawing) while managing cooldown rules and state transitions. |
| `src/control/mouse_controller.py` | Wrapper for PyAutoGUI pointer controls, incorporating coordinate scaling, smoothing logic, and click action commands. |
| `src/camera/hand_tracker.py` | Encapsulates the Google MediaPipe Hand Landmark detection pipeline, returning landmarks and converting index/pip/thumb tips to coordinate locations. |
| `src/ai/predictor.py` | Loads the serialized gesture classifier pickle file and outputs prediction labels for normalized coordinate vectors. |
| `src/ai/trainer.py` | Script to load `data/gestures.csv`, train a Random Forest model, and write the model pickle file to disk. |
| `src/ai/data_collector.py` | Logs training data vectors into the CSV format. |

## Working Gestures and Actions

### Normal Mode (Default Control Mode)
- **`fist`** $\rightarrow$ Transitions computer cursor control to `"freeze"` state (stops pointer movement).
- **`open_hand`** $\rightarrow$ Transitions computer cursor control to `"move"` state (default cursor tracking).
- **`point`** $\rightarrow$ Transitions computer cursor control to `"precision"` state (tracks cursor at half-speed).
- **`three_fingers`** $\rightarrow$ Opens the Windows OS virtual on-screen keyboard (`win + ctrl + o`).
- **`four_fingers`** $\rightarrow$ Takes a screenshot via Windows Snipping Tool (`win + shift + s`).
- **`thumbs_up`** $\rightarrow$ Increases system audio volume (`volumeup`).
- **`thumbs_down`** $\rightarrow$ Decreases system audio volume (`volumedown`).
- **`l_shape`** $\rightarrow$ Triggers right-click context menu.
- **`pinch`** $\rightarrow$ Triggers mouse left-click.
- **`two_fingers`** (Hold for 2.0s) $\rightarrow$ Switches active application mode from **Normal** to **Drawing**.

### Drawing Mode (Transparent Overlay Drawing Canvas)
- **`pinch`** $\rightarrow$ Switches active application mode from **Drawing** back to **Normal**.
- **`fist`** $\rightarrow$ Clears the drawing overlay canvas (`clear_canvas`).
- **`open_hand`** $\rightarrow$ Lifts the drawing pen up (`pen_up`).
- **`point`** $\rightarrow$ Lowers the drawing pen to write/draw (`pen_down`).
- **`two_fingers`** $\rightarrow$ Cyclically changes current brush color (`change_color`).
- **`three_fingers`** $\rightarrow$ Increases brush size (`brush_size_up`).
- **`four_fingers`** $\rightarrow$ Saves the current canvas drawing to an image file (`save_drawing`).
- **`thumbs_up`** $\rightarrow$ Performs an undo action (`undo`).
- **`thumbs_down`** $\rightarrow$ Performs a redo action (`redo`).
- **`l_shape`** $\rightarrow$ Toggles eraser brush mode (`erase_mode`).

---

## Key Logic and Configurations

### 1. Buffer Size and Threshold
- **Buffer Size**: Keeps track of the last **10** raw prediction inputs.
- **Confirmation Threshold**: A gesture requires at least **6 out of 10** votes in the buffer to be confirmed (and cannot be `"unknown"`).
- **Unknown Buffer Clearing**: If the most common prediction remains `"unknown"` for **5 consecutive** cycles, the buffer is fully cleared.

### 2. Pinch Threshold Values
- **Trigger Distance**: `< 60` pixels between thumb tip (landmark 4) and index finger tip (landmark 8).
- **Index Finger Curl Validation**: Absolute y-distance between index fingertip (landmark 8) and index PIP joint (landmark 6) must be less than **30** pixels.
- **Release Distance**: `> 80` pixels.
- **Safety Restriction**: Pinch is ignored if the confirmed gesture is `"fist"`.

### 3. Gesture Cooldowns (Seconds)
- `"open_hand"`: 2.0
- `"point"`: 2.0
- `"fist"`: 2.0
- `"two_fingers"`: 0.1
- `"three_fingers"`: 3.0
- `"four_fingers"`: 3.0
- `"thumbs_up"`: 2.0
- `"thumbs_down"`: 2.0
- `"l_shape"`: 2.0
- `"pinch"`: 2.0

### 4. Coordinate Normalization Method
Hand landmark coordinates are normalized relative to the wrist (landmark 0). For each of the 21 landmarks detected by MediaPipe:
$$\text{Normalized } X_i = X_i - X_{\text{wrist}}$$
$$\text{Normalized } Y_i = Y_i - Y_{\text{wrist}}$$
This ensures gesture predictions are invariant to translation (where the hand is located in the webcam frame).

---

## DO NOT CHANGE

The following files are locked and should not be modified:
* `src/ai/predictor.py`
* `src/ai/trainer.py`
* `src/ai/data_collector.py`
* `src/camera/hand_tracker.py`
* `src/control/mouse_controller.py`
* `record_gestures.py`
* `data/gestures.csv`
* `data/gesture_model.pkl`
