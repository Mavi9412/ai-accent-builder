"""
Speech-to-Text Service using Vosk (Primary) + Whisper (Fallback)
Fast, accurate, offline transcription with word timestamps.
"""
import os
import json
import wave
from typing import Dict, List, Optional

# Check for Vosk
VOSK_AVAILABLE = False
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)  # Disable Vosk logging
    VOSK_AVAILABLE = True
except ImportError:
    print("Vosk not available for STT")

# Check for Whisper (fallback)
WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    print("Whisper not available for STT fallback")


class STTService:
    """Speech-to-Text service using Vosk (primary) with Whisper fallback."""
    
    # Default Vosk model path
    VOSK_MODEL_PATH = r"D:\Vosk Model\vosk-model-en-us-0.22"
    
    def __init__(self, vosk_model_path: str = None, whisper_model: str = "base"):
        """
        Initialize STT service.
        
        Args:
            vosk_model_path: Path to Vosk model directory
            whisper_model: Whisper model size for fallback
        """
        self.vosk_model = None
        self.whisper_model = None
        self.vosk_model_path = vosk_model_path or self.VOSK_MODEL_PATH
        self.whisper_model_name = whisper_model
        self._vosk_initialized = False
        self._whisper_initialized = False
    
    def _init_vosk(self):
        """Initialize Vosk model lazily."""
        if self._vosk_initialized:
            return
        
        if not VOSK_AVAILABLE:
            print("Vosk not available")
            return
        
        if not os.path.exists(self.vosk_model_path):
            print(f"Vosk model not found at: {self.vosk_model_path}")
            return
        
        try:
            print(f"Loading Vosk model from: {self.vosk_model_path}")
            self.vosk_model = Model(self.vosk_model_path)
            self._vosk_initialized = True
            print("Vosk model loaded successfully!")
        except Exception as e:
            print(f"Failed to load Vosk model: {e}")
    
    def _init_whisper(self):
        """Initialize Whisper model lazily (fallback)."""
        if self._whisper_initialized:
            return
        
        if not WHISPER_AVAILABLE:
            print("Whisper not available")
            return
        
        try:
            print(f"Loading Whisper '{self.whisper_model_name}' model...")
            self.whisper_model = whisper.load_model(self.whisper_model_name)
            self._whisper_initialized = True
            print("Whisper model loaded successfully!")
        except Exception as e:
            print(f"Failed to load Whisper: {e}")
    
    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe audio file to text.
        Uses Vosk as primary, Whisper as fallback.
        
        Args:
            audio_path: Path to WAV audio file
        
        Returns:
            Dict with transcribed_text, word_timestamps, confidence
        """
        # Check if file exists
        if not os.path.exists(audio_path):
            print(f"[ERROR] Audio file not found: {audio_path}")
            return {
                "transcribed_text": "",
                "word_timestamps": [],
                "confidence": 0,
                "error": f"File not found: {audio_path}"
            }
        
        # Try Vosk first
        result = self._transcribe_vosk(audio_path)
        
        if result.get("transcribed_text"):
            result["source"] = "vosk"
            return result
        
        # Fallback to Whisper if Vosk failed
        print("[DEBUG] Vosk returned empty, trying Whisper fallback...")
        result = self._transcribe_whisper(audio_path)
        result["source"] = "whisper"
        return result
    
    def _transcribe_vosk(self, audio_path: str) -> Dict:
        """Transcribe using Vosk."""
        self._init_vosk()
        
        if not self.vosk_model:
            return {
                "transcribed_text": "",
                "word_timestamps": [],
                "confidence": 0,
                "error": "Vosk model not loaded"
            }
        
        try:
            # Convert to proper WAV format if needed
            audio_path = self._ensure_wav_format(audio_path)
            
            wf = wave.open(audio_path, "rb")
            
            # Check audio format
            if wf.getnchannels() != 1:
                print(f"[WARN] Audio has {wf.getnchannels()} channels, converting to mono...")
                wf.close()
                audio_path = self._convert_to_mono(audio_path)
                wf = wave.open(audio_path, "rb")
            
            sample_rate = wf.getframerate()
            print(f"[DEBUG] Vosk processing: {audio_path}, rate={sample_rate}Hz")
            
            rec = KaldiRecognizer(self.vosk_model, sample_rate)
            rec.SetWords(True)  # Enable word timestamps
            
            # Process audio in chunks
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    part_result = json.loads(rec.Result())
                    if part_result.get("text"):
                        results.append(part_result)
            
            # Get final result
            final = json.loads(rec.FinalResult())
            if final.get("text"):
                results.append(final)
            
            wf.close()
            
            # Combine results
            full_text = " ".join(r.get("text", "") for r in results).strip()
            
            # Extract word timestamps
            word_timestamps = []
            for r in results:
                for word_info in r.get("result", []):
                    word_timestamps.append({
                        "word": word_info.get("word", ""),
                        "start": round(word_info.get("start", 0), 3),
                        "end": round(word_info.get("end", 0), 3),
                        "probability": round(word_info.get("conf", 0.9), 3)
                    })
            
            # Calculate confidence
            if word_timestamps:
                avg_conf = sum(w["probability"] for w in word_timestamps) / len(word_timestamps)
            else:
                avg_conf = 0.9 if full_text else 0
            
            print(f"[DEBUG] Vosk result: '{full_text[:50]}...' ({len(word_timestamps)} words)")
            
            return {
                "transcribed_text": full_text,
                "word_timestamps": word_timestamps,
                "confidence": round(avg_conf, 3),
                "word_count": len(word_timestamps)
            }
            
        except Exception as e:
            print(f"[ERROR] Vosk transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "transcribed_text": "",
                "word_timestamps": [],
                "confidence": 0,
                "error": str(e)
            }
    
    def _transcribe_whisper(self, audio_path: str) -> Dict:
        """Transcribe using Whisper (fallback)."""
        self._init_whisper()
        
        if not self.whisper_model:
            return {
                "transcribed_text": "",
                "word_timestamps": [],
                "confidence": 0,
                "error": "Whisper model not loaded"
            }
        
        try:
            # Load audio with librosa (no ffmpeg needed)
            import librosa
            audio, sr = librosa.load(audio_path, sr=16000)
            print(f"[DEBUG] Whisper processing: {len(audio)/sr:.2f}s audio")
            
            result = self.whisper_model.transcribe(
                audio,
                word_timestamps=True,
                language="en",
                fp16=False
            )
            
            text = result.get("text", "").strip()
            
            # Extract word timestamps
            word_timestamps = []
            for segment in result.get("segments", []):
                for word_info in segment.get("words", []):
                    word = word_info.get("word", "").strip()
                    if word:
                        word_timestamps.append({
                            "word": word,
                            "start": round(word_info.get("start", 0), 3),
                            "end": round(word_info.get("end", 0), 3),
                            "probability": round(word_info.get("probability", 0.9), 3)
                        })
            
            avg_conf = sum(w["probability"] for w in word_timestamps) / len(word_timestamps) if word_timestamps else 0.9
            
            return {
                "transcribed_text": text,
                "word_timestamps": word_timestamps,
                "confidence": round(avg_conf, 3),
                "word_count": len(word_timestamps)
            }
            
        except Exception as e:
            print(f"[ERROR] Whisper transcription failed: {e}")
            return {
                "transcribed_text": "",
                "word_timestamps": [],
                "confidence": 0,
                "error": str(e)
            }
    
    def _ensure_wav_format(self, audio_path: str) -> str:
        """Ensure audio is in proper WAV format for Vosk."""
        if not audio_path.endswith('.wav'):
            # Convert using pydub or librosa
            try:
                import librosa
                import soundfile as sf
                
                audio, sr = librosa.load(audio_path, sr=16000, mono=True)
                wav_path = audio_path.rsplit('.', 1)[0] + '_converted.wav'
                sf.write(wav_path, audio, 16000)
                return wav_path
            except:
                return audio_path
        return audio_path
    
    def _convert_to_mono(self, audio_path: str) -> str:
        """Convert stereo audio to mono."""
        try:
            import librosa
            import soundfile as sf
            
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            mono_path = audio_path.rsplit('.', 1)[0] + '_mono.wav'
            sf.write(mono_path, audio, 16000)
            return mono_path
        except:
            return audio_path


# Singleton instance
stt_service = STTService()
