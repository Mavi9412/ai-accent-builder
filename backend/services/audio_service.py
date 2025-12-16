"""
Audio Service - Handles audio file processing
"""
import os
import uuid
from pathlib import Path
from typing import Dict, Optional


# Find and add FFmpeg to PATH if not already available  
def _setup_ffmpeg_path():
    """Find FFmpeg installation and add to PATH."""
    # Check if ffmpeg is already in PATH
    import shutil
    if shutil.which('ffmpeg'):
        return
    
    # Common FFmpeg installation paths on Windows
    possible_paths = [
        # WinGet installation
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'WinGet' / 'Packages',
        # Chocolatey
        Path(r'C:\ProgramData\chocolatey\bin'),
        # Manual installations
        Path(r'C:\ffmpeg\bin'),
        Path(r'C:\Program Files\ffmpeg\bin'),
        Path(r'C:\Program Files (x86)\ffmpeg\bin'),
    ]
    
    for base_path in possible_paths:
        if not base_path.exists():
            continue
        
        # For WinGet, search in subdirectories
        if 'WinGet' in str(base_path):
            for subdir in base_path.glob('*ffmpeg*/**/bin'):
                if (subdir / 'ffmpeg.exe').exists():
                    os.environ['PATH'] = str(subdir) + os.pathsep + os.environ.get('PATH', '')
                    print(f"[AudioService] Added FFmpeg to PATH: {subdir}")
                    return
        elif (base_path / 'ffmpeg.exe').exists():
            os.environ['PATH'] = str(base_path) + os.pathsep + os.environ.get('PATH', '')
            print(f"[AudioService] Added FFmpeg to PATH: {base_path}")
            return

_setup_ffmpeg_path()


class AudioService:
    """Service for handling audio files"""
    
    def __init__(self, upload_dir: str = None):
        if upload_dir is None:
            self.upload_dir = Path(__file__).parent.parent / "uploads" / "audio"
        else:
            self.upload_dir = Path(upload_dir)
        
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_audio(self, file_content: bytes, filename: str = None) -> Dict:
        """Save uploaded audio file and return file info"""
        if filename is None:
            filename = f"audio_{uuid.uuid4().hex}.wav"
        
        file_path = self.upload_dir / filename
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        
        return {
            "path": str(file_path),
            "filename": filename,
            "size": file_size,
            "duration": self._estimate_duration(file_size)
        }
    
    async def save_user_recording(self, file_content: bytes, user_id: int, 
                                   original_filename: str = None) -> tuple:
        """
        Save user's voice recording
        Returns: (file_path, filename)
        """
        # Generate unique filename
        ext = ".wav"
        if original_filename:
            _, ext = os.path.splitext(original_filename)
            if not ext:
                ext = ".wav"
        
        filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = self.upload_dir / filename
        
        # Ensure directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Convert to absolute path string for consistency
        abs_path = str(file_path.resolve())
        print(f"[DEBUG] Saved audio to: {abs_path}, size: {len(file_content)} bytes")
        
        # Verify file exists
        if not os.path.exists(abs_path):
            print(f"[ERROR] File not found after save: {abs_path}")
        
        return abs_path, filename
    
    def validate_audio_file(self, file_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate audio file format and content
        Returns: (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "File not found"
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
            
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            return False, "File too large (max 10MB)"
            
        return True, None
    
    def convert_to_wav(self, file_path: str) -> str:
        """
        Convert audio file to WAV format.
        Uses librosa first (works without FFmpeg), falls back to pydub.
        Returns the path to the converted file.
        """
        print(f"[AudioService] Converting to WAV: {file_path}")
        wav_path = file_path.rsplit('.', 1)[0] + '_converted.wav'
        
        # Try librosa first (works without FFmpeg for many formats)
        try:
            import librosa
            import soundfile as sf
            
            print(f"[AudioService] Loading audio with librosa...")
            audio, sr = librosa.load(file_path, sr=16000, mono=True)
            duration_sec = len(audio) / sr
            print(f"[AudioService] Loaded: {duration_sec:.2f}s, 16kHz mono")
            
            if duration_sec < 0.5:
                print(f"[AudioService] WARNING: Audio too short ({duration_sec}s)")
            
            sf.write(wav_path, audio, 16000)
            
            # Verify file
            if os.path.exists(wav_path):
                size = os.path.getsize(wav_path)
                print(f"[AudioService] SUCCESS: WAV saved ({size} bytes)")
                return wav_path
            
        except Exception as e:
            print(f"[AudioService] librosa conversion failed: {e}")
        
        # Fallback to pydub (requires FFmpeg)
        try:
            from pydub import AudioSegment
            
            print(f"[AudioService] Trying pydub (requires FFmpeg)...")
            audio = AudioSegment.from_file(file_path)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_path, format='wav')
            
            if os.path.exists(wav_path):
                size = os.path.getsize(wav_path)
                print(f"[AudioService] SUCCESS via pydub: WAV saved ({size} bytes)")
                return wav_path
            
        except Exception as e:
            print(f"[AudioService] pydub conversion failed: {e}")
        
        print(f"[AudioService] All conversion methods failed, returning original")
        return file_path

    def _estimate_duration(self, file_size: int) -> float:
        """Estimate audio duration from file size (for WAV files)"""
        # WAV file: sample_rate * channels * bytes_per_sample = bytes_per_second
        # For 16kHz, mono, 16-bit: 16000 * 1 * 2 = 32000 bytes/second
        bytes_per_second = 32000
        return file_size / bytes_per_second
    
    def get_audio_info(self, file_path: str) -> Dict:
        """Get information about an audio file"""
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        
        file_size = os.path.getsize(path)
        return {
            "path": str(path),
            "filename": path.name,
            "size": file_size,
            "duration": self._estimate_duration(file_size)
        }


# Singleton instance
audio_service = AudioService()
