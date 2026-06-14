import math
import pyautogui
import time


class MouseController:
    def __init__(self, smoothing_factor=0.7):
        pyautogui.FAILSAFE = False
        self.screen_width, self.screen_height = pyautogui.size()
        pyautogui.PAUSE = 0.01
        self.smoothing_factor = smoothing_factor
        self.prev_x = None
        self.prev_y = None
        self.last_click_time = 0

    def move(self, x, y, frame_width, frame_height, speed_multiplier=1.0):
        # Add margin compensation so hand doesn't need to reach extreme edges
        margin_x = 0.1  # 10% margin on each side
        margin_y = 0.1

        # Normalize with margin
        norm_x = (x / frame_width - margin_x) / (1 - 2 * margin_x)
        norm_y = (y / frame_height - margin_y) / (1 - 2 * margin_y)

        # Clamp normalized values
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Map to screen
        screen_x = int(norm_x * self.screen_width)
        screen_y = int(norm_y * self.screen_height)

        # Clamp to screen bounds
        screen_x = max(0, min(screen_x, self.screen_width - 1))
        screen_y = max(0, min(screen_y, self.screen_height - 1))

        # Apply smoothing using exponential moving average
        if self.prev_x is None or self.prev_y is None:
            smoothed_x = screen_x
            smoothed_y = screen_y
        else:
            alpha = (1 - self.smoothing_factor) * speed_multiplier
            smoothed_x = int(self.prev_x * self.smoothing_factor + screen_x * alpha)
            smoothed_y = int(self.prev_y * self.smoothing_factor + screen_y * alpha)

        # Clamp again after smoothing
        smoothed_x = max(0, min(smoothed_x, self.screen_width - 1))
        smoothed_y = max(0, min(smoothed_y, self.screen_height - 1))

        # Dead zone filter to ignore micro-jitter and reset stale EWMA
        if self.prev_x is not None and self.prev_y is not None:
            dist = math.sqrt((smoothed_x - self.prev_x) ** 2 + (smoothed_y - self.prev_y) ** 2)
            if dist <= 3:
                return

        self.prev_x = smoothed_x
        self.prev_y = smoothed_y
        pyautogui.moveTo(smoothed_x, smoothed_y)

    def click(self, typing_mode=False):
        current_time = time.time()
        cooldown = 0.2 if typing_mode else 0.3
        
        if current_time - self.last_click_time >= cooldown:
            pyautogui.click()
            self.last_click_time = current_time
