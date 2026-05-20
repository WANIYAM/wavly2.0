import pyautogui
import time

class AppProfiles:
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
                "pinch": lambda: pyautogui.hotkey('ctrl', 'l'),
            },
        }

    def get_profile(self, app_name):
        if not app_name or app_name == "default":
            return {}
        return self.profiles.get(app_name.lower(), {})
