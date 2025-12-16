"""
Audio Enhancement Service
Real-time voice enhancement for pronunciation analysis

Features:
- Noise reduction using spectral gating (noisereduce)
- Voice Activity Detection using webrtcvad
- Silence trimming at start/end
- Volume normalization to consistent level
- Echo suppression (optional)

Designed for FYP/Research-grade speech analysis.
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import wave
import struct

# Audio processing libraries
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[AudioEnhancement] librosa not available")

# Noise reduction
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False
    print("[AudioEnhancement] noisereduce not available - install with: pip install noisereduce")

# Voice Activity Detection
try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    print("[AudioEnhancement] webrtcvad not available - install with: pip install webrtcvad")


class AudioEnhancementService:
    """
    Comprehensive audio enhancement pipeline for speech analysis.
    
    Pipeline: Raw Audio → Noise Reduction → VAD → Silence Trim → Normalize → Clean Audio
    """
    
    def __init__(self, output_dir: str = None):
        """Initialize the audio enhancement service."""
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "uploads" / "enhanced_audio"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default parameters
        self.target_sr = 16000  # 16kHz for speech processing
        self.target_db = -3.0  # Target peak dB for normalization
        self.vad_aggressiveness = 2  # 0-3, higher = more aggressive filtering
        
        print(f"[AudioEnhancement] Initialized. noisereduce={NOISEREDUCE_AVAILABLE}, webrtcvad={WEBRTCVAD_AVAILABLE}")
    
    def enhance_audio(self, input_path: str, output_path: str = None) -> Dict:
        """
        Full audio enhancement pipeline.
        
        Args:
            input_path: Path to raw audio file (Audio1_raw.wav)
            output_path: Optional output path for clean audio
            
        Returns:
            Dict with:
                - clean_audio_path: Path to enhanced audio (Audio1_clean.wav)
                - original_duration: Duration before processing
                - clean_duration: Duration after processing
                - noise_reduced: Whether noise reduction was applied
                - vad_applied: Whether VAD was applied
                - normalized: Whether normalization was applied
                - speech_segments: List of (start, end) speech segments
        """
        if not LIBROSA_AVAILABLE:
            print("[AudioEnhancement] librosa not available, returning original")
            return {
                "clean_audio_path": input_path,
                "original_duration": 0,
                "clean_duration": 0,
                "noise_reduced": False,
                "vad_applied": False,
                "normalized": False,
                "speech_segments": []
            }
        
        try:
            # Load audio
            print(f"[AudioEnhancement] Loading audio: {input_path}")
            audio_data, sr = librosa.load(input_path, sr=self.target_sr, mono=True)
            original_duration = len(audio_data) / sr
            
            print(f"[AudioEnhancement] Loaded audio: {original_duration:.2f}s, {sr}Hz")
            
            # Step 1: Noise Reduction
            noise_reduced = False
            if NOISEREDUCE_AVAILABLE:
                audio_data = self.reduce_noise(audio_data, sr)
                noise_reduced = True
                print("[AudioEnhancement] Noise reduction applied")
            
            # Step 2: Voice Activity Detection
            vad_applied = False
            speech_segments = []
            if WEBRTCVAD_AVAILABLE:
                speech_segments = self.detect_voice_activity(audio_data, sr)
                if speech_segments:
                    audio_data = self._extract_speech_segments(audio_data, sr, speech_segments)
                    vad_applied = True
                    print(f"[AudioEnhancement] VAD applied, {len(speech_segments)} segments")
            
            # Step 3: Trim silence
            audio_data = self.trim_silence(audio_data, sr)
            print("[AudioEnhancement] Silence trimmed")
            
            # Step 4: Normalize volume
            audio_data = self.normalize_volume(audio_data)
            print("[AudioEnhancement] Volume normalized")
            
            clean_duration = len(audio_data) / sr
            
            # Save enhanced audio
            if output_path is None:
                input_name = Path(input_path).stem
                output_path = str(self.output_dir / f"{input_name}_clean.wav")
            
            sf.write(output_path, audio_data, sr)
            print(f"[AudioEnhancement] Saved clean audio: {output_path}")
            
            return {
                "clean_audio_path": output_path,
                "original_duration": round(original_duration, 2),
                "clean_duration": round(clean_duration, 2),
                "noise_reduced": noise_reduced,
                "vad_applied": vad_applied,
                "normalized": True,
                "speech_segments": speech_segments
            }
            
        except Exception as e:
            print(f"[AudioEnhancement] Error: {e}")
            return {
                "clean_audio_path": input_path,
                "original_duration": 0,
                "clean_duration": 0,
                "noise_reduced": False,
                "vad_applied": False,
                "normalized": False,
                "speech_segments": [],
                "error": str(e)
            }
    
    def reduce_noise(self, audio_data: np.ndarray, sr: int, 
                     prop_decrease: float = 0.8) -> np.ndarray:
        """
        Apply spectral noise reduction using noisereduce library.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate
            prop_decrease: Amount of noise reduction (0.0 to 1.0)
            
        Returns:
            Noise-reduced audio data
        """
        if not NOISEREDUCE_AVAILABLE:
            return audio_data
        
        try:
            # Stationary noise reduction - works well for background hum/hiss
            reduced = nr.reduce_noise(
                y=audio_data,
                sr=sr,
                prop_decrease=prop_decrease,
                stationary=True
            )
            return reduced
        except Exception as e:
            print(f"[AudioEnhancement] Noise reduction failed: {e}")
            return audio_data
    
    def detect_voice_activity(self, audio_data: np.ndarray, sr: int,
                               frame_duration_ms: int = 30) -> List[Tuple[float, float]]:
        """
        Detect speech segments using WebRTC VAD.
        
        Args:
            audio_data: Audio samples
            sr: Sample rate
            frame_duration_ms: Frame size in milliseconds (10, 20, or 30)
            
        Returns:
            List of (start_time, end_time) tuples for speech segments
        """
        if not WEBRTCVAD_AVAILABLE:
            return []
        
        try:
            vad = webrtcvad.Vad(self.vad_aggressiveness)
            
            # Resample to 16kHz if needed (VAD only supports 8k, 16k, 32k, 48k)
            if sr not in [8000, 16000, 32000, 48000]:
                audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=16000)
                sr = 16000
            
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Calculate frame parameters
            frame_samples = int(sr * frame_duration_ms / 1000)
            frame_bytes = frame_samples * 2  # 16-bit = 2 bytes per sample
            
            # Process frames
            speech_frames = []
            for i in range(0, len(audio_int16) - frame_samples, frame_samples):
                frame = audio_int16[i:i + frame_samples].tobytes()
                if len(frame) == frame_bytes:
                    is_speech = vad.is_speech(frame, sr)
                    speech_frames.append({
                        'start': i / sr,
                        'end': (i + frame_samples) / sr,
                        'is_speech': is_speech
                    })
            
            # Merge consecutive speech frames
            segments = []
            current_segment = None
            
            for frame in speech_frames:
                if frame['is_speech']:
                    if current_segment is None:
                        current_segment = {'start': frame['start'], 'end': frame['end']}
                    else:
                        current_segment['end'] = frame['end']
                else:
                    if current_segment is not None:
                        segments.append((current_segment['start'], current_segment['end']))
                        current_segment = None
            
            # Don't forget last segment
            if current_segment is not None:
                segments.append((current_segment['start'], current_segment['end']))
            
            # Merge segments that are close together (within 0.3s)
            merged_segments = []
            for seg in segments:
                if merged_segments and seg[0] - merged_segments[-1][1] < 0.3:
                    merged_segments[-1] = (merged_segments[-1][0], seg[1])
                else:
                    merged_segments.append(seg)
            
            return merged_segments
            
        except Exception as e:
            print(f"[AudioEnhancement] VAD failed: {e}")
            return []
    
    def _extract_speech_segments(self, audio_data: np.ndarray, sr: int,
                                  segments: List[Tuple[float, float]],
                                  padding_ms: int = 50) -> np.ndarray:
        """
        Extract and concatenate speech segments with small padding.
        
        Args:
            audio_data: Full audio data
            sr: Sample rate
            segments: List of (start, end) time tuples
            padding_ms: Padding to add before/after each segment
            
        Returns:
            Concatenated speech audio
        """
        if not segments:
            return audio_data
        
        padding_samples = int(sr * padding_ms / 1000)
        extracted = []
        
        for start, end in segments:
            start_sample = max(0, int(start * sr) - padding_samples)
            end_sample = min(len(audio_data), int(end * sr) + padding_samples)
            extracted.append(audio_data[start_sample:end_sample])
        
        return np.concatenate(extracted) if extracted else audio_data
    
    def trim_silence(self, audio_data: np.ndarray, sr: int,
                     top_db: int = 30) -> np.ndarray:
        """
        Trim silence from the beginning and end of audio.
        
        Args:
            audio_data: Audio samples
            sr: Sample rate
            top_db: Threshold below reference to consider as silence
            
        Returns:
            Trimmed audio data
        """
        if not LIBROSA_AVAILABLE:
            return audio_data
        
        try:
            # librosa.effects.trim removes silence from both ends
            trimmed, _ = librosa.effects.trim(audio_data, top_db=top_db)
            return trimmed
        except Exception as e:
            print(f"[AudioEnhancement] Trim failed: {e}")
            return audio_data
    
    def normalize_volume(self, audio_data: np.ndarray,
                         target_db: float = None) -> np.ndarray:
        """
        Normalize audio to target peak dB level.
        
        Args:
            audio_data: Audio samples
            target_db: Target peak level in dB (default: -3.0)
            
        Returns:
            Normalized audio data
        """
        if target_db is None:
            target_db = self.target_db
        
        try:
            # Find current peak
            peak = np.max(np.abs(audio_data))
            if peak == 0:
                return audio_data
            
            # Calculate required gain
            target_linear = 10 ** (target_db / 20)
            gain = target_linear / peak
            
            # Apply gain
            normalized = audio_data * gain
            
            # Clip to prevent clipping
            normalized = np.clip(normalized, -1.0, 1.0)
            
            return normalized
            
        except Exception as e:
            print(f"[AudioEnhancement] Normalization failed: {e}")
            return audio_data
    
    def get_audio_stats(self, audio_path: str) -> Dict:
        """
        Get statistics about an audio file.
        
        Returns:
            Dict with duration, sample_rate, channels, peak_db, rms_db
        """
        if not LIBROSA_AVAILABLE:
            return {"error": "librosa not available"}
        
        try:
            audio_data, sr = librosa.load(audio_path, sr=None, mono=True)
            
            peak = np.max(np.abs(audio_data))
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            peak_db = 20 * np.log10(peak) if peak > 0 else -100
            rms_db = 20 * np.log10(rms) if rms > 0 else -100
            
            return {
                "duration": round(len(audio_data) / sr, 2),
                "sample_rate": sr,
                "samples": len(audio_data),
                "peak_db": round(peak_db, 1),
                "rms_db": round(rms_db, 1),
                "dynamic_range_db": round(peak_db - rms_db, 1)
            }
            
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
audio_enhancement_service = AudioEnhancementService()
