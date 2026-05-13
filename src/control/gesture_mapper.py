import pyautogui
import time


class GestureMapper:
    def __init__(self):
        self.last_action_time = 0
        self.cooldown = 1.0  # 1 second cooldown for actions
        self.current_mode = "normal"  # default cursor mode

        # Gesture stabilizer - requires 3 consecutive frames of same gesture
        self.gesture_history = []
        self.stabilization_frames = 3

        # Mode gestures (no cooldown) - affect cursor behavior
        self.mode_gestures = {
            "fist": "freeze",
            "open_hand": "normal",
            "point": "precise",
            "two_fingers": "scroll"
        }

        # Action gestures (with cooldown) - execute system actions
        self.action_gestures = {
            "three_fingers": self._open_keyboard,
            "four_fingers": self._screenshot,
            "thumbs_up": self._volume_up,
            "thumbs_down": self._volume_down,
            "pinch": self._left_click,
            "l_shape": self._right_click
        }

    def execute(self, gesture_name):
        """
        Execute action or set mode based on gesture name.
        Requires 3 consecutive frames of the same gesture before executing.

        Returns:
            - Mode name (str) for mode gestures
            - "executed" for successful action execution
            - "cooldown" if action is on cooldown
            - "stabilizing" if waiting for gesture stabilization
            - None for unknown gestures
        """
        # Ignore "unknown" gestures - they reset the history
        if gesture_name == "unknown" or gesture_name is None:
            self.gesture_history = []
            return None

        # Add current gesture to history
        self.gesture_history.append(gesture_name)

        # Keep only the last N frames
        if len(self.gesture_history) > self.stabilization_frames:
            self.gesture_history.pop(0)

        # Check if we have enough frames and they're all the same
        if len(self.gesture_history) < self.stabilization_frames:
            return "stabilizing"

        if len(set(self.gesture_history)) != 1:
            # Not all gestures are the same
            return "stabilizing"

        # All frames show the same gesture - proceed with execution
        stabilized_gesture = self.gesture_history[0]

        # Handle mode gestures (no cooldown)
        if stabilized_gesture in self.mode_gestures:
            self.current_mode = self.mode_gestures[stabilized_gesture]
            return self.current_mode

        # Handle action gestures (with cooldown)
        if stabilized_gesture in self.action_gestures:
            current_time = time.time()
            if current_time - self.last_action_time >= self.cooldown:
                self.action_gestures[stabilized_gesture]()
                self.last_action_time = current_time
                # Clear history after successful execution to prevent repeated triggers
                self.gesture_history = []
                return "executed"
            else:
                return "cooldown"

        return None

    def get_current_mode(self):
        """Get the current cursor mode."""
        return self.current_mode

    def _open_keyboard(self):
        """Open on-screen keyboard (Win+Ctrl+O)."""
        pyautogui.hotkey('win', 'ctrl', 'o')

    def _screenshot(self):
        """Take screenshot (Win+Shift+S)."""
        pyautogui.hotkey('win', 'shift', 's')

    def _volume_up(self):
        """Increase system volume."""
        pyautogui.press('volumeup')

    def _volume_down(self):
        """Decrease system volume."""
        pyautogui.press('volumedown')

    def _left_click(self):
        """Perform left mouse click."""
        pyautogui.click()

    def _right_click(self):
        """Perform right mouse click."""
        pyautogui.rightClick()
