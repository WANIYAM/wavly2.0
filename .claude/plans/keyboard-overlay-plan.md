# Overlay Keyboard Implementation Plan

## Overview
Add a new "keyboard" mode with a transparent full-width QWERTY overlay. Users type by dwelling (0.5s) on keys with either index finger. Left-hand gestures provide Shift (fist) and Ctrl (open_palm) modifiers (momentary/hold). Entry: any hand three_fingers from normal mode. Exit: right-hand three_fingers.

## User Decisions (Confirmed)
- **Keys:** 26 letters + Space, Backspace, Enter (Shift = capitals)
- **Modifiers:** Momentary (hold left fist/open_palm while right index dwells)
- **Cursors:** Both index fingers dwell-type independently
- **Invoke:** Any three_fingers from normal mode; exit on right-hand three_fingers

## Architecture Changes Required

### 1. Two-Hand Tracking with Handedness (`src/camera/hand_tracker.py`)
**Current limitation:** `max_num_hands=1`, returns only `multi_hand_landmarks[0]`, discards `multi_handedness`.

**Changes:**
- Modify `__init__`: keep `max_num_hands` as a parameter (will pass 2 from vision_thread)
- Modify `detect()` signature: return `List[Tuple[landmarks, handedness_label]]` instead of single landmarks
  - Extract both `results.multi_hand_landmarks` and `results.multi_handedness`
  - Pair them: `[(landmarks, handedness.classification[0].label) for landmarks, handedness in zip(...)]`
  - `handedness_label` is "Left" or "Right" (MediaPipe's camera-mirrored labels)
  - Return empty list if no hands detected
- Keep `get_landmark_list()` and `draw()` as-is (they operate on single landmarks objects)

**Backward compatibility:** Vision thread will handle the new return format; existing single-hand code paths won't break (just take first element).

---

### 2. Vision Thread: Dual-Hand Processing (`src/ui/vision_thread.py`)

**Current:** Processes one hand, emits `draw_event` dict for drawing mode.

**Changes:**

#### New signal:
```python
keyboard_event = pyqtSignal(dict)  # Per-frame keyboard state
```

#### New instance variables (line ~54):
```python
self.keyboard_mode = False  # New mode flag
```

#### Modify `__init__` (line 33):
```python
self.hand_tracker = HandTracker(
    max_hands=2,  # <-- Change from 1 to 2
    detection_confidence=0.7,
    tracking_confidence=0.7
)
```

#### New helper method `_classify_hands(hands_data)`:
```python
def _classify_hands(self, hands_data):
    """Split detected hands into left and right.
    MediaPipe labels are camera-mirrored: 'Left' in feed = user's right hand.
    Returns: (left_hand_data, right_hand_data) where each is (landmarks, label) or None.
    """
    left, right = None, None
    for landmarks, label in hands_data:
        # MediaPipe 'Left' = user's RIGHT hand (mirrored)
        if label == "Left":
            right = (landmarks, label)
        else:
            left = (landmarks, label)
    return left, right
```

#### Main `run()` loop changes (line 90-326):

**After `landmarks = self.hand_tracker.detect(frame)` (line 117):**
```python
hands_data = self.hand_tracker.detect(frame)  # Now returns list of (landmarks, handedness)
frame_height, frame_width = frame.shape[:2]

# Keyboard mode gets its own branch
if self.keyboard_mode:
    self._process_keyboard_frame(hands_data, frame_width, frame_height)
    # Emit "No Hand" for HUD so it doesn't show stale gestures
    self.gesture_detected.emit("Keyboard Mode")
    self.frame_ready.emit(frame.copy())
    self.msleep(5)
    continue

# Normal/Drawing modes: use first hand only (backward compat)
landmarks = hands_data[0][0] if hands_data else None
# ... rest of existing logic unchanged
```

**New method `_process_keyboard_frame()`:**
```python
def _process_keyboard_frame(self, hands_data, frame_width, frame_height):
    """Process both hands for keyboard mode and emit keyboard_event."""
    left_hand, right_hand = self._classify_hands(hands_data)
    
    # Build per-frame keyboard state dict
    kbd = {
        "left_present": left_hand is not None,
        "right_present": right_hand is not None,
        "frame_w": frame_width,
        "frame_h": frame_height,
    }
    
    # Left hand: extract gesture + index fingertip position
    if left_hand:
        landmarks, _ = left_hand
        raw_lm = [(lm.x, lm.y) for lm in landmarks.landmark]
        wrist_x, wrist_y = raw_lm[0]
        norm_lm = [(x - wrist_x, y - wrist_y) for x, y in raw_lm]
        left_gesture = self.gesture_predictor.predict(norm_lm)
        
        lm_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
        left_index_tip = lm_list[8]  # Index fingertip
        
        kbd["left_gesture"] = left_gesture
        kbd["left_x"] = left_index_tip[0]
        kbd["left_y"] = left_index_tip[1]
    else:
        kbd["left_gesture"] = None
        kbd["left_x"] = 0
        kbd["left_y"] = 0
    
    # Right hand: same extraction
    if right_hand:
        landmarks, _ = right_hand
        raw_lm = [(lm.x, lm.y) for lm in landmarks.landmark]
        wrist_x, wrist_y = raw_lm[0]
        norm_lm = [(x - wrist_x, y - wrist_y) for x, y in raw_lm]
        right_gesture = self.gesture_predictor.predict(norm_lm)
        
        lm_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
        right_index_tip = lm_list[8]
        
        kbd["right_gesture"] = right_gesture
        kbd["right_x"] = right_index_tip[0]
        kbd["right_y"] = right_index_tip[1]
    else:
        kbd["right_gesture"] = None
        kbd["right_x"] = 0
        kbd["right_y"] = 0
    
    self.keyboard_event.emit(kbd)
    
    # Check exit gesture: right hand three_fingers
    if kbd["right_gesture"] == "three_fingers":
        # Debounce: only exit once
        if not hasattr(self, '_kbd_exit_triggered'):
            self._kbd_exit_triggered = True
            self.keyboard_mode = False
            self.mode_changed.emit("normal")
            print("[MODE] Keyboard → Normal")
            if self.voice_responder:
                self.voice_responder.system_speak("Keyboard closed")
    else:
        self._kbd_exit_triggered = False
```

**Mode entry:** Handled in gesture_mapper (three_fingers returns "keyboard"), vision_thread listens for mode change.

---

### 3. Gesture Mapper: Keyboard Mode Entry (`src/control/gesture_mapper.py`)

**Changes:**

#### Add mode flag (line 9):
```python
self.keyboard_mode = False
```

#### Modify `execute()` normal-mode branch (line 112-115):
Replace:
```python
elif gesture_name == "three_fingers":
    pyautogui.hotkey('win', 'ctrl', 'o')
    print("[GESTURE] three_fingers → keyboard")
    return "executed"
```

With:
```python
elif gesture_name == "three_fingers":
    self.keyboard_mode = True
    print("[MODE] Normal → Keyboard")
    if self.voice_responder:
        self.voice_responder.system_speak("Keyboard mode on")
    return "keyboard"
```

#### Add helper methods (end of file):
```python
def is_keyboard_mode(self):
    return self.keyboard_mode

def set_keyboard_mode(self, enabled):
    self.keyboard_mode = enabled
```

---

### 4. Overlay Window: Keyboard Rendering & Dwell (`src/ui/overlay_window.py`)

**Changes:**

#### New instance variables (line ~180):
```python
# Keyboard mode state
self.keyboard_active = False
self.kbd_layout = self._build_keyboard_layout()  # Key rects + labels

# Per-hand dwell state
self.left_dwell_key = None
self.left_dwell_start = 0.0
self.left_pointer = None
self.left_smooth_x = OneEuroFilter()
self.left_smooth_y = OneEuroFilter()

self.right_dwell_key = None
self.right_dwell_start = 0.0
self.right_pointer = None
self.right_smooth_x = OneEuroFilter()
self.right_smooth_y = OneEuroFilter()

self.kbd_dwell_time = 0.5  # seconds to trigger key press

# Modifier state (from left hand gestures)
self.shift_active = False
self.ctrl_active = False
```

#### Connect signal (line 218):
```python
self.vision_thread.keyboard_event.connect(self.on_keyboard_event)
```

#### New method `_build_keyboard_layout()`:
```python
def _build_keyboard_layout(self):
    """Build QWERTY layout: 3 rows of letters + bottom row with Space/Backspace/Enter.
    Returns list of dicts: {"char": str, "rect": QRectF, "shift_char": str}.
    Full-width keyboard, transparent background, vertically centered.
    """
    rows = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
    ]
    
    # Keyboard dimensions
    kbd_height = 280
    key_height = 60
    row_gap = 10
    col_gap = 8
    side_margin = 40
    
    # Vertical centering
    kbd_y = (self.screen_height - kbd_height) / 2.0
    
    keys = []
    current_y = kbd_y + 20
    
    for row_idx, row in enumerate(rows):
        num_keys = len(row)
        row_width = self.screen_width - 2 * side_margin
        key_width = (row_width - (num_keys - 1) * col_gap) / num_keys
        
        # Center offset for each row (optional stagger)
        offset_x = side_margin
        if row_idx == 1:
            offset_x += key_width * 0.25  # Slight stagger for home row
        elif row_idx == 2:
            offset_x += key_width * 0.5   # Larger stagger for bottom row
        
        current_x = offset_x
        for char in row:
            rect = QRectF(current_x, current_y, key_width, key_height)
            keys.append({
                "char": char.lower(),
                "shift_char": char.upper(),
                "rect": rect,
                "is_special": False,
            })
            current_x += key_width + col_gap
        
        current_y += key_height + row_gap
    
    # Bottom row: Space (wide), Backspace, Enter
    current_y += 10
    space_width = row_width * 0.55
    other_width = (row_width - space_width - 2 * col_gap) / 2.0
    
    current_x = side_margin
    keys.append({
        "char": " ",
        "label": "SPACE",
        "shift_char": " ",
        "rect": QRectF(current_x, current_y, space_width, key_height),
        "is_special": True,
    })
    current_x += space_width + col_gap
    
    keys.append({
        "char": "backspace",
        "label": "⌫",
        "shift_char": "backspace",
        "rect": QRectF(current_x, current_y, other_width, key_height),
        "is_special": True,
    })
    current_x += other_width + col_gap
    
    keys.append({
        "char": "enter",
        "label": "↵",
        "shift_char": "enter",
        "rect": QRectF(current_x, current_y, other_width, key_height),
        "is_special": True,
    })
    
    return keys
```

#### New method `update_keyboard_mode()`:
```python
def update_keyboard_mode(self, mode):
    """Called when vision_thread emits mode_changed("keyboard" or "normal")."""
    if mode == "keyboard":
        self.keyboard_active = True
        self.system_mode = "KEYBOARD"
        # Reset dwell state
        self.left_dwell_key = None
        self.right_dwell_key = None
        self.left_pointer = None
        self.right_pointer = None
        self.left_smooth_x.reset()
        self.left_smooth_y.reset()
        self.right_smooth_x.reset()
        self.right_smooth_y.reset()
        self.shift_active = False
        self.ctrl_active = False
    elif mode == "normal" and self.keyboard_active:
        # Exiting keyboard mode
        self.keyboard_active = False
        self.system_mode = "NORMAL"
    self.update()
```

Hook this into the existing `update_system_mode()` method (line 314):
```python
def update_system_mode(self, mode):
    if mode == "keyboard":
        self.update_keyboard_mode("keyboard")
    elif mode == "drawing":
        # ... existing drawing logic
    else:
        # ... existing normal logic
        if self.keyboard_active:
            self.update_keyboard_mode("normal")
```

#### New method `on_keyboard_event()`:
```python
def on_keyboard_event(self, ev):
    """Process per-frame keyboard state: update pointers, detect dwells, handle modifiers."""
    t = time.time()
    fw = ev["frame_w"]
    fh = ev["frame_h"]
    
    # Extract modifier state from left hand gesture
    left_gesture = ev.get("left_gesture")
    self.shift_active = (left_gesture == "fist")
    self.ctrl_active = (left_gesture == "open_hand")
    
    # Process left hand pointer
    if ev["left_present"]:
        lx, ly = self._to_screen(ev["left_x"], ev["left_y"], fw, fh)
        sx = self.left_smooth_x.filter(lx, t)
        sy = self.left_smooth_y.filter(ly, t)
        self.left_pointer = QPointF(sx, sy)
        self._handle_dwell("left", self.left_pointer, t)
    else:
        self.left_pointer = None
        self.left_dwell_key = None
        self.left_smooth_x.reset()
        self.left_smooth_y.reset()
    
    # Process right hand pointer
    if ev["right_present"]:
        rx, ry = self._to_screen(ev["right_x"], ev["right_y"], fw, fh)
        sx = self.right_smooth_x.filter(rx, t)
        sy = self.right_smooth_y.filter(ry, t)
        self.right_pointer = QPointF(sx, sy)
        self._handle_dwell("right", self.right_pointer, t)
    else:
        self.right_pointer = None
        self.right_dwell_key = None
        self.right_smooth_x.reset()
        self.right_smooth_y.reset()
    
    self.update()
```

#### New method `_handle_dwell()`:
```python
def _handle_dwell(self, hand, pointer, t):
    """Check if pointer is dwelling on a key; trigger press after kbd_dwell_time."""
    # Get dwell state for this hand
    if hand == "left":
        dwell_key_attr = "left_dwell_key"
        dwell_start_attr = "left_dwell_start"
    else:
        dwell_key_attr = "right_dwell_key"
        dwell_start_attr = "right_dwell_start"
    
    current_dwell_key = getattr(self, dwell_key_attr)
    current_dwell_start = getattr(self, dwell_start_attr)
    
    # Find which key the pointer is over
    hit_key = None
    for key in self.kbd_layout:
        if key["rect"].contains(pointer):
            hit_key = key
            break
    
    if hit_key is None:
        # Not over any key: reset dwell
        setattr(self, dwell_key_attr, None)
        return
    
    # Over a key
    if hit_key is not current_dwell_key:
        # Started dwelling on a new key
        setattr(self, dwell_key_attr, hit_key)
        setattr(self, dwell_start_attr, t)
    else:
        # Still on same key: check if dwell time reached
        elapsed = t - current_dwell_start
        if elapsed >= self.kbd_dwell_time:
            # Trigger key press
            self._press_key(hit_key)
            # Reset dwell so it doesn't repeat (lift finger to type again)
            setattr(self, dwell_key_attr, None)
```

#### New method `_press_key()`:
```python
def _press_key(self, key):
    """Execute pyautogui key press with modifiers."""
    import pyautogui
    
    char = key["char"]
    
    # Special keys
    if char == "backspace":
        pyautogui.press("backspace")
        self.show_toast("⌫")
        return
    elif char == "enter":
        pyautogui.press("enter")
        self.show_toast("↵")
        return
    elif char == " ":
        pyautogui.press("space")
        self.show_toast("SPACE")
        return
    
    # Letter keys
    if self.ctrl_active:
        # Ctrl+letter
        pyautogui.hotkey("ctrl", char)
        self.show_toast(f"Ctrl+{char.upper()}")
    elif self.shift_active:
        # Shift = capital letter
        pyautogui.press(char.upper())
        self.show_toast(char.upper())
    else:
        # Lowercase
        pyautogui.press(char)
        self.show_toast(char)
```

#### Rendering in `paintEvent()` (line 1052):

Add after the drawing layers block (line 1079):
```python
# Keyboard overlay
if self.keyboard_active:
    self._paint_keyboard(painter)
```

#### New method `_paint_keyboard()`:
```python
def _paint_keyboard(self, painter):
    """Render the transparent QWERTY keyboard with dwell indicators."""
    t = time.time()
    
    # Semi-transparent dark background panel
    kbd_bounds = self._get_keyboard_bounds()
    painter.setBrush(QColor(0, 10, 30, 180))
    painter.setPen(QPen(QColor(0, 150, 255, 200), 2))
    painter.drawRoundedRect(kbd_bounds, 16, 16)
    
    # Render each key
    for key in self.kbd_layout:
        rect = key["rect"]
        char = key.get("label", key["shift_char"] if self.shift_active else key["char"])
        
        # Key background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(20, 40, 70, 200))
        painter.drawRoundedRect(rect, 8, 8)
        
        # Key border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 180, 255, 180), 1.5))
        painter.drawRoundedRect(rect, 8, 8)
        
        # Key label
        painter.setPen(QColor(200, 220, 255))
        painter.setFont(QFont("Segoe UI", 16 if not key["is_special"] else 14, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, char.upper() if len(char) == 1 else char)
        
        # Dwell progress rings (left hand = cyan, right hand = yellow)
        for hand, color in [("left", QColor(0, 220, 255)), ("right", QColor(255, 200, 0))]:
            dwell_key = getattr(self, f"{hand}_dwell_key")
            dwell_start = getattr(self, f"{hand}_dwell_start")
            if dwell_key is key:
                elapsed = t - dwell_start
                frac = min(1.0, elapsed / self.kbd_dwell_time)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(color, 3))
                painter.drawArc(rect.adjusted(4, 4, -4, -4), 90 * 16, int(-frac * 360 * 16))
    
    # Draw hand cursors
    if self.left_pointer:
        self._paint_hand_cursor(painter, self.left_pointer, QColor(0, 220, 255), "L")
    if self.right_pointer:
        self._paint_hand_cursor(painter, self.right_pointer, QColor(255, 200, 0), "R")
    
    # Modifier indicators (top-left corner of keyboard)
    self._paint_modifiers(painter, kbd_bounds)

def _get_keyboard_bounds(self):
    """Get bounding rect of entire keyboard for background panel."""
    if not self.kbd_layout:
        return QRectF()
    min_x = min(k["rect"].left() for k in self.kbd_layout)
    min_y = min(k["rect"].top() for k in self.kbd_layout)
    max_x = max(k["rect"].right() for k in self.kbd_layout)
    max_y = max(k["rect"].bottom() for k in self.kbd_layout)
    padding = 20
    return QRectF(min_x - padding, min_y - padding, 
                  max_x - min_x + 2 * padding, max_y - min_y + 2 * padding)

def _paint_hand_cursor(self, painter, pos, color, label):
    """Draw a small crosshair cursor with hand label."""
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(color, 2))
    painter.drawEllipse(pos, 8, 8)
    painter.drawLine(QPointF(pos.x() - 14, pos.y()), QPointF(pos.x() + 14, pos.y()))
    painter.drawLine(QPointF(pos.x(), pos.y() - 14), QPointF(pos.x(), pos.y() + 14))
    # Label
    painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    painter.setPen(color)
    painter.drawText(int(pos.x() + 12), int(pos.y() - 12), label)

def _paint_modifiers(self, painter, kbd_bounds):
    """Show active modifiers (Shift/Ctrl) in top-left of keyboard."""
    x = kbd_bounds.left() + 16
    y = kbd_bounds.top() + 16
    
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    
    if self.shift_active:
        painter.setPen(QColor(255, 200, 0))
        painter.drawText(int(x), int(y), "⇧ SHIFT")
        y += 20
    
    if self.ctrl_active:
        painter.setPen(QColor(0, 220, 255))
        painter.drawText(int(x), int(y), "⌃ CTRL")
```

---

## Implementation Order

1. **hand_tracker.py** — Enable two-hand detection with handedness labels
2. **vision_thread.py** — Add keyboard mode flag, keyboard_event signal, dual-hand processing
3. **gesture_mapper.py** — Change three_fingers binding to enter keyboard mode
4. **overlay_window.py** — Add keyboard layout, dwell detection, rendering

## Testing Steps

1. Run `python main.py`
2. Show three_fingers gesture (either hand) → should enter keyboard mode, see QWERTY overlay
3. Hover left index finger over a letter for 0.5s → should type lowercase letter
4. Hold left fist, hover right index over a letter for 0.5s → should type uppercase
5. Hold left open_palm, hover right index over a letter → should send Ctrl+letter
6. Hover right index over Space/Backspace/Enter → should work
7. Hover left index over keys → should also type (independent dwell timers)
8. Show right-hand three_fingers → should exit keyboard mode back to normal

## Edge Cases & Considerations

- **Re-trigger guard:** Entering with three_fingers, if user holds the gesture, don't immediately re-exit. The exit check is right-hand only, and we debounce with `_kbd_exit_triggered` flag.
- **Modifier conflicts:** If left hand is typing while also holding fist, the dwell will fire with Shift. This is acceptable per user spec ("both hands independent").
- **Hand loss:** If a hand disappears mid-dwell, the dwell resets (pointer becomes None).
- **Smooth pointer:** Using the same One-Euro filter as drawing mode for responsive yet stable targeting.
- **Layout responsiveness:** Full-width, vertically centered. Keys scale to screen width with slight row stagger for visual clarity.
- **Visual feedback:** Dwell progress ring (cyan for left, gold for right), toast on key press, modifier badges on keyboard panel.

## Files to Modify

1. `src/camera/hand_tracker.py` — ~40 lines changed (detect returns list of tuples)
2. `src/ui/vision_thread.py` — ~120 lines added (keyboard mode branch, dual-hand processing)
3. `src/control/gesture_mapper.py` — ~10 lines changed (three_fingers binding + mode flag)
4. `src/ui/overlay_window.py` — ~250 lines added (keyboard layout, dwell, rendering)

**Total: ~420 lines of new/modified code across 4 files.**
