import os
import sys
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"

import warnings
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import qInstallMessageHandler
from src.ui.overlay_window import OverlayWindow

warnings.filterwarnings("ignore")

def qt_message_handler(mode, context, message):
    pass
qInstallMessageHandler(qt_message_handler)

def main():
    print("[WAVLY] Starting...")
    app = QApplication(sys.argv)
    
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()

    window = OverlayWindow()
    window.show()
    exit_code = app.exec()
    print("[WAVLY] Shutting down...")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()