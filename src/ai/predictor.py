import pickle
import numpy as np
from pathlib import Path


class GesturePredictor:
    def __init__(self):
        """Load the trained gesture model from data/gesture_model.pkl"""
        model_path = Path(__file__).parent.parent.parent / "data" / "gesture_model.pkl"

        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

    def predict(self, landmark_list):
        """
        Predict gesture from hand landmarks.

        Args:
            landmark_list: List of 21 (x, y) coordinate pairs

        Returns:
            str: Predicted gesture name, or "unknown" if confidence < 45%
        """
        # Flatten the landmark list into a 1D array (42 features)
        features = np.array(landmark_list).flatten().reshape(1, -1)

        # Get prediction probabilities
        probabilities = self.model.predict_proba(features)[0]

        # Get top 2 predictions
        top_2_indices = np.argsort(probabilities)[-2:][::-1]
        top_confidence = probabilities[top_2_indices[0]]
        second_confidence = probabilities[top_2_indices[1]]

        # Get the predicted class
        prediction = self.model.predict(features)[0]

        # Get class names and create probability dict
        class_names = self.model.classes_
        prob_dict = {class_names[i]: probabilities[i] for i in range(len(class_names))}

        # Print debugging information every frame
        print(f"\n--- PREDICTION DEBUG ---")
        print(f"Model thinks: {prediction}")
        print(f"Top confidence: {top_confidence:.2%}")
        print(f"Second confidence: {second_confidence:.2%}")
        print(f"Difference: {(top_confidence - second_confidence):.2%}")
        print(f"All probabilities:")
        for gesture, prob in sorted(prob_dict.items(), key=lambda x: x[1], reverse=True):
            print(f"  {gesture}: {prob:.2%}")

        # Special case for four_fingers
        if prediction == "four_fingers" and top_confidence >= 0.35:
            print(f"Returning: {prediction} (confidence {top_confidence:.2%} >= 35% special case)")
            result = prediction

        # Return "unknown" if confidence is below 45%
        elif top_confidence < 0.45:
            print(f"Returning 'unknown' (confidence {top_confidence:.2%} < 45%)")
            result = "unknown"

        # If confidence is between 45-60%, check if second best is more than 20% different
        elif 0.45 <= top_confidence < 0.60:
            confidence_diff = top_confidence - second_confidence
            if confidence_diff <= 0.20:
                print(f"Returning 'unknown' (confidence {top_confidence:.2%} in 45-60% range, but diff {confidence_diff:.2%} <= 20%)")
                result = "unknown"
            else:
                print(f"Returning: {prediction} (confidence {top_confidence:.2%}, diff {confidence_diff:.2%} > 20%)")
                result = prediction

        # If confidence is above 60%, always return the gesture
        else:
            print(f"Returning: {prediction} (confidence {top_confidence:.2%} >= 60%)")
            result = prediction

        # Post-processing override
        if result == "open_hand":
            thumb_tip_x = landmark_list[4][0]
            thumb_base_x = landmark_list[2][0]
            index_base_x = landmark_list[5][0]
            
            # Assuming standard 640px width to calculate 'pixels' from normalized x coords
            distance_pixels = abs(thumb_tip_x - index_base_x) * 640
            
            if distance_pixels <= 30:
                print("OVERRIDE: open_hand → four_fingers")
                result = "four_fingers"

        return result
