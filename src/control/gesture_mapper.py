import pyautogui
import time

class GestureMapper:
    def __init__(self):
        self.current_mode = "normal"
        self.drawing_mode = False
        self.two_fingers_start = None
        self.last_confirmed_gesture = None
        self.last_gesture_times = {}
        self.gesture_cooldowns = {
            "open_hand": 2.0,
            "point": 2.0,
            "fist": 2.0,
            "two_fingers": 0.1,
            "three_fingers": 3.0,
            "four_fingers": 3.0,
            "thumbs_up": 2.0,
            "thumbs_down": 2.0,
            "l_shape": 2.0,
            "pinch": 2.0,
        }

    def _can_execute(self, gesture_name):
        now = time.time()
        cooldown = self.gesture_cooldowns.get(gesture_name, 2.0)
        last = self.last_gesture_times.get(gesture_name, 0)
        if now - last >= cooldown:
            self.last_gesture_times[gesture_name] = now
            return True
        return False

    def execute(self, gesture_name):
        if gesture_name == "unknown" or gesture_name is None:
            self.two_fingers_start = None
            self.last_confirmed_gesture = None
            return None

        # Skip if same gesture still confirmed
        if gesture_name == self.last_confirmed_gesture:
            if gesture_name in ["open_hand", "point", "fist"]:
                return self.current_mode
            return None
        self.last_confirmed_gesture = gesture_name

        # two_fingers hold for drawing mode (before cooldown)
        if not self.drawing_mode and gesture_name == "two_fingers":
            if self.two_fingers_start is None:
                self.two_fingers_start = time.time()
                return "scroll"
            elif time.time() - self.two_fingers_start >= 2.0:
                self.drawing_mode = True
                self.two_fingers_start = None
                print("[MODE] Normal → Drawing")
                return "drawing"
            else:
                return "scroll"
        else:
            self.two_fingers_start = None

        if not self._can_execute(gesture_name):
            return None

        # DRAWING MODE
        if self.drawing_mode:
            if gesture_name == "pinch":
                self.drawing_mode = False
                print("[MODE] Drawing → Normal")
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
                return action

        # NORMAL MODE
        else:
            if gesture_name == "fist":
                print("[GESTURE] fist → freeze")
                self.current_mode = "freeze"
                return "freeze"
            elif gesture_name == "open_hand":
                print("[GESTURE] open_hand → move")
                self.current_mode = "move"
                return "move"
            elif gesture_name == "point":
                print("[GESTURE] point → precision")
                self.current_mode = "precision"
                return "precision"
            elif gesture_name == "three_fingers":
                print("[GESTURE] three_fingers → open_keyboard")
                pyautogui.hotkey('win', 'ctrl', 'o')
                return "executed"
            elif gesture_name == "four_fingers":
                print("[GESTURE] four_fingers → screenshot")
                pyautogui.hotkey('win', 'shift', 's')
                return "executed"
            elif gesture_name == "thumbs_up":
                print("[GESTURE] thumbs_up → volume_up")
                pyautogui.press('volumeup')
                return "executed"
            elif gesture_name == "thumbs_down":
                print("[GESTURE] thumbs_down → volume_down")
                pyautogui.press('volumedown')
                return "executed"
            elif gesture_name == "l_shape":
                print("[GESTURE] l_shape → right_click")
                pyautogui.rightClick()
                return "executed"
            elif gesture_name == "pinch":
                print("[GESTURE] pinch → left_click")
                pyautogui.click()
                return "executed"

        return None

    def get_current_mode(self):
        if self.drawing_mode:
            return "drawing"
        return self.current_mode

    def is_drawing_mode(self):
        return self.drawing_mode
