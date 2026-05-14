# Wavly 2.0

**AI-Powered Touchless Computer Control System**

Control your computer with hand gestures using computer vision and machine learning. No physical contact required.

---

## Overview

Wavly is an intelligent gesture recognition system that translates hand movements into computer actions. Using your webcam, MediaPipe hand tracking, and machine learning, Wavly enables touchless control of your mouse, keyboard, and system functions through natural hand gestures.

The system captures real-time video, detects hand landmarks, classifies gestures using trained ML models, and executes corresponding system actions with PyAutoGUI automation.

---

## Gestures & Actions

Wavly recognizes **10 distinct hand gestures** divided into two categories:

### Mode Gestures (Cursor Control)
These gestures change how your cursor behaves:

1. **Fist** → Freeze cursor (stops all movement)
2. **Open Hand** → Normal cursor mode (default tracking)
3. **Point** (index finger extended) → Precise cursor mode (fine control)
4. **Two Fingers** (index + middle) → Scroll mode

### Action Gestures (System Commands)
These gestures execute system actions with a 1-second cooldown:

5. **Three Fingers** → Open on-screen keyboard (Win+Ctrl+O)
6. **Four Fingers** → Take screenshot (Win+Shift+S)
7. **Thumbs Up** → Volume up
8. **Thumbs Down** → Volume down
9. **Pinch** (thumb + index) → Left mouse click
10. **L-Shape** (thumb + middle) → Right mouse click

All gestures require 3 consecutive frames of detection for stabilization, preventing accidental triggers.

---

## Tech Stack

- **Python 3.10+** - Core programming language
- **OpenCV** - Video capture and image processing
- **MediaPipe** - Real-time hand landmark detection and tracking
- **PyAutoGUI** - System automation (mouse, keyboard, hotkeys)
- **scikit-learn** - Machine learning for gesture classification
- **PyQt6** - GUI framework for control interface
- **NumPy** - Numerical operations and array processing
- **Pandas** - Data handling for training datasets

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Webcam
- Windows OS (for current hotkey mappings)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wavly2.0
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

---

## Project Status

**Current Phase: Phase 3 Complete ✓**

### Completed
- ✅ Phase 1: Core hand tracking and gesture detection
- ✅ Phase 2: Gesture classification and action mapping
- ✅ Phase 3: ML model training and data collection pipeline

### Coming Next
- 🚧 Phase 4: PyQt6 GUI interface with live camera feed
- 🚧 Phase 5: Settings panel and gesture customization
- 🚧 Phase 6: Performance optimization and testing

---

## Project Structure

```
wavly2.0/
├── src/
│   ├── ai/                      # Machine learning components
│   │   ├── data_collector.py   # Collect training data from gestures
│   │   ├── trainer.py           # Train ML models on gesture data
│   │   └── predictor.py         # Real-time gesture prediction
│   ├── camera/                  # Video capture and hand tracking
│   │   ├── capture.py           # Webcam initialization and frame capture
│   │   └── hand_tracker.py      # MediaPipe hand landmark detection
│   ├── gestures/                # Gesture detection logic
│   │   └── gesture_detector.py  # Geometric gesture detection (pinch, scroll)
│   ├── control/                 # Action execution
│   │   ├── gesture_mapper.py    # Maps gestures to system actions
│   │   └── mouse_controller.py  # Cursor movement and control modes
│   ├── ui/                      # PyQt6 GUI components (Phase 4)
│   ├── automation/              # PyAutoGUI wrappers
│   └── utils/                   # Helper functions
├── config/                      # Configuration files
├── data/                        # Training datasets
├── models/                      # Trained ML models
├── tests/                       # Unit tests
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
└── CLAUDE.md                    # Development guidelines
```

---

## Usage

1. Launch the application with `python main.py`
2. Position your hand in front of the webcam
3. Perform gestures to control your computer
4. Use mode gestures to switch cursor behavior
5. Use action gestures to execute system commands

**Tips:**
- Ensure good lighting for accurate hand detection
- Keep your hand within the camera frame
- Wait for gesture stabilization (3 frames) before actions execute
- Move mouse to screen corner to trigger PyAutoGUI failsafe if needed

---

## Configuration

Configuration files in `config/` directory allow customization of:
- Gesture-to-action mappings
- Camera settings (resolution, FPS, device ID)
- ML model parameters
- Detection thresholds and cooldown timers

---

## Contributing

Contributions are welcome! Please follow the guidelines in `CLAUDE.md` for development standards and project architecture.

---

## License

[Add your license here]

---

## Acknowledgments

Built with MediaPipe by Google for hand tracking and PyAutoGUI for system automation.
0 = fist
1 = open_hand
2 = peace
3 = point
4 = two_fingers
5 = three_fingers
6 = four_fingers
7 = thumbs_up
8 = thumbs_down
9 = l_shape