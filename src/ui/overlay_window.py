import os
from datetime import datetime
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer, QStandardPaths
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont

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

        # Connect to VisionThread
        self.vision_thread = VisionThread()
        self.vision_thread.point_detected.connect(self.update_trail)
        self.vision_thread.gesture_detected.connect(self.update_gesture_hud)
        self.vision_thread.gesture_command.connect(self.handle_gesture_command)
        self.vision_thread.mode_changed.connect(self.update_system_mode)
        self.vision_thread.app_changed.connect(self.update_app_hud)

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

        # Draw HUD with opacity control
        painter.setOpacity(self.hud_opacity)
        self.draw_hud(painter)
        painter.setOpacity(1.0)
        painter.end()

    def draw_hud(self, painter):
        # HUD size and position (bottom right corner)
        hud_width = 280
        hud_height = 160
        margin = 30
        hud_x = self.screen_width - hud_width - margin
        hud_y = self.screen_height - hud_height - margin

        # Background rounded rectangle (semi-transparent dark background)
        painter.setBrush(QColor(15, 15, 15, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(hud_x, hud_y, hud_width, hud_height, 12.0, 12.0)

        # Padding content offsets
        content_x = hud_x + 15

        # 1. Gesture Name (16px bold white)
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(content_x, hud_y + 15 + 22, f"Gesture: {self.current_gesture}")

        # 2. Mode (13px colored text: Green for NORMAL, Blue for DRAWING)
        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        if self.system_mode == "DRAWING":
            painter.setPen(QColor(52, 152, 219)) # Blue
        else:
            painter.setPen(QColor(46, 204, 113)) # Green
        painter.drawText(content_x, hud_y + 15 + 22 + 28, f"Mode: {self.system_mode}")

        # 3. Active App Name (12px light gray)
        painter.setFont(QFont("Segoe UI", 12))
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(content_x, hud_y + 15 + 22 + 28 + 26, f"Active App: {self.active_app_name.lower()}")

        # 4. Small Hint Text (10px gray)
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor(150, 150, 150))
        if self.system_mode == "DRAWING":
            hint_text = "Hint: Pinch to exit drawing"
        else:
            hint_text = "Hint: Hold 2-fingers to draw"
        painter.drawText(content_x, hud_y + 160 - 15 - 2, hint_text)

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
