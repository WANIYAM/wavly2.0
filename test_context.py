import time
from src.control.context_detector import ContextDetector

def main():
    detector = ContextDetector()
    print("Starting context detection test (runs for 30 seconds)...")
    for _ in range(30):
        title = detector.get_active_title()
        app = detector.get_active_app()
        title_str = f'"{title}"' if title is not None else 'None'
        print(f'[CONTEXT] Title: {title_str} → App: {app}')
        time.sleep(1)

if __name__ == "__main__":
    main()
