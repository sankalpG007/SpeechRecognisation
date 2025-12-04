import wave
import struct
import math

# Create a simple sine wave WAV file
def create_test_wav(filename="test.wav", duration=3, frequency=440, sample_rate=16000):
    # Create WAV file
    with wave.open(filename, 'w') as wav_file:
        # Set parameters
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes = 16 bits
        wav_file.setframerate(sample_rate)
        
        # Generate audio data
        num_frames = int(duration * sample_rate)
        
        for i in range(num_frames):
            # Generate sine wave
            value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
            # Pack as 16-bit signed integer
            data = struct.pack('<h', value)
            wav_file.writeframes(data)
    
    print(f"Created test WAV file: {filename} ({duration} seconds, {frequency} Hz)")

if __name__ == "__main__":
    create_test_wav("test_audio.wav")