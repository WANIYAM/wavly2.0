import pyautogui
import time


class GestureMapper:
    def __init__(self):
        self.last_action_time = 0
        self.cooldown = 1.0  # 1 second cooldown for actions
        self.current_mode = "normal"  # default cursor mode
        self.typing_mode = False



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
            "peace": self._open_browser,
            "l_shape": self._right_click
        }

    def execute(self, gesture_name):
        """
        Execute action or set mode based on gesture name.

        Returns:
            - Mode name (str) for mode gestures
            - "executed" for successful action execution
            - "cooldown" if action is on cooldown
            - None for unknown gestures
        """
        if gesture_name == "unknown" or gesture_name is None:
            return None

        # Print the received gesture and its mapped action
        mapped_action = None
        if gesture_name in self.mode_gestures:
            mapped_action = self.mode_gestures[gesture_name]
        elif gesture_name in self.action_gestures:
            mapped_action = self.action_gestures[gesture_name].__name__.lstrip('_')
            
        if mapped_action:
            print(f"MAPPER RECEIVED: {gesture_name} → {mapped_action}")

        # Handle mode gestures (no cooldown)
        if gesture_name in self.mode_gestures:
            if gesture_name == "fist":
                self.typing_mode = False
            self.current_mode = self.mode_gestures[gesture_name]
            return self.current_mode

        # Handle action gestures (with cooldown)
        if gesture_name in self.action_gestures:
            current_time = time.time()
            if current_time - self.last_action_time >= self.cooldown:
                self.action_gestures[gesture_name]()
                self.last_action_time = current_time
                return "executed"
            else:
                return "cooldown"

        return None

    def get_current_mode(self):
        """Get the current cursor mode."""
        return self.current_mode

    def is_typing_mode(self):
        """Return whether typing mode is currently active."""
        return self.typing_mode

    def _open_keyboard(self):
        """Open on-screen keyboard (Win+Ctrl+O)."""
        self.typing_mode = True
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

    def _open_browser(self):
        """Open a new browser tab."""
        pyautogui.hotkey('ctrl', 't')

    def _right_click(self):
        """Perform right mouse click."""
        pyautogui.rightClick()
