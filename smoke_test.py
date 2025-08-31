from pydub import AudioSegment
from pydub.utils import which

# Ensure PyDub knows where ffmpeg is
AudioSegment.converter = which("ffmpeg")

print("🔍 Using ffmpeg at:", AudioSegment.converter)

# Create 1 second of silence
s = AudioSegment.silent(duration=1000)

# Export to MP3 to confirm end-to-end
out_file = "smoke_test.mp3"
s.export(out_file, format="mp3")

print(f"✅ pydub + ffmpeg working! File saved as {out_file}")
