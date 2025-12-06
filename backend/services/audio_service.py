"""
Audio Service - Handles audio file processing
"""
import os
import uuid
from pathlib import Path
from typing import Dict, Optional


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
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return str(file_path), filename
    
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
