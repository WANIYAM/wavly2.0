# Wavly — AI-Powered Gesture & Voice Interface
**Control your computer with hand gestures and voice commands**

Wavly is an intelligent, touchless user interface system that translates real-time hand movements and spoken voice commands into system automation inputs. Using a standard webcam, MediaPipe hand tracking, PyAudio microphone capture, and machine learning, Wavly maps natural physical interactions to keyboard hotkeys, cursor movements, clicks, and application controls. This enables hands-free operation of browsers, media players, presentation software, and active drawing tools.

---

## Project Status

### Completed Phases
- **✅ Phase 1 — Foundation**: Core MediaPipe tracking integration, hand landmark parsing, and normalized coordinate processing.
- **✅ Phase 2 — Mouse Control**: Cursor movement tracking, coordinate smoothing (exponential weighted moving average), and click handling.
- **✅ Phase 3 — Gesture Recognition (99.66% accuracy)**: Custom gesture classifier utilizing a RandomForest classifier model trained on a 10-gesture dataset.
- **✅ Phase 5 — Context Awareness**: Dynamic detection of foreground active windows and context-sensitive application profiles.
- **✅ Phase 6 — UI Overlay**: Transparent overlay drawing canvas (Drawing Mode) with custom painter tools (brush size, colors, erase, undo/redo).
- **✅ Phase 8 — Presentation Mode**: Custom PowerPoint presentation control actions with transition delays.
- **✅ Phase 9 — Voice Integration**: Threaded background speech command listener utilizing Google Web Speech API and PyAudio to trigger system automation.

---

## All 11 Gestures & Default Actions

Wavly recognizes **11 distinct hand gestures**. In the **Default System Profile (Normal Mode)**, these gestures control mouse movement, clicking, scrolling, and system utilities:

1. **`open_hand`** (Label 1) → Normal Cursor Mode (Default pointer tracking)
2. **`point`** (Label 2) → Precise Cursor Mode (Slower, fine-grain mouse control)
3. **`fist`** (Label 0) → Freeze Cursor (Stops all mouse movement)
4. **`two_fingers`** (Label 3) → Scroll Mode (Triggers vertical scroll based on hand movement / Hold for 2 seconds to enter **Drawing Mode**)
5. **`pinch`** (Label 9) → Left Mouse Click (Exits **Drawing Mode** if active)
6. **`l_shape`** (Label 8) → Right Mouse Click
7. **`three_fingers`** (Label 4) → Open On-Screen Keyboard (`Win + Ctrl + O`)
8. **`four_fingers`** (Label 5) → Capture Screenshot to Clipboard (direct grab, no Snipping Tool; shows an on-screen confirmation)
9. **`thumbs_up`** (Label 6) → Volume Up
10. **`thumbs_down`** (Label 7) → Volume Down

---

## All 20 Voice Commands

Speak clearly to execute any of the following 20 voice commands:

- **`click`** → Left mouse click
- **`right click`** → Right mouse click
- **`scroll up`** → Scroll mouse wheel up (`pyautogui.scroll(5)`)
- **`scroll down`** → Scroll mouse wheel down (`pyautogui.scroll(-5)`)
- **`screenshot`** → Take screenshot (`Win + Shift + S`)
- **`volume up`** → System volume up
- **`volume down`** → System volume down
- **`open chrome`** → Launch Google Chrome browser
- **`open notepad`** → Launch Notepad application
- **`switch tab`** → Switch application tabs (`Ctrl + Tab`)
- **`close tab`** → Close active tab (`Ctrl + W`)
- **`zoom in`** → Zoom page/view in (`Ctrl + =`)
- **`zoom out`** → Zoom page/view out (`Ctrl + -`)
- **`new tab`** → Open new application tab (`Ctrl + T`)
- **`go back`** → Browser/navigation back (`Alt + Left Arrow`)
- **`go forward`** → Browser/navigation forward (`Alt + Right Arrow`)
- **`next slide`** → PowerPoint next slide (`Right Arrow`)
- **`previous slide`** → PowerPoint previous slide (`Left Arrow`)
- **`start presentation`** → PowerPoint slide show start (`F5`)
- **`stop presentation`** → PowerPoint exit slide show (`Escape`)

### Natural Language & Aliases

Wavly supports fuzzy keyword matching and synonyms. You don't have to say the exact phrase—as long as your sentence contains the keyword, it will execute the command. Some examples:

- **"chrome"** or **"browser"** → Maps to `open chrome`
- **"notepad"** or **"editor"** → Maps to `open notepad`
- **"new"**, **"close"**, **"switch"** → Maps to tab controls
- **"next"**, **"previous"** → Maps to slide controls
- **"forward"**, **"back"** → Maps to navigation
- **"louder"**, **"quieter"** → Maps to volume controls
- **"snap"** or **"print screen"** → Maps to `screenshot`

*Example: Saying "Wavly, pull up the browser please" will successfully detect "browser" and open Chrome.*

### Voice Session Management

#### Wake Words

Wavly starts in **standby mode** and activates when it hears the wake word. Because Google Web Speech API often mishears "Wavly", the following **26 fuzzy/phonetic variants** are all accepted:

`wavly` · `wavy` · `wavely` · `wably` · `waverly` · `waveely` · `babli` · `bably` · `baby` · `devli` · `wobbly` · `wavley` · `wally` · `wevley` · `wifely` · `waffly` · `wavvy` · `wabli` · `waveli` · `wahli` · `wovly` · `wobly` · `webly` · `waylee` · `wabley`

#### Goodbye / Session-End Phrases

To end an active session and return Wavly to standby, say any of these phrases (substring matching, so surrounding words like "okay" or "please" won't break it):

- **Phrases**: `goodbye` · `goodbye wavly` · `stop listening` · `shut down` · `deactivate` · `bye bye` · `see you` · `see ya` · `go to sleep` · `power down` · `end session` · `that's all` · `that's it` · `thank you wavly` · `thanks wavly` · `goodnight` · `goodnight wavly` · `good night`
- **Keywords** (whole-word match only): `bye` · `sleep` · `stop` (guarded — won't trigger inside "stop presentation")

Goodbye triggers a **randomized farewell response** (e.g. *"See you soon, sir."*, *"Standing by, sir."*, *"Going to sleep, sir. Say my name when you need me."*).

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
- **SpeechRecognition** == `3.16.1` (Vocal capture parsing and API interaction)
- **PyAudio** == `0.2.14` (Interface to PortAudio for input stream handling)

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

To collect a training dataset for new gestures or to expand existing classes:

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
* **Voice Phrase Transcription Test**:
  ```bash
  python test_voice.py
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
│   │   ├── mouse_controller.py  # Coordinates screen cursor movement and clicking
│   │   ├── voice_controller.py  # Threaded background speech listener
│   │   └── voice_mapper.py      # Maps verbal keywords to PyAutoGUI/OS actions
│   ├── gesture_recognition/     # Core gesture module init
│   │   └── __init__.py
│   ├── gestures/                # Geometric gesture definitions
│   │   └── __init__.py
│   ├── ui/                      # PyQt6 user interface components
│   │   ├── __init__.py
│   │   ├── overlay_window.py    # Fullscreen overlay painting canvas
│   │   └── vision_thread.py     # Worker thread for camera loop & voice processing
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
├── test_gestures.py             # Debug utility to display raw gesture prediction confidence
└── test_voice.py                # Debug utility to test microphone voice recognition
```

---

## Coming Soon
- **🚧 Voice Hybrid**: Combining spoken commands with hand position tracking for multi-modal context inputs.
- **🚧 Air Drawing**: Full 3D path drawing coordinates and vocal shape stroke tools.

---

## Contributing

Contributions are welcome! Please follow the guidelines in `CLAUDE.md` for development standards and project architecture.

---

## License

[Add your license here]

---

## Acknowledgments

Built with MediaPipe by Google for hand tracking, PyQt6 for overlay graphics, and PyAutoGUI for system automation.