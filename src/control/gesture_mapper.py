import pyautogui
import time
from src.control.context_detector import ContextDetector
from src.control.app_profiles import AppProfiles

class GestureMapper:
    def __init__(self, voice_responder=None):
        self.current_mode = "normal"
        self.drawing_mode = False
        self.voice_responder = voice_responder
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
            "spider_man": 2.0,
        }
        self.context_detector = ContextDetector()
        self.app_profiles = AppProfiles()
        self.current_app = "default"
        self.last_app_check = 0
        self.app_check_interval = 2.0
        self.current_hand_y = 0

    def _can_execute(self, gesture_name):
        now = time.time()
        cooldown_name = gesture_name
        if cooldown_name in ["two_fingers_up", "two_fingers_down"]:
            cooldown_name = "two_fingers"
        cooldown = self.gesture_cooldowns.get(cooldown_name, 2.0)
        if self.current_app == "powerpoint" and cooldown_name in ["two_fingers", "l_shape"]:
            cooldown = 0.8
        last = self.last_gesture_times.get(gesture_name, 0)
        if now - last >= cooldown:
            self.last_gesture_times[gesture_name] = now
            return True
        return False

    def execute(self, gesture_name):
        if gesture_name == "unknown" or gesture_name is None:
            self.two_fingers_start = None
            self.last_confirmed_gesture = None
            self.prev_two_fingers_y = None
            return None

        # DRAWING MODE is handled separately with its own dedup/cooldown so the
        # continuous tools (point=draw, open_hand=erase, pinch=drag) never fall
        # through to the normal-mode cursor / scroll / click logic.
        if self.drawing_mode:
            return self._execute_drawing(gesture_name)

        # ===================== NORMAL MODE =====================
        # spider_man -> Toggle Drawing Mode

        # Continuous gestures that bypass deduplication completely
        continuous_gestures = ["two_fingers", "thumbs_up", "thumbs_down"]

        # Skip if same gesture still confirmed
        if gesture_name == self.last_confirmed_gesture:
            if gesture_name in ["open_hand", "point", "fist"]:
                return self.current_mode
            if gesture_name not in continuous_gestures:
                return None
        self.last_confirmed_gesture = gesture_name

        if not self._can_execute(gesture_name):
            return None

        # App-specific profiles take precedence in normal mode
        if self.current_app != "default":
            profile = self.app_profiles.get_profile(self.current_app)
            if gesture_name in profile:
                profile[gesture_name]()
                print(f"[GESTURE] {gesture_name} → {self.current_app} action")
                return "executed"

        # Default mode gestures
        if gesture_name == "spider_man":
            self.drawing_mode = True
            print("[MODE] Normal → Drawing")
            if self.voice_responder:
                self.voice_responder.system_speak("Drawing mode on")
            return "drawing"
        elif gesture_name == "fist":
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
        elif gesture_name == "two_fingers":
            if self.current_hand_y < 300:
                pyautogui.scroll(3)
            else:
                pyautogui.scroll(-3)
            print("[GESTURE] two_fingers → scroll")
            return "scroll"
        elif gesture_name == "three_fingers":
            pyautogui.hotkey('win', 'ctrl', 'o')
            print("[GESTURE] three_fingers → keyboard")
            return "executed"
        elif gesture_name == "four_fingers":
            # Capture handled by the overlay (direct grab to clipboard + toast),
            # so we just signal the action instead of opening the Snipping Tool.
            print("[GESTURE] four_fingers → screenshot")
            return "screenshot"
        elif gesture_name == "thumbs_up":
            pyautogui.press('volumeup')
            print("[GESTURE] thumbs_up → volume_up")
            return "executed"
        elif gesture_name == "thumbs_down":
            pyautogui.press('volumedown')
            print("[GESTURE] thumbs_down → volume_down")
            return "executed"
        elif gesture_name == "l_shape":
            pyautogui.rightClick()
            print("[GESTURE] l_shape → right_click")
            return "executed"
        elif gesture_name == "pinch":
            pyautogui.click()
            print("[GESTURE] pinch → left_click")
            return "executed"

        return None

    def _execute_drawing(self, gesture_name):
        """Resolve a confirmed gesture while in drawing mode.

        Continuous tools (point=draw, open_hand=erase, pinch=drag) are applied
        per-frame by the overlay from the draw_event stream, so they produce no
        action here. Only the discrete one-shot commands and the exit gesture
        return a value:

            spider_man   -> exit drawing mode ("normal")   [pinch no longer exits]
            fist         -> "clear_canvas"
            thumbs_up    -> "size_up"      (repeats while held, on a cooldown)
            thumbs_down  -> "size_down"    (repeats while held, on a cooldown)
            two_fingers  -> "toggle_palette"
            four_fingers -> "paste_image"
        """
        # Exit — spider_man only. Edge-triggered so a held pose exits just once.
        if gesture_name == "spider_man":
            if self.last_confirmed_gesture == "spider_man":
                return None
            self.last_confirmed_gesture = "spider_man"
            self.drawing_mode = False
            print("[MODE] Drawing → Normal")
            if self.voice_responder:
                self.voice_responder.system_speak("Drawing mode off")
            return "normal"

        # Continuous tools — applied by the overlay, nothing to do here.
        if gesture_name in ["point", "open_hand", "pinch"]:
            self.last_confirmed_gesture = gesture_name
            return None

        drawing_actions = {
            "fist": "clear_canvas",
            "thumbs_up": "size_up",
            "thumbs_down": "size_down",
            "two_fingers": "toggle_palette",
            "four_fingers": "paste_image",
        }
        if gesture_name in drawing_actions:
            held = (gesture_name == self.last_confirmed_gesture)
            self.last_confirmed_gesture = gesture_name
            is_size = gesture_name in ["thumbs_up", "thumbs_down"]
            # Toggles / clear / paste fire once per fresh show; size stepping is
            # allowed to repeat while held so the user can hold to keep growing.
            if held and not is_size:
                return None
            now = time.time()
            cooldown = 0.45 if is_size else 0.8
            if now - self.last_gesture_times.get(gesture_name, 0) < cooldown:
                return None
            self.last_gesture_times[gesture_name] = now
            print(f"[GESTURE] {gesture_name} → {drawing_actions[gesture_name]}")
            return drawing_actions[gesture_name]

        # Anything else (three_fingers, l_shape, …): no-op in drawing mode.
        self.last_confirmed_gesture = gesture_name
        return None

    def _set_mode(self, mode):
        self.current_mode = mode

    def get_current_mode(self):
        if self.drawing_mode:
            return "drawing"
        return self.current_mode

    def is_drawing_mode(self):
        return self.drawing_mode

    def update_hand_position(self, y):
        self.current_hand_y = y
