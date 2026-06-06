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
    point_detected = pyqtSignal(int, int)
    gesture_detected = pyqtSignal(str)
    gesture_command = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    app_changed = pyqtSignal(str)
    voice_status_changed = pyqtSignal(str)

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
        self.voice_responder = VoiceResponder()
        self.voice_responder.start()
        self.voice_controller = VoiceController(voice_responder=self.voice_responder)
        self.voice_mapper = VoiceMapper(voice_responder=self.voice_responder)

        self.prev_frame_time = 0
        self.fps = 0
        self.gesture_buffer = []
        self.unknown_streak = 0
        self.last_logged_gesture = None
        self.pinch_active = False
        self.last_voice_status = "STANDBY"

    def stop(self):
        if not self.running:
            return
        self.running = False
        # Stop both voice controller and responder gracefully
        self.voice_controller.stop()
        self.voice_responder.stop()
        cv2.destroyAllWindows()

    def run(self):
        cap = cv2.VideoCapture(0)

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

            # Show small PIP camera window
            small_frame = cv2.resize(frame, (320, 240))
            cv2.imshow("Wavly Camera", small_frame)
            cv2.waitKey(1)

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
