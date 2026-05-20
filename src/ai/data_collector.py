import csv
from pathlib import Path


class DataCollector:
    def __init__(self, data_dir="data", filename="gestures.csv"):
        self.data_dir = Path(data_dir)
        self.filepath = self.data_dir / filename
        self.buffer = []
        self.buffer_size = 30

    def __del__(self):
        try:
            self.flush()
        except Exception:
            pass

    def save(self, landmark_list, gesture_name):
        """
        Save hand landmarks to CSV file.

        Args:
            landmark_list: List of 21 landmarks, each with x, y coordinates
            gesture_name: Name of the gesture being saved
        """
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Normalize landmarks relative to wrist (landmark 0)
        wrist_x = landmark_list[0].x
        wrist_y = landmark_list[0].y
        normalized = [(lm.x - wrist_x, lm.y - wrist_y) for lm in landmark_list]

        # Flatten landmarks into [x1, y1, x2, y2, ..., x21, y21]
        flattened_landmarks = []
        for x, y in normalized:
            flattened_landmarks.extend([x, y])

        # Prepare row: [gesture_name, x1, y1, x2, y2, ..., x21, y21]
        row = [gesture_name] + flattened_landmarks

        # Append to buffer
        self.buffer.append(row)

        # Write to disk if buffer reaches maximum size
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        """Force write remaining buffer to CSV file."""
        if not self.buffer:
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(self.buffer)
        self.buffer.clear()
