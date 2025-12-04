from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
import os
import logging
import tempfile
import subprocess
import sys
import wave
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Language codes for Google Speech Recognition
LANGUAGES = {
    'en-IN': 'English (India)',
    'en-US': 'English (US)',
    'hi-IN': 'Hindi (India)',
    'mr-IN': 'Marathi (India)',
    'ta-IN': 'Tamil (India)',
    'te-IN': 'Telugu (India)',
    'kn-IN': 'Kannada (India)',
    'ml-IN': 'Malayalam (India)',
    'bn-IN': 'Bengali (India)',
    'gu-IN': 'Gujarati (India)',
    'pa-IN': 'Punjabi (India)'
}

# Supported audio formats
SUPPORTED_FORMATS = {
    '.wav': 'WAV Audio',
    '.mp3': 'MP3 Audio',
    '.m4a': 'MPEG-4 Audio',
    '.ogg': 'Ogg Vorbis',
    '.flac': 'FLAC Audio',
    '.webm': 'WebM Audio',
    '.weba': 'WebM Audio',
    '.aac': 'AAC Audio',
    '.wma': 'Windows Media Audio'
}

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        if result.returncode == 0:
            logger.info("✅ FFmpeg is available")
            return True
        else:
            logger.warning("⚠️ FFmpeg check failed")
            return False
    except FileNotFoundError:
        logger.warning("❌ FFmpeg not found in PATH")
        return False

def convert_audio_to_wav(input_data, input_format='webm'):
    """Convert any audio format to WAV using ffmpeg"""
    try:
        # Create temporary input file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{input_format}') as input_file:
            input_file.write(input_data)
            input_path = input_file.name
        
        # Create temporary output WAV file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as output_file:
            output_path = output_file.name
        
        # Convert using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', input_path,           # Input file
            '-acodec', 'pcm_s16le',     # 16-bit PCM codec
            '-ac', '1',                 # Mono audio (better for speech recognition)
            '-ar', '16000',             # 16kHz sample rate (optimal for speech)
            '-sample_fmt', 's16',       # 16-bit samples
            '-y',                       # Overwrite output file
            output_path
        ]
        
        logger.info(f"Converting {input_format} to WAV...")
        
        # Run ffmpeg with timeout
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True,
                              timeout=30,
                              creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg conversion failed: {result.stderr}")
            raise Exception(f"Audio conversion failed. Error: {result.stderr[:200]}")
        
        # Read the converted WAV file
        with open(output_path, 'rb') as f:
            wav_data = f.read()
        
        # Get duration of converted file
        duration = get_wav_duration(output_path)
        logger.info(f"✅ Conversion successful. Duration: {duration:.2f} seconds, Size: {len(wav_data)} bytes")
        
        # Clean up temporary files
        os.unlink(input_path)
        os.unlink(output_path)
        
        return wav_data, duration
        
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timeout")
        raise Exception("Audio conversion took too long. Please try a shorter audio file.")
    except Exception as e:
        logger.error(f"Error converting audio to wav: {e}")
        # Clean up in case of error
        for path in [input_path, output_path]:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except:
                pass
        raise

def get_wav_duration(wav_path):
    """Get duration of WAV file"""
    try:
        with wave.open(wav_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except:
        return 0

def get_file_extension(filename):
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()

def split_audio_file(wav_path, chunk_duration=50):
    """Split WAV file into chunks"""
    try:
        with wave.open(wav_path, 'rb') as wav_file:
            # Get WAV parameters
            params = wav_file.getparams()
            frame_rate = params.framerate
            n_channels = params.nchannels
            samp_width = params.sampwidth
            
            # Calculate frames per chunk
            frames_per_chunk = int(frame_rate * chunk_duration)
            
            chunks = []
            total_frames = wav_file.getnframes()
            current_frame = 0
            
            while current_frame < total_frames:
                # Read frames for this chunk
                frames_to_read = min(frames_per_chunk, total_frames - current_frame)
                frames = wav_file.readframes(frames_to_read)
                
                if not frames:
                    break
                
                # Create temporary WAV file for this chunk
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as chunk_file:
                    chunk_path = chunk_file.name
                    
                with wave.open(chunk_path, 'wb') as chunk_wav:
                    chunk_wav.setparams(params)
                    chunk_wav.writeframes(frames)
                
                chunks.append(chunk_path)
                current_frame += frames_to_read
            
            return chunks
            
    except Exception as e:
        logger.error(f"Error splitting audio: {e}")
        return []

def recognize_audio_chunk(chunk_path, language_code):
    """Recognize speech from a single audio chunk"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(chunk_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Record the audio
            audio = recognizer.record(source)
            
            # Try recognition
            text = recognizer.recognize_google(audio, language=language_code)
            return {'status': 'success', 'text': text}
            
    except sr.UnknownValueError:
        return {'status': 'error', 'message': 'Could not understand audio in this chunk'}
    except sr.RequestError as e:
        return {'status': 'error', 'message': f'Recognition service error: {e}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Error processing chunk: {str(e)}'}

def process_audio_data(audio_data, language_code, filename='audio'):
    """Process audio data and convert to text with chunking for long files"""
    # Get file extension
    file_ext = get_file_extension(filename)
    
    logger.info(f"Converting {file_ext or 'unknown'} format to WAV...")
    try:
        # Convert to WAV using ffmpeg
        format_name = file_ext.lstrip('.') if file_ext else 'webm'
        wav_data, duration = convert_audio_to_wav(audio_data, format_name)
        
        # Check if audio is too long
        MAX_DURATION = 300  # 5 minutes max for chunking (Google limit is ~1 minute per request)
        
        if duration > MAX_DURATION:
            logger.warning(f"Audio is too long ({duration:.2f} seconds). Splitting into chunks...")
            
            # Save WAV to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                temp_wav.write(wav_data)
                temp_wav_path = temp_wav.name
            
            try:
                # Split into chunks (50 seconds each for safety)
                chunks = split_audio_file(temp_wav_path, chunk_duration=50)
                logger.info(f"Split into {len(chunks)} chunks")
                
                all_text = []
                successful_chunks = 0
                
                for i, chunk_path in enumerate(chunks):
                    logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
                    result = recognize_audio_chunk(chunk_path, language_code)
                    
                    if result['status'] == 'success':
                        all_text.append(result['text'])
                        successful_chunks += 1
                    
                    # Clean up chunk file
                    try:
                        os.unlink(chunk_path)
                    except:
                        pass
                
                # Clean up main WAV file
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
                
                if successful_chunks > 0:
                    final_text = ' '.join(all_text)
                    logger.info(f"✅ Successfully processed {successful_chunks}/{len(chunks)} chunks")
                    return {'status': 'success', 'text': final_text, 'chunks_processed': successful_chunks}
                else:
                    return {'status': 'error', 'message': 'Could not recognize speech in any chunk'}
                    
            except Exception as e:
                logger.error(f"Error in chunk processing: {e}")
                return {'status': 'error', 'message': f'Error processing long audio: {str(e)}'}
            finally:
                # Clean up
                for path in [temp_wav_path] + chunks:
                    try:
                        if os.path.exists(path):
                            os.unlink(path)
                    except:
                        pass
        else:
                            # For short audio, process directly
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                temp_wav.write(wav_data)
                temp_wav_path = temp_wav.name

            try:
                # Use wave-based duration getter instead of source.DURATION
                duration = get_wav_duration(temp_wav_path)
                logger.info(f"Audio duration (calculated): {duration:.2f} seconds")

                with sr.AudioFile(temp_wav_path) as source:
                    logger.info("Processing audio file with SpeechRecognition...")

                    # Initialize recognizer
                    recognizer = sr.Recognizer()

                    # Adjust for ambient noise (use small duration safely)
                    adjust_duration = min(1.0, max(0.1, duration / 3)) if duration > 0 else 0.5
                    try:
                        recognizer.adjust_for_ambient_noise(source, duration=adjust_duration)
                    except Exception as ex:
                        # Some audio files may not support seeking in the same way; log and continue
                        logger.warning(f"Warning adjusting for ambient noise: {ex}")

                    # Reset audio file pointer by re-opening (sr.AudioFile read will handle)
                    audio = recognizer.record(source)

                    logger.info(f"Sending to Google Speech Recognition (Language: {language_code})...")

                    # Try recognition
                    try:
                        text = recognizer.recognize_google(audio, language=language_code)
                        logger.info(f"✅ Recognition successful: {text[:100]}...")
                        return {'status': 'success', 'text': text}

                    except sr.UnknownValueError:
                        logger.error("Google Speech Recognition could not understand audio")
                        return {'status': 'error', 'message': "Could not understand the audio. Please speak clearly and try again."}

                    except sr.RequestError as e:
                        logger.error(f"Google Speech Recognition error: {e}")
                        return {'status': 'error', 'message': f"Could not connect to recognition service. Please check your internet connection."}

            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)
                except Exception as cleanup_ex:
                    logger.warning(f"Failed to delete temp wav file: {cleanup_ex}")

        
    except Exception as e:
        logger.error(f"Error in audio processing: {e}")
        return {'status': 'error', 'message': f"Error processing audio: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html', languages=LANGUAGES, formats=SUPPORTED_FORMATS)

@app.route('/record', methods=['POST'])
def record_audio():
    """Endpoint to handle recorded audio from browser"""
    try:
        if 'audio_data' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio data received'}), 400
        
        audio_file = request.files['audio_data']
        language_code = request.form.get('language', 'en-IN')
        
        if audio_file.filename == '':
            return jsonify({'status': 'error', 'message': 'No audio file'}), 400
        
        # Read the audio data
        audio_data = audio_file.read()
        
        if len(audio_data) == 0:
            return jsonify({'status': 'error', 'message': 'Empty audio file'}), 400
        
        # Process the audio
        result = process_audio_data(audio_data, language_code, filename=audio_file.filename)
        
        if result['status'] == 'success':
            response_data = {
                'status': 'success',
                'text': result['text'],
                'language': LANGUAGES.get(language_code, language_code)
            }
            if 'chunks_processed' in result:
                response_data['chunks_processed'] = result['chunks_processed']
            return jsonify(response_data)
        else:
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in record endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Server error: {str(e)}"
        }), 500

@app.route('/upload', methods=['POST'])
def upload_audio():
    """Endpoint to handle uploaded audio files"""
    try:
        if 'audio_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No audio file uploaded'}), 400
        
        audio_file = request.files['audio_file']
        language_code = request.form.get('language', 'en-IN')
        
        if audio_file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        
        # Check file size (max 50MB for longer files)
        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)
        
        if file_size > 50 * 1024 * 1024:
            return jsonify({
                'status': 'error', 
                'message': 'File too large. Maximum size is 50MB.'
            }), 400
        
        # Check file extension
        file_ext = get_file_extension(audio_file.filename)
        if file_ext not in SUPPORTED_FORMATS:
            return jsonify({
                'status': 'error',
                'message': f'Unsupported file format: {file_ext}. Supported formats: {", ".join(SUPPORTED_FORMATS.keys())}'
            }), 400
        
        # Read the audio data
        audio_data = audio_file.read()
        
        if len(audio_data) == 0:
            return jsonify({'status': 'error', 'message': 'Empty audio file'}), 400
        
        # Process the audio
        result = process_audio_data(audio_data, language_code, filename=audio_file.filename)
        
        if result['status'] == 'success':
            response_data = {
                'status': 'success',
                'text': result['text'],
                'language': LANGUAGES.get(language_code, language_code),
                'filename': audio_file.filename,
                'file_size': file_size
            }
            if 'chunks_processed' in result:
                response_data['chunks_processed'] = result['chunks_processed']
                response_data['processing_note'] = 'Audio was split into chunks for processing'
            return jsonify(response_data)
        else:
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': f"Server error: {str(e)}"
        }), 500

@app.route('/test')
def test():
    """Test endpoint to check if server is running"""
    ffmpeg_available = check_ffmpeg()
    return jsonify({
        'status': 'running',
        'message': 'Speech Recognition Server is running',
        'supported_languages': LANGUAGES,
        'supported_formats': SUPPORTED_FORMATS,
        'ffmpeg_available': ffmpeg_available,
        'max_file_size': '50MB',
        'max_duration': '5 minutes (automatically split into chunks)'
    })

if __name__ == '__main__':
    # Check for ffmpeg
    ffmpeg_available = check_ffmpeg()
    
    logger.info("""
    ============================================
    🎤 REAL-TIME SPEECH RECOGNITION APP - PRO VERSION
    ============================================
    Features:
    1. Record audio with microphone
    2. Upload audio files (MP3, WAV, M4A, etc.)
    3. Support for multiple Indian languages
    4. Real-time speech to text conversion
    5. Automatic chunking for long audio files
    
    Supported Languages: %d languages
    Supported Formats: %s
    
    FFmpeg Status: %s
    
    Max File Size: 50MB
    Max Duration: 5 minutes (auto-split into chunks)
    
    Access at: http://localhost:5000
    ============================================
    """ % (
        len(LANGUAGES),
        ", ".join(SUPPORTED_FORMATS.keys()),
        "✅ AVAILABLE" if ffmpeg_available else "❌ NOT FOUND"
    ))
    
    if not ffmpeg_available:
        logger.error("""
        ❌ FFmpeg is required but not found!
        Please install FFmpeg and restart the application.
        """)
    
    app.run(debug=True, port=5000, host='0.0.0.0')