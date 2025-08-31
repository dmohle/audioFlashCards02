# generate_audio.py
# Create native MP3s for Russian numbers 0–10
# Run: python generate_audio.py

from gtts import gTTS
import os
import unicodedata
import re
import time

AUDIO_DIR = "audio_native"

# (Russian with stress, English)
WORDS = [
    ("ну́ль", "zero"),
    ("оди́н", "one"),
    ("два́", "two"),
    ("три́", "three"),
    ("четы́ре", "four"),
    ("пять", "five"),
    ("шесть", "six"),
    ("се́мь", "seven"),
    ("во́семь", "eight"),
    ("де́вять", "nine"),
    ("де́сять", "ten"),
]

os.makedirs(AUDIO_DIR, exist_ok=True)

def sanitize_filename(text: str) -> str:
    """
    Make a safe, consistent Cyrillic filename:
    - remove combining accent marks
    - normalize ё→е / Ё→Е
    - remove punctuation that can confuse filesystems
    - collapse whitespace; trim
    """
    no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    yo_fixed = no_accents.replace("ё", "е").replace("Ё", "Е")
    cleaned = re.sub(r'[?!:;,"\'.…—–-]', '', yo_fixed)
    cleaned = cleaned.replace('/', '-').replace('\\', '-')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

for rus, eng in WORDS:
    try:
        tts = gTTS(text=rus, lang='ru')
        filename = sanitize_filename(rus) + ".mp3"   # e.g., "нуль.mp3", "один.mp3"
        out_path = os.path.join(AUDIO_DIR, filename)
        tts.save(out_path)
        print(f"✅ Saved: {out_path}  ← {rus} ({eng})")
        time.sleep(0.4)  # tiny pause to be polite to the service
    except Exception as e:
        print(f"❌ Failed: {rus} ({eng}) -> {e}")

print("\nDone. Files are in ./audio_native")
