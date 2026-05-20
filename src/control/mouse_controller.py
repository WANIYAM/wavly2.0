import pyautogui
import time


class MouseController:
    def __init__(self, smoothing_factor=0.5):
        pyautogui.FAILSAFE = False
        self.screen_width, self.screen_height = pyautogui.size()
        pyautogui.PAUSE = 0.01
        self.smoothing_factor = smoothing_factor
        self.prev_x = None
        self.prev_y = None
        self.last_click_time = 0

    def move(self, x, y, frame_width, frame_height, speed_multiplier=1.0):
        screen_x = int((x / frame_width) * self.screen_width)
        screen_y = int((y / frame_height) * self.screen_height)

        screen_x = max(0, min(screen_x, self.screen_width - 1))
        screen_y = max(0, min(screen_y, self.screen_height - 1))

        # Apply smoothing using weighted average
        if self.prev_x is None or self.prev_y is None:
            # First movement, no smoothing
            smoothed_x = screen_x
            smoothed_y = screen_y
        else:
            # Calculate movement delta
            delta_x = screen_x - self.prev_x
            delta_y = screen_y - self.prev_y

            # Apply speed multiplier to delta
            delta_x = int(delta_x * speed_multiplier)
            delta_y = int(delta_y * speed_multiplier)

            # Apply smoothing with speed-adjusted delta
            smoothed_x = int(self.prev_x + delta_x * (1 - self.smoothing_factor))
            smoothed_y = int(self.prev_y + delta_y * (1 - self.smoothing_factor))

        # Update previous position
        self.prev_x = smoothed_x
        self.prev_y = smoothed_y

        pyautogui.moveTo(smoothed_x, smoothed_y)

    def click(self, typing_mode=False):
        current_time = time.time()
        cooldown = 0.2 if typing_mode else 0.3
        
        if current_time - self.last_click_time >= cooldown:
            pyautogui.click()
            self.last_click_time = current_time
