import threading
import time

def test_threaded_tts():
    """Test pyttsx3 in a background thread - same way VoiceResponder uses it"""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        print("[TEST] COM initialized in thread")
    except ImportError:
        print("[TEST] pythoncom not available, skipping COM init")
    except Exception as e:
        print(f"[TEST] COM init failed: {e}")

    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)
    engine.setProperty('volume', 1.0)
    
    voices = engine.getProperty('voices')
    print(f"[TEST] Available voices: {len(voices)}")
    for i, v in enumerate(voices):
        print(f"  [{i}] {v.name} (id={v.id})")
    
    print("[TEST] Saying text from background thread...")
    engine.say("Testing audio from a background thread")
    engine.runAndWait()
    print("[TEST] runAndWait() completed")

if __name__ == "__main__":
    print("=== Test 1: Main thread ===")
    import pyttsx3
    e = pyttsx3.init()
    e.setProperty('rate', 170)
    e.say("Test from main thread")
    e.runAndWait()
    print("[TEST] Main thread done\n")
    
    time.sleep(1)
    
    print("=== Test 2: Background thread (like VoiceResponder) ===")
    t = threading.Thread(target=test_threaded_tts, daemon=True)
    t.start()
    t.join(timeout=10)
    print("[TEST] Background thread done")
