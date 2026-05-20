import queue
import threading
import speech_recognition as sr

class VoiceController:
    def __init__(self):
        self.command_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[VOICE] Background listener started")

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[VOICE] Background listener stopped")

    def _run_loop(self):
        # Adjust for ambient noise once on start
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"[VOICE] Ambient noise adjustment failed: {e}")

        while self.running:
            try:
                with self.microphone as source:
                    # Timeout of 3 seconds per listen attempt
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                
                # Check running flag again in case we stopped during listening
                if not self.running:
                    break

                text = self.recognizer.recognize_google(audio).strip()
                if text:
                    print(f'[VOICE] Heard: "{text}"')
                    self.command_queue.put(text)
            except sr.WaitTimeoutError:
                # Normal timeout when no one is speaking
                pass
            except sr.UnknownValueError:
                # Could not understand audio, ignore
                pass
            except sr.RequestError as e:
                print(f"[VOICE] API Error: {e}")
            except Exception as e:
                # Avoid crashing loop on device conflicts/errors
                if self.running:
                    print(f"[VOICE] Loop error: {e}")
