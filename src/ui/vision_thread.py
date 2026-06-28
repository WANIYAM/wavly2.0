import cv2
import time
import math
import warnings
from collections import Counter
from PyQt6.QtCore import QThread, pyqtSignal

from src.camera.hand_tracker import HandTracker
from src.control.mouse_controller import MouseController
from src.control.gesture_mapper import GestureMapper
from src.ai.predictor import GesturePredictor
from src.control.voice_controller import VoiceController
from src.control.voice_mapper import VoiceMapper
from src.control.voice_responder import VoiceResponder

warnings.filterwarnings("ignore")

class VisionThread(QThread):
    # Signals to communicate with the PyQt main thread
    # draw_event carries the full per-frame drawing state (position + active
    # tool + pinch) while in drawing mode; the overlay owns canvas manipulation.
    draw_event = pyqtSignal(dict)
    keyboard_event = pyqtSignal(dict)
    gesture_detected = pyqtSignal(str)
    gesture_command = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    app_changed = pyqtSignal(str)
    voice_status_changed = pyqtSignal(str)
    frame_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.running = True
        self.hand_tracker = HandTracker(
            max_hands=2,
            detection_confidence=0.7,
            tracking_confidence=0.7
        )
        self.mouse_controller = MouseController()
        self.voice_responder = VoiceResponder()
        self.voice_responder.start()
        self.gesture_mapper = GestureMapper(voice_responder=self.voice_responder)
        self.gesture_predictor = GesturePredictor()
        self.voice_controller = VoiceController(voice_responder=self.voice_responder)
        self.voice_mapper = VoiceMapper(voice_responder=self.voice_responder)

        self.prev_frame_time = 0
        self.fps = 0
        self.gesture_buffer = []
        self.unknown_streak = 0
        self.last_logged_gesture = None
        self.pinch_active = False
        # Separate hysteretic pinch state used for drawing-mode object drag
        # (deliberate pinch-and-hold), kept apart from the normal-mode click.
        self.draw_pinching = False
        self.last_voice_status = "STANDBY"
        # Tracks whether the cursor was moving last frame, so we clutch (reseed)
        # only on the moving -> not-moving transition rather than every frame.
        self.prev_should_move = False
        # Keyboard mode flag
        self.keyboard_mode = False
        self._kbd_exit_triggered = False
        # Per-hand gesture buffers for keyboard mode
        self.left_gesture_buffer = []
        self.right_gesture_buffer = []

    def stop(self):
        if not self.running:
            return
        self.running = False
        # Stop both voice controller and responder gracefully
        self.voice_controller.stop()
        self.voice_responder.stop()

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
        left_confirmed_gesture = None
        if left_hand:
            landmarks, _ = left_hand
            raw_lm = [(lm.x, lm.y) for lm in landmarks.landmark]
            wrist_x, wrist_y = raw_lm[0]
            norm_lm = [(x - wrist_x, y - wrist_y) for x, y in raw_lm]
            left_gesture = self.gesture_predictor.predict(norm_lm)

            # Buffer and confirm left hand gesture
            self.left_gesture_buffer.append(left_gesture)
            if len(self.left_gesture_buffer) > 6:
                self.left_gesture_buffer.pop(0)

            # Confirm gesture with 4/6 votes (looser than normal mode for responsiveness)
            from collections import Counter
            gesture_counts = Counter(self.left_gesture_buffer)
            most_common, vote_count = gesture_counts.most_common(1)[0] if gesture_counts else ("unknown", 0)
            if vote_count >= 4 and most_common != "unknown":
                left_confirmed_gesture = most_common

            lm_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
            left_index_tip = lm_list[8]  # Index fingertip

            kbd["left_gesture"] = left_confirmed_gesture
            kbd["left_x"] = left_index_tip[0]
            kbd["left_y"] = left_index_tip[1]
        else:
            self.left_gesture_buffer = []
            kbd["left_gesture"] = None
            kbd["left_x"] = 0
            kbd["left_y"] = 0

        # Right hand: same extraction
        right_confirmed_gesture = None
        if right_hand:
            landmarks, _ = right_hand
            raw_lm = [(lm.x, lm.y) for lm in landmarks.landmark]
            wrist_x, wrist_y = raw_lm[0]
            norm_lm = [(x - wrist_x, y - wrist_y) for x, y in raw_lm]
            right_gesture = self.gesture_predictor.predict(norm_lm)

            # Buffer and confirm right hand gesture
            self.right_gesture_buffer.append(right_gesture)
            if len(self.right_gesture_buffer) > 6:
                self.right_gesture_buffer.pop(0)

            from collections import Counter
            gesture_counts = Counter(self.right_gesture_buffer)
            most_common, vote_count = gesture_counts.most_common(1)[0] if gesture_counts else ("unknown", 0)
            if vote_count >= 4 and most_common != "unknown":
                right_confirmed_gesture = most_common

            lm_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
            right_index_tip = lm_list[8]

            kbd["right_gesture"] = right_confirmed_gesture
            kbd["right_x"] = right_index_tip[0]
            kbd["right_y"] = right_index_tip[1]
        else:
            self.right_gesture_buffer = []
            kbd["right_gesture"] = None
            kbd["right_x"] = 0
            kbd["right_y"] = 0

        self.keyboard_event.emit(kbd)

        # Check exit gesture: left hand three_fingers (confirmed)
        if left_confirmed_gesture == "three_fingers":
            # Debounce: only exit once
            if not self._kbd_exit_triggered:
                self._kbd_exit_triggered = True
                self.keyboard_mode = False
                self.gesture_mapper.set_keyboard_mode(False)
                self.left_gesture_buffer = []
                self.right_gesture_buffer = []
                self.mode_changed.emit("normal")
                print("[MODE] Keyboard → Normal (left hand three_fingers)")
                if self.voice_responder:
                    self.voice_responder.system_speak("Keyboard closed")
        else:
            self._kbd_exit_triggered = False

    def run(self):
        cap = cv2.VideoCapture(1)

        if not cap.isOpened():
            print("Error: Could not open webcam")
            return

        print("[CAMERA] Webcam started")
        self.voice_responder.greet()

        # Emit initial active app
        try:
            initial_app = self.gesture_mapper.context_detector.get_active_app()
            self.gesture_mapper.current_app = initial_app
            self.gesture_mapper.last_app_check = time.time()
            self.app_changed.emit(initial_app)
        except Exception as e:
            print(f"[VISION] Error getting initial app: {e}")

        self.voice_controller.start()
        print("[VOICE] Voice control started")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                break

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            # Check active app every 2 seconds
            now = time.time()
            if now - self.gesture_mapper.last_app_check >= self.gesture_mapper.app_check_interval:
                try:
                    new_app = self.gesture_mapper.context_detector.get_active_app()
                    if new_app != self.gesture_mapper.current_app:
                        self.gesture_mapper.current_app = new_app
                        print(f"[CONTEXT] App changed → {new_app}")
                        self.app_changed.emit(new_app)
                except Exception as e:
                    print(f"[VISION] Error checking active app: {e}")
                self.gesture_mapper.last_app_check = now

            # Calculate FPS
            current_time = time.time()
            self.fps = 1 / (current_time - self.prev_frame_time) if self.prev_frame_time > 0 else 0
            self.prev_frame_time = current_time

            # Detect hand landmarks
            hands_data = self.hand_tracker.detect(frame)
            frame_height, frame_width = frame.shape[:2]

            # Keyboard mode gets its own branch
            if self.keyboard_mode:
                self._process_keyboard_frame(hands_data, frame_width, frame_height)
                # Emit "Keyboard Mode" for HUD so it doesn't show stale gestures
                self.gesture_detected.emit("Keyboard Mode")
                self.frame_ready.emit(frame.copy())
                self.msleep(5)
                continue

            # Normal/Drawing modes: use first hand only (backward compat)
            landmarks = hands_data[0][0] if hands_data else None

            display_gesture = "No Hand"

            if landmarks is not None:
                # Get landmark list and find tips
                landmark_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
                index_fingertip = landmark_list[8]
                index_pip = landmark_list[6]
                thumb_tip = landmark_list[4]

                self.gesture_mapper.update_hand_position(index_fingertip[1])

                # Predict gesture using ML model (use normalized landmarks)
                raw_landmarks = [(lm.x, lm.y) for lm in landmarks.landmark]
                wrist_x_norm, wrist_y_norm = raw_landmarks[0]
                normalized_landmarks = [(x - wrist_x_norm, y - wrist_y_norm) for x, y in raw_landmarks]
                predicted_gesture = self.gesture_predictor.predict(normalized_landmarks)

                # Geometric Spider-Man check
                wrist_pos = landmark_list[0]
                thumb_tip = landmark_list[4]
                thumb_mcp = landmark_list[2]
                # index_fingertip is already landmark_list[8]
                # index_pip is already landmark_list[6]
                middle_fingertip = landmark_list[12]
                middle_pip = landmark_list[10]
                ring_fingertip = landmark_list[16]
                ring_pip = landmark_list[14]
                pinky_fingertip = landmark_list[20]
                pinky_pip = landmark_list[18]

                is_thumb_extended = abs(thumb_tip[0] - wrist_pos[0]) > abs(thumb_mcp[0] - wrist_pos[0])
                is_index_extended = index_fingertip[1] < index_pip[1] - 15
                is_middle_curled = middle_fingertip[1] > middle_pip[1] - 10
                is_ring_curled = ring_fingertip[1] > ring_pip[1] - 10
                is_pinky_extended = pinky_fingertip[1] < pinky_pip[1] - 15

                if is_thumb_extended and is_index_extended and is_middle_curled and is_ring_curled and is_pinky_extended:
                    predicted_gesture = "spider_man"

                # Add prediction to buffer
                self.gesture_buffer.append(predicted_gesture)
                if len(self.gesture_buffer) > 10:
                    self.gesture_buffer.pop(0)

                # Count votes
                gesture_counts = Counter(self.gesture_buffer)
                most_common_gesture, vote_count = gesture_counts.most_common(1)[0] if gesture_counts else ("unknown", 0)

                # Track unknown streak
                if most_common_gesture == "unknown":
                    self.unknown_streak += 1
                else:
                    self.unknown_streak = 0

                # Only clear buffer after 5 consecutive unknowns
                if self.unknown_streak >= 5:
                    self.gesture_buffer = []
                    self.unknown_streak = 0

                # Confirm gesture if 6 out of 10 votes
                confirmed_gesture = most_common_gesture if vote_count >= 6 and most_common_gesture != "unknown" else None
                is_confirmed = confirmed_gesture is not None

                if is_confirmed and confirmed_gesture != self.last_logged_gesture:
                    print(f"[BUFFER] confirmed: {confirmed_gesture} ({vote_count}/10 votes)")
                    self.last_logged_gesture = confirmed_gesture

                # Geometric pinch distance (thumb tip ↔ index tip).
                pinch_distance = math.sqrt(
                    (thumb_tip[0] - index_fingertip[0]) ** 2 +
                    (thumb_tip[1] - index_fingertip[1]) ** 2
                )

                # Hysteretic pinch state for drawing-mode drag: latch on when the
                # fingers close past 45px, release only past 70px so a held drag
                # doesn't flicker.
                if self.draw_pinching:
                    if pinch_distance > 70:
                        self.draw_pinching = False
                else:
                    if pinch_distance < 45:
                        self.draw_pinching = True

                # Execute gesture action. In drawing mode this resolves only to
                # discrete commands; in normal mode it performs the cursor /
                # scroll / click actions directly.
                if is_confirmed:
                    action = self.gesture_mapper.execute(confirmed_gesture)
                    if action == "drawing":
                        self.mode_changed.emit("drawing")
                    elif action == "normal":
                        self.mode_changed.emit("normal")
                    elif action == "keyboard":
                        self.keyboard_mode = True
                        self.mode_changed.emit("keyboard")
                    elif action in ["clear_canvas", "size_up", "size_down",
                                    "toggle_palette", "paste_image", "screenshot"]:
                        print(f"[VISION] emitting command: {action}")
                        self.gesture_command.emit(action)
                    display_gesture = confirmed_gesture
                else:
                    display_gesture = "stabilizing..."

                # is_drawing_mode() is read AFTER execute() so a mode just toggled
                # this frame takes effect immediately.
                if self.gesture_mapper.is_drawing_mode():
                    # Tool follows the live gesture; position streams every frame
                    # (even before a gesture confirms) so the pointer tracks
                    # smoothly. The overlay performs all canvas manipulation.
                    if self.draw_pinching:
                        tool = "drag"
                    elif confirmed_gesture == "point":
                        tool = "draw"
                    elif confirmed_gesture == "open_hand":
                        tool = "erase"
                    else:
                        tool = "hover"
                    self.draw_event.emit({
                        "x": index_fingertip[0], "y": index_fingertip[1],
                        "tx": thumb_tip[0], "ty": thumb_tip[1],
                        "tool": tool, "pinching": self.draw_pinching,
                        "gesture": confirmed_gesture, "present": True,
                        "frame_w": frame_width, "frame_h": frame_height,
                    })
                    # No OS-cursor movement or pinch-click while drawing.
                    if self.prev_should_move:
                        self.mouse_controller.reseed()
                    self.prev_should_move = False
                else:
                    # -------------------- NORMAL MODE --------------------
                    # Pinch-click (own thresholds; index must be curled so it
                    # doesn't fire mid-gesture, and never while making a fist).
                    is_index_curled = abs(index_fingertip[1] - index_pip[1]) < 30
                    if pinch_distance < 60 and is_index_curled and confirmed_gesture != "fist":
                        if not self.pinch_active:
                            self.pinch_active = True
                            self.mouse_controller.click()
                            print("[PINCH] Click detected")
                    elif pinch_distance > 80:
                        self.pinch_active = False

                    # Determine cursor movement
                    should_move = False
                    speed_multiplier = 1.0
                    if is_confirmed:
                        if confirmed_gesture == "open_hand":
                            should_move = True
                            speed_multiplier = 1.0
                        elif confirmed_gesture == "point":
                            should_move = True
                            speed_multiplier = 0.5
                        elif confirmed_gesture == "fist":
                            should_move = False

                    # Move mouse cursor
                    if should_move:
                        self.mouse_controller.move(index_fingertip[0], index_fingertip[1],
                                                  frame_width, frame_height, speed_multiplier)
                    elif self.prev_should_move:
                        # Just stopped moving (fist / gesture change / stabilizing):
                        # clutch once so the next move re-anchors without snapping
                        # the cursor.
                        self.mouse_controller.reseed()
                    self.prev_should_move = should_move

                # Emit gesture detected
                self.gesture_detected.emit(display_gesture)
            else:
                if self.gesture_mapper.is_drawing_mode():
                    # In drawing mode: tell the overlay the hand is gone so it
                    # lifts the pen and hides the cursor (no OS-cursor clutch).
                    self.draw_pinching = False
                    self.draw_event.emit({
                        "x": 0, "y": 0, "tool": "hover", "pinching": False,
                        "present": False,
                        "frame_w": frame_width, "frame_h": frame_height,
                    })
                else:
                    # Hand lost: clutch (once) so re-acquisition resumes from the
                    # cursor's current position instead of jumping.
                    if self.prev_should_move:
                        self.mouse_controller.reseed()
                    self.prev_should_move = False
                self.gesture_detected.emit("No Hand")

            self.frame_ready.emit(frame.copy())

            # Process voice commands
            queue_size = self.voice_controller.command_queue.qsize()
            if queue_size > 0:
                print(f"[VISION] Voice queue has {queue_size} commands")
            while not self.voice_controller.command_queue.empty():
                voice_cmd = self.voice_controller.command_queue.get()
                print(f"[VISION] Processing voice: {voice_cmd}")
                self.voice_mapper.execute(voice_cmd)

            # Check and emit voice status if changed
            current_voice_status = "STANDBY"
            if self.voice_controller.running:
                if self.voice_controller.activated:
                    current_voice_status = "ACTIVE"
                else:
                    current_voice_status = "LISTENING"

            if current_voice_status != self.last_voice_status:
                self.last_voice_status = current_voice_status
                self.voice_status_changed.emit(current_voice_status)

            # Small sleep to prevent 100% thread usage on fast loops
            self.msleep(5)

        cap.release()
