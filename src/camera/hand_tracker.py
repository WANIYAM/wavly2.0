import cv2
import mediapipe as mp


class HandTracker:
    def __init__(self, max_hands=1, detection_confidence=0.5, tracking_confidence=0.5):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

    def detect(self, frame):
        """
        Detect hand landmarks in the given frame.

        Args:
            frame: OpenCV BGR image frame

        Returns:
            List of (landmarks, handedness_label) tuples, one per detected hand.
            handedness_label is "Left" or "Right" (camera-mirrored: MediaPipe "Left" = user's right hand).
            Returns empty list if no hands detected.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks and results.multi_handedness:
            hands_data = []
            for landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label  # "Left" or "Right"
                hands_data.append((landmarks, label))
            return hands_data

        return []

    def get_landmark_list(self, landmarks, frame_width, frame_height):
        """
        Convert normalized landmarks to pixel coordinates.

        Args:
            landmarks: MediaPipe hand landmarks object
            frame_width: Width of the frame in pixels
            frame_height: Height of the frame in pixels

        Returns:
            List of 21 (x, y) pixel coordinate tuples
        """
        landmark_list = []
        for landmark in landmarks.landmark:
            x = int(landmark.x * frame_width)
            y = int(landmark.y * frame_height)
            landmark_list.append((x, y))
        return landmark_list

    def draw(self, frame, landmarks):
        """
        Draw hand landmarks and connections on the frame.

        Args:
            frame: OpenCV BGR image frame
            landmarks: MediaPipe hand landmarks object

        Returns:
            frame: Frame with landmarks drawn
        """
        if landmarks is not None:
            self.mp_drawing.draw_landmarks(
                frame,
                landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )

        return frame

    def close(self):
        """Release MediaPipe resources."""
        self.hands.close()
