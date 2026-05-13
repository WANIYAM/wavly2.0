import cv2
import time
from .hand_tracker import HandTracker
from src.control.mouse_controller import MouseController
from src.control.gesture_mapper import GestureMapper
from src.gestures.gesture_detector import GestureDetector
from src.ai.data_collector import DataCollector
from src.ai.predictor import GesturePredictor


class CameraFeed:
    def __init__(self):
        self.cap = None
        self.hand_tracker = HandTracker()
        self.mouse_controller = MouseController()
        self.gesture_mapper = GestureMapper()
        self.gesture_detector = GestureDetector()
        self.data_collector = DataCollector()
        self.gesture_predictor = GesturePredictor()
        self.prev_frame_time = 0
        self.fps = 0
        self.prev_hand_y = None
        self.scroll_threshold = 20
        self.last_scroll_time = 0
        self.recording = False
        self.current_gesture_label = None
        self.gesture_mapping = {
            ord('0'): 'fist',
            ord('1'): 'open_hand',
            ord('2'): 'peace',
            ord('3'): 'point',
            ord('4'): 'two_fingers',
            ord('5'): 'three_fingers',
            ord('6'): 'four_fingers',
            ord('7'): 'thumbs_up',
            ord('8'): 'thumbs_down',
            ord('9'): 'l_shape'
        }

    def start(self):
        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            print("Error: Could not open webcam")
            return

        print("Camera started. Press 'Q' to quit, 'R' to toggle recording.")

        while True:
            ret, frame = self.cap.read()

            if not ret:
                print("Error: Failed to capture frame")
                break

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            # Toggle recording mode with 'R' key
            if key == ord('r') or key == ord('R'):
                self.recording = not self.recording
                if self.recording:
                    print("Recording mode ON")
                else:
                    print("Recording mode OFF")

            # Set gesture label with keys 0-4
            if key in self.gesture_mapping:
                self.current_gesture_label = self.gesture_mapping[key]
                print(f"Gesture label set to: {self.current_gesture_label}")

            # Check for quit
            if key == ord('q') or key == ord('Q'):
                break

            # Calculate FPS
            current_time = time.time()
            self.fps = 1 / (current_time - self.prev_frame_time) if self.prev_frame_time > 0 else 0
            self.prev_frame_time = current_time

            # Detect hand landmarks
            landmarks = self.hand_tracker.detect(frame)

            # Draw landmarks on frame
            frame = self.hand_tracker.draw(frame, landmarks)

            # Get frame dimensions
            frame_height, frame_width = frame.shape[:2]

            # Draw hand detection status and index fingertip circle
            if landmarks is not None:
                # Draw "Hand Detected" text
                cv2.putText(frame, "Hand Detected", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Save data if recording mode is ON and gesture label is set
                if self.recording and self.current_gesture_label is not None:
                    self.data_collector.save(landmarks.landmark, self.current_gesture_label)

                # Get landmark list and draw circle on index fingertip
                landmark_list = self.hand_tracker.get_landmark_list(landmarks, frame_width, frame_height)
                index_fingertip = landmark_list[8]
                print(f"Index fingertip: {index_fingertip}")

                # Predict gesture using ML model (use normalized landmarks)
                normalized_landmarks = [(lm.x, lm.y) for lm in landmarks.landmark]
                predicted_gesture = self.gesture_predictor.predict(normalized_landmarks)

                # Execute gesture action/mode via GestureMapper
                gesture_result = self.gesture_mapper.execute(predicted_gesture)
                current_mode = self.gesture_mapper.get_current_mode()

                # Determine cursor movement based on gesture
                should_move = False
                speed_multiplier = 1.0

                if predicted_gesture == "open_hand":
                    should_move = True
                    speed_multiplier = 1.0
                elif predicted_gesture == "point":
                    should_move = True
                    speed_multiplier = 0.5
                elif predicted_gesture == "fist":
                    should_move = False
                else:
                    # All other gestures freeze cursor while action executes
                    should_move = False

                # Move mouse cursor if allowed
                if should_move:
                    self.mouse_controller.move(index_fingertip[0], index_fingertip[1],
                                              frame_width, frame_height, speed_multiplier)

                # Determine display mode
                if predicted_gesture == "open_hand":
                    display_mode = "MOVING"
                elif predicted_gesture == "point":
                    display_mode = "PRECISION"
                elif predicted_gesture == "fist":
                    display_mode = "IDLE"
                else:
                    display_mode = "ACTION"

                # Display predicted gesture name in green
                cv2.putText(frame, f"Gesture: {predicted_gesture}", (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Display current mode in yellow
                cv2.putText(frame, f"Mode: {display_mode}", (10, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                # Draw larger distinct circle on index fingertip (landmark 8)
                cv2.circle(frame, index_fingertip, 15, (255, 0, 255), -1)  # Magenta filled circle
            else:
                # Draw "No Hand" text
                cv2.putText(frame, "No Hand", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Draw FPS counter in top left corner
            cv2.putText(frame, f"FPS: {int(self.fps)}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # Draw recording status if recording mode is ON
            if self.recording:
                if self.current_gesture_label:
                    recording_text = f"RECORDING: {self.current_gesture_label.upper()}"
                    cv2.putText(frame, recording_text, (10, 190),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                else:
                    recording_text = "RECORDING: No label set (press 0-9)"
                    cv2.putText(frame, recording_text, (10, 190),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            else:
                # Show available gesture keys when not recording
                cv2.putText(frame, "Press R to record | 0-9 to set gesture", (10, 190),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow("Wavly", frame)

        self.stop()

    def stop(self):
        if self.cap is not None:
            self.cap.release()
        self.hand_tracker.close()
        cv2.destroyAllWindows()
        print("Camera stopped")
