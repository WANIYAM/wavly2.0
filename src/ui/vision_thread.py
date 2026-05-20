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

warnings.filterwarnings("ignore")

class VisionThread(QThread):
    # Signals to communicate with the PyQt main thread
    point_detected = pyqtSignal(int, int)
    gesture_detected = pyqtSignal(str)
    gesture_command = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    app_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.hand_tracker = HandTracker(
            max_hands=1,
            detection_confidence=0.7,
            tracking_confidence=0.7
        )
        self.mouse_controller = MouseController()
        self.gesture_mapper = GestureMapper()
        self.gesture_predictor = GesturePredictor()

        self.prev_frame_time = 0
        self.fps = 0
        self.gesture_buffer = []
        self.unknown_streak = 0
        self.last_logged_gesture = None
        self.pinch_active = False

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.wait()
        self.hand_tracker.close()

    def run(self):
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Could not open webcam")
            return

        print("[CAMERA] Webcam started")

        # Emit initial active app
        try:
            initial_app = self.gesture_mapper.context_detector.get_active_app()
            self.gesture_mapper.current_app = initial_app
            self.gesture_mapper.last_app_check = time.time()
            self.app_changed.emit(initial_app)
        except Exception as e:
            print(f"[VISION] Error getting initial app: {e}")

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
            landmarks = self.hand_tracker.detect(frame)
            frame_height, frame_width = frame.shape[:2]

            display_gesture = "No Hand"

            if landmarks is not None:
                # Get landmark list and find tips
                landmark_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
                index_fingertip = landmark_list[8]
                index_pip = landmark_list[6]
                thumb_tip = landmark_list[4]

                self.gesture_mapper.update_hand_position(index_fingertip[1])

                # Emit drawing coordinates to the UI thread
                self.point_detected.emit(index_fingertip[0], index_fingertip[1])

                # Predict gesture using ML model (use normalized landmarks)
                raw_landmarks = [(lm.x, lm.y) for lm in landmarks.landmark]
                wrist_x, wrist_y = raw_landmarks[0]
                normalized_landmarks = [(x - wrist_x, y - wrist_y) for x, y in raw_landmarks]
                predicted_gesture = self.gesture_predictor.predict(normalized_landmarks)

                # Add prediction to buffer
                self.gesture_buffer.append(predicted_gesture)
                if len(self.gesture_buffer) > 7:
                    self.gesture_buffer.pop(0)

                # Count votes
                gesture_counts = Counter(self.gesture_buffer)
                most_common_gesture, vote_count = gesture_counts.most_common(1)[0] if gesture_counts else ("unknown", 0)

                # Track unknown streak
                if most_common_gesture == "unknown":
                    self.unknown_streak += 1
                else:
                    self.unknown_streak = 0

                # Only clear buffer after 3 consecutive unknowns
                if self.unknown_streak >= 3:
                    self.gesture_buffer = []
                    self.unknown_streak = 0

                # Confirm gesture if 5 out of 7 votes
                confirmed_gesture = most_common_gesture if vote_count >= 5 and most_common_gesture != "unknown" else None
                is_confirmed = confirmed_gesture is not None

                if is_confirmed and confirmed_gesture != self.last_logged_gesture:
                    print(f"[BUFFER] confirmed: {confirmed_gesture} ({vote_count}/7 votes)")
                    self.last_logged_gesture = confirmed_gesture

                # Pinch detection
                pinch_distance = math.sqrt(
                    (thumb_tip[0] - index_fingertip[0]) ** 2 +
                    (thumb_tip[1] - index_fingertip[1]) ** 2
                )

                # Check if index finger is curled (y positions are close)
                is_index_curled = abs(index_fingertip[1] - index_pip[1]) < 30

                # Trigger click if pinch detected and current gesture is NOT fist
                if pinch_distance < 60 and is_index_curled and confirmed_gesture != "fist":
                    if not self.pinch_active:
                        self.pinch_active = True
                        self.mouse_controller.click()
                        print("[PINCH] Click detected")
                elif pinch_distance > 80:
                    self.pinch_active = False



                # Execute gesture action
                if is_confirmed:
                    action = self.gesture_mapper.execute(confirmed_gesture)

                    # Emit mode change signals
                    if action == "drawing":
                        self.mode_changed.emit("drawing")
                    elif action == "normal":
                        self.mode_changed.emit("normal")

                    # Emit drawing mode gesture commands
                    if action in ["clear_canvas", "pen_up", "pen_down", "change_color",
                                  "brush_size_up", "save_drawing", "undo", "redo", "erase_mode"]:
                        print(f"[VISION] emitting command: {action}")
                        self.gesture_command.emit(action)

                    display_gesture = confirmed_gesture
                else:
                    display_gesture = "stabilizing..."

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

                # Emit gesture detected
                self.gesture_detected.emit(display_gesture)
            else:
                self.gesture_detected.emit("No Hand")

            # Small sleep to prevent 100% thread usage on fast loops
            self.msleep(5)

        cap.release()
