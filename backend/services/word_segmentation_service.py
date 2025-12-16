"""
Word Segmentation Service
Trims audio into individual word segments using Vosk timestamps

This service:
1. Takes word timestamps from STT (Vosk/Whisper)
2. Segments user audio into per-word WAV files
3. Segments reference (TTS) audio into matching per-word WAV files
4. Enables A/B comparison of pronunciation per word

Uses Vosk model at: D:\Vosk Model\vosk-model-en-us-0.22
"""

import os
import uuid
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Audio processing
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[WordSegmentation] librosa not available")

# Pydub for audio manipulation
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("[WordSegmentation] pydub not available")


class WordSegmentationService:
    """
    Service for segmenting audio into individual words.
    Uses word timestamps from STT to extract word-level audio.
    """
    
    def __init__(self, output_dir: str = None):
        """Initialize word segmentation service."""
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "uploads" / "word_segments"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default parameters
        self.target_sr = 16000
        self.padding_ms = 50  # Add padding around each word
        self.min_word_duration_ms = 100  # Minimum word duration
        
        print(f"[WordSegmentation] Initialized. Output: {self.output_dir}")
    
    def segment_audio(self, audio_path: str, word_timestamps: List[Dict],
                       session_id: str = None) -> Dict:
        """
        Split audio into word-level WAV files.
        
        Args:
            audio_path: Path to full audio file
            word_timestamps: List of dicts with 'word', 'start', 'end' keys
            session_id: Optional session identifier for file naming
            
        Returns:
            Dict with:
                - word_audio_paths: List of paths to word audio files
                - word_data: List of dicts with word info and audio path
                - success: Boolean indicating success
        """
        if not LIBROSA_AVAILABLE:
            return {"success": False, "error": "librosa not available", "word_audio_paths": []}
        
        if not word_timestamps:
            return {"success": False, "error": "No word timestamps provided", "word_audio_paths": []}
        
        try:
            # Load audio
            audio_data, sr = librosa.load(audio_path, sr=self.target_sr, mono=True)
            total_duration = len(audio_data) / sr
            
            print(f"[WordSegmentation] Loaded audio: {total_duration:.2f}s, {len(word_timestamps)} words")
            
            # Create session directory
            if session_id is None:
                session_id = uuid.uuid4().hex[:8]
            session_dir = self.output_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            word_audio_paths = []
            word_data = []
            
            for idx, word_info in enumerate(word_timestamps):
                word = word_info.get('word', f'word_{idx}')
                start_time = word_info.get('start', 0)
                end_time = word_info.get('end', start_time + 0.5)
                
                # Add padding
                padding_sec = self.padding_ms / 1000
                start_sample = max(0, int((start_time - padding_sec) * sr))
                end_sample = min(len(audio_data), int((end_time + padding_sec) * sr))
                
                # Extract word audio
                word_audio = audio_data[start_sample:end_sample]
                
                # Skip if too short
                if len(word_audio) / sr < self.min_word_duration_ms / 1000:
                    print(f"[WordSegmentation] Word '{word}' too short, skipping")
                    continue
                
                # Save word audio
                word_filename = f"word_{idx:03d}_{self._sanitize_filename(word)}.wav"
                word_path = str(session_dir / word_filename)
                sf.write(word_path, word_audio, sr)
                
                word_audio_paths.append(word_path)
                word_data.append({
                    "word": word,
                    "word_index": idx,
                    "audio_path": word_path,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": end_time - start_time
                })
            
            print(f"[WordSegmentation] Created {len(word_audio_paths)} word segments")
            
            return {
                "success": True,
                "session_id": session_id,
                "word_audio_paths": word_audio_paths,
                "word_data": word_data,
                "session_dir": str(session_dir)
            }
            
        except Exception as e:
            print(f"[WordSegmentation] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "word_audio_paths": []
            }
    
    def segment_reference_audio(self, ref_audio_path: str, ref_text: str,
                                 user_word_data: List[Dict],
                                 session_id: str = None) -> Dict:
        """
        Segment reference (TTS) audio to match user word segments.
        
        Since TTS audio may have different timing, we estimate word boundaries
        based on text length ratios and adjust accordingly.
        
        Args:
            ref_audio_path: Path to reference (TTS) audio file
            ref_text: The text that was spoken
            user_word_data: Word data from user segmentation (for alignment)
            session_id: Session identifier
            
        Returns:
            Dict with reference word audio paths paired with user words
        """
        if not LIBROSA_AVAILABLE:
            return {"success": False, "error": "librosa not available"}
        
        try:
            # Load reference audio
            ref_audio, sr = librosa.load(ref_audio_path, sr=self.target_sr, mono=True)
            ref_duration = len(ref_audio) / sr
            
            # Get words from reference text
            ref_words = ref_text.strip().split()
            
            print(f"[WordSegmentation] Reference: {ref_duration:.2f}s, {len(ref_words)} words")
            
            # Create session directory
            if session_id is None:
                session_id = uuid.uuid4().hex[:8]
            session_dir = self.output_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Estimate word boundaries based on character count
            # This is approximate but works reasonably for TTS
            total_chars = sum(len(w) for w in ref_words)
            char_duration = ref_duration / total_chars if total_chars > 0 else 0.1
            
            ref_word_data = []
            current_time = 0
            
            for idx, word in enumerate(ref_words):
                word_duration = max(0.1, len(word) * char_duration)
                start_time = current_time
                end_time = current_time + word_duration
                
                # Add padding
                padding_sec = self.padding_ms / 1000
                start_sample = max(0, int((start_time - padding_sec) * sr))
                end_sample = min(len(ref_audio), int((end_time + padding_sec) * sr))
                
                # Extract word audio
                word_audio = ref_audio[start_sample:end_sample]
                
                # Save word audio
                word_filename = f"ref_word_{idx:03d}_{self._sanitize_filename(word)}.wav"
                word_path = str(session_dir / word_filename)
                sf.write(word_path, word_audio, sr)
                
                ref_word_data.append({
                    "word": word,
                    "word_index": idx,
                    "audio_path": word_path,
                    "start_time": round(start_time, 3),
                    "end_time": round(end_time, 3),
                    "duration": round(word_duration, 3)
                })
                
                current_time = end_time
            
            # Pair with user words
            paired_words = self._pair_user_ref_words(user_word_data, ref_word_data)
            
            return {
                "success": True,
                "session_id": session_id,
                "ref_word_data": ref_word_data,
                "paired_words": paired_words
            }
            
        except Exception as e:
            print(f"[WordSegmentation] Reference segmentation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _pair_user_ref_words(self, user_words: List[Dict], 
                             ref_words: List[Dict]) -> List[Dict]:
        """
        Pair user word segments with reference word segments.
        Uses simple alignment based on word matching.
        
        Returns:
            List of dicts with user_audio_path, ref_audio_path, word
        """
        paired = []
        
        # Create lookup for reference words
        ref_lookup = {w['word'].lower(): w for w in ref_words}
        
        for user_word in user_words:
            user_word_text = user_word['word'].lower().strip('.,!?;:"\'-')
            
            # Try to find matching reference word
            ref_word = ref_lookup.get(user_word_text)
            
            paired.append({
                "word": user_word['word'],
                "word_index": user_word['word_index'],
                "user_audio_path": user_word['audio_path'],
                "ref_audio_path": ref_word['audio_path'] if ref_word else None,
                "user_start": user_word['start_time'],
                "user_end": user_word['end_time'],
                "ref_start": ref_word['start_time'] if ref_word else None,
                "ref_end": ref_word['end_time'] if ref_word else None,
                "has_match": ref_word is not None
            })
        
        return paired
    
    def create_comparison_audio(self, user_word_path: str, ref_word_path: str,
                                 output_path: str = None) -> str:
        """
        Create A/B comparison audio file: user -> silence -> reference
        
        Args:
            user_word_path: Path to user word audio
            ref_word_path: Path to reference word audio
            output_path: Optional output path
            
        Returns:
            Path to comparison audio file
        """
        if not PYDUB_AVAILABLE:
            return None
        
        try:
            # Load audio segments
            user_audio = AudioSegment.from_wav(user_word_path)
            ref_audio = AudioSegment.from_wav(ref_word_path)
            
            # Create 500ms silence
            silence = AudioSegment.silent(duration=500)
            
            # Concatenate: User -> Silence -> Reference
            comparison = user_audio + silence + ref_audio
            
            # Save
            if output_path is None:
                output_path = str(self.output_dir / f"comparison_{uuid.uuid4().hex[:8]}.wav")
            
            comparison.export(output_path, format="wav")
            
            return output_path
            
        except Exception as e:
            print(f"[WordSegmentation] Comparison creation error: {e}")
            return None
    
    def get_word_audio_features(self, word_audio_path: str) -> Dict:
        """
        Extract audio features from a word segment.
        
        Returns:
            Dict with duration, peak_db, rms_db, pitch_mean, pitch_std
        """
        if not LIBROSA_AVAILABLE:
            return {"error": "librosa not available"}
        
        try:
            audio, sr = librosa.load(word_audio_path, sr=self.target_sr)
            
            # Basic features
            duration = len(audio) / sr
            peak = np.max(np.abs(audio))
            rms = np.sqrt(np.mean(audio ** 2))
            
            peak_db = 20 * np.log10(peak) if peak > 0 else -100
            rms_db = 20 * np.log10(rms) if rms > 0 else -100
            
            # Pitch features
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            pitch_mean = np.mean(pitch_values) if pitch_values else 0
            pitch_std = np.std(pitch_values) if pitch_values else 0
            
            return {
                "duration": round(duration, 3),
                "peak_db": round(peak_db, 1),
                "rms_db": round(rms_db, 1),
                "pitch_mean": round(pitch_mean, 1),
                "pitch_std": round(pitch_std, 1),
                "sample_rate": sr
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _sanitize_filename(self, word: str) -> str:
        """Sanitize word for use in filename."""
        # Remove special characters, keep only alphanumeric
        sanitized = ''.join(c for c in word if c.isalnum())
        return sanitized[:20] if sanitized else "word"
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up word segment files for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if cleanup successful
        """
        try:
            session_dir = self.output_dir / session_id
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
                print(f"[WordSegmentation] Cleaned up session: {session_id}")
                return True
            return False
        except Exception as e:
            print(f"[WordSegmentation] Cleanup error: {e}")
            return False


# Singleton instance
word_segmentation_service = WordSegmentationService()
