from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
import os
import logging
from werkzeug.utils import secure_filename
from pydub import AudioSegment  
import pyaudio

def check_microphone():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            print(f"Microphone found: {dev['name']}")
    p.terminate()

check_microphone()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize_speech():
    try:
        logger.debug("Received recognition request")
        
        if 'audio_data' not in request.files:
            logger.error("No audio file in request")
            return jsonify({'error': 'No audio file uploaded'}), 400

        audio_file = request.files['audio_data']
        lang_code = request.form.get('language', 'en-IN')
        
        if audio_file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No selected file'}), 400

        # Save the original audio file
        original_filename = secure_filename(audio_file.filename)
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        audio_file.save(original_path)
        logger.debug(f"Saved uploaded file to {original_path}")

        # Convert to WAV format
        wav_filename = os.path.splitext(original_filename)[0] + '.wav'
        wav_path = os.path.join(app.config['UPLOAD_FOLDER'], wav_filename)
        
        try:
            audio = AudioSegment.from_file(original_path)
            audio.export(wav_path, format="wav")
            logger.debug(f"Converted file to WAV format: {wav_path}")
        except Exception as e:
            logger.error(f"Audio conversion failed: {str(e)}")
            return jsonify({'error': 'Audio conversion failed', 'status': 'error'}), 400

        recognizer = sr.Recognizer()

        try:
            with sr.AudioFile(wav_path) as source:
                recognizer.adjust_for_ambient_noise(source)
                audio_data = recognizer.record(source)

                try:
                    text = recognizer.recognize_google(audio_data, language=lang_code)
                    logger.debug(f"Recognition successful: {text[:50]}...")
                    return jsonify({'result': text, 'status': 'success'})
                except sr.UnknownValueError:
                    logger.error("Could not understand audio")
                    return jsonify({'error': "Could not understand audio", 'status': 'error'}), 400
                except sr.RequestError as e:
                    logger.error(f"Recognition service error: {e}")
                    return jsonify({'error': f"Recognition service error: {e}", 'status': 'error'}), 500

        finally:
            
            if os.path.exists(original_path):
                os.remove(original_path)
                logger.debug(f"Deleted original file: {original_path}")
            if os.path.exists(wav_path):
                os.remove(wav_path)
                logger.debug(f"Deleted converted WAV file: {wav_path}")

    except Exception as e:
        logger.error(f"Unexpected error in endpoint: {str(e)}")
        return jsonify({'error': f"Server error: {str(e)}", 'status': 'error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
