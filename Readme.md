
Multi-Language Speech Recognition in Python

📌 Project Overview:
This Python project uses the `speech_recognition` library to convert speech into text. 
The user can choose from multiple Indian languages including English, Hindi, and Marathi. 
The program listens through the microphone and prints out the spoken words in the selected language.

------------------------------
📦 Required Libraries:
- speech_recognition
- pyaudio

Installation:
> pip install SpeechRecognition
> pip install pipwin
> pipwin install pyaudio

------------------------------
🧠 How the Code Works:

1. The program first asks the user to select a language:
   - 1 = English
   - 2 = Hindi
   - 3 = Marathi

2. Based on user input, it sets the appropriate **language code** (e.g., "en-IN" for English, "hi-IN" for Hindi).

3. The microphone is then activated, and the user is asked to speak.

4. The `speech_recognition` library captures the audio and uses the **Google Web Speech API** to convert it into text in the selected language.

5. The recognized text is printed. If there's an error (like unclear speech or no internet), an appropriate message is shown.

------------------------------
✅ Python Code:

```python
import speech_recognition as sr

# Initialize recognizer
recognizer = sr.Recognizer()

# Select language
print("Select a language:")
print("1. English (en-IN)")
print("2. Hindi (hi-IN)")
print("3. Marathi (mr-IN)")
choice = input("Enter your choice (1/2/3): ")

# Set language code based on user input
if choice == '1':
    language_code = 'en-IN'
elif choice == '2':
    language_code = 'hi-IN'
elif choice == '3':
    language_code = 'mr-IN'
else:
    print("Invalid choice! Defaulting to English.")
    language_code = 'en-IN'

# Use microphone to capture audio
with sr.Microphone() as source:
    print(f"Listening... (Language: {language_code})")
    recognizer.adjust_for_ambient_noise(source)
    audio = recognizer.listen(source)

    try:
        print("Recognizing...")
        text = recognizer.recognize_google(audio, language=language_code)
        print("You said:", text)
    except sr.UnknownValueError:
        print("Sorry, could not understand your voice.")
    except sr.RequestError:
        print("Could not request results; check your internet connection.")
