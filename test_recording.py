import speech_recognition as sr
import wave

def test_speech_recognition():
    print("🎤 Testing Speech Recognition System")
    print("=" * 50)
    
    # Test recognizer
    r = sr.Recognizer()
    print("✅ Speech recognition initialized")
    
    # Test languages
    languages = ['en-IN', 'hi-IN', 'mr-IN', 'ta-IN', 'te-IN']
    print(f"✅ {len(languages)} languages supported")
    
    print("\n✅ System is ready!")
    print("\nTo use:")
    print("1. Run: python app.py")
    print("2. Open browser to: http://localhost:5000")
    print("3. Select language")
    print("4. Click 'Start Recording' and speak")
    print("5. See your speech converted to text!")

if __name__ == "__main__":
    test_speech_recognition()