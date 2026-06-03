import queue
import threading
import pyttsx3

class VoiceResponder:
    def __init__(self):
        self.speech_queue = queue.Queue()
        self.running = False
        self.thread = None
        self.is_speaking = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.speech_queue.put(None)
        if self.thread:
            self.thread.join(timeout=2)

    def speak(self, text):
        if not self.running:
            self.start()
        if text:
            print(f'[RESPONDER] Queueing speech: "{text}"')
            self.speech_queue.put(text)

    def greet(self):
        import random
        greetings = [
            "Wavly systems online. All systems fully operational. How can I assist you, sir?",
            "Good evening, sir. Wavly systems are online and ready for your command.",
            "Wavly online. Always a pleasure watching you work, sir.",
            "Systems online. I'm ready for your command, sir."
        ]
        self.speak(random.choice(greetings))

    def speak_wake_response(self):
        import random
        responses = [
            "At your service, sir.",
            "Always a pleasure, sir.",
            "Yes, sir?",
            "Systems stand ready, sir.",
            "Online and listening, sir.",
            "How can I assist you, sir?"
        ]
        self.speak(random.choice(responses))

    def _run_loop(self):
        # Initialize COM apartment for this thread — required for SAPI5 TTS
        # when running alongside PyQt6 which owns the main thread's COM apartment
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass  # pythoncom not installed, pyttsx3 may still work
        except Exception:
            pass

        engine = None
        try:
            engine = pyttsx3.init()
            
            # Configure engine rate
            engine.setProperty('rate', 170)
            
            # Configure engine volume
            engine.setProperty('volume', 1.0)
            
            # Configure voice: use the first English voice available
            voices = engine.getProperty('voices')
            english_voice = None
            for voice in voices:
                languages = getattr(voice, 'languages', [])
                languages_str = "".join([str(l) for l in languages]).lower()
                name_str = str(voice.name).lower() if voice.name else ""
                id_str = str(voice.id).lower() if voice.id else ""
                
                if 'en' in languages_str or 'english' in name_str or 'en' in id_str or 'us' in name_str or 'gb' in name_str:
                    english_voice = voice
                    break
            
            if english_voice:
                engine.setProperty('voice', english_voice.id)
            elif voices:
                engine.setProperty('voice', voices[0].id)
                
        except Exception as e:
            print(f"[RESPONDER] Failed to initialize pyttsx3: {e}")

        while self.running:
            try:
                try:
                    text = self.speech_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if text is None:
                    break

                self.is_speaking = True
                
                # Try speaking using pyttsx3
                spoken = False
                if engine:
                    try:
                        print(f"[RESPONDER] About to speak: {text}")
                        engine.say(text)
                        engine.runAndWait()
                        print(f"[RESPONDER] Finished speaking: {text}")
                        spoken = True
                    except Exception as e:
                        print(f"[RESPONDER] Speech failed: {e}")
                        try:
                            engine.stop()
                            engine = pyttsx3.init()
                            engine.setProperty('rate', 175)
                            engine.setProperty('volume', 1.0)
                            engine.say(text)
                            engine.runAndWait()
                            spoken = True
                        except Exception as e2:
                            print(f"[RESPONDER] Retry failed: {e2}")
                
                # Fallback to PowerShell SpeechSynthesizer if pyttsx3 is not available or failed
                if not spoken:
                    try:
                        print(f'[RESPONDER] Speaking (PowerShell Fallback): "{text}"')
                        import subprocess
                        escaped_text = text.replace('"', '\\"')
                        ps_command = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{escaped_text}")'
                        subprocess.run(["powershell", "-Command", ps_command], capture_output=True)
                    except Exception as e:
                        print(f"[RESPONDER] PowerShell speech fallback failed: {e}")

                self.is_speaking = False
                self.speech_queue.task_done()
            except Exception as e:
                self.is_speaking = False
                print(f"[RESPONDER] Speech loop error: {e}")

