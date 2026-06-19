"""
Gesture Recording Tool
======================
Opens webcam, displays live hand landmarks, and records labeled gesture data.

Controls:
    0-9  → Set gesture label
    R    → Toggle recording on/off
    Q    → Quit
"""

import cv2
from src.camera.hand_tracker import HandTracker
from src.ai.data_collector import DataCollector

# Gesture label mapping
GESTURE_LABELS = {
    0: "fist",
    1: "open_hand",
    2: "point",
    3: "two_fingers",
    4: "three_fingers",
    5: "four_fingers",
    6: "thumbs_up",
    7: "thumbs_down",
    8: "l_shape",
    9: "pinch",
}


def main():
    tracker = HandTracker(max_hands=1, detection_confidence=0.7, tracking_confidence=0.7)
    collector = DataCollector()

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return

    current_label = 0
    recording = False
    sample_counts = {name: 0 for name in GESTURE_LABELS.values()}

    print("=== Gesture Recorder ===")
    print("Press 0-9 to set gesture label")
    print("Press R to toggle recording")
    print("Press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read frame.")
            break

        frame = cv2.flip(frame, 1)
        landmarks = tracker.detect(frame)

        # Draw hand landmarks on the frame
        frame = tracker.draw(frame, landmarks)

        # Record data when enabled and hand is visible
        if recording and landmarks is not None:
            gesture_name = GESTURE_LABELS[current_label]
            collector.save(landmarks.landmark, gesture_name)
            sample_counts[gesture_name] += 1

        # --- HUD overlay ---
        gesture_name = GESTURE_LABELS[current_label]
        status_text = "RECORDING" if recording else "PAUSED"
        status_color = (0, 0, 255) if recording else (128, 128, 128)

        # Status and current gesture
        cv2.putText(frame, f"Status: {status_text}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        cv2.putText(frame, f"Gesture: [{current_label}] {gesture_name}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Sample counts per gesture
        y_offset = 100
        cv2.putText(frame, "Samples:", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25
        for idx, name in GESTURE_LABELS.items():
            count = sample_counts[name]
            highlight = (0, 255, 255) if idx == current_label else (200, 200, 200)
            cv2.putText(frame, f"  {idx}: {name} = {count}", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, highlight, 1)
            y_offset += 20

        # Hand detection indicator
        hand_status = "Hand: DETECTED" if landmarks else "Hand: ---"
        hand_color = (0, 255, 0) if landmarks else (0, 0, 200)
        cv2.putText(frame, hand_status, (10, y_offset + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, hand_color, 1)

        cv2.imshow("Gesture Recorder", frame)

        # --- Key handling ---
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('r') or key == ord('R'):
            recording = not recording
            state = "ON" if recording else "OFF"
            print(f"[INFO] Recording {state} — gesture: [{current_label}] {gesture_name}")
        elif ord('0') <= key <= ord('9'):
            current_label = key - ord('0')
            print(f"[INFO] Label set to [{current_label}] {GESTURE_LABELS[current_label]}")

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    tracker.close()

    print("\n=== Final Sample Counts ===")
    for idx, name in GESTURE_LABELS.items():
        print(f"  {idx}: {name} = {sample_counts[name]}")
    total = sum(sample_counts.values())
    print(f"  Total: {total}")


if __name__ == "__main__":
    main()
