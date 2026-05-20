# Wavly 2.0
**AI-Powered Touchless Computer Control System**

Control your computer with hand gestures using computer vision and machine learning. No physical contact required.

---

## Overview
Wavly is an intelligent gesture recognition system that translates hand movements into computer actions. Using a standard webcam, MediaPipe hand tracking, and machine learning, Wavly enables touchless control of your mouse, keyboard, and system functions through natural hand gestures.

The system captures real-time video, detects hand landmarks, classifies gestures using a trained machine learning model, and executes corresponding system actions (such as cursor control, application hotkeys, and mode switching) with PyAutoGUI automation.

---

## Project Status

### Completed Phases
- **✅ Phase 1 — Foundation**: Core MediaPipe tracking integration, hand landmark parsing, and normalized coordinate processing.
- **✅ Phase 2 — Mouse Control**: Cursor movement tracking, coordinate smoothing (exponential weighted moving average), and click handling.
- **✅ Phase 3 — Gesture Recognition (99.66% accuracy)**: Custom gesture classifier utilizing a RandomForest classifier model trained on a 10-gesture dataset.
- **✅ Phase 5 — Context Awareness**: Dynamic detection of foreground active windows and context-sensitive application profiles.
- **✅ Phase 6 — UI Overlay**: Transparent overlay drawing canvas (Drawing Mode) with custom painter tools (brush size, colors, erase, undo/redo).
- **✅ Phase 8 — Presentation Mode**: Custom PowerPoint presentation control actions with transition delays.

### Coming Soon
- **🚧 Voice Hybrid**: Integrating voice command recognition alongside hand gestures for hybrid inputs.
- **🚧 Air Drawing**: Advanced 3D drawing paths and gesture-based shape recognition.

---

## Project Health
- **Score: 8.5 / 10**

---

## All 10 Gestures & Default Actions

Wavly recognizes **10 distinct hand gestures**. In the **Default System Profile (Normal Mode)**, these gestures control mouse movement, clicking, scrolling, and system utilities:

1. **`open_hand`** (Label 1) → Normal Cursor Mode (Default pointer tracking)
2. **`point`** (Label 2) → Precise Cursor Mode (Slower, fine-grain mouse control)
3. **`fist`** (Label 0) → Freeze Cursor (Stops all mouse movement)
4. **`two_fingers`** (Label 3) → Scroll Mode (Triggers vertical scroll based on hand movement / Hold for 2 seconds to enter **Drawing Mode**)
5. **`pinch`** (Label 9) → Left Mouse Click (Exits **Drawing Mode** if active)
6. **`l_shape`** (Label 8) → Right Mouse Click
7. **`three_fingers`** (Label 4) → Open On-Screen Keyboard (`Win + Ctrl + O`)
8. **`four_fingers`** (Label 5) → Take Screenshot (`Win + Shift + S`)
9. **`thumbs_up`** (Label 6) → Volume Up
10. **`thumbs_down`** (Label 7) → Volume Down

---

## Context-Aware Application Profiles

Wavly automatically detects the active foreground application and switches gesture mappings dynamically:

### Chrome Gestures
- **`two_fingers`** → Scroll up (`pyautogui.scroll(3)`)
- **`l_shape`** → Open new tab (`Ctrl + T`)
- **`four_fingers`** → Close current tab (`Ctrl + W`)
- **`thumbs_up`** → Navigate forward (`Alt + Right Arrow`)
- **`thumbs_down`** → Navigate backward (`Alt + Left Arrow`)
- **`pinch`** → Zoom in (`Ctrl + =`)
- **`fist`** → Zoom out (`Ctrl + -`)

### VLC Gestures
- **`pinch`** → Play / Pause (`Spacebar`)
- **`two_fingers`** → Fast forward seek (`Shift + Right Arrow`)
- **`l_shape`** → Rewind seek (`Shift + Left Arrow`)
- **`thumbs_up`** → Volume up (`volumeup`)
- **`thumbs_down`** → Volume down (`volumedown`)
- **`four_fingers`** → Toggle fullscreen (`F`)
- **`fist`** → Stop playback (`S`)
- **`three_fingers`** → Mute / Unmute (`M`)

### PowerPoint Gestures
- **`two_fingers`** → Next slide (`Right Arrow`)
- **`l_shape`** → Previous slide (`Left Arrow`)
- **`four_fingers`** → Start presentation / slideshow from beginning (`F5`)
- **`fist`** → Exit presentation / slideshow (`Escape`)
- **`thumbs_up`** → Zoom in (`Ctrl + =`)
- **`thumbs_down`** → Zoom out (`Ctrl + -`)
- **`three_fingers`** → Black screen toggle (`B`)
- **`pinch`** → Hold `Ctrl` (useful for pointer controls)

---

## Tech Stack & Versions

- **Python 3.12.10**
- **mediapipe** == `0.10.14` (Real-time hand tracking and landmark extraction)
- **opencv-python** == `4.13.0.92` (Video capture and image processing)
- **numpy** == `2.4.0` (Array manipulations and coordinates processing)
- **pandas** == `2.2.3` (Dataset formatting and CSV loading)
- **scikit-learn** == `1.8.0` (Machine learning for gesture classification)
- **PyQt6** == `6.11.0` (GUI application overlay and canvas painting)
- **PyAutoGUI** == `0.9.54` (System automation and hotkey execution)

---

## How to Install & Run

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wavly2.0
   ```

2. **Create virtual environment**
   - Windows:
     ```powershell
     python -m venv venv
     ```
   - Linux/macOS:
     ```bash
     python3 -m venv venv
     ```

3. **Activate virtual environment**
   - Windows:
     ```powershell
     venv\Scripts\activate
     ```
   - Linux/macOS:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

---

## How to Record New Gestures

To collect training dataset for new gestures or to expand existing classes:

```bash
python record_gestures.py
```

### Controls in Gesture Recorder:
- Press keys **`0-9`** to set the target gesture label (e.g., `0` for fist, `1` for open_hand, etc.)
- Press **`R`** to toggle recording on/off (real-time landmark data will be appended to `data/gestures.csv` when your hand is visible)
- Press **`Q`** to quit and save your session's final sample count.

---

## How to Retrain Model

To train the machine learning model on the collected CSV data:

```bash
python src/ai/trainer.py
```

This trains a `RandomForestClassifier` using features from `data/gestures.csv` and outputs the updated model to `data/gesture_model.pkl`. It displays overall dataset statistics, confusion matrix, and accuracy breakdown per gesture.

---

## Diagnostic Tools

You can verify separate components using the following test utilities:
* **Active Window Context Detection Check**:
  ```bash
  python test_context.py
  ```
* **Raw Model Inference & Confidence HUD**:
  ```bash
  python test_gestures.py
  ```

---

## Project Structure

Here is the complete project directory structure showing all files:

```
wavly2.0/
├── config/                      # Configuration files directory (currently empty)
├── data/                        # Training datasets and machine learning model files
│   ├── gesture_model.pkl        # Trained RandomForest classifier model
│   └── gestures.csv             # Collected dataset containing normalized hand landmarks
├── models/                      # Machine learning models directory (currently empty)
├── src/                         # Core source code of Wavly
│   ├── __init__.py
│   ├── ai/                      # Machine learning components
│   │   ├── __init__.py
│   │   ├── data_collector.py    # Buffered landmarks parser and CSV writer
│   │   ├── predictor.py         # Real-time gesture prediction and confidence checker
│   │   └── trainer.py           # RandomForest model trainer with validation reports
│   ├── automation/              # System automation wrappers
│   │   └── __init__.py
│   ├── camera/                  # Camera frame capture and tracking
│   │   ├── __init__.py
│   │   └── hand_tracker.py      # MediaPipe hand detection and tracking implementation
│   ├── control/                 # Input control and actions execution
│   │   ├── __init__.py
│   │   ├── app_profiles.py      # Application specific profiles (Chrome, VLC, PowerPoint)
│   │   ├── context_detector.py  # Tracks active foreground application
│   │   ├── gesture_mapper.py    # Maps gestures to profile actions or drawing modes
│   │   └── mouse_controller.py  # Coordinates screen cursor movement and clicking
│   ├── gesture_recognition/     # Core gesture module init
│   │   └── __init__.py
│   ├── gestures/                # Geometric gesture definitions
│   │   └── __init__.py
│   ├── ui/                      # PyQt6 user interface components
│   │   ├── __init__.py
│   │   ├── overlay_window.py    # Fullscreen overlay painting canvas
│   │   └── vision_thread.py     # Worker thread for non-blocking camera/hand tracking
│   └── utils/                   # General helper utilities
│       └── __init__.py
├── tests/                       # Testing module directory (currently empty)
├── .gitignore                   # Git ignore configurations
├── CHECKPOINT.md                # Development checkpoint logs
├── CLAUDE.md                    # Coding standards and development guidelines
├── README.md                    # Project documentation (this file)
├── main.py                      # Application entry point
├── record_gestures.py           # Gesture dataset recording utility
├── requirements.txt             # Pinned project dependencies
├── test_context.py              # Debug utility to test active app detection
└── test_gestures.py             # Debug utility to display raw gesture prediction confidence
```

---

## Contributing

Contributions are welcome! Please follow the guidelines in `CLAUDE.md` for development standards and project architecture.

---

## License

[Add your license here]

---

## Acknowledgments

Built with MediaPipe by Google for hand tracking, PyQt6 for overlay graphics, and PyAutoGUI for system automation.