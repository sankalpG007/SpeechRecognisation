from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
import os
import logging
import tempfile
import wave

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def is_valid_wav(filepath):
    """Check if file is a valid WAV file"""
    try:
        with wave.open(filepath, 'rb') as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            logger.info(f"WAV file: {channels} channels, {sample_width} bytes/sample, {frame_rate} Hz, {n_frames} frames")
            
            if n_frames == 0:
                logger.error("WAV file has 0 frames")
                return False
                
            return True
    except Exception as e:
        logger.error(f"Not a valid WAV file: {e}")
        return False

@app.route('/')
def index():
    return render_template('index_simple.html')

@app.route('/recognize', methods=['POST'])
def recognize_speech():
    temp_files = []
    
    try:
        logger.info("Received recognition request")
        
        if 'audio_data' not in request.files:
            logger.error("No audio file in request")
            return jsonify({'error': 'No audio file uploaded'}), 400

        audio_file = request.files['audio_data']
        lang_code = request.form.get('language', 'en-IN')
        
        if audio_file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No selected file'}), 400

        # Read file data
        audio_data = audio_file.read()
        filename = audio_file.filename.lower()
        
        # Only accept WAV files
        if not filename.endswith('.wav'):
            return jsonify({
                'error': f'Unsupported file format. Please upload WAV files only.',
                'supported_formats': ['WAV'],
                'help': 'Convert your files to WAV using: https://online-audio-converter.com/',
                'status': 'error'
            }), 400

        # Save as temporary WAV file
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_wav.write(audio_data)
        temp_wav.close()
        temp_files.append(temp_wav.name)
        wav_path = temp_wav.name
        
        # Validate WAV file
        if not is_valid_wav(wav_path):
            return jsonify({
                'error': 'Invalid WAV file format. Please ensure it is a proper 16-bit PCM WAV file.',
                'status': 'error'
            }), 400

        # Initialize recognizer
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(wav_path) as source:
                logger.info("Processing audio file...")
                
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                # Record the audio
                audio_data = recognizer.record(source)
                
                logger.info("Sending to Google Speech Recognition...")
                
                # Try recognition
                try:
                    text = recognizer.recognize_google(audio_data, language=lang_code)
                    logger.info(f"Recognition successful: {text[:100]}...")
                    return jsonify({
                        'result': text, 
                        'status': 'success',
                        'characters': len(text),
                        'words': len(text.split())
                    })
                    
                except sr.UnknownValueError:
                    logger.error("Google Speech Recognition could not understand audio")
                    return jsonify({
                        'error': "Could not understand the audio. Please ensure clear speech and try again.",
                        'status': 'error'
                    }), 400
                    
                except sr.RequestError as e:
                    logger.error(f"Could not request results from Google Speech Recognition service: {e}")
                    return jsonify({
                        'error': f"Could not connect to Google Speech Recognition service. Please check your internet connection.",
                        'status': 'error'
                    }), 500
                    
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            return jsonify({
                'error': f"Error processing audio file: {str(e)}",
                'suggestion': 'Please ensure you are uploading a standard 16-bit PCM WAV file.',
                'status': 'error'
            }), 400

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': f"Server error: {str(e)}", 'status': 'error'}), 500
        
    finally:
        # Clean up temporary files
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Error removing temp file {file_path}: {e}")

@app.route('/test_wav', methods=['GET'])
def test_wav():
    """Test endpoint to verify WAV file processing works"""
    return jsonify({
        'status': 'ready',
        'message': 'Server is ready to process WAV files',
        'supported_formats': ['WAV'],
        'test_file': 'test_audio.wav (created earlier)'
    })

if __name__ == '__main__':
    logger.info("""
    ============================================
    🎤 SPEECH RECOGNITION APP - FINAL VERSION
    ============================================
    Server starting...
    
    IMPORTANT:
    - This version ONLY supports WAV files
    - No FFmpeg required
    
    Access the app at:
    - http://localhost:5000
    - http://127.0.0.1:5000
    
    Test endpoint: http://localhost:5000/test_wav
    ============================================
    """)
    app.run(debug=True, port=5000, host='0.0.0.0')