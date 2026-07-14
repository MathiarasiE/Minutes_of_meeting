try:
    import pyttsx3
except Exception as e:
    pyttsx3 = None


class TTS:
    """Simple TTS wrapper using pyttsx3 (offline).

    On Windows this uses SAPI5; on other platforms it uses available engines.
    """

    def __init__(self):
        if pyttsx3 is None:
            raise RuntimeError("pyttsx3 is not installed. Install requirements.txt to enable TTS.")
        self._engine = pyttsx3.init()

    def speak(self, text: str):
        if not text:
            return
        self._engine.say(text)
        self._engine.runAndWait()
