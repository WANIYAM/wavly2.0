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

    def system_speak(self, text):
        if not self.running:
            self.start()
        if text:
            print(f'[VoiceResponder] system_speak: "{text}"')
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

    def speak_goodbye_response(self):
        import random
        farewells = [
            "Goodbye, sir.",
            "See you soon, sir.",
            "Standing by, sir.",
            "Wavly going to standby. Call me anytime, sir.",
            "Until next time, sir.",
            "Signing off. Have a good one, sir.",
            "Going to sleep, sir. Say my name when you need me.",
            "Session ended. Standing by for your call, sir.",
        ]
        self.speak(random.choice(farewells))

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

        target_voice_id = None
        engine_available = False
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty('voices')
            female_voice = None

            # Try to find a female English voice
            female_keywords = ['zira', 'female', 'woman', 'girl', 'hazel', 'susan', 'catherine']
            for voice in voices:
                name_str = str(voice.name).lower()
                id_str = str(voice.id).lower()
                for keyword in female_keywords:
                    if keyword in name_str or keyword in id_str:
                        female_voice = voice
                        break
                if female_voice:
                    break

            # Fallback to second voice if no female found
            if female_voice:
                target_voice_id = female_voice.id
            elif len(voices) > 1:
                target_voice_id = voices[1].id
            elif voices:
                target_voice_id = voices[0].id
                
            del temp_engine
            engine_available = True
        except Exception as e:
            print(f"[RESPONDER] Failed to query pyttsx3 voices: {e}")

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
                if engine_available:
                    try:
                        print(f"[RESPONDER] About to speak: {text}")
                        # Workaround for pyttsx3 thread bug: re-initialize engine per utterance
                        engine = pyttsx3.init()
                        engine.setProperty('rate', 185)
                        engine.setProperty('volume', 1.0)
                        if target_voice_id:
                            engine.setProperty('voice', target_voice_id)

                        engine.say(text)
                        engine.runAndWait()
                        del engine
                        print(f"[RESPONDER] Finished speaking: {text}")
                        spoken = True
                    except Exception as e:
                        print(f"[RESPONDER] Speech failed: {e}")
                
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

