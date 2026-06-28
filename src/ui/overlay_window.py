import time
import math
from collections import deque

import numpy as np
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QImage, QPolygonF

from src.ui.vision_thread import VisionThread

try:
    from scipy import ndimage as _ndimage
    _HAS_SCIPY = True
except Exception:  # scipy ships with scikit-learn, but degrade gracefully
    _HAS_SCIPY = False


class _LowPass:
    """First-order low-pass stage used by the One-Euro filter."""

    def __init__(self):
        self.y = None

    def filter(self, x, alpha):
        if self.y is None:
            self.y = x
        else:
            self.y = alpha * x + (1.0 - alpha) * self.y
        return self.y


class OneEuroFilter:
    """One-Euro filter: smooths jitter while the hand moves slowly yet stays
    responsive on fast motion — exactly what smooth freehand drawing needs.
    Filters a single scalar; use one instance per axis.
    """

    def __init__(self, min_cutoff=1.2, beta=0.02, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self._x = _LowPass()
        self._dx = _LowPass()
        self._last_t = None
        self._last_x = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x, t):
        if self._last_t is None:
            self._last_t = t
            self._last_x = x
            self._x.filter(x, 1.0)
            return x
        dt = t - self._last_t
        if dt <= 0.0:
            dt = 1e-3
        self._last_t = t
        dx = (x - self._last_x) / dt
        self._last_x = x
        edx = self._dx.filter(dx, self._alpha(self.d_cutoff, dt))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self._x.filter(x, self._alpha(cutoff, dt))


class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window flags
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )

        # 2. Translucent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 3. Fullscreen transparent window on top of everything
        self.showFullScreen()

        # 4. Create QPixmap canvas buffer same size as screen
        screen_geometry = QApplication.primaryScreen().geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()

        self.canvas = QPixmap(self.screen_width, self.screen_height)
        self.canvas.fill(Qt.GlobalColor.transparent)

        # ---------------- Drawing model ----------------
        # Strokes live on a raster canvas (pixel-accurate draw + pointer-erase);
        # pasted images are separate objects rendered on top (crisp at any scale).
        self.canvas = QPixmap(self.screen_width, self.screen_height)
        self.canvas.fill(Qt.GlobalColor.transparent)
        self.images = []          # [{orig, center:QPointF, scale, selected, _cache}]
        # Unified pinch manipulation (grab -> translate + scale -> drop). Holds
        # the element currently grabbed: an ink blob lifted off the canvas, or an
        # image. None when nothing is being manipulated.
        self.manip = None

        # Map a central sub-region of the camera frame to the FULL screen so the
        # fingertip can reach every edge/corner (it can't physically touch the
        # frame border while the whole hand stays tracked).
        self.draw_margin = 0.10

        # Rendering gate: drawing layers are only painted while in drawing mode,
        # but kept in memory so they reappear when re-entering.
        self.drawing_active = False

        # Palette of stroke colours
        self.colors = [
            QColor(255, 60, 60),    # red
            QColor(60, 140, 255),   # blue
            QColor(60, 220, 120),   # green
            QColor(255, 220, 0),    # yellow
            QColor(190, 90, 255),   # purple
            QColor(255, 255, 255),  # white
            QColor(255, 140, 0),    # orange
            QColor(20, 20, 20),     # near-black
        ]
        self.current_color = self.colors[0]
        self.brush_size = 6
        self.min_brush = 2
        self.max_brush = 60

        # Pointer / tool state (driven by VisionThread.draw_event)
        self.pointer = None        # QPointF smoothed screen position (or None)
        self.smooth_x = OneEuroFilter()
        self.smooth_y = OneEuroFilter()
        self.current_tool = "hover"
        self.hand_present = False
        self.last_draw_point = None
        self.pinching = False
        self.prev_pinching = False

        # Popup colour palette
        self.palette_open = False
        self.palette_anchor = QPointF(0, 0)
        self.dwell_idx = -1
        self.dwell_start = 0.0
        self.dwell_needed = 0.5

        # Pinch-manipulation smoothing + drop-by-stillness tuning
        self.smooth_mx = OneEuroFilter()   # thumb-index midpoint x (manip position)
        self.smooth_my = OneEuroFilter()   # thumb-index midpoint y
        self.dist_ema = None               # smoothed thumb-index distance (scale)
        # Stillness escalation while an element is grabbed: hold still ~2s to
        # toggle Move <-> Resize, keep holding to ~3.5s total to drop it.
        self.manip_mode_dwell = 2.0
        self.manip_drop_dwell = 3.5

        # Open palm releases a grabbed element; brief guard so the palm doesn't
        # erase right after the drop.
        self.drop_gesture = "open_hand"
        self.drop_guard_until = 0.0

        # Toolbar panel (dwell-to-activate). active_tool is the live draw/erase
        # tool: it follows the gesture (point=draw, open palm=erase) AND can be
        # preset from the panel, and the panel always highlights it.
        self.active_tool = "draw"
        self.panel_items = ["draw", "eraser", "stroke_up", "stroke_down",
                            "color", "paste", "clear"]
        self.panel_dwell_idx = -1
        self.panel_dwell_start = 0.0
        self.panel_activated = False
        self.panel_dwell_needed = 1.0

        # Transient brush-size preview ring
        self.size_preview_until = 0.0

        # Keyboard mode state
        self.keyboard_active = False
        self.kbd_layout = []  # Built on first keyboard mode entry

        # Per-hand dwell state
        self.left_dwell_key = None
        self.left_dwell_start = 0.0
        self.left_pointer = None
        self.left_smooth_x = OneEuroFilter()
        self.left_smooth_y = OneEuroFilter()

        self.right_dwell_key = None
        self.right_dwell_start = 0.0
        self.right_pointer = None
        self.right_smooth_x = OneEuroFilter()
        self.right_smooth_y = OneEuroFilter()

        self.kbd_dwell_time = 0.5  # seconds to trigger key press

        # Modifier state (from left hand gestures)
        self.shift_active = False
        self.ctrl_active = False

        # State variables
        self.current_gesture = "Initializing..."
        self.system_mode = "NORMAL"
        self.active_app_name = "default"
        self.hud_opacity = 1.0

        # Toast notification state (transient messages, e.g. screenshot confirmation)
        self.toast_message = ""
        self.toast_opacity = 0.0
        self.toast_start = 0.0
        self.toast_duration = 2.0   # seconds fully visible before fading
        self.toast_fade = 0.6       # seconds to fade out



        # HUD auto-fade timer
        self.hud_fade_timer = QTimer()
        self.hud_fade_timer.setSingleShot(True)
        self.hud_fade_timer.timeout.connect(self.fade_hud)
        self.hud_fade_timer.start(3000)

        self.voice_status = "STANDBY"
        self.camera_frame = None
        self.pip_width = 280
        self.pip_height = 210
        self.pip_margin = 30

        # Animation properties for the Arc Reactor HUD
        self.pulse_angle = 0.0      # Rotation angle for segments
        self.pulse_val = 0.0        # Breathing pulse intensity (0.0 -> 1.0)
        
        # Continuous animation timer (approx. 33 FPS)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(30)

        # Connect to VisionThread
        self.vision_thread = VisionThread()
        self.vision_thread.draw_event.connect(self.on_draw_event)
        self.vision_thread.keyboard_event.connect(self.on_keyboard_event)
        self.vision_thread.gesture_detected.connect(self.update_gesture_hud)
        self.vision_thread.gesture_command.connect(self.handle_gesture_command)
        self.vision_thread.mode_changed.connect(self.update_system_mode)
        self.vision_thread.app_changed.connect(self.update_app_hud)
        self.vision_thread.voice_status_changed.connect(self.update_voice_status)
        self.vision_thread.frame_ready.connect(self.update_camera_frame)

        self.vision_thread.start()


    def update_gesture_hud(self, gesture_name):
        if gesture_name != self.current_gesture:
            self.current_gesture = gesture_name
            self.hud_opacity = 1.0
            self.hud_fade_timer.start(3000)
            self.update()

    def update_app_hud(self, app_name):
        self.active_app_name = app_name
        self.update()

    def fade_hud(self):
        self.hud_opacity = 0.3
        self.update()

    def update_voice_status(self, status):
        self.voice_status = status
        self.hud_opacity = 1.0
        self.hud_fade_timer.start(3000)
        self.update()

    def update_camera_frame(self, frame):
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        self.camera_frame = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        self.update()

    def draw_pip(self, painter):
        if self.camera_frame is None:
            return

        # Position: bottom-left corner
        pip_x = self.pip_margin
        pip_y = self.screen_height - self.pip_height - self.pip_margin

        # Draw dark background behind pip
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(pip_x - 3, pip_y - 3, self.pip_width + 6, self.pip_height + 6, 8.0, 8.0)

        # Draw electric blue border
        painter.setPen(QPen(QColor(0, 150, 255, 200), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(pip_x - 3, pip_y - 3, self.pip_width + 6, self.pip_height + 6, 8.0, 8.0)

        # Scale and draw camera frame
        scaled = self.camera_frame.scaled(
            self.pip_width, self.pip_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawImage(pip_x, pip_y, scaled)

        # Draw "CAM" label in top-left corner of pip
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor(0, 200, 255))
        painter.drawText(pip_x + 6, pip_y + 14, "CAM")

    def update_animation(self):
        if self.voice_status == "ACTIVE":
            self.pulse_angle = (self.pulse_angle + 6) % 360
        else:
            self.pulse_angle = (self.pulse_angle + 1.5) % 360

        if self.voice_status == "ACTIVE":
            pulse_speed = 0.15
        elif self.voice_status == "LISTENING":
            pulse_speed = 0.05
        else:
            pulse_speed = 0.02
            
        self.pulse_val = abs(math.sin(time.time() * pulse_speed * 10))

        # Fade out the toast notification after its visible duration
        if self.toast_message:
            elapsed = time.time() - self.toast_start
            if elapsed > self.toast_duration:
                self.toast_opacity = max(0.0, 1.0 - (elapsed - self.toast_duration) / self.toast_fade)
                if self.toast_opacity <= 0.0:
                    self.toast_message = ""

        self.update()

    def update_system_mode(self, mode):
        if mode == "keyboard":
            self.system_mode = "KEYBOARD"
            self.keyboard_active = True
            # Build layout on first entry
            if not self.kbd_layout:
                self.kbd_layout = self._build_keyboard_layout()
            # Reset dwell state
            self.left_dwell_key = None
            self.right_dwell_key = None
            self.left_pointer = None
            self.right_pointer = None
            self.left_smooth_x.reset()
            self.left_smooth_y.reset()
            self.right_smooth_x.reset()
            self.right_smooth_y.reset()
            self.shift_active = False
            self.ctrl_active = False
        elif mode == "drawing":
            self.system_mode = "DRAWING"
            self.drawing_active = True
            # Fresh pointer state on entry so we don't streak from a stale point.
            self.smooth_x.reset()
            self.smooth_y.reset()
            self.smooth_mx.reset()
            self.smooth_my.reset()
            self.dist_ema = None
            self.pointer = None
            self.last_draw_point = None
            self.palette_open = False
            self.manip = None
            # Exit keyboard mode if it was active
            if self.keyboard_active:
                self.keyboard_active = False
        else:
            self.system_mode = "NORMAL"
            # Drop anything grabbed, then stop rendering the drawing layers. The
            # canvas + images stay in memory so they reappear on re-entry.
            self._drop_manip()
            self.drawing_active = False
            self.palette_open = False
            self.last_draw_point = None
            self.pointer = None
            # Exit keyboard mode if it was active
            if self.keyboard_active:
                self.keyboard_active = False
        self.update()

    def handle_gesture_command(self, command):
        print(f"[OVERLAY] received command: {command}")
        # While an element is grabbed, ignore discrete commands — they are almost
        # always misreads of the pinching hand, and a stray fist must not clear
        # the canvas mid-manipulation. Drop by holding still first.
        if self.manip is not None:
            return
        if command == "clear_canvas":
            self.canvas.fill(Qt.GlobalColor.transparent)
            self.images.clear()
            self.manip = None
            self.last_draw_point = None
            self.show_toast("Canvas cleared")
            self.update()
        elif command == "size_up":
            self.brush_size = min(self.max_brush, self.brush_size + 4)
            self._flash_size()
        elif command == "size_down":
            self.brush_size = max(self.min_brush, self.brush_size - 4)
            self._flash_size()
        elif command == "toggle_palette":
            self.last_draw_point = None
            self.palette_open = not self.palette_open
            if self.palette_open:
                self.palette_anchor = QPointF(self.pointer) if self.pointer is not None \
                    else QPointF(self.screen_width / 2, self.screen_height / 2)
                self.dwell_idx = -1
            self.update()
        elif command == "paste_image":
            self.last_draw_point = None
            self._paste_image()
        elif command == "screenshot":
            self.take_screenshot()

    def _flash_size(self):
        self.size_preview_until = time.time() + 1.0
        self.show_toast(f"Brush size: {self.brush_size}")
        self.update()

    def _paste_image(self):
        img = QApplication.clipboard().image()
        if img is None or img.isNull():
            self.show_toast("No image in clipboard")
            return
        orig = QPixmap.fromImage(img)
        longest = max(orig.width(), orig.height())
        target = 0.4 * min(self.screen_width, self.screen_height)
        scale = (target / longest) if longest > 0 else 1.0
        center = QPointF(self.pointer) if self.pointer is not None \
            else QPointF(self.screen_width / 2, self.screen_height / 2)
        self._select_only(None)
        self.images.append({"orig": orig, "center": center, "scale": scale,
                            "selected": True, "_cache": None})
        self.palette_open = False
        self.show_toast("Image pasted - pinch to move; hold still ~2s to resize")
        self.update()

    def show_toast(self, message):
        """Show a small transient notification near the top-center of the screen."""
        self.toast_message = message
        self.toast_opacity = 1.0
        self.toast_start = time.time()
        self.update()

    def take_screenshot(self):
        """Capture the whole screen straight to the clipboard (no Snipping Tool).

        The overlay is hidden first so the HUD, camera preview and drawing canvas
        are excluded from the capture, then restored once the grab completes.
        """
        self.hide()
        # Give the compositor a moment to remove the overlay before grabbing.
        QTimer.singleShot(200, self._capture_to_clipboard)

    def _capture_to_clipboard(self):
        try:
            pixmap = QApplication.primaryScreen().grabWindow(0)
            QApplication.clipboard().setPixmap(pixmap)
            print("[SCREENSHOT] Captured to clipboard")
            message = "Screenshot saved to clipboard"
        except Exception as e:
            print(f"[SCREENSHOT] Error: {e}")
            message = "Screenshot failed"
        finally:
            self.showFullScreen()
        self.show_toast(message)

    def draw_toast(self, painter):
        text = self.toast_message
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)

        pad_left = 38
        pad_right = 26
        box_height = 46
        box_width = text_width + pad_left + pad_right
        box_x = (self.screen_width - box_width) / 2.0
        box_y = 70.0
        rect = QRectF(box_x, box_y, box_width, box_height)

        # Background + border, matching the cyberpunk HUD palette
        painter.setBrush(QColor(0, 10, 30, 230))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 12.0, 12.0)
        painter.setPen(QPen(QColor(0, 180, 255, 220), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 12.0, 12.0)

        # Gold accent dot
        dot_cx = box_x + 20
        dot_cy = box_y + box_height / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 200, 0))
        painter.drawEllipse(QPoint(int(dot_cx), int(dot_cy)), 5, 5)

        # Message text (cyan), vertically centered in the box
        painter.setPen(QColor(0, 220, 255))
        text_x = box_x + pad_left
        text_y = box_y + (box_height + metrics.ascent() - metrics.descent()) / 2.0
        painter.drawText(int(text_x), int(text_y), text)

    # ===================== Drawing event pipeline =====================

    def _to_screen(self, x, y, fw, fh):
        # Stretch the central [margin, 1-margin] band of the frame onto the full
        # screen, then clamp — so the reachable hand range covers every corner
        # instead of only the middle of the screen.
        m = self.draw_margin
        span = max(1e-3, 1.0 - 2.0 * m)
        nx = ((x / max(1, fw)) - m) / span
        ny = ((y / max(1, fh)) - m) / span
        nx = min(1.0, max(0.0, nx))
        ny = min(1.0, max(0.0, ny))
        return (min(nx * self.screen_width, self.screen_width - 1.0),
                min(ny * self.screen_height, self.screen_height - 1.0))

    @staticmethod
    def _dist(a, b):
        return math.hypot(a.x() - b.x(), a.y() - b.y())

    def on_draw_event(self, ev):
        """Single per-frame entry point for everything on the drawing surface.
        VisionThread picks the tool from the live gesture; here we turn position
        + tool + pinch into canvas changes. A grabbed element (manipulation) is
        latched and owns the surface until it is dropped.
        """
        present = ev.get("present", True)
        fw = ev.get("frame_w", 640)
        fh = ev.get("frame_h", 480)
        tool = ev.get("tool", "hover")
        pinching = ev.get("pinching", False)

        self.prev_pinching = self.pinching
        self.pinching = pinching
        self.current_tool = tool
        self.hand_present = present

        if not present:
            # Hand gone: drop any held element, lift the pen, hide the cursor.
            self._drop_manip()
            self.last_draw_point = None
            self.pointer = None
            self.smooth_x.reset()
            self.smooth_y.reset()
            self.smooth_mx.reset()
            self.smooth_my.reset()
            self.dist_ema = None
            self.update()
            return

        t = time.time()

        # Index fingertip -> smoothed pointer (draw / erase / hover + cursor).
        rx, ry = self._to_screen(ev["x"], ev["y"], fw, fh)
        sx = self.smooth_x.filter(rx, t)
        sy = self.smooth_y.filter(ry, t)
        new_pt = QPointF(sx, sy)
        if self.pointer is not None:
            if self._dist(new_pt, self.pointer) > 0.25 * self.screen_width:
                self.last_draw_point = None
        self.pointer = new_pt

        # Thumb-index midpoint (manip position) + distance (manip scale). The
        # distance is taken in raw frame pixels so the edge clamp on the mapped
        # midpoint doesn't distort the scale ratio.
        ix, iy = ev["x"], ev["y"]
        tx, ty = ev.get("tx", ix), ev.get("ty", iy)
        dist_raw = math.hypot(ix - tx, iy - ty)
        self.dist_ema = dist_raw if self.dist_ema is None \
            else 0.45 * self.dist_ema + 0.55 * dist_raw
        mrx, mry = self._to_screen((ix + tx) / 2.0, (iy + ty) / 2.0, fw, fh)
        mid = QPointF(self.smooth_mx.filter(mrx, t), self.smooth_my.filter(mry, t))

        # 1. A grabbed element owns the surface. An open palm drops it instantly;
        #    otherwise translate + scale (with the stillness escalation).
        if self.manip is not None:
            if ev.get("gesture") == self.drop_gesture:
                self._drop_manip()
                self.drop_guard_until = t + 0.5
            else:
                self._update_manip(mid, self.dist_ema)
            self.update()
            return

        # 2. Palette open -> the pointer selects a colour instead of drawing.
        if self.palette_open:
            self._handle_palette(new_pt, t)
            self.update()
            return

        # 3. Toolbar panel: dwelling (~1s) on a button activates it. The panel
        #    area never draws.
        if self._panel_rect().contains(new_pt):
            self._handle_panel(new_pt, t)
            self.update()
            return
        self.panel_dwell_idx = -1

        # 4. Pinch just started -> try to grab the element under the fingers.
        if pinching and not self.prev_pinching:
            if self._try_grab(mid, self.dist_ema):
                self.last_draw_point = None
                self.update()
                return

        # 5. Otherwise the tool follows the gesture. Just after a gesture-drop we
        #    suppress draw/erase briefly so the open palm doesn't erase what was
        #    just placed.
        if t < self.drop_guard_until:
            self.last_draw_point = None
        elif tool == "draw":
            self.active_tool = "draw"      # index finger = draw; panel follows
            self._draw_to(new_pt)
        elif tool == "erase":
            self.active_tool = "erase"     # open palm = erase; panel follows
            self._erase_to(new_pt)
        else:  # hover, or pinch over empty space
            self.last_draw_point = None

        self.update()

    # --------------------------- pen / eraser ---------------------------

    def _draw_to(self, pt):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.last_draw_point is None:
            # Anchor + leave a dot so a quick tap still marks.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.current_color)
            painter.drawEllipse(pt, self.brush_size / 2.0, self.brush_size / 2.0)
        else:
            pen = QPen(self.current_color, self.brush_size, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_draw_point, pt)
        painter.end()
        self.last_draw_point = pt

    def _erase_to(self, pt):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        r = max(self.brush_size * 2, 14)
        if self.last_draw_point is None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.GlobalColor.black)  # colour irrelevant under Clear
            painter.drawEllipse(pt, r / 2.0, r / 2.0)
        else:
            pen = QPen(Qt.GlobalColor.black, r, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_draw_point, pt)
        painter.end()
        self.last_draw_point = pt

    # ------------- unified grab / translate / scale / drop -------------

    def _select_only(self, img):
        for other in self.images:
            other["selected"] = (other is img)

    def _try_grab(self, mid, dist):
        """Grab the topmost image, or the connected ink blob, under `mid`.
        On success starts a manipulation and returns True. Grabbing an image
        also raises it to the top (the z-index requirement)."""
        for img in reversed(self.images):
            if self._image_rect(img).contains(mid):
                self.images.remove(img)
                self.images.append(img)            # raise to top
                self._select_only(img)
                self.manip = self._new_manip("image", QPointF(mid), dist,
                                             QPointF(img["center"]), img["scale"],
                                             image=img)
                return True

        layer, origin = self._lift_ink_component(mid)
        if layer is not None:
            self._select_only(None)
            center = QPointF(origin.x() + layer.width() / 2.0,
                             origin.y() + layer.height() / 2.0)
            self.manip = self._new_manip("ink", QPointF(mid), dist,
                                         center, 1.0, layer=layer)
            return True
        return False

    def _new_manip(self, kind, mid, dist, center, scale, image=None, layer=None):
        """Build the manipulation state for a freshly grabbed element. Starts in
        Move mode; stillness escalation toggles Resize then drops."""
        return {
            "kind": kind, "image": image, "layer": layer,
            "grab_mid": QPointF(mid), "grab_center": QPointF(center),
            "center": QPointF(center), "scale": scale,
            "mode": "move", "toggled": False,
            "scale_ref_dist": max(1.0, dist), "scale_ref_scale": scale,
            "still_since": 0.0, "still_anchor_mid": None, "still_anchor_dist": 0.0,
            "last_mid": QPointF(mid),
        }

    def _update_manip(self, mid, dist):
        m = self.manip
        # Translate always follows the thumb-index midpoint.
        m["center"] = m["grab_center"] + (mid - m["grab_mid"])
        # Scale ONLY in Resize mode — Move mode ignores the finger spread so the
        # element can't resize by accident while you reposition it.
        if m["mode"] == "resize":
            lo, hi = (0.2, 6.0) if m["kind"] == "ink" else (0.05, 10.0)
            m["scale"] = min(hi, max(lo,
                             m["scale_ref_scale"] * dist / m["scale_ref_dist"]))
            if m["kind"] == "image":
                m["image"]["scale"] = m["scale"]
        if m["kind"] == "image":
            m["image"]["center"] = m["center"]

        # Stillness escalation. "Still" means BOTH the midpoint and the finger
        # spread are steady (so actively resizing keeps the timer from running),
        # measured against an anchor so a slow drift doesn't read as held:
        #   hold ~mode_dwell  -> toggle Move <-> Resize
        #   hold ~drop_dwell  -> drop the element
        now = time.time()
        anchor = m["still_anchor_mid"]
        if (anchor is not None and self._dist(mid, anchor) < 14.0
                and abs(dist - m["still_anchor_dist"]) < 10.0):
            held = now - m["still_since"]
            if held >= self.manip_drop_dwell:
                self._drop_manip()
                return
            if held >= self.manip_mode_dwell and not m["toggled"]:
                m["toggled"] = True
                if m["mode"] == "move":
                    m["mode"] = "resize"
                    m["scale_ref_dist"] = max(1.0, dist)   # re-baseline: no jump
                    m["scale_ref_scale"] = m["scale"]
                    self.show_toast("Resize mode - spread fingers to scale")
                else:
                    m["mode"] = "move"
                    self.show_toast("Move mode")
        else:
            # Moving (or a fresh stillness window) — (re)anchor and reset.
            m["still_anchor_mid"] = QPointF(mid)
            m["still_anchor_dist"] = dist
            m["still_since"] = now
            m["toggled"] = False
        m["last_mid"] = QPointF(mid)

    def _drop_manip(self):
        m = self.manip
        if m is None:
            return
        if m["kind"] == "ink":
            layer = m["layer"]
            s = m["scale"]
            w = max(1, int(round(layer.width() * s)))
            h = max(1, int(round(layer.height() * s)))
            scaled = layer.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            c = m["center"]
            painter = QPainter(self.canvas)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(int(c.x() - w / 2.0), int(c.y() - h / 2.0), scaled)
            painter.end()
        # Image manipulation already wrote center/scale into the object.
        self.manip = None

    def _lift_ink_component(self, pt):
        """Cut the connected ink blob under `pt` out of the canvas and return it
        as (layer_pixmap, origin_point). Runs once per pinch, on a window around
        the pointer so labeling stays cheap.
        """
        W, H = self.screen_width, self.screen_height
        px, py = int(pt.x()), int(pt.y())
        if not (0 <= px < W and 0 <= py < H):
            return None, None

        image = self.canvas.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.sizeInBytes())
        arr = np.frombuffer(ptr, np.uint8).reshape((H, W, 4)).copy()  # writable BGRA

        R = 320
        x0, y0 = max(0, px - R), max(0, py - R)
        x1, y1 = min(W, px + R), min(H, py + R)
        win = arr[y0:y1, x0:x1, :]
        mask = win[:, :, 3] > 10
        lx, ly = px - x0, py - y0
        if not mask[ly, lx]:
            near = self._nearest_ink(mask, lx, ly, 20)
            if near is None:
                return None, None
            lx, ly = near

        labels, target = self._label_component(mask, lx, ly)
        if target is None:
            return None, None
        comp = labels == target
        ys, xs = np.where(comp)
        if xs.size == 0:
            return None, None
        bx0, bx1 = int(xs.min()), int(xs.max()) + 1
        by0, by1 = int(ys.min()), int(ys.max()) + 1

        sub = win[by0:by1, bx0:bx1, :].copy()
        sub[~comp[by0:by1, bx0:bx1]] = 0
        layer = self._pixmap_from_argb(sub)

        win[comp] = 0  # erase the blob from the canvas copy
        new_image = QImage(arr.data, W, H, 4 * W, QImage.Format.Format_ARGB32).copy()
        self.canvas = QPixmap.fromImage(new_image)
        return layer, QPoint(x0 + bx0, y0 + by0)

    def _label_component(self, mask, lx, ly):
        if not mask[ly, lx]:
            return None, None
        if _HAS_SCIPY:
            structure = np.ones((3, 3), dtype=bool)  # 8-connectivity
            labels, _ = _ndimage.label(mask, structure=structure)
            target = int(labels[ly, lx])
            return labels, (target if target != 0 else None)
        labels = self._flood_label(mask, lx, ly)
        return (labels, 1) if labels is not None else (None, None)

    def _flood_label(self, mask, lx, ly):
        """Bounded BFS flood fill fallback when scipy is unavailable."""
        h, w = mask.shape
        labels = np.zeros((h, w), dtype=np.int32)
        labels[ly, lx] = 1
        dq = deque([(ly, lx)])
        steps = 0
        while dq and steps < 400000:
            cy, cx = dq.popleft()
            steps += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and labels[ny, nx] == 0:
                    labels[ny, nx] = 1
                    dq.append((ny, nx))
        return labels

    @staticmethod
    def _nearest_ink(mask, lx, ly, radius):
        h, w = mask.shape
        for rad in range(1, radius + 1):
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    if abs(dy) != rad and abs(dx) != rad:
                        continue
                    ny, nx = ly + dy, lx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                        return nx, ny
        return None

    @staticmethod
    def _pixmap_from_argb(sub):
        sub = np.ascontiguousarray(sub)
        h, w = sub.shape[:2]
        qimg = QImage(sub.data, w, h, 4 * w, QImage.Format.Format_ARGB32).copy()
        return QPixmap.fromImage(qimg)

    # ------------------------- pasted images -------------------------

    def _image_rect(self, img):
        w = img["orig"].width() * img["scale"]
        h = img["orig"].height() * img["scale"]
        c = img["center"]
        return QRectF(c.x() - w / 2.0, c.y() - h / 2.0, w, h)

    def _scaled_image(self, img):
        w = max(1, int(round(img["orig"].width() * img["scale"])))
        h = max(1, int(round(img["orig"].height() * img["scale"])))
        cache = img.get("_cache")
        if cache is not None and cache[1] == w and cache[2] == h:
            return cache[0]
        # Always scale from the ORIGINAL full-res pixmap so enlarging never
        # compounds pixelation; SmoothTransformation keeps it clean.
        scaled = img["orig"].scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        img["_cache"] = (scaled, w, h)
        return scaled

    # ------------------------- colour palette -------------------------

    def _palette_layout(self):
        n = len(self.colors)
        sw, gap, pad = 46, 10, 16
        panel_w = pad * 2 + n * sw + (n - 1) * gap
        panel_h = pad * 2 + sw + 24
        ax, ay = self.palette_anchor.x(), self.palette_anchor.y()
        x = min(max(10.0, ax - panel_w / 2.0), self.screen_width - panel_w - 10)
        y = min(max(10.0, ay - panel_h - 24), self.screen_height - panel_h - 10)
        panel = QRectF(x, y, panel_w, panel_h)
        rects = []
        cx = x + pad
        cy = y + pad
        for i in range(n):
            rects.append((QRectF(cx, cy, sw, sw), i))
            cx += sw + gap
        return panel, rects

    def _handle_palette(self, pt, t):
        _, rects = self._palette_layout()
        hit = -1
        for rect, i in rects:
            if rect.contains(pt):
                hit = i
                break
        if hit == -1:
            self.dwell_idx = -1
            return
        if hit != self.dwell_idx:
            self.dwell_idx = hit
            self.dwell_start = t
        elif t - self.dwell_start >= self.dwell_needed:
            self.current_color = self.colors[hit]
            self.palette_open = False
            self.dwell_idx = -1
            self.show_toast("Colour selected")

    # ------------------------- toolbar panel -------------------------

    PANEL_BTN = 54
    PANEL_GAP = 8
    PANEL_PAD = 10
    PANEL_MARGIN = 26

    def _panel_rect(self):
        n = len(self.panel_items)
        h = self.PANEL_PAD * 2 + n * self.PANEL_BTN + (n - 1) * self.PANEL_GAP
        w = self.PANEL_PAD * 2 + self.PANEL_BTN
        x = self.screen_width - w - self.PANEL_MARGIN     # right edge
        y = (self.screen_height - h) / 2.0
        return QRectF(x, y, w, h)

    def _panel_layout(self):
        panel = self._panel_rect()
        rects = []
        cx = panel.x() + self.PANEL_PAD
        cy = panel.y() + self.PANEL_PAD
        for i, key in enumerate(self.panel_items):
            rects.append((QRectF(cx, cy, self.PANEL_BTN, self.PANEL_BTN), i, key))
            cy += self.PANEL_BTN + self.PANEL_GAP
        return panel, rects

    def _handle_panel(self, pt, t):
        _, rects = self._panel_layout()
        hit, hit_key = -1, None
        for rect, i, key in rects:
            if rect.contains(pt):
                hit, hit_key = i, key
                break
        if hit == -1:
            self.panel_dwell_idx = -1
            return
        if hit != self.panel_dwell_idx:
            self.panel_dwell_idx = hit
            self.panel_dwell_start = t
            self.panel_activated = False
            return
        if not self.panel_activated and (t - self.panel_dwell_start) >= self.panel_dwell_needed:
            self._activate_panel(hit_key)
            if hit_key in ("stroke_up", "stroke_down"):
                # repeatable: re-arm so holding keeps stepping every ~0.4s
                self.panel_dwell_start = t - (self.panel_dwell_needed - 0.4)
            else:
                self.panel_activated = True

    def _activate_panel(self, key):
        if key == "draw":
            self.active_tool = "draw"
            self.show_toast("Draw tool")
        elif key == "eraser":
            self.active_tool = "erase"
            self.show_toast("Eraser tool")
        elif key == "stroke_up":
            self.brush_size = min(self.max_brush, self.brush_size + 4)
            self._flash_size()
        elif key == "stroke_down":
            self.brush_size = max(self.min_brush, self.brush_size - 4)
            self._flash_size()
        elif key == "color":
            # Pop the palette to the LEFT of the panel so it doesn't overlap it
            # (the panel sits on the right edge).
            pr = self._panel_rect()
            self.palette_anchor = QPointF(pr.left() - 260, pr.center().y())
            self.palette_open = True
            self.dwell_idx = -1
        elif key == "paste":
            self._paste_image()
        elif key == "clear":
            self.canvas.fill(Qt.GlobalColor.transparent)
            self.images.clear()
            self.manip = None
            self.last_draw_point = None
            self.show_toast("Canvas cleared")

    def _paint_panel(self, painter):
        panel, rects = self._panel_layout()
        painter.setBrush(QColor(0, 10, 30, 220))
        painter.setPen(QPen(QColor(0, 150, 255, 200), 1.5))
        painter.drawRoundedRect(panel, 12, 12)
        now = time.time()
        for rect, i, key in rects:
            active = ((key == "draw" and self.active_tool == "draw")
                      or (key == "eraser" and self.active_tool == "erase"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 70, 120, 210) if active else QColor(0, 25, 55, 160))
            painter.drawRoundedRect(rect, 8, 8)
            if active:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(0, 230, 255, 230), 1.6))
                painter.drawRoundedRect(rect, 8, 8)
            self._draw_panel_icon(painter, key, rect)
            if i == self.panel_dwell_idx and not self.panel_activated:
                frac = min(1.0, (now - self.panel_dwell_start) / self.panel_dwell_needed)
                if frac > 0.02:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(QColor(255, 200, 0, 235), 3))
                    painter.drawArc(rect.adjusted(2, 2, -2, -2), 90 * 16, int(-frac * 360 * 16))

    # ===================== Keyboard Mode =====================

    def _build_keyboard_layout(self):
        """Build QWERTY layout: 3 rows of letters + bottom row with Space/Backspace/Enter.
        Returns list of dicts: {"char": str, "rect": QRectF, "shift_char": str}.
        Full-width keyboard, transparent background, positioned at bottom of screen.
        """
        rows = [
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
        ]

        # Keyboard dimensions
        kbd_height = 280
        key_height = 60
        row_gap = 10
        col_gap = 8
        side_margin = 40
        bottom_margin = 30

        # Position at bottom of screen
        kbd_y = self.screen_height - kbd_height - bottom_margin

        keys = []
        current_y = kbd_y + 20

        for row_idx, row in enumerate(rows):
            num_keys = len(row)
            row_width = self.screen_width - 2 * side_margin
            key_width = (row_width - (num_keys - 1) * col_gap) / num_keys

            # Center offset for each row (optional stagger)
            offset_x = side_margin
            if row_idx == 1:
                offset_x += key_width * 0.25  # Slight stagger for home row
            elif row_idx == 2:
                offset_x += key_width * 0.5   # Larger stagger for bottom row

            current_x = offset_x
            for char in row:
                rect = QRectF(current_x, current_y, key_width, key_height)
                keys.append({
                    "char": char.lower(),
                    "shift_char": char.upper(),
                    "rect": rect,
                    "is_special": False,
                })
                current_x += key_width + col_gap

            current_y += key_height + row_gap

        # Bottom row: Space (wide), Backspace, Enter
        current_y += 10
        row_width = self.screen_width - 2 * side_margin
        space_width = row_width * 0.55
        other_width = (row_width - space_width - 2 * col_gap) / 2.0

        current_x = side_margin
        keys.append({
            "char": " ",
            "label": "SPACE",
            "shift_char": " ",
            "rect": QRectF(current_x, current_y, space_width, key_height),
            "is_special": True,
        })
        current_x += space_width + col_gap

        keys.append({
            "char": "backspace",
            "label": "⌫",
            "shift_char": "backspace",
            "rect": QRectF(current_x, current_y, other_width, key_height),
            "is_special": True,
        })
        current_x += other_width + col_gap

        keys.append({
            "char": "enter",
            "label": "↵",
            "shift_char": "enter",
            "rect": QRectF(current_x, current_y, other_width, key_height),
            "is_special": True,
        })

        return keys

    def on_keyboard_event(self, ev):
        """Process per-frame keyboard state: update pointers, detect dwells, handle modifiers."""
        t = time.time()
        fw = ev["frame_w"]
        fh = ev["frame_h"]

        # Extract modifier state from left hand gesture
        left_gesture = ev.get("left_gesture")
        self.shift_active = (left_gesture == "fist")
        self.ctrl_active = (left_gesture == "open_hand")

        # Process left hand pointer
        if ev["left_present"]:
            lx, ly = self._to_screen(ev["left_x"], ev["left_y"], fw, fh)
            sx = self.left_smooth_x.filter(lx, t)
            sy = self.left_smooth_y.filter(ly, t)
            self.left_pointer = QPointF(sx, sy)
            self._handle_dwell("left", self.left_pointer, t)
        else:
            self.left_pointer = None
            self.left_dwell_key = None
            self.left_smooth_x.reset()
            self.left_smooth_y.reset()

        # Process right hand pointer
        if ev["right_present"]:
            rx, ry = self._to_screen(ev["right_x"], ev["right_y"], fw, fh)
            sx = self.right_smooth_x.filter(rx, t)
            sy = self.right_smooth_y.filter(ry, t)
            self.right_pointer = QPointF(sx, sy)
            self._handle_dwell("right", self.right_pointer, t)
        else:
            self.right_pointer = None
            self.right_dwell_key = None
            self.right_smooth_x.reset()
            self.right_smooth_y.reset()

        self.update()

    def _handle_dwell(self, hand, pointer, t):
        """Check if pointer is dwelling on a key; trigger press after kbd_dwell_time."""
        # Get dwell state for this hand
        if hand == "left":
            dwell_key_attr = "left_dwell_key"
            dwell_start_attr = "left_dwell_start"
        else:
            dwell_key_attr = "right_dwell_key"
            dwell_start_attr = "right_dwell_start"

        current_dwell_key = getattr(self, dwell_key_attr)
        current_dwell_start = getattr(self, dwell_start_attr)

        # Find which key the pointer is over
        hit_key = None
        for key in self.kbd_layout:
            if key["rect"].contains(pointer):
                hit_key = key
                break

        if hit_key is None:
            # Not over any key: reset dwell
            setattr(self, dwell_key_attr, None)
            return

        # Over a key
        if hit_key is not current_dwell_key:
            # Started dwelling on a new key
            setattr(self, dwell_key_attr, hit_key)
            setattr(self, dwell_start_attr, t)
        else:
            # Still on same key: check if dwell time reached
            elapsed = t - current_dwell_start
            if elapsed >= self.kbd_dwell_time:
                # Trigger key press
                self._press_key(hit_key)
                # Reset dwell so it doesn't repeat (lift finger to type again)
                setattr(self, dwell_key_attr, None)

    def _press_key(self, key):
        """Execute pyautogui key press with modifiers."""
        import pyautogui

        char = key["char"]

        # Special keys
        if char == "backspace":
            pyautogui.press("backspace")
            self.show_toast("⌫")
            return
        elif char == "enter":
            pyautogui.press("enter")
            self.show_toast("↵")
            return
        elif char == " ":
            pyautogui.press("space")
            self.show_toast("SPACE")
            return

        # Letter keys
        if self.ctrl_active:
            # Ctrl+letter
            pyautogui.hotkey("ctrl", char)
            self.show_toast(f"Ctrl+{char.upper()}")
        elif self.shift_active:
            # Shift = capital letter
            pyautogui.press(char.upper())
            self.show_toast(char.upper())
        else:
            # Lowercase
            pyautogui.press(char)
            self.show_toast(char)

    # ===================== End Keyboard Mode =====================

    def _draw_panel_icon(self, painter, key, rect):
        r = rect.adjusted(16, 16, -16, -16)
        cx, cy = r.center().x(), r.center().y()
        ink = QColor(225, 245, 255)

        def stroke(w):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(ink, w, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

        if key == "draw":                                   # pencil
            stroke(3.0)
            painter.drawLine(QPointF(r.left() + 4, r.bottom() - 2),
                             QPointF(r.right() - 1, r.top() + 3))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ink)
            painter.drawPolygon(QPolygonF([
                QPointF(r.left() - 2, r.bottom() + 2),
                QPointF(r.left() + 7, r.bottom() - 1),
                QPointF(r.left() + 2, r.bottom() - 8)]))
        elif key == "eraser":                               # tilted eraser block
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(-32)
            er = QRectF(-r.width() / 2, -r.height() / 4, r.width(), r.height() / 2)
            painter.setPen(QPen(ink, 2.2))
            painter.setBrush(QColor(0, 130, 210, 130))
            painter.drawRoundedRect(er, 3, 3)
            painter.drawLine(QPointF(er.center().x(), er.top()),
                             QPointF(er.center().x(), er.bottom()))
            painter.restore()
        elif key == "stroke_up":                            # thick line + plus
            stroke(6.5)
            painter.drawLine(QPointF(r.left(), cy + 4), QPointF(r.right() - 7, cy + 4))
            stroke(2.2)
            painter.drawLine(QPointF(r.right() - 4, r.top()), QPointF(r.right() - 4, r.top() + 9))
            painter.drawLine(QPointF(r.right() - 8.5, r.top() + 4.5), QPointF(r.right() + 0.5, r.top() + 4.5))
        elif key == "stroke_down":                          # thin line + minus
            stroke(2.0)
            painter.drawLine(QPointF(r.left(), cy + 4), QPointF(r.right() - 7, cy + 4))
            stroke(2.2)
            painter.drawLine(QPointF(r.right() - 8.5, r.top() + 4.5), QPointF(r.right() + 0.5, r.top() + 4.5))
        elif key == "color":                                # overlapping swatches
            painter.setPen(QPen(QColor(255, 255, 255, 170), 1.0))
            cols = [QColor(255, 70, 70), QColor(70, 200, 110),
                    QColor(80, 150, 255), QColor(255, 210, 0)]
            rad = r.width() * 0.30
            offs = [(-0.33, -0.30), (0.33, -0.30), (-0.30, 0.36), (0.33, 0.36)]
            for (ox, oy), col in zip(offs, cols):
                painter.setBrush(col)
                painter.drawEllipse(QPointF(cx + ox * r.width(), cy + oy * r.height()), rad, rad)
        elif key == "paste":                                # image frame + sun + mountain
            painter.setPen(QPen(ink, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(r, 3, 3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 210, 0))
            painter.drawEllipse(QPointF(r.left() + r.width() * 0.30, r.top() + r.height() * 0.30),
                                r.width() * 0.11, r.width() * 0.11)
            painter.setBrush(ink)
            painter.drawPolygon(QPolygonF([
                QPointF(r.left() + 2, r.bottom() - 2),
                QPointF(r.left() + r.width() * 0.46, r.center().y() + 1),
                QPointF(r.right() - 2, r.bottom() - 2)]))
        elif key == "clear":                                # trash can
            stroke(2.0)
            painter.drawLine(QPointF(r.left() - 1, r.top() + 3), QPointF(r.right() + 1, r.top() + 3))
            painter.drawLine(QPointF(cx - 3, r.top()), QPointF(cx + 3, r.top()))
            painter.drawLine(QPointF(r.left() + 3, r.top() + 4), QPointF(r.left() + 5, r.bottom()))
            painter.drawLine(QPointF(r.right() - 3, r.top() + 4), QPointF(r.right() - 5, r.bottom()))
            painter.drawLine(QPointF(r.left() + 5, r.bottom()), QPointF(r.right() - 5, r.bottom()))
            painter.drawLine(QPointF(cx, r.top() + 6), QPointF(cx, r.bottom() - 2))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Drawing layers are only rendered while in drawing mode (kept in memory
        # otherwise, so they reappear on re-entry).
        if self.drawing_active:
            painter.drawPixmap(0, 0, self.canvas)

            # Images (a grabbed image was raised to the end of the list, so it
            # renders on top — the z-index requirement).
            for img in self.images:
                self._paint_image(painter, img)

            # An in-flight ink blob renders above everything so the grabbed
            # element is never hidden behind an image.
            if self.manip is not None and self.manip["kind"] == "ink":
                self._paint_manip_ink(painter)

            self._paint_panel(painter)

            if self.palette_open:
                self._paint_palette(painter)

            self._paint_cursor(painter)
            self._paint_manip_ring(painter)

        # Keyboard overlay
        if self.keyboard_active:
            self._paint_keyboard(painter)

        self.draw_pip(painter)

        # Draw HUD with opacity control
        painter.setOpacity(self.hud_opacity)
        self.draw_hud(painter)
        painter.setOpacity(1.0)

        # Draw transient toast notification (e.g. screenshot confirmation)
        if self.toast_message:
            painter.setOpacity(self.toast_opacity)
            self.draw_toast(painter)
            painter.setOpacity(1.0)

        painter.end()

    def _paint_image(self, painter, img):
        rect = self._image_rect(img)
        painter.drawPixmap(int(rect.x()), int(rect.y()), self._scaled_image(img))
        # Outline the freshly pasted image or the one currently grabbed.
        manip_img = self.manip["image"] if (self.manip is not None
                                            and self.manip["kind"] == "image") else None
        if img.get("selected") or img is manip_img:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 200, 255, 220), 1.5, Qt.PenStyle.DashLine))
            painter.drawRect(rect)

    def _paint_manip_ink(self, painter):
        m = self.manip
        layer = m["layer"]
        s = m["scale"]
        w = max(1, int(round(layer.width() * s)))
        h = max(1, int(round(layer.height() * s)))
        scaled = layer.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        c = m["center"]
        painter.drawPixmap(int(c.x() - w / 2.0), int(c.y() - h / 2.0), scaled)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 220, 255, 200), 1.2, Qt.PenStyle.DashLine))
        painter.drawRect(QRectF(c.x() - w / 2.0, c.y() - h / 2.0, w, h))

    def _paint_manip_ring(self, painter):
        # Stillness countdown: a yellow ring fills toward the Move/Resize toggle,
        # then a red ring fills toward the drop.
        if self.manip is None or self.manip["still_since"] <= 0.0:
            return
        held = time.time() - self.manip["still_since"]
        if held < 0.15:
            return
        c = self.manip["last_mid"]
        if held < self.manip_mode_dwell:
            frac = held / self.manip_mode_dwell
            col = QColor(255, 200, 0, 230)      # yellow: approaching toggle
        else:
            frac = min(1.0, (held - self.manip_mode_dwell)
                       / max(0.01, self.manip_drop_dwell - self.manip_mode_dwell))
            col = QColor(255, 90, 60, 240)       # red: approaching drop
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(col, 3))
        painter.drawArc(QRectF(c.x() - 20, c.y() - 20, 40, 40), 90 * 16, int(-frac * 360 * 16))

    def _paint_cursor(self, painter):
        if not self.hand_present:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # While manipulating, the element follows the thumb-index midpoint — show
        # a move crosshair there instead of the normal tool cursor.
        if self.manip is not None:
            c = self.manip["last_mid"]
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 220, 255, 230), 2))
            painter.drawLine(QPointF(c.x() - 13, c.y()), QPointF(c.x() + 13, c.y()))
            painter.drawLine(QPointF(c.x(), c.y() - 13), QPointF(c.x(), c.y() + 13))
            label = "RESIZE" if self.manip["mode"] == "resize" else "MOVE"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor(0, 220, 255))
            painter.drawText(int(c.x() + 16), int(c.y() - 12), label)
            return
        if self.pointer is None:
            return
        pt = self.pointer
        tool = self.current_tool
        if tool == "erase":
            r = max(self.brush_size * 2, 14) / 2.0
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0, 120), 3))
            painter.drawEllipse(pt, r + 1, r + 1)
            painter.setPen(QPen(QColor(255, 255, 255, 230), 1.5))
            painter.drawEllipse(pt, r, r)
        elif tool == "drag":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 220, 255, 230), 2))
            painter.drawEllipse(pt, 10, 10)
            painter.drawLine(QPointF(pt.x() - 15, pt.y()), QPointF(pt.x() + 15, pt.y()))
            painter.drawLine(QPointF(pt.x(), pt.y() - 15), QPointF(pt.x(), pt.y() + 15))
        else:  # draw / hover
            r = max(self.brush_size / 2.0, 3.0)
            col = self.current_color
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
            painter.setBrush(QColor(col.red(), col.green(), col.blue(),
                                    235 if tool == "draw" else 110))
            painter.drawEllipse(pt, r, r)

        if time.time() < self.size_preview_until:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 200, 0, 220), 1.5))
            painter.drawEllipse(pt, self.brush_size / 2.0 + 5, self.brush_size / 2.0 + 5)

    def _paint_palette(self, painter):
        panel, rects = self._palette_layout()
        painter.setBrush(QColor(0, 10, 30, 235))
        painter.setPen(QPen(QColor(0, 150, 255, 200), 1.5))
        painter.drawRoundedRect(panel, 10, 10)
        now = time.time()
        for rect, i in rects:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.colors[i])
            painter.drawRoundedRect(rect, 6, 6)
            if self.colors[i] == self.current_color:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(255, 255, 255, 230), 2))
                painter.drawRoundedRect(rect, 6, 6)
            if i == self.dwell_idx:
                frac = min(1.0, (now - self.dwell_start) / self.dwell_needed)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(255, 200, 0), 3))
                painter.drawArc(rect.adjusted(-4, -4, 4, 4), 90 * 16, int(-frac * 360 * 16))
        painter.setPen(QColor(0, 200, 255))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(int(panel.x() + 12), int(panel.y() + panel.height() - 9),
                         f"Brush size: {self.brush_size}")

    def _paint_keyboard(self, painter):
        """Render the transparent QWERTY keyboard with dwell indicators."""
        t = time.time()

        # Semi-transparent dark background panel
        kbd_bounds = self._get_keyboard_bounds()
        painter.setBrush(QColor(0, 10, 30, 180))
        painter.setPen(QPen(QColor(0, 150, 255, 200), 2))
        painter.drawRoundedRect(kbd_bounds, 16, 16)

        # Render each key
        for key in self.kbd_layout:
            rect = key["rect"]
            char = key.get("label", key["shift_char"] if self.shift_active else key["char"])

            # Key background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(20, 40, 70, 200))
            painter.drawRoundedRect(rect, 8, 8)

            # Key border
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 180, 255, 180), 1.5))
            painter.drawRoundedRect(rect, 8, 8)

            # Key label
            painter.setPen(QColor(200, 220, 255))
            painter.setFont(QFont("Segoe UI", 16 if not key["is_special"] else 14, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, char.upper() if len(char) == 1 else char)

            # Dwell progress rings (left hand = cyan, right hand = yellow)
            for hand, color in [("left", QColor(0, 220, 255)), ("right", QColor(255, 200, 0))]:
                dwell_key = getattr(self, f"{hand}_dwell_key")
                dwell_start = getattr(self, f"{hand}_dwell_start")
                if dwell_key is key:
                    elapsed = t - dwell_start
                    frac = min(1.0, elapsed / self.kbd_dwell_time)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(color, 3))
                    painter.drawArc(rect.adjusted(4, 4, -4, -4), 90 * 16, int(-frac * 360 * 16))

        # Draw hand cursors
        if self.left_pointer:
            self._paint_hand_cursor(painter, self.left_pointer, QColor(0, 220, 255), "L")
        if self.right_pointer:
            self._paint_hand_cursor(painter, self.right_pointer, QColor(255, 200, 0), "R")

        # Modifier indicators (top-left corner of keyboard)
        self._paint_modifiers(painter, kbd_bounds)

    def _get_keyboard_bounds(self):
        """Get bounding rect of entire keyboard for background panel."""
        if not self.kbd_layout:
            return QRectF()
        min_x = min(k["rect"].left() for k in self.kbd_layout)
        min_y = min(k["rect"].top() for k in self.kbd_layout)
        max_x = max(k["rect"].right() for k in self.kbd_layout)
        max_y = max(k["rect"].bottom() for k in self.kbd_layout)
        padding = 20
        return QRectF(min_x - padding, min_y - padding,
                      max_x - min_x + 2 * padding, max_y - min_y + 2 * padding)

    def _paint_hand_cursor(self, painter, pos, color, label):
        """Draw a small crosshair cursor with hand label."""
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 2))
        painter.drawEllipse(pos, 8, 8)
        painter.drawLine(QPointF(pos.x() - 14, pos.y()), QPointF(pos.x() + 14, pos.y()))
        painter.drawLine(QPointF(pos.x(), pos.y() - 14), QPointF(pos.x(), pos.y() + 14))
        # Label
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(color)
        painter.drawText(int(pos.x() + 12), int(pos.y() - 12), label)

    def _paint_modifiers(self, painter, kbd_bounds):
        """Show active modifiers (Shift/Ctrl) in top-left of keyboard."""
        x = kbd_bounds.left() + 16
        y = kbd_bounds.top() + 16

        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

        if self.shift_active:
            painter.setPen(QColor(255, 200, 0))
            painter.drawText(int(x), int(y), "⇧ SHIFT")
            y += 20

        if self.ctrl_active:
            painter.setPen(QColor(0, 220, 255))
            painter.drawText(int(x), int(y), "⌃ CTRL")

    def draw_hud(self, painter):
        # HUD size and position (bottom right corner)
        hud_width = 280
        hud_height = 190
        margin = 30
        hud_x = self.screen_width - hud_width - margin
        hud_y = self.screen_height - hud_height - margin

        hud_rect = QRectF(hud_x, hud_y, hud_width, hud_height)

        # Background rounded rectangle (deep navy)
        painter.setBrush(QColor(0, 10, 30, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(hud_rect, 12.0, 12.0)

        # Add border around HUD (electric blue)
        painter.setPen(QPen(QColor(0, 150, 255, 200), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(hud_rect, 12.0, 12.0)

        # Padding content offsets
        content_x = hud_x + 15
        current_y = hud_y + 12

        # 0. Title "WAVLY" at top in gold color
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor(255, 200, 0)) # Accent: Gold
        painter.drawText(int(content_x), int(current_y + 18), "WAVLY")

        # Thin blue horizontal line separator under title
        current_y += 24
        painter.setPen(QPen(QColor(0, 150, 255, 100), 1))
        painter.drawLine(int(content_x), int(current_y), int(hud_x + hud_width - 15), int(current_y))

        current_y += 10

        # 1. Gesture Name (cyan text)
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor(0, 200, 255)) # Cyan
        painter.drawText(int(content_x), int(current_y + 16), f"Gesture: {self.current_gesture}")
        current_y += 24

        # 2. Mode (NORMAL: green, DRAWING: blue)
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if self.system_mode == "DRAWING":
            painter.setPen(QColor(0, 150, 255)) # Mode DRAWING: blue
        else:
            painter.setPen(QColor(0, 255, 150)) # Mode NORMAL: green
        painter.drawText(int(content_x), int(current_y + 16), f"Mode: {self.system_mode}")
        current_y += 24

        # 3. Active App Name (cyan text)
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor(0, 200, 255)) # Cyan
        painter.drawText(int(content_x), int(current_y + 15), f"Active App: {self.active_app_name.lower()}")
        current_y += 22

        # 4. Show voice status
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        status = getattr(self, 'voice_status', 'STANDBY')
        if status == "LISTENING":
            painter.setPen(QColor(0, 200, 255)) # Cyan
            status_text = "VOICE: LISTENING"
        elif status == "ACTIVE":
            painter.setPen(QColor(0, 255, 150)) # Green
            status_text = "VOICE: ACTIVE"
        else:
            painter.setPen(QColor(150, 150, 150)) # Gray
            status_text = "VOICE: STANDBY"
        painter.drawText(int(content_x), int(current_y + 15), status_text)

        # 5. Small Hint Text (9px gray)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(120, 130, 150))
        if self.system_mode == "DRAWING":
            hint_text = "Hint: Pinch or Spider-Man to exit drawing"
        else:
            hint_text = "Hint: Spider-Man gesture to draw"
        painter.drawText(int(content_x), int(hud_y + hud_height - 12), hint_text)

        # Draw the holographic Arc Reactor on the right side of the HUD
        self.draw_arc_reactor(painter, hud_x + hud_width - 55, hud_y + 85, 30)

    def draw_arc_reactor(self, painter, cx, cy, r):
        # Save painter state
        painter.save()
        
        status = getattr(self, 'voice_status', 'STANDBY')
        
        # Determine colors based on status
        if status == "ACTIVE":
            color_outer = QColor(255, 200, 0, 200) # Gold
            color_inner = QColor(0, 255, 255, int(150 + 105 * self.pulse_val)) # Bright pulsating Cyan
            color_core = QColor(255, 255, 255, int(180 + 75 * self.pulse_val)) # Pure white core
            outer_pen_width = 3
        elif status == "LISTENING":
            color_outer = QColor(0, 150, 255, 180) # Cyber Blue
            color_inner = QColor(0, 200, 255, int(100 + 100 * self.pulse_val)) # Cyber Cyan
            color_core = QColor(0, 255, 255, 150)
            outer_pen_width = 2
        else: # STANDBY
            color_outer = QColor(100, 110, 130, 100) # Muted gray
            color_inner = QColor(0, 150, 255, int(50 + 50 * self.pulse_val))
            color_core = QColor(0, 150, 255, 80)
            outer_pen_width = 1.5

        # 1. Draw glowing background aura
        glow_rad = r + 10
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(5):
            alpha = int((15 - i * 3) * (0.5 + 0.5 * self.pulse_val))
            painter.setBrush(QColor(color_inner.red(), color_inner.green(), color_inner.blue(), alpha))
            painter.drawEllipse(QPoint(int(cx), int(cy)), int(glow_rad - i * 2), int(glow_rad - i * 2))

        # 2. Draw outer rotating segmented ring
        pen_outer = QPen(color_outer, outer_pen_width)
        pen_outer.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # 4 segments, each 60 degrees, separated by 30 degree gaps
        for angle_offset in [0, 90, 180, 270]:
            start_angle = int((self.pulse_angle + angle_offset) * 16)
            span_angle = int(60 * 16)
            painter.drawArc(
                int(cx - r), int(cy - r), int(r * 2), int(r * 2),
                start_angle, span_angle
            )

        # 3. Draw inner breathing ring
        r_inner = r - 8
        pen_inner = QPen(color_inner, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(r_inner), int(r_inner))

        # 4. Draw energetic core rays (in ACTIVE status)
        if status == "ACTIVE":
            pen_ray = QPen(QColor(0, 255, 255, 120), 1)
            painter.setPen(pen_ray)
            for i in range(8):
                angle_rad = math.radians(self.pulse_angle + i * 45)
                # Rays extending from core to inner ring
                x1 = cx + math.cos(angle_rad) * 4
                y1 = cy + math.sin(angle_rad) * 4
                x2 = cx + math.cos(angle_rad) * (r_inner - 2)
                y2 = cy + math.sin(angle_rad) * (r_inner - 2)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 5. Draw bright core
        core_r = 4 if status == "ACTIVE" else 3
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color_core)
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(core_r), int(core_r))

        # Restore painter state
        painter.restore()

    def keyPressEvent(self, event):
        # Note: the overlay is input-transparent, so these rarely fire — kept as
        # a dev convenience when focus does land on the window.
        if event.key() == Qt.Key.Key_C:
            self.canvas.fill(Qt.GlobalColor.transparent)
            self.images.clear()
            self.manip = None
            self.update()
        elif event.key() == Qt.Key.Key_Escape:
            self.vision_thread.stop()
            self.close()

    def closeEvent(self, event):
        self.vision_thread.stop()
        super().closeEvent(event)
