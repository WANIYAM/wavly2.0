import os
import time
import math
from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer, QStandardPaths, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QImage

from src.ui.vision_thread import VisionThread


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

        # Variables requested
        self.colors = [
            QColor(255, 0, 0),     # red
            QColor(0, 0, 255),     # blue
            QColor(0, 255, 0),     # green
            QColor(255, 255, 0),   # yellow
            QColor(128, 0, 128),   # purple
            QColor(255, 255, 255)  # white
        ]
        self.current_color_index = 0
        self.current_color = self.colors[self.current_color_index]
        self.brush_size = 5
        self.is_drawing = False
        self.erase_mode = False
        self.undo_stack = []
        self.redo_stack = []

        # State variables
        self.last_point = None
        self.current_gesture = "Initializing..."
        self.system_mode = "NORMAL"
        self.active_app_name = "default"
        self.hud_opacity = 1.0



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
        self.vision_thread.point_detected.connect(self.update_trail)
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
        self.update()

    def update_system_mode(self, mode):
        if mode == "drawing":
            self.system_mode = "DRAWING"
        else:
            self.system_mode = "NORMAL"
            self.is_drawing = False # Stop drawing when exiting mode
        self.update()

    def handle_gesture_command(self, command):
        print(f"[OVERLAY] received command: {command}")
        if command == "clear_canvas":
            self.save_to_undo()
            self.canvas.fill(Qt.GlobalColor.transparent)
            self.update()
        elif command == "pen_up":
            self.is_drawing = False
            self.last_point = None
        elif command == "pen_down":
            self.is_drawing = True
        elif command == "change_color":
            self.current_color_index = (self.current_color_index + 1) % len(self.colors)
            self.current_color = self.colors[self.current_color_index]
            self.update()
        elif command == "brush_size_up":
            self.brush_size += 2
            if self.brush_size > 20:
                self.brush_size = 2
            self.update()
        elif command == "save_drawing":
            pics = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
            if not pics:
                pics = os.path.expanduser('~')
            filename = os.path.join(pics, f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.canvas.save(filename)
            print(f"Saved to {filename}")
        elif command == "undo":
            if self.undo_stack:
                self.redo_stack.append(self.canvas.copy())
                self.canvas = self.undo_stack.pop()
                self.update()
        elif command == "redo":
            if self.redo_stack:
                self.undo_stack.append(self.canvas.copy())
                self.canvas = self.redo_stack.pop()
                self.update()
        elif command == "erase_mode":
            self.erase_mode = not self.erase_mode
            self.update()

    def save_to_undo(self):
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > 10:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def update_trail(self, x, y):
        mapped_x = int((x / 640.0) * self.screen_width)
        mapped_y = int((y / 480.0) * self.screen_height)
        current_point = QPoint(mapped_x, mapped_y)

        if self.is_drawing:
            print(f"[OVERLAY] drawing at: {mapped_x}, {mapped_y}")
            if self.last_point is None:
                self.save_to_undo()
            
            if self.last_point is not None:
                painter = QPainter(self.canvas)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                if self.erase_mode:
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                    pen = QPen(Qt.GlobalColor.transparent, self.brush_size * 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                else:
                    pen = QPen(self.current_color, self.brush_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                
                painter.setPen(pen)
                painter.drawLine(self.last_point, current_point)
                painter.end()

            self.last_point = current_point
            self.update()
        else:
            self.last_point = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the canvas buffer on screen
        painter.drawPixmap(0, 0, self.canvas)
        self.draw_pip(painter)

        # Draw HUD with opacity control
        painter.setOpacity(self.hud_opacity)
        self.draw_hud(painter)
        painter.setOpacity(1.0)
        painter.end()

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
        if event.key() == Qt.Key.Key_C:
            self.canvas.fill(Qt.GlobalColor.transparent)
            self.update()
        elif event.key() == Qt.Key.Key_D:
            self.is_drawing = not self.is_drawing
            self.last_point = None
            self.update()
        elif event.key() == Qt.Key.Key_Escape:
            self.vision_thread.stop()
            self.close()

    def closeEvent(self, event):
        self.vision_thread.stop()
        super().closeEvent(event)
