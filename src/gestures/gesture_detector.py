import math


class GestureDetector:
    def __init__(self):
        self.click_threshold = 30

    def is_clicking(self, landmarks):
        """
        Detect pinch gesture (thumb tip close to index fingertip).

        Args:
            landmarks: MediaPipe hand landmarks

        Returns:
            bool: True if pinch detected, False otherwise
        """
        if not landmarks:
            return False

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]

        distance = math.sqrt(
            (thumb_tip.x - index_tip.x) ** 2 +
            (thumb_tip.y - index_tip.y) ** 2
        )

        distance_pixels = distance * 1000

        return distance_pixels < self.click_threshold

    def is_right_clicking(self, landmarks):
        """
        Detect right-click gesture (thumb tip close to middle fingertip).

        Args:
            landmarks: MediaPipe hand landmarks

        Returns:
            bool: True if right-click gesture detected, False otherwise
        """
        if not landmarks:
            return False

        thumb_tip = landmarks[4]
        middle_tip = landmarks[12]

        distance = math.sqrt(
            (thumb_tip.x - middle_tip.x) ** 2 +
            (thumb_tip.y - middle_tip.y) ** 2
        )

        distance_pixels = distance * 1000

        return distance_pixels < self.click_threshold

    def is_scrolling(self, landmarks):
        """
        Detect scroll gesture (index and middle fingers extended and close together).

        Args:
            landmarks: MediaPipe hand landmarks

        Returns:
            bool: True if scroll gesture detected, False otherwise
        """
        if not landmarks:
            return False

        # Check if index finger is extended (tip above PIP joint)
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        index_extended = index_tip.y < index_pip.y

        # Check if middle finger is extended (tip above PIP joint)
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        middle_extended = middle_tip.y < middle_pip.y

        # Check if index and middle fingers are close together
        distance = math.sqrt(
            (index_tip.x - middle_tip.x) ** 2 +
            (index_tip.y - middle_tip.y) ** 2
        )
        distance_pixels = distance * 1000
        close_together = distance_pixels < 50

        return index_extended and middle_extended and close_together
