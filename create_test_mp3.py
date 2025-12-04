import pydub
from pydub import AudioSegment
from pydub.generators import Sine

# Create a simple tone
print("Creating test audio...")
tone = Sine(440).to_audio_segment(duration=3000)  # 3 seconds

# Add some silence
silence = AudioSegment.silent(duration=1000)  # 1 second

# Combine
audio = tone + silence + tone

# Export as MP3
print("Exporting as MP3...")
audio.export("test_short.mp3", format="mp3", bitrate="128k")

print("✅ Created test_short.mp3 (5 seconds)")
print("Upload this file to test MP3 support!")