import pyautogui
import time


class GestureMapper:
    def __init__(self):
        self.current_mode = "normal"  # default cursor mode
        self.drawing_mode = False
        self.two_fingers_start = None
        self.last_executed_gesture = None
        self.last_executed_time = 0
        self.last_gesture_time = 0

        # Normal Mode actions (with cooldown) - execute system actions
        self.normal_actions = {
            "three_fingers": self._open_keyboard,
            "four_fingers": self._screenshot,
            "thumbs_up": self._volume_up,
            "thumbs_down": self._volume_down,
            "l_shape": self._right_click,
            "pinch": self._left_click
        }

    def execute(self, gesture_name):
        """
        Execute action or set mode based on gesture name.

        Returns:
            - string indicating action/mode
            - None for unknown gestures
        """
        current_time = time.time()

        # Reset last_executed_gesture to None after 2 seconds of no gesture
        if current_time - self.last_gesture_time >= 2.0:
            self.last_executed_gesture = None

        if gesture_name == "unknown" or gesture_name is None:
            self.two_fingers_start = None
            return None

        self.last_gesture_time = current_time

        # Define cooldown periods for different gesture types
        gesture_cooldowns = {
            "open_hand": 0.5,
            "point": 0.5,
            "fist": 0.5,
            "four_fingers": 5.0,
            "three_fingers": 3.0,
            "thumbs_up": 3.0,
            "thumbs_down": 3.0,
            "l_shape": 3.0,
            "pinch": 3.0,
            "two_fingers": 3.0
        }

        # Cooldown check: Skip duplicate gestures within their cooldown period
        if gesture_name == self.last_executed_gesture:
            cooldown_period = gesture_cooldowns.get(gesture_name, 3.0)
            if current_time - self.last_executed_time < cooldown_period:
                return None  # Skip execution completely

        # Check for drawing mode switch via two_fingers
        if not self.drawing_mode and gesture_name == "two_fingers":
            if self.two_fingers_start is None:
                self.two_fingers_start = time.time()
                return "scroll"
            elif time.time() - self.two_fingers_start >= 2.0:
                self.drawing_mode = True
                self.two_fingers_start = None
                print("[MODE] Normal → Drawing")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                return "drawing"
            else:
                return "scroll"
        else:
            self.two_fingers_start = None

        # Mode: DRAWING
        if self.drawing_mode:
            if gesture_name == "pinch":
                self.drawing_mode = False
                print("[MODE] Drawing → Normal")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                return "normal"

            drawing_actions = {
                "fist": "clear_canvas",
                "open_hand": "pen_up",
                "point": "pen_down",
                "two_fingers": "change_color",
                "three_fingers": "brush_size_up",
                "four_fingers": "save_drawing",
                "thumbs_up": "undo",
                "thumbs_down": "redo",
                "l_shape": "erase_mode"
            }
            if gesture_name in drawing_actions:
                action = drawing_actions[gesture_name]
                print(f"[GESTURE] {gesture_name} → {action}")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                return action

        # Mode: NORMAL
        else:
            # Mode gestures
            if gesture_name == "fist":
                print("[GESTURE] fist → freeze")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                pyautogui.hotkey('win', 'ctrl', 'o')  # Toggle keyboard (close if open)
                self.current_mode = "freeze"
                return "freeze"
            elif gesture_name == "open_hand":
                print("[GESTURE] open_hand → move")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                self.current_mode = "move"
                return "move"
            elif gesture_name == "point":
                print("[GESTURE] point → precision")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                self.current_mode = "precision"
                return "precision"

            # Action gestures
            if gesture_name in self.normal_actions:
                # Execute the action
                self.normal_actions[gesture_name]()
                action_name = self.normal_actions[gesture_name].__name__.strip('_')
                print(f"[GESTURE] {gesture_name} → {action_name}")
                self.last_executed_gesture = gesture_name
                self.last_executed_time = current_time
                return "executed"

        return None

    def get_current_mode(self):
        """Get the current cursor mode."""
        if self.drawing_mode:
            return "drawing"
        return self.current_mode

    def is_drawing_mode(self):
        """Return whether drawing mode is currently active."""
        return self.drawing_mode

    def _open_keyboard(self):
        pyautogui.hotkey('win', 'ctrl', 'o')

    def _screenshot(self):
        pyautogui.hotkey('win', 'shift', 's')

    def _volume_up(self):
        pyautogui.press('volumeup')

    def _volume_down(self):
        pyautogui.press('volumedown')

    def _right_click(self):
        pyautogui.rightClick()

    def _left_click(self):
        pyautogui.click()
