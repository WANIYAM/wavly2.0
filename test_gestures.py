"""
Gesture Test Tool
=================
Opens webcam, shows live hand landmarks, and displays raw ML predictions
with confidence percentages. No buffer, no cooldown, no gesture mapper.

Controls:
    Q → Quit
"""

import cv2
import numpy as np
from src.camera.hand_tracker import HandTracker


def main():
    tracker = HandTracker(max_hands=1, detection_confidence=0.7, tracking_confidence=0.7)

    # Load model directly to access predict_proba
    from src.ai.predictor import GesturePredictor
    predictor = GesturePredictor()

    if predictor.model is None:
        print("[ERROR] No trained model found at data/gesture_model.pkl")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return

    print("=== Gesture Tester (Raw Predictions) ===")
    print("Press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame.")
            break

        frame = cv2.flip(frame, 1)
        landmarks = tracker.detect(frame)
        frame = tracker.draw(frame, landmarks)

        if landmarks is not None:
            h, w, _ = frame.shape
            # Use raw MediaPipe normalized coordinates (not pixel coords)
            raw_landmarks = [(lm.x, lm.y) for lm in landmarks.landmark]
            wrist_x, wrist_y = raw_landmarks[0]
            normalized = [(x - wrist_x, y - wrist_y) for x, y in raw_landmarks]

            # Get raw prediction and probabilities
            features = np.array(normalized).flatten().reshape(1, -1)
            probabilities = predictor.model.predict_proba(features)[0]
            prediction = predictor.model.predict(features)[0]
            class_names = predictor.model.classes_

            # Top confidence
            top_idx = np.argmax(probabilities)
            top_conf = probabilities[top_idx] * 100

            # Top 3 predictions
            top_3_indices = np.argsort(probabilities)[-3:][::-1]

            # --- HUD overlay ---
            # Raw prediction with confidence
            color = (0, 255, 0) if top_conf >= 60 else (0, 255, 255) if top_conf >= 45 else (0, 0, 255)
            cv2.putText(frame, f"Prediction: {prediction}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(frame, f"Confidence: {top_conf:.1f}%", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Top 3 gestures
            cv2.putText(frame, "Top 3:", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_offset = 130
            for rank, idx in enumerate(top_3_indices, 1):
                name = class_names[idx]
                conf = probabilities[idx] * 100
                bar_width = int(conf * 2)  # Scale for visual bar
                bar_color = (0, 255, 0) if rank == 1 else (200, 200, 200)

                cv2.putText(frame, f"{rank}. {name}: {conf:.1f}%", (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, bar_color, 1)
                cv2.rectangle(frame, (250, y_offset - 12), (250 + bar_width, y_offset),
                              bar_color, -1)
                y_offset += 28
        else:
            cv2.putText(frame, "No hand detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)

        cv2.imshow("Gesture Tester", frame)

        if (cv2.waitKey(1) & 0xFF) in (ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()


if __name__ == "__main__":
    main()
