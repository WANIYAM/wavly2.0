import pickle
import numpy as np
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

class GesturePredictor:
    def __init__(self):
        """Load the trained gesture model from data/gesture_model.pkl"""
        model_path = Path(__file__).parent.parent.parent / "data" / "gesture_model.pkl"

        if not model_path.exists():
            print("[PREDICTOR] No model found. Running in collection mode only.")
            self.model = None
        else:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)

    def predict(self, landmark_list):
        """
        Predict gesture from hand landmarks.

        Args:
            landmark_list: List of 21 (x, y) coordinate pairs

        Returns:
            str: Predicted gesture name, or "unknown" if confidence < 40% or model not loaded
        """
        if self.model is None:
            return "unknown"

        # Flatten landmark list into a 1D array (42 features)
        # Landmarks are already normalized relative to wrist by data_collector
        features = np.array(landmark_list).flatten().reshape(1, -1)

        # Get prediction probabilities
        probabilities = self.model.predict_proba(features)[0]

        # Get class names
        class_names = self.model.classes_

        # Get top 2 predictions
        top_2_indices = np.argsort(probabilities)[-2:][::-1]
        top_confidence = probabilities[top_2_indices[0]]
        second_confidence = probabilities[top_2_indices[1]]

        # Get prediction from probabilities instead of self.model.predict
        prediction = class_names[top_2_indices[0]]

        # Special case for four_fingers
        if prediction == "four_fingers" and top_confidence >= 0.35:
            result = prediction

        # Return "unknown" if confidence is below 40%
        elif top_confidence < 0.40:
            result = "unknown"

        # If confidence is between 40-55%, check if second best is more than 15% different
        elif 0.40 <= top_confidence < 0.55:
            confidence_diff = top_confidence - second_confidence
            if confidence_diff <= 0.15:
                result = "unknown"
            else:
                result = prediction

        # If confidence is above 55%, always return the gesture
        else:
            result = prediction

        return result
