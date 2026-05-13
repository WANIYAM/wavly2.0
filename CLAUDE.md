# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wavly is an AI-powered touchless computer control system that uses hand gestures and computer vision to control a computer. The system captures webcam input, processes hand gestures using MediaPipe, and translates them into automated actions using PyAutoGUI.

## Tech Stack

- **Python 3.10+** - Core language
- **OpenCV** - Video capture and image processing
- **MediaPipe** - Hand landmark detection and tracking
- **PyAutoGUI** - System automation (mouse, keyboard control)
- **scikit-learn** - Gesture classification and ML models
- **PyQt6** - GUI framework for control interface
- **NumPy** - Numerical operations and array processing

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

### Testing
```bash
# When tests are added
pytest tests/
```

## Project Architecture

### Module Structure

```
src/
├── gesture_recognition/  # Hand tracking and gesture detection
│   ├── hand_tracker.py      # MediaPipe hand tracking wrapper
│   ├── gesture_classifier.py # ML-based gesture classification
│   └── gesture_config.py     # Gesture definitions and mappings
├── ui/                    # PyQt6 GUI components
│   ├── main_window.py        # Main application window
│   ├── camera_widget.py      # Webcam feed display
│   └── settings_dialog.py    # Configuration UI
├── automation/            # System automation logic
│   ├── action_executor.py    # PyAutoGUI action wrapper
│   └── gesture_mapper.py     # Maps gestures to actions
└── utils/                 # Helper functions
    ├── camera.py             # Camera initialization and management
    └── config_loader.py      # Configuration file handling
```

### Key Design Patterns

1. **Pipeline Architecture**: Webcam → Hand Detection → Gesture Recognition → Action Execution
2. **Separation of Concerns**: 
   - `gesture_recognition/` handles CV and ML
   - `automation/` handles system control
   - `ui/` handles user interface
3. **Configuration-Driven**: Gesture-to-action mappings stored in `config/` for easy customization

### Data Flow

1. Camera captures frame (OpenCV)
2. MediaPipe detects hand landmarks
3. Gesture classifier identifies gesture from landmarks
4. Gesture mapper translates gesture to action
5. Action executor performs system automation (PyAutoGUI)
6. UI displays feedback to user

## Development Guidelines

### Adding New Gestures

1. Define gesture in `src/gesture_recognition/gesture_config.py`
2. Add training data or detection logic in `gesture_classifier.py`
3. Map gesture to action in `src/automation/gesture_mapper.py`
4. Test with `python main.py`

### Camera and MediaPipe

- MediaPipe hands model runs on CPU by default
- For better performance, consider GPU acceleration
- Camera resolution affects processing speed (default: 640x480)
- Hand detection confidence threshold: 0.5 (adjustable)

### System Automation Safety

- PyAutoGUI has built-in failsafe (move mouse to corner to abort)
- Add delays between actions to prevent system overload
- Test automation actions in safe environment first
- Consider adding confirmation dialogs for destructive actions

### Performance Considerations

- Target: 30 FPS for smooth gesture recognition
- Optimize by reducing frame processing resolution
- Use frame skipping if needed (process every Nth frame)
- Profile with `cProfile` if performance issues arise

## Common Commands

```bash
# Run application
python main.py

# Install new dependency
pip install <package>
pip freeze > requirements.txt

# Run tests (when implemented)
pytest tests/ -v

# Check code style (if linting added)
flake8 src/
black src/
```

## Configuration

Configuration files in `config/` directory:
- `gesture_mappings.json` - Maps gestures to system actions
- `camera_settings.json` - Camera resolution, FPS, device ID
- `model_config.json` - ML model parameters and paths

## Troubleshooting

### Camera Issues
- Ensure webcam is not in use by another application
- Check camera permissions in system settings
- Try different camera device IDs (0, 1, 2...)

### MediaPipe Issues
- Ensure good lighting for hand detection
- Keep hand within camera frame
- Adjust detection confidence threshold if needed

### PyAutoGUI Issues
- Disable failsafe for testing: `pyautogui.FAILSAFE = False`
- Add delays between actions: `pyautogui.PAUSE = 0.1`
- Test on secondary monitor if available
