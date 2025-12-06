"""
Audio utility functions
"""
import wave
import os
from typing import Optional, Tuple


def get_audio_duration(filepath: str) -> float:
    """Get duration of audio file in seconds"""
    try:
        with wave.open(filepath, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except Exception:
        return 0.0


def convert_audio_format(input_path: str, output_path: str = None,
                         sample_rate: int = 16000, 
                         channels: int = 1) -> str:
    """
    Convert audio to specified format using pydub
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output file (default: same as input with _converted suffix)
        sample_rate: Target sample rate (default: 16000 for Vosk)
        channels: Number of channels (default: 1 for mono)
        
    Returns:
        Path to converted file
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_converted.wav"
    
    try:
        from pydub import AudioSegment
        
        # Load audio
        audio = AudioSegment.from_file(input_path)
        
        # Convert
        audio = audio.set_frame_rate(sample_rate)
        audio = audio.set_channels(channels)
        audio = audio.set_sample_width(2)  # 16-bit
        
        # Export
        audio.export(output_path, format="wav")
        
        return output_path
    except ImportError:
        print("pydub not installed. Audio conversion not available.")
        return input_path
    except Exception as e:
        print(f"Error converting audio: {e}")
        return input_path


def normalize_audio(filepath: str, target_dBFS: float = -20.0) -> str:
    """Normalize audio volume to target dBFS"""
    try:
        from pydub import AudioSegment
        
        audio = AudioSegment.from_file(filepath)
        change_in_dBFS = target_dBFS - audio.dBFS
        normalized_audio = audio.apply_gain(change_in_dBFS)
        
        # Overwrite original
        normalized_audio.export(filepath, format="wav")
        return filepath
    except Exception:
        return filepath


def trim_silence(filepath: str, silence_thresh: int = -50, 
                 min_silence_len: int = 500) -> str:
    """Remove silence from beginning and end of audio"""
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        
        audio = AudioSegment.from_file(filepath)
        
        # Detect non-silent chunks
        nonsilent_ranges = detect_nonsilent(
            audio, 
            min_silence_len=min_silence_len, 
            silence_thresh=silence_thresh
        )
        
        if nonsilent_ranges:
            start = nonsilent_ranges[0][0]
            end = nonsilent_ranges[-1][1]
            trimmed_audio = audio[start:end]
            trimmed_audio.export(filepath, format="wav")
        
        return filepath
    except Exception:
        return filepath


def split_audio_by_words(filepath: str, word_timestamps: list) -> list:
    """
    Split audio file into word-level segments
    
    Args:
        filepath: Path to audio file
        word_timestamps: List of dicts with 'start' and 'end' times
        
    Returns:
        List of audio segment paths
    """
    try:
        from pydub import AudioSegment
        
        audio = AudioSegment.from_file(filepath)
        segments = []
        
        base_dir = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        
        for i, word_info in enumerate(word_timestamps):
            start_ms = int(word_info["start"] * 1000)
            end_ms = int(word_info["end"] * 1000)
            
            segment = audio[start_ms:end_ms]
            segment_path = os.path.join(base_dir, f"{base_name}_word_{i}.wav")
            segment.export(segment_path, format="wav")
            
            segments.append({
                "word": word_info.get("word", ""),
                "path": segment_path,
                "start": word_info["start"],
                "end": word_info["end"]
            })
        
        return segments
    except Exception as e:
        print(f"Error splitting audio: {e}")
        return []
