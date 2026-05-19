import pyautogui
import time
from src.control.context_detector import ContextDetector
from src.control.app_profiles import AppProfiles

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
        self.context_detector = ContextDetector()
        self.app_profiles = AppProfiles()
        self.current_app = "default"
        self.last_app_check = 0
        self.app_check_interval = 2.0
        self.prev_two_fingers_y = None

    def _can_execute(self, gesture_name):
        now = time.time()
        cooldown_name = gesture_name
        if cooldown_name in ["two_fingers_up", "two_fingers_down"]:
            cooldown_name = "two_fingers"
        cooldown = self.gesture_cooldowns.get(cooldown_name, 2.0)
        last = self.last_gesture_times.get(gesture_name, 0)
        if now - last >= cooldown:
            self.last_gesture_times[gesture_name] = now
            return True
        return False

    def execute(self, gesture_name):
        # Check active app every 2 seconds
        now = time.time()
        if now - self.last_app_check >= self.app_check_interval:
            new_app = self.context_detector.get_active_app()
            if new_app != self.current_app:
                self.current_app = new_app
                print(f"[CONTEXT] App changed → {self.current_app}")
            self.last_app_check = now

        if gesture_name == "unknown" or gesture_name is None:
            self.two_fingers_start = None
            self.last_confirmed_gesture = None
            self.prev_two_fingers_y = None
            return None

        # Skip if same gesture still confirmed
        if gesture_name == self.last_confirmed_gesture:
            if gesture_name in ["open_hand", "point", "fist"]:
                return self.current_mode
            return None
        self.last_confirmed_gesture = gesture_name

        # two_fingers hold for drawing mode (before cooldown)
        if self.current_app == "default" and not self.drawing_mode and gesture_name == "two_fingers":
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

        # Track two_fingers direction using caller's landmark_list
        if gesture_name == "two_fingers":
            try:
                import sys
                frame = sys._getframe(1)
                if 'landmark_list' in frame.f_locals:
                    landmark_list = frame.f_locals['landmark_list']
                    if landmark_list and len(landmark_list) > 8:
                        current_y = landmark_list[8][1]
                        if self.prev_two_fingers_y is not None:
                            dy = current_y - self.prev_two_fingers_y
                            if dy < -10:
                                gesture_name = "two_fingers_up"
                            elif dy > 10:
                                gesture_name = "two_fingers_down"
                        self.prev_two_fingers_y = current_y
            except Exception:
                pass
        else:
            self.prev_two_fingers_y = None

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
            # Fallback for drawing mode if gesture got mapped to up/down
            resolved_drawing_gesture = gesture_name
            if resolved_drawing_gesture in ["two_fingers_up", "two_fingers_down"]:
                resolved_drawing_gesture = "two_fingers"

            if resolved_drawing_gesture in drawing_actions:
                action = drawing_actions[resolved_drawing_gesture]
                print(f"[GESTURE] {resolved_drawing_gesture} → {action}")
                return action

        # NORMAL MODE
        else:
            profile = self.app_profiles.get_profile(self.current_app)
            if gesture_name in profile and self.current_app != "default":
                profile[gesture_name]()
                print(f"[GESTURE] {gesture_name} → {self.current_app} action")
                return "executed"

        return None

    def _get_action_callable(self, action_name):
        action_map = {
            # Chrome actions
            "scroll_up": lambda: pyautogui.scroll(300),
            "scroll_down": lambda: pyautogui.scroll(-300),
            "new_tab": lambda: pyautogui.hotkey('ctrl', 't'),
            "close_tab": lambda: pyautogui.hotkey('ctrl', 'w'),
            "forward": lambda: pyautogui.hotkey('alt', 'right'),
            "back": lambda: pyautogui.hotkey('alt', 'left'),
            "zoom_in": lambda: pyautogui.hotkey('ctrl', '=' if self.current_app == "chrome" else '+') if self.current_app == "chrome" else (lambda: pyautogui.hotkey('ctrl', '=')),
            "zoom_out": lambda: pyautogui.hotkey('ctrl', '-'),
            
            # VLC actions
            "play_pause": lambda: pyautogui.press('space'),
            "seek_forward": lambda: pyautogui.hotkey('shift', 'right'),
            "seek_backward": lambda: pyautogui.hotkey('shift', 'left'),
            "volume_up": lambda: pyautogui.press('volumeup'),
            "volume_down": lambda: pyautogui.press('volumedown'),
            "fullscreen": lambda: pyautogui.press('f' if self.current_app == "vlc" else 'f5'),
            "stop": lambda: pyautogui.press('s'),
            "mute": lambda: pyautogui.press('m'),
            
            # PowerPoint actions
            "next_slide": lambda: pyautogui.press('right'),
            "previous_slide": lambda: pyautogui.press('left'),
            "end_slideshow": lambda: pyautogui.press('escape'),
            "black_screen": lambda: pyautogui.press('b'),
            "laser_pointer": lambda: pyautogui.hotkey('ctrl', 'l'),
            
            # Default actions / Mode switching
            "freeze": lambda: self._set_mode("freeze"),
            "move": lambda: self._set_mode("move"),
            "precision": lambda: self._set_mode("precision"),
            "scroll": lambda: None,
            "open_keyboard": lambda: pyautogui.hotkey('win', 'ctrl', 'o'),
            "screenshot": lambda: pyautogui.hotkey('win', 'shift', 's'),
            "right_click": lambda: pyautogui.rightClick(),
            "left_click": lambda: pyautogui.click()
        }
        return action_map.get(action_name, lambda: None)

    def _set_mode(self, mode):
        self.current_mode = mode

    def get_current_mode(self):
        if self.drawing_mode:
            return "drawing"
        return self.current_mode

    def is_drawing_mode(self):
        return self.drawing_mode
