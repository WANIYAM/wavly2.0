import os
import pyautogui
from src.control.voice_responder import VoiceResponder

class VoiceMapper:
    def __init__(self, voice_responder=None):
        self.voice_responder = voice_responder if voice_responder else VoiceResponder()
        self.commands = {
            "click": lambda: pyautogui.click(),
            "right click": lambda: pyautogui.rightClick(),
            "scroll up": lambda: pyautogui.scroll(5),
            "scroll down": lambda: pyautogui.scroll(-5),
            "screenshot": lambda: pyautogui.hotkey('win', 'shift', 's'),
            "volume up": lambda: pyautogui.press('volumeup'),
            "volume down": lambda: pyautogui.press('volumedown'),
            "open chrome": lambda: os.system('start chrome'),
            "open notepad": lambda: os.system('start notepad'),
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
        self.responses = {
            "click": "Done",
            "right click": "Right click executed",
            "scroll up": "Scrolling up",
            "scroll down": "Scrolling down",
            "screenshot": "Screenshot captured",
            "volume up": "Increasing volume",
            "volume down": "Decreasing volume",
            "open chrome": "Opening Chrome for you",
            "open notepad": "Opening Notepad",
            "switch tab": "Switching tab",
            "close tab": "Closing tab",
            "zoom in": "Zooming in",
            "zoom out": "Zooming out",
            "new tab": "Opening new tab",
            "go back": "Going back",
            "go forward": "Going forward",
            "next slide": "Next slide",
            "previous slide": "Previous slide",
            "start presentation": "Starting presentation",
            "stop presentation": "Ending presentation",
        }

    def execute(self, command):
        if not command:
            return False
            
        # Clean punctuation which Google Speech Recognition often appends
        normalized = command.strip().lower().replace(".", "").replace(",", "").replace("!", "").strip()
        
        # 1. First check for exact match
        matched_cmd = None
        if normalized in self.commands:
            matched_cmd = normalized
            
        # 2. If no exact match, check for keyword/substring matches (e.g. "please open notepad")
        if not matched_cmd:
            for cmd_key in self.commands:
                if cmd_key in normalized:
                    matched_cmd = cmd_key
                    break
                    
        # 3. Add common aliases/synonyms
        if not matched_cmd:
            aliases = {
                "increase volume": "volume up",
                "raise volume": "volume up",
                "louder": "volume up",
                "decrease volume": "volume down",
                "lower volume": "volume down",
                "quieter": "volume down",
                "take screenshot": "screenshot",
                "print screen": "screenshot",
                "snap": "screenshot",
                "launch chrome": "open chrome",
                "start chrome": "open chrome",
                "launch notepad": "open notepad",
                "start notepad": "open notepad",
                "click mouse": "click",
                "left click": "click",
            }
            for alias, target in aliases.items():
                if alias in normalized:
                    matched_cmd = target
                    break

        if matched_cmd:
            try:
                self.commands[matched_cmd]()
                print(f'[VOICE CMD] "{normalized}" matched to "{matched_cmd}" → executed')
                if matched_cmd in self.responses:
                    self.voice_responder.speak(self.responses[matched_cmd])
                return True
            except Exception as e:
                print(f'[VOICE CMD] Error executing "{matched_cmd}": {e}')
                if self.voice_responder:
                    self.voice_responder.speak("I ran into an error executing that, sir.")
                return False
        else:
            print(f'[VOICE CMD] Command not recognized: "{normalized}"')
            if self.voice_responder:
                import random
                failures = [
                    "I'm sorry sir, I couldn't find a mapping for that command.",
                    "I didn't quite catch that, sir.",
                    "Pardon me, sir, could you repeat that?",
                    "Command not recognized, sir."
                ]
                self.voice_responder.speak(random.choice(failures))
            return False
