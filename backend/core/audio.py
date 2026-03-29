# Handles text-to-speech generation
from gtts import gTTS
from io import BytesIO

def generate_audio(text, lang='en'):
    try:
        if not text:
            return None
        tts = gTTS(text=text, lang=lang)
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None
