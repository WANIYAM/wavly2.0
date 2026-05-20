import os
import pyautogui

class VoiceMapper:
    def __init__(self):
        self.commands = {
            "click": lambda: pyautogui.click(),
            "right click": lambda: pyautogui.rightClick(),
            "scroll up": lambda: pyautogui.scroll(5),
            "scroll down": lambda: pyautogui.scroll(-5),
            "screenshot": lambda: pyautogui.hotkey('win', 'shift', 's'),
            "volume up": lambda: pyautogui.press('volumeup'),
            "volume down": lambda: pyautogui.press('volumedown'),
            "open chrome": lambda: os.startfile('chrome'),
            "open notepad": lambda: os.startfile('notepad'),
            "switch tab": lambda: pyautogui.hotkey('ctrl', 'tab'),
            "close tab": lambda: pyautogui.hotkey('ctrl', 'w'),
            "zoom in": lambda: pyautogui.hotkey('ctrl', '='),
            "zoom out": lambda: pyautogui.hotkey('ctrl', '-'),
            "new tab": lambda: pyautogui.hotkey('ctrl', 't'),
            "go back": lambda: pyautogui.hotkey('alt', 'left'),
            "go forward": lambda: pyautogui.hotkey('alt', 'right'),
            "next slide": lambda: pyautogui.press('right'),
            "previous slide": lambda: pyautogui.press('left'),
            "start presentation": lambda: pyautogui.press('f5'),
            "stop presentation": lambda: pyautogui.press('escape'),
        }

    def execute(self, command):
        if not command:
            return False
            
        normalized = command.strip().lower()
        if normalized in self.commands:
            try:
                self.commands[normalized]()
                print(f'[VOICE CMD] "{normalized}" → executed')
                return True
            except Exception as e:
                print(f'[VOICE CMD] Error executing "{normalized}": {e}')
                return False
        return False
