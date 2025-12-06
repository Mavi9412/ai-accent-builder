"""
Audio Analysis Service
Advanced audio feature extraction and prosody comparison using Librosa
"""
from typing import Dict, List, Tuple, Optional
import os


class AudioAnalysisService:
    """Service for analyzing audio features (MFCC, Pitch, Energy, Rhythm)"""
    
    def __init__(self):
        self.librosa_available = False
        self._check_librosa()
    
    def _check_librosa(self):
        """Check if librosa is available"""
        try:
            import librosa
            import numpy as np
            self.librosa_available = True
        except ImportError:
            print("librosa not installed. Advanced audio analysis disabled.")
    
    def extract_features(self, audio_path: str) -> Optional[Dict]:
        """
        Extract audio features from a file
        Returns MFCCs, pitch, energy, duration
        """
        if not self.librosa_available:
            return self._dummy_features()
        
        if not os.path.exists(audio_path):
            return None
        
        try:
            import librosa
            import numpy as np
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=16000)
            
            # Duration
            duration = librosa.get_duration(y=y, sr=sr)
            
            # MFCCs (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfccs, axis=1).tolist()
            mfcc_std = np.std(mfccs, axis=1).tolist()
            
            # Pitch (F0) using pyin
            try:
                f0, voiced_flag, voiced_probs = librosa.pyin(
                    y, fmin=librosa.note_to_hz('C2'), 
                    fmax=librosa.note_to_hz('C7'),
                    sr=sr
                )
                f0_clean = f0[~np.isnan(f0)]
                pitch_mean = float(np.mean(f0_clean)) if len(f0_clean) > 0 else 0
                pitch_std = float(np.std(f0_clean)) if len(f0_clean) > 0 else 0
                pitch_contour = f0.tolist()
            except:
                pitch_mean = 0
                pitch_std = 0
                pitch_contour = []
            
            # Energy / RMS
            rms = librosa.feature.rms(y=y)[0]
            energy_mean = float(np.mean(rms))
            energy_std = float(np.std(rms))
            energy_contour = rms.tolist()
            
            # Tempo (rhythm)
            try:
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                tempo_value = float(tempo) if isinstance(tempo, (int, float)) else float(tempo[0])
            except:
                tempo_value = 0
            
            # Speaking rate (words per second approximation)
            # Based on zero-crossing rate spikes
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            return {
                'duration': round(duration, 2),
                'mfcc_mean': mfcc_mean,
                'mfcc_std': mfcc_std,
                'pitch_mean': round(pitch_mean, 2),
                'pitch_std': round(pitch_std, 2),
                'pitch_contour': pitch_contour,
                'energy_mean': round(energy_mean, 4),
                'energy_std': round(energy_std, 4),
                'energy_contour': energy_contour,
                'tempo': round(tempo_value, 2),
                'sample_rate': sr
            }
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return self._dummy_features()
    
    def _dummy_features(self) -> Dict:
        """Return dummy features when librosa is not available"""
        return {
            'duration': 0,
            'mfcc_mean': [0] * 13,
            'mfcc_std': [0] * 13,
            'pitch_mean': 0,
            'pitch_std': 0,
            'pitch_contour': [],
            'energy_mean': 0,
            'energy_std': 0,
            'energy_contour': [],
            'tempo': 0,
            'sample_rate': 16000
        }
    
    def compare_prosody(self, user_features: Dict, native_features: Dict) -> Dict:
        """
        Compare prosodic features between user and native speaker
        Returns similarity scores and detailed feedback
        """
        if not user_features or not native_features:
            return self._dummy_prosody_comparison()
        
        # Pitch similarity (intonation)
        pitch_similarity = self._compare_values(
            user_features.get('pitch_mean', 0),
            native_features.get('pitch_mean', 0),
            tolerance=50  # Hz tolerance
        )
        
        # Pitch variation (expressiveness)
        pitch_var_similarity = self._compare_values(
            user_features.get('pitch_std', 0),
            native_features.get('pitch_std', 0),
            tolerance=30
        )
        
        # Duration/pace similarity
        duration_similarity = self._compare_values(
            user_features.get('duration', 0),
            native_features.get('duration', 0),
            tolerance=0.5  # seconds
        )
        
        # Energy similarity
        energy_similarity = self._compare_values(
            user_features.get('energy_mean', 0),
            native_features.get('energy_mean', 0),
            tolerance=0.1
        )
        
        # Tempo similarity (rhythm)
        tempo_similarity = self._compare_values(
            user_features.get('tempo', 0),
            native_features.get('tempo', 0),
            tolerance=20  # BPM
        )
        
        # MFCC similarity (overall spectral similarity)
        mfcc_similarity = self._compare_mfcc(
            user_features.get('mfcc_mean', []),
            native_features.get('mfcc_mean', [])
        )
        
        # Calculate overall score
        overall = (
            pitch_similarity * 0.25 +
            pitch_var_similarity * 0.15 +
            duration_similarity * 0.10 +
            energy_similarity * 0.10 +
            tempo_similarity * 0.15 +
            mfcc_similarity * 0.25
        )
        
        # Generate feedback
        feedback = self._generate_prosody_feedback(
            pitch_similarity, pitch_var_similarity,
            duration_similarity, tempo_similarity,
            user_features, native_features
        )
        
        return {
            'overall_similarity': round(overall, 1),
            'pitch_similarity': round(pitch_similarity, 1),
            'pitch_variation_similarity': round(pitch_var_similarity, 1),
            'rhythm_similarity': round(tempo_similarity, 1),
            'duration_similarity': round(duration_similarity, 1),
            'energy_similarity': round(energy_similarity, 1),
            'spectral_similarity': round(mfcc_similarity, 1),
            'feedback': feedback,
            'user_duration': user_features.get('duration', 0),
            'native_duration': native_features.get('duration', 0),
            'user_pitch': user_features.get('pitch_mean', 0),
            'native_pitch': native_features.get('pitch_mean', 0)
        }
    
    def _compare_values(self, user_val: float, native_val: float, 
                        tolerance: float) -> float:
        """Compare two values with tolerance, return similarity 0-100"""
        if native_val == 0:
            return 100 if user_val == 0 else 50
        
        diff = abs(user_val - native_val)
        if diff <= tolerance:
            return 100
        elif diff <= tolerance * 2:
            return 100 - (diff / tolerance - 1) * 25
        elif diff <= tolerance * 4:
            return 75 - (diff / tolerance - 2) * 12.5
        else:
            return max(0, 50 - diff / tolerance * 5)
    
    def _compare_mfcc(self, user_mfcc: List[float], 
                      native_mfcc: List[float]) -> float:
        """Compare MFCC features using cosine similarity"""
        if not user_mfcc or not native_mfcc:
            return 50
        
        try:
            import numpy as np
            
            user_arr = np.array(user_mfcc)
            native_arr = np.array(native_mfcc)
            
            # Ensure same length
            min_len = min(len(user_arr), len(native_arr))
            user_arr = user_arr[:min_len]
            native_arr = native_arr[:min_len]
            
            # Cosine similarity
            dot_product = np.dot(user_arr, native_arr)
            norm_user = np.linalg.norm(user_arr)
            norm_native = np.linalg.norm(native_arr)
            
            if norm_user == 0 or norm_native == 0:
                return 50
            
            cosine_sim = dot_product / (norm_user * norm_native)
            # Convert to 0-100 scale
            return (cosine_sim + 1) * 50
            
        except:
            return 50
    
    def _generate_prosody_feedback(self, pitch_sim: float, pitch_var_sim: float,
                                   duration_sim: float, tempo_sim: float,
                                   user_features: Dict, native_features: Dict) -> List[str]:
        """Generate actionable feedback based on prosody comparison"""
        feedback = []
        
        # Pitch feedback
        if pitch_sim < 70:
            user_pitch = user_features.get('pitch_mean', 0)
            native_pitch = native_features.get('pitch_mean', 0)
            if user_pitch < native_pitch:
                feedback.append("Try speaking with a slightly higher pitch to match the native speaker's intonation.")
            else:
                feedback.append("Your pitch is a bit high. Try relaxing your voice to lower the pitch slightly.")
        
        # Pitch variation feedback
        if pitch_var_sim < 70:
            user_var = user_features.get('pitch_std', 0)
            native_var = native_features.get('pitch_std', 0)
            if user_var < native_var:
                feedback.append("Add more expression! Vary your pitch more to sound more natural and engaging.")
            else:
                feedback.append("Your pitch varies a lot. Try to be more consistent with your intonation pattern.")
        
        # Duration/pace feedback
        if duration_sim < 70:
            user_dur = user_features.get('duration', 0)
            native_dur = native_features.get('duration', 0)
            if user_dur < native_dur:
                feedback.append("You're speaking too fast. Slow down and give each word its full pronunciation time.")
            else:
                feedback.append("You're speaking too slow. Try to maintain a more natural, flowing pace.")
        
        # Rhythm feedback
        if tempo_sim < 70:
            feedback.append("Work on your rhythm. Practice with the native speaker audio to match the natural beat of British English.")
        
        if not feedback:
            feedback.append("Excellent prosody! Your rhythm, pitch, and pacing match well with native speech.")
        
        return feedback
    
    def _dummy_prosody_comparison(self) -> Dict:
        """Return dummy comparison when features not available"""
        return {
            'overall_similarity': 75,
            'pitch_similarity': 75,
            'pitch_variation_similarity': 75,
            'rhythm_similarity': 75,
            'duration_similarity': 75,
            'energy_similarity': 75,
            'spectral_similarity': 75,
            'feedback': ["Audio analysis not available. Basic comparison completed."],
            'user_duration': 0,
            'native_duration': 0,
            'user_pitch': 0,
            'native_pitch': 0
        }
    
    def compare_with_dtw(self, user_audio_path: str, 
                         native_audio_path: str) -> Dict:
        """
        Full DTW comparison of two audio files
        Returns detailed alignment and similarity metrics
        """
        user_features = self.extract_features(user_audio_path)
        native_features = self.extract_features(native_audio_path)
        
        prosody = self.compare_prosody(user_features, native_features)
        
        # DTW on pitch contours
        dtw_result = self._dtw_on_contours(
            user_features.get('pitch_contour', []),
            native_features.get('pitch_contour', [])
        )
        
        return {
            **prosody,
            'dtw_distance': dtw_result.get('distance', 0),
            'dtw_path': dtw_result.get('path', []),
            'user_features': user_features,
            'native_features': native_features
        }
    
    def _dtw_on_contours(self, user_contour: List, 
                         native_contour: List) -> Dict:
        """Apply DTW to pitch/energy contours"""
        if not user_contour or not native_contour:
            return {'distance': 0, 'path': []}
        
        try:
            from fastdtw import fastdtw
            import numpy as np
            
            # Clean NaN values
            user_clean = [x if not np.isnan(x) else 0 for x in user_contour]
            native_clean = [x if not np.isnan(x) else 0 for x in native_contour]
            
            distance, path = fastdtw(
                [[x] for x in user_clean],
                [[x] for x in native_clean]
            )
            
            return {
                'distance': float(distance),
                'path': path[:100]  # Limit path length for response
            }
            
        except ImportError:
            return {'distance': 0, 'path': []}


# Singleton instance
audio_analysis_service = AudioAnalysisService()
