# gui_flashcards.py
import tkinter as tk
from tkinter import ttk, messagebox
import csv, os, threading, unicodedata, re
from pydub import AudioSegment
from pydub.playback import play
from pydub.utils import which
import sounddevice as sd
import soundfile as sf
import time

WORD_LIST_FILE = "word_list.csv"
AUDIO_FOLDER = "audio_native"
RECORDINGS_FOLDER = "audio_user"

# Ensure ffmpeg is known to pydub (Homebrew installs to /opt/homebrew/bin on Apple Silicon)
AudioSegment.converter = which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

def sanitize_filename(text: str) -> str:
    """Produce a safe base name: strip accents, normalize ё→е, drop punctuation, trim spaces."""
    no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    yo_fixed = no_accents.replace("ё", "е").replace("Ё", "Е")
    cleaned = re.sub(r'[?!:;,"\'.…—–-]', '', yo_fixed).replace('/', '-').replace('\\', '-')
    return re.sub(r'\s+', ' ', cleaned).strip()

def norm_base(name: str) -> str:
    """
    Normalize any filename (or word) to a comparable base:
    - strip extension
    - NFD → remove combining marks
    - ё→е, drop punctuation, collapse spaces, lowercase
    """
    base = os.path.splitext(name)[0]
    base = unicodedata.normalize('NFD', base)
    base = ''.join(c for c in base if unicodedata.category(c) != 'Mn')
    base = base.replace("ё", "е").replace("Ё", "Е")
    base = re.sub(r'[?!:;,"\'.…—–-]', '', base)
    base = re.sub(r'\s+', ' ', base).strip()
    return base.lower()

def find_audio_path(display_word: str) -> str | None:
    """
    Try to find the best-matching MP3 in AUDIO_FOLDER for display_word.
    Handles stress marks, ё/е, NFC/NFD, punctuation, spaces, case.
    """
    if not os.path.isdir(AUDIO_FOLDER):
        return None

    target_norm = norm_base(display_word)
    try:
        candidates = [f for f in os.listdir(AUDIO_FOLDER) if f.lower().endswith(".mp3")]
    except Exception:
        return None

    # 1) Direct sanitized attempt (fast path)
    direct = os.path.join(AUDIO_FOLDER, sanitize_filename(display_word) + ".mp3")
    if os.path.exists(direct):
        return direct

    # 2) Scan for a normalized match
    for fname in candidates:
        if norm_base(fname) == target_norm:
            return os.path.join(AUDIO_FOLDER, fname)

    # 3) Last resort: case-insensitive & space-insensitive loose match
    loose_target = target_norm.replace(" ", "")
    for fname in candidates:
        if norm_base(fname).replace(" ", "") == loose_target:
            return os.path.join(AUDIO_FOLDER, fname)

    return None

def load_words():
    if not os.path.exists(WORD_LIST_FILE):
        messagebox.showerror("Missing word list", f"Can't find {WORD_LIST_FILE} in the project folder.")
        return []
    with open(WORD_LIST_FILE, encoding='utf-8') as f:
        return list(csv.reader(f))

rows = load_words()  # [ [rus, eng, ipa, filename?], ... ]

def play_audio(display_word: str, filename_hint: str):
    """
    Prefer the CSV filename hint if present; otherwise sanitize & search.
    Always falls back to a robust directory scan to find the correct file.
    """
    # Try filename hint first (exact)
    if filename_hint:
        hinted = os.path.join(AUDIO_FOLDER, f"{filename_hint}.mp3")
        if os.path.exists(hinted):
            path = hinted
        else:
            # Also try sanitized hint (in case hint contains accents/punct)
            hinted_sanitized = os.path.join(AUDIO_FOLDER, f"{sanitize_filename(filename_hint)}.mp3")
            path = hinted_sanitized if os.path.exists(hinted_sanitized) else None
    else:
        path = None

    # If not found via hint, do robust lookup
    if path is None or not os.path.exists(path):
        path = find_audio_path(display_word)

    if not path or not os.path.exists(path):
        messagebox.showwarning(
            "Missing audio",
            f"Not found in {AUDIO_FOLDER} for:\n{display_word}\n"
            f"(looked for variants of: {sanitize_filename(display_word)})"
        )
        return

    print(f"🔊 Playing: {path}")

    def run():
        try:
            audio = AudioSegment.from_mp3(path)
            play(audio)
        except Exception as e:
            messagebox.showerror("Playback error", str(e))

    threading.Thread(target=run, daemon=True).start()

def record_audio(display_word: str, seconds=3):
    os.makedirs(RECORDINGS_FOLDER, exist_ok=True)
    base = sanitize_filename(display_word)
    # To keep multiple takes, uncomment the timestamped version and comment the fixed name:
    # stamp = time.strftime("%Y%m%d-%H%M%S")
    # out_wav = os.path.join(RECORDINGS_FOLDER, f"{base}_your_voice_{stamp}.wav")
    out_wav = os.path.join(RECORDINGS_FOLDER, f"{base}_your_voice.wav")
    fs = 44100
    try:
        rec = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
        sd.wait()
        sf.write(out_wav, rec, fs)
        messagebox.showinfo("Saved", f"Recording saved:\n{out_wav}")
    except Exception as e:
        messagebox.showerror("Record error", str(e))

def find_latest_user_recording(display_word: str) -> str | None:
    """
    Return the most recent WAV for this word in audio_user/,
    matching by sanitized base, or None if not found.
    """
    if not os.path.isdir(RECORDINGS_FOLDER):
        return None

    base = sanitize_filename(display_word)
    latest_path = None
    latest_mtime = -1.0

    try:
        for fname in os.listdir(RECORDINGS_FOLDER):
            if not fname.lower().endswith(".wav"):
                continue
            if not os.path.splitext(fname)[0].startswith(base):
                continue
            path = os.path.join(RECORDINGS_FOLDER, fname)
            try:
                mtime = os.path.getmtime(path)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_path = path
            except OSError:
                continue
    except Exception:
        return None

    return latest_path

def play_user_recording(display_word: str):
    """Play the newest user recording for the selected word."""
    path = find_latest_user_recording(display_word)
    if not path:
        messagebox.showinfo(
            "No recording found",
            "No user recording exists for this word yet.\nClick “Record” to create one."
        )
        return

    print(f"🔊 Playing your recording: {path}")

    def run():
        try:
            audio = AudioSegment.from_file(path)  # WAV
            play(audio)
        except Exception as e:
            messagebox.showerror("Playback error", str(e))

    threading.Thread(target=run, daemon=True).start()

# ---- GUI ----
root = tk.Tk()
root.title("🎧 Russian Audio Flashcards (macOS)")
root.geometry("600x480")

left = tk.Frame(root); left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
right = tk.Frame(root); right.pack(side="right", fill="y", padx=10, pady=10)

lst = tk.Listbox(left, width=40, height=20)
for r in rows:
    # Gracefully handle 3- or 4-column CSVs
    rus = r[0] if len(r) > 0 else ""
    eng = r[1] if len(r) > 1 else ""
    lst.insert(tk.END, f"{rus} — {eng}")
lst.pack(fill="both", expand=True)

sel_word = tk.StringVar()
sel_eng = tk.StringVar()
sel_ipa = tk.StringVar()
sel_filename = tk.StringVar()

def on_select(_e=None):
    if not lst.curselection():
        return
    i = lst.curselection()[0]
    # Support both 3-col (rus, eng, ipa) and 4-col (rus, eng, ipa, filename)
    rus = rows[i][0] if len(rows[i]) > 0 else ""
    eng = rows[i][1] if len(rows[i]) > 1 else ""
    ipa = rows[i][2] if len(rows[i]) > 2 else ""
    fname = rows[i][3] if len(rows[i]) > 3 else ""
    sel_word.set(rus); sel_eng.set(eng); sel_ipa.set(ipa); sel_filename.set(fname)

lst.bind("<<ListboxSelect>>", on_select)

ttk.Label(right, text="Word", font=("Arial", 12, "bold")).pack(anchor="w")
ttk.Label(right, textvariable=sel_word, font=("Arial", 16)).pack(anchor="w", pady=(0,10))
ttk.Label(right, text="Meaning", font=("Arial", 12, "bold")).pack(anchor="w")
ttk.Label(right, textvariable=sel_eng).pack(anchor="w", pady=(0,10))
ttk.Label(right, text="Pronunciation", font=("Arial", 12, "bold")).pack(anchor="w")
ttk.Label(right, textvariable=sel_ipa).pack(anchor="w", pady=(0,20))

def do_play():
    if not sel_word.get():
        messagebox.showinfo("Pick a word", "Select a word first.")
        return
    play_audio(sel_word.get(), sel_filename.get())

def do_record():
    if not sel_word.get():
        messagebox.showinfo("Pick a word", "Select a word first.")
        return
    record_audio(sel_word.get(), seconds=3)

def do_play_user():
    if not sel_word.get():
        messagebox.showinfo("Pick a word", "Select a word first.")
        return
    play_user_recording(sel_word.get())

ttk.Button(right, text="▶️ Play", command=do_play).pack(fill="x", pady=6)
ttk.Button(right, text="🎤 Record (3s)", command=do_record).pack(fill="x", pady=6)
ttk.Button(right, text="▶️ Play My Recording", command=do_play_user).pack(fill="x", pady=6)

print("✅ GUI launched")
root.mainloop()
