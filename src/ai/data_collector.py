import csv
import os
from pathlib import Path


class DataCollector:
    def __init__(self, data_dir="data", filename="gestures.csv"):
        self.data_dir = Path(data_dir)
        self.filepath = self.data_dir / filename

    def save(self, landmark_list, gesture_name):
        """
        Save hand landmarks to CSV file.

        Args:
            landmark_list: List of 21 landmarks, each with x, y coordinates
            gesture_name: Name of the gesture being saved
        """
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Flatten landmarks into [x1, y1, x2, y2, ..., x21, y21]
        flattened_landmarks = []
        for landmark in landmark_list:
            flattened_landmarks.extend([landmark.x, landmark.y])

        # Prepare row: [gesture_name, x1, y1, x2, y2, ..., x21, y21]
        row = [gesture_name] + flattened_landmarks

        # Append to CSV file
        with open(self.filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
