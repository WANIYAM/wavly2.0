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
        self.frame_count = 0
        self.gesture_buffer = []
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

            # Increment frame count
            self.frame_count += 1

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
                thumb_tip = landmark_list[4]

                # Predict gesture using ML model (use normalized landmarks)
                normalized_landmarks = [(lm.x, lm.y) for lm in landmarks.landmark]
                predicted_gesture = self.gesture_predictor.predict(normalized_landmarks)

                # Add raw prediction to gesture buffer
                self.gesture_buffer.append(predicted_gesture)

                # Keep buffer size at maximum 7
                if len(self.gesture_buffer) > 7:
                    self.gesture_buffer.pop(0)

                # Count occurrences of each gesture in buffer
                from collections import Counter
                gesture_counts = Counter(self.gesture_buffer)

                # Find gesture with most votes
                most_common_gesture, vote_count = gesture_counts.most_common(1)[0] if gesture_counts else ("unknown", 0)

                # Confirm gesture only if it appears 5 or more times out of 7
                confirmed_gesture = most_common_gesture if vote_count >= 5 else None
                is_confirmed = confirmed_gesture is not None

                # PINCH DETECTION (independent from ML prediction)
                # Calculate distance between thumb tip (landmark 4) and index tip (landmark 8)
                import math
                pinch_distance = math.sqrt(
                    (thumb_tip[0] - index_fingertip[0]) ** 2 +
                    (thumb_tip[1] - index_fingertip[1]) ** 2
                )

                # Trigger click if pinch detected and current gesture is NOT fist
                pinch_detected = pinch_distance < 40 and confirmed_gesture != "fist"
                if pinch_detected:
                    self.mouse_controller.click()
                    # Display "PINCH DETECTED" in blue
                    cv2.putText(frame, "PINCH DETECTED", (10, 230),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

                # Get top 3 predictions with confidence scores for debug overlay
                import numpy as np
                features = np.array(normalized_landmarks).flatten().reshape(1, -1)
                probabilities = self.gesture_predictor.model.predict_proba(features)[0]
                class_names = self.gesture_predictor.model.classes_

                # Get top 3 indices and their probabilities
                top_3_indices = np.argsort(probabilities)[-3:][::-1]
                top_3_predictions = [(class_names[i], probabilities[i]) for i in top_3_indices]

                # Print debug info every 15 frames
                if self.frame_count % 15 == 0:
                    first_gesture, first_conf = top_3_predictions[0]
                    second_gesture, second_conf = top_3_predictions[1]
                    print(f"GESTURE: {first_gesture} | {int(first_conf * 100)}% | 2nd: {second_gesture} {int(second_conf * 100)}%")

                # Execute gesture action/mode via GestureMapper only with confirmed gesture
                if is_confirmed:
                    gesture_result = self.gesture_mapper.execute(confirmed_gesture)
                    current_mode = self.gesture_mapper.get_current_mode()
                    display_gesture = confirmed_gesture
                else:
                    # No confirmed gesture, use current mode
                    current_mode = self.gesture_mapper.get_current_mode()
                    display_gesture = "stabilizing..."

                # Determine cursor movement based on confirmed gesture
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
                    else:
                        # All other gestures freeze cursor while action executes
                        should_move = False

                # Move mouse cursor if allowed
                if should_move:
                    self.mouse_controller.move(index_fingertip[0], index_fingertip[1],
                                              frame_width, frame_height, speed_multiplier)

                # Determine display mode
                if is_confirmed:
                    if confirmed_gesture == "open_hand":
                        display_mode = "MOVING"
                    elif confirmed_gesture == "point":
                        display_mode = "PRECISION"
                    elif confirmed_gesture == "fist":
                        display_mode = "IDLE"
                    else:
                        display_mode = "ACTION"
                else:
                    display_mode = "STABILIZING"

                # Display gesture name - green if confirmed, yellow if stabilizing
                gesture_color = (0, 255, 0) if is_confirmed else (0, 255, 255)
                cv2.putText(frame, f"Gesture: {display_gesture}", (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)

                # Display current mode in yellow
                cv2.putText(frame, f"Mode: {display_mode}", (10, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                # Draw debug overlay in top-right corner
                overlay_x = frame_width - 300
                overlay_y = 30

                # Draw semi-transparent background for debug overlay
                overlay_bg = frame.copy()
                cv2.rectangle(overlay_bg, (overlay_x - 10, overlay_y - 25),
                             (frame_width - 10, overlay_y + 115), (0, 0, 0), -1)
                cv2.addWeighted(overlay_bg, 0.6, frame, 0.4, 0, frame)

                # Display top 3 predictions with confidence
                for i, (gesture_name, confidence) in enumerate(top_3_predictions):
                    rank_text = f"{i+1}st:" if i == 0 else f"{i+1}nd:" if i == 1 else f"{i+1}rd:"
                    pred_text = f"{rank_text} {gesture_name}  {int(confidence * 100)}%"
                    cv2.putText(frame, pred_text, (overlay_x, overlay_y + i * 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Display frame count
                cv2.putText(frame, f"Frame: {self.frame_count}", (overlay_x, overlay_y + 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Display buffer voting status
                buffer_size = len(self.gesture_buffer)
                if is_confirmed:
                    stable_text = f"Confirmed: {vote_count}/7 votes"
                    stable_color = (0, 255, 0)
                else:
                    stable_text = f"Buffer: {vote_count}/7 votes ({buffer_size} frames)"
                    stable_color = (0, 255, 255)
                cv2.putText(frame, stable_text, (overlay_x, overlay_y + 115),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, stable_color, 1)

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
