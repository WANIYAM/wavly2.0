import pygetwindow

class ContextDetector:
    """
    Detects the current active window and identifies the running application.
    """
    def get_active_title(self):
        """
        Returns the raw window title of the currently active window.
        Returns None if no active window is found or if an error occurs.
        """
        try:
            window = pygetwindow.getActiveWindow()
            if window is not None:
                return window.title
            return None
        except Exception:
            return None

    def get_active_app(self):
        """
        Gets the currently active window title and returns the application identifier:
        - "chrome" if "Chrome" or "Edge" is in the title
        - "vlc" if "VLC" is in the title
        - "powerpoint" if "PowerPoint" is in the title
        - "default" for everything else or if an error occurs
        """
        try:
            title = self.get_active_title()
            if not title:
                return "default"
            
            if "Chrome" in title or "Edge" in title:
                return "chrome"
            elif "VLC" in title:
                return "vlc"
            elif "PowerPoint" in title:
                return "powerpoint"
            
            return "default"
        except Exception:
            return "default"
