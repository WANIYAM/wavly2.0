import pyautogui

class AppProfiles:
    """
    Defines gesture mapping profiles for different applications,
    including Chrome, VLC, PowerPoint, and a default system profile.
    """
    def __init__(self):
        self.profiles = {
            "chrome": {
                "two_fingers": lambda: pyautogui.scroll(3),
                "l_shape": lambda: pyautogui.hotkey('ctrl', 't'),
                "four_fingers": lambda: pyautogui.hotkey('ctrl', 'w'),
                "thumbs_up": lambda: pyautogui.hotkey('alt', 'right'),
                "thumbs_down": lambda: pyautogui.hotkey('alt', 'left'),
                "pinch": lambda: pyautogui.hotkey('ctrl', '='),
                "fist": lambda: pyautogui.hotkey('ctrl', '-'),
            },
            "vlc": {
                "pinch": lambda: pyautogui.press('space'),
                "two_fingers": lambda: pyautogui.hotkey('shift', 'right'),
                "l_shape": lambda: pyautogui.hotkey('shift', 'left'),
                "thumbs_up": lambda: pyautogui.press('volumeup'),
                "thumbs_down": lambda: pyautogui.press('volumedown'),
                "four_fingers": lambda: pyautogui.press('f'),
                "fist": lambda: pyautogui.press('s'),
                "three_fingers": lambda: pyautogui.press('m'),
            },
            "powerpoint": {
                "two_fingers": lambda: pyautogui.press('right'),
                "l_shape": lambda: pyautogui.press('left'),
                "four_fingers": lambda: pyautogui.press('f5'),
                "fist": lambda: pyautogui.press('escape'),
                "thumbs_up": lambda: pyautogui.hotkey('ctrl', '='),
                "thumbs_down": lambda: pyautogui.hotkey('ctrl', '-'),
                "three_fingers": lambda: pyautogui.press('b'),
                "pinch": lambda: pyautogui.press('ctrl'),
            },
            "default": {
                "fist": "freeze",
                "open_hand": "move",
                "point": "precision",
                "two_fingers": "scroll",
                "three_fingers": "open_keyboard",
                "four_fingers": "screenshot",
                "thumbs_up": "volume_up",
                "thumbs_down": "volume_down",
                "l_shape": "right_click",
                "pinch": "left_click"
            }
        }

        # Monkey-patch GestureMapper._get_action_callable to support returning callables directly
        try:
            from src.control.gesture_mapper import GestureMapper
            if not hasattr(GestureMapper, "_original_get_action_callable"):
                GestureMapper._original_get_action_callable = GestureMapper._get_action_callable
                def new_get_action_callable(self_gm, action_name):
                    if callable(action_name):
                        return action_name
                    return self_gm._original_get_action_callable(action_name)
                GestureMapper._get_action_callable = new_get_action_callable
        except Exception:
            pass

    def get_profile(self, app_name):
        """
        Returns the profile dictionary for the given app name.
        If the app name is not found, returns the default profile dictionary.
        """
        if not app_name:
            return self.profiles["default"]
        return self.profiles.get(app_name.lower(), self.profiles["default"])

