import sys
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

        # Frame counting for UI FPS
        self.frames = 0
        self.fps = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.calculate_fps)
        self.fps_timer.start(1000)

        # Connect to VisionThread
        self.vision_thread = VisionThread()
        self.vision_thread.point_detected.connect(self.update_trail)
        self.vision_thread.gesture_detected.connect(self.update_gesture_hud)
        self.vision_thread.gesture_command.connect(self.handle_gesture_command)
        self.vision_thread.mode_changed.connect(self.update_system_mode)

        self.vision_thread.start()

    def calculate_fps(self):
        self.fps = self.frames
        self.frames = 0
        self.update()

    def update_gesture_hud(self, gesture_name):
        self.current_gesture = gesture_name
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
        self.frames += 1
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the canvas buffer on screen
        painter.drawPixmap(0, 0, self.canvas)

        # Draw HUD
        self.draw_hud(painter)

    def draw_hud(self, painter):
        # HUD semi-transparent background
        hud_width = 300
        hud_height = 200
        painter.fillRect(20, 20, hud_width, hud_height, QColor(0, 0, 0, 180))

        # HUD Text
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        # Gesture Name
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(35, 50, f"Gesture: {self.current_gesture}")

        # Current Mode
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(35, 80, f"Mode: {self.system_mode}")
        
        # Color & Size
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(35, 110, "Color: ")
        
        painter.setBrush(self.current_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(90, 97, 15, 15)
        
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(120, 110, f"Size: {self.brush_size}")

        # Erase Mode
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(35, 140, "Erase:")
        
        erase_text = "ON" if self.erase_mode else "OFF"
        erase_color = QColor(255, 50, 50) if self.erase_mode else QColor(150, 150, 150)
        painter.setPen(erase_color)
        painter.drawText(95, 140, erase_text)

        # Hints
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        painter.setPen(QColor(200, 200, 200))
        if self.system_mode == "NORMAL":
            painter.drawText(35, 170, "Hint: Hold 2-fingers to draw")
        else:
            painter.drawText(35, 170, "Hint: Pinch to exit drawing")

        # FPS
        painter.setPen(QColor(255, 255, 0))
        painter.drawText(35, 200, f"FPS: {self.fps}")

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
