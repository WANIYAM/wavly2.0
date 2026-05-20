import speech_recognition as sr

def main():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    print("[VOICE] Initializing microphone...")
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
    except Exception as e:
        print(f"[VOICE] Microphone initialization failed: {e}")
        return

    print("[VOICE] Starting voice loop (3 iterations)...")
    for i in range(3):
        print(f"[VOICE] Listening iteration {i + 1}/3...")
        try:
            with microphone as source:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            text = recognizer.recognize_google(audio)
            print(f'[VOICE] Heard: "{text}"')
        except sr.WaitTimeoutError:
            print('[VOICE] Heard: ""')
        except sr.UnknownValueError:
            print('[VOICE] Heard: ""')
        except sr.RequestError as e:
            print(f'[VOICE] Error: {e}')
        except Exception as e:
            print(f'[VOICE] Unexpected error: {e}')

if __name__ == "__main__":
    main()
