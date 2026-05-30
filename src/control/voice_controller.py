import queue
import threading
import time
import speech_recognition as sr
import pyttsx3

class VoiceController:
    def __init__(self, voice_responder=None):
        self.command_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.running = False
        self.thread = None
        self.wake_word = "wavly"
        self.activated = False
        self.voice_responder = voice_responder

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

        activation_time = 0

        while self.running:
            try:
                # Calculate remaining time before activation timeout
                current_timeout = 3
                if self.activated:
                    elapsed = time.time() - activation_time
                    if elapsed >= 8:
                        self.activated = False
                        print("[VOICE] Deactivated")
                        continue
                    current_timeout = min(3, max(1, int(8 - elapsed)))

                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=current_timeout, phrase_time_limit=3)
                
                # Check running flag again in case we stopped during listening
                if not self.running:
                    break

                text = self.recognizer.recognize_google(audio).strip().lower()
                if not text:
                    continue

                if not self.activated:
                    print(f'[VOICE] Standby heard: "{text}"')
                    wake_words = [
                        "wavly", "wavy", "wavely", "wably", "waverly", "waveely",
                        "babli", "bably", "bobly", "bravely", "gravely", "webly", 
                        "weebly", "lovely", "warmly", "warbly", "ravly", "robly", "radley"
                    ]
                    if any(word in text for word in wake_words):
                        print("[VOICE] Wake word detected!")
                        if self.voice_responder:
                            self.voice_responder.speak_wake_response()
                            # Wait for speech to start and finish to prevent self-hearing echo
                            time.sleep(0.2)
                            while getattr(self.voice_responder, 'is_speaking', False):
                                time.sleep(0.05)
                        
                        self.activated = True
                        activation_time = time.time()
                        print("[VOICE] Listening for command...")
                else:
                    print(f'[VOICE] Heard: "{text}"')
                    self.command_queue.put(text)
                    self.activated = False

            except sr.WaitTimeoutError:
                if self.activated:
                    elapsed = time.time() - activation_time
                    if elapsed >= 8:
                        self.activated = False
                        print("[VOICE] Deactivated")
            except sr.UnknownValueError:
                if self.activated:
                    elapsed = time.time() - activation_time
                    if elapsed >= 8:
                        self.activated = False
                        print("[VOICE] Deactivated")
            except sr.RequestError as e:
                print(f"[VOICE] API Error: {e}")
            except Exception as e:
                if self.running:
                    print(f"[VOICE] Loop error: {e}")
