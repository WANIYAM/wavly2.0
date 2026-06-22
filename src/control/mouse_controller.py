import pyautogui
import time


class MouseController:
    """Relative (delta-based) cursor control with a 'clutch'.

    Instead of mapping the hand's absolute position in the frame to an absolute
    screen position, the cursor accumulates the *movement* of the hand between
    frames. The cursor holds its own persistent position, so when the hand
    leaves the frame and re-appears (or a non-moving gesture interrupts control),
    the cursor stays exactly where it was and resumes moving relatively from
    there. This lets the user re-stroke (like a trackpad / lifting a mouse) to
    reach any screen edge or corner.
    """

    def __init__(self, sensitivity=1.6, smoothing_factor=0.4):
        pyautogui.FAILSAFE = False
        # No inter-call delay: move() runs in the per-frame hot loop, so any
        # pause adds direct cursor latency.
        pyautogui.PAUSE = 0.0
        self.screen_width, self.screen_height = pyautogui.size()

        # Gain: how far the cursor travels relative to hand motion.
        # 1.0 => one full-frame hand swipe maps to one full screen width.
        self.sensitivity = sensitivity
        # EWMA blend on the velocity: vel = vel * s + target * (1 - s).
        # 0.0 = no smoothing (snappiest, most jitter); closer to 1.0 = heavier
        # smoothing (smoother, more lag). 0.4 stays responsive while filtering.
        self.smoothing_factor = smoothing_factor

        # Last hand fingertip position (frame pixels). None => needs a clutch
        # (re-anchor without moving on the next frame).
        self.prev_hand_x = None
        self.prev_hand_y = None

        # Persistent cursor position kept as float for sub-pixel accumulation.
        cur_x, cur_y = pyautogui.position()
        self.cur_x = float(cur_x)
        self.cur_y = float(cur_y)

        # Smoothed per-frame velocity (screen px/frame).
        self.vel_x = 0.0
        self.vel_y = 0.0

        self.last_click_time = 0

    def reseed(self):
        """Drop the hand reference (the 'clutch' / pen-lift).

        The next move() call re-anchors to the hand's new position without
        moving the cursor. Call this once when cursor control is interrupted:
        hand lost, fist / non-moving gesture, or stabilizing between gestures.
        """
        self.prev_hand_x = None
        self.prev_hand_y = None
        self.vel_x = 0.0
        self.vel_y = 0.0

    def move(self, hand_x, hand_y, frame_width, frame_height, speed_multiplier=1.0):
        # Guard against malformed frame dimensions (avoid divide-by-zero below).
        if frame_width <= 0 or frame_height <= 0:
            return

        # Clutch: first frame after (re)acquisition anchors only, no movement.
        if self.prev_hand_x is None or self.prev_hand_y is None:
            self.prev_hand_x = hand_x
            self.prev_hand_y = hand_y
            # Re-sync our cached cursor to the real one in case it was moved
            # elsewhere (voice command, another input) while control was idle.
            cx, cy = pyautogui.position()
            self.cur_x = float(cx)
            self.cur_y = float(cy)
            return

        # Raw hand delta in frame pixels.
        dx = hand_x - self.prev_hand_x
        dy = hand_y - self.prev_hand_y

        # Re-acquisition jump rejection: an implausibly large single-frame jump
        # means the hand teleported (re-entered elsewhere / tracking glitch).
        # Re-anchor here and drop this whole frame's motion so the cursor never
        # flings. This is glitch-rejection, so both axes are dropped together.
        if abs(dx) > 0.20 * frame_width or abs(dy) > 0.20 * frame_height:
            self.prev_hand_x = hand_x
            self.prev_hand_y = hand_y
            self.vel_x = 0.0
            self.vel_y = 0.0
            return

        # Hand-space dead zone: hold the anchor (don't update prev_hand) so true
        # jitter oscillates around it and cancels, while slow intentional motion
        # still accumulates past the threshold within a couple of frames.
        if abs(dx) < 1.5 and abs(dy) < 1.5:
            return

        self.prev_hand_x = hand_x
        self.prev_hand_y = hand_y

        # Normalize delta by frame size (resolution-independent), then scale to
        # screen space by the gain and the per-gesture speed multiplier.
        gain = self.sensitivity * speed_multiplier
        target_vx = (dx / frame_width) * self.screen_width * gain
        target_vy = (dy / frame_height) * self.screen_height * gain

        # Low-pass the velocity to tame jitter while staying responsive.
        s = self.smoothing_factor
        self.vel_x = self.vel_x * s + target_vx * (1.0 - s)
        self.vel_y = self.vel_y * s + target_vy * (1.0 - s)

        # Accumulate onto the persistent cursor position and clamp to screen.
        new_x = self.cur_x + self.vel_x
        new_y = self.cur_y + self.vel_y
        clamped_x = max(0.0, min(new_x, self.screen_width - 1))
        clamped_y = max(0.0, min(new_y, self.screen_height - 1))

        # Kill velocity on any axis that hit a screen edge so it doesn't keep
        # pushing into the boundary (which makes edges feel sticky/unresponsive).
        if clamped_x != new_x:
            self.vel_x = 0.0
        if clamped_y != new_y:
            self.vel_y = 0.0

        self.cur_x = clamped_x
        self.cur_y = clamped_y

        pyautogui.moveTo(int(self.cur_x), int(self.cur_y))

    def click(self, typing_mode=False):
        current_time = time.time()
        cooldown = 0.2 if typing_mode else 0.3

        if current_time - self.last_click_time >= cooldown:
            pyautogui.click()
            self.last_click_time = current_time
