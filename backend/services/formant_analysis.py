"""
Formant Analysis Service
Uses librosa for MFCC extraction and LPC for formant estimation.
Fully offline, no Rust dependencies.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np

# Try importing librosa
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# Try importing scipy for LPC
try:
    from scipy.signal import lfilter
    from scipy.linalg import solve_toeplitz
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class FormantAnalysisService:
    """Acoustic formant analysis using MFCC and LPC."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        print(f"FormantAnalysisService: librosa={LIBROSA_AVAILABLE}, scipy={SCIPY_AVAILABLE}")
    
    def load_audio(self, audio_path: str) -> Tuple[Optional[np.ndarray], int]:
        """Load audio file."""
        if not LIBROSA_AVAILABLE:
            return None, self.sample_rate
        
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            return y, sr
        except Exception as e:
            print(f"Audio load error: {e}")
            return None, self.sample_rate
    
    def extract_mfcc(self, audio: np.ndarray, sr: int, n_mfcc: int = 13) -> Dict:
        """
        Extract MFCC features.
        Returns mean, std, and full feature matrix.
        """
        if not LIBROSA_AVAILABLE or audio is None:
            return {'error': 'librosa not available'}
        
        try:
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)
            
            return {
                'mfcc_mean': mfcc.mean(axis=1).tolist(),
                'mfcc_std': mfcc.std(axis=1).tolist(),
                'mfcc_min': mfcc.min(axis=1).tolist(),
                'mfcc_max': mfcc.max(axis=1).tolist(),
                'n_frames': mfcc.shape[1],
                'n_mfcc': n_mfcc
            }
        except Exception as e:
            return {'error': str(e)}
    
    def extract_delta_mfcc(self, audio: np.ndarray, sr: int) -> Dict:
        """Extract MFCC with delta and delta-delta features."""
        if not LIBROSA_AVAILABLE or audio is None:
            return {'error': 'librosa not available'}
        
        try:
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            delta = librosa.feature.delta(mfcc)
            delta2 = librosa.feature.delta(mfcc, order=2)
            
            return {
                'mfcc': mfcc.mean(axis=1).tolist(),
                'delta': delta.mean(axis=1).tolist(),
                'delta2': delta2.mean(axis=1).tolist(),
                'n_frames': mfcc.shape[1]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def lpc_coefficients(self, audio: np.ndarray, order: int = 12) -> Optional[np.ndarray]:
        """
        Compute LPC coefficients using autocorrelation method.
        """
        if audio is None or len(audio) < order + 1:
            return None
        
        try:
            # Autocorrelation
            n = len(audio)
            r = np.correlate(audio, audio, mode='full')[n-1:n+order]
            
            # Levinson-Durbin recursion
            if r[0] == 0:
                return None
            
            # Solve Toeplitz system
            a = np.zeros(order)
            e = r[0]
            
            for i in range(order):
                # Reflection coefficient
                lambda_val = 0
                for j in range(i):
                    lambda_val += a[j] * r[i - j]
                lambda_val = (r[i + 1] - lambda_val) / e
                
                # Update coefficients
                a_new = np.zeros(order)
                a_new[i] = lambda_val
                for j in range(i):
                    a_new[j] = a[j] - lambda_val * a[i - 1 - j]
                a = a_new
                
                # Update error
                e = e * (1 - lambda_val ** 2)
            
            return a
            
        except Exception as e:
            print(f"LPC error: {e}")
            return None
    
    def estimate_formants(self, audio: np.ndarray, sr: int, 
                          n_formants: int = 4, order: int = 12) -> Dict:
        """
        Estimate formant frequencies from LPC coefficients.
        F1, F2, F3, F4 are key for vowel identification.
        """
        if audio is None:
            return {'error': 'no audio'}
        
        try:
            # Pre-emphasis
            pre_emphasis = 0.97
            audio_emph = np.append(audio[0], audio[1:] - pre_emphasis * audio[:-1])
            
            # Frame the audio (analyze middle portion)
            frame_length = min(len(audio_emph), int(0.025 * sr))  # 25ms
            center = len(audio_emph) // 2
            frame = audio_emph[center - frame_length//2 : center + frame_length//2]
            
            # Apply window
            frame = frame * np.hamming(len(frame))
            
            # Get LPC coefficients
            lpc = self.lpc_coefficients(frame, order)
            
            if lpc is None:
                return {'error': 'LPC failed'}
            
            # Find roots of LPC polynomial
            # A(z) = 1 - sum(a_k * z^-k)
            roots = np.roots(np.concatenate([[1], -lpc]))
            
            # Keep roots inside unit circle with positive imaginary part
            roots = roots[np.imag(roots) > 0]
            roots = roots[np.abs(roots) < 1]
            
            # Convert to frequencies
            angles = np.angle(roots)
            freqs = angles * sr / (2 * np.pi)
            
            # Sort by frequency and filter valid formants (200-5000 Hz)
            freqs = np.sort(freqs)
            formants = [f for f in freqs if 200 < f < 5000][:n_formants]
            
            # Pad if needed
            while len(formants) < n_formants:
                formants.append(0)
            
            return {
                'f1': round(formants[0], 1) if len(formants) > 0 else 0,
                'f2': round(formants[1], 1) if len(formants) > 1 else 0,
                'f3': round(formants[2], 1) if len(formants) > 2 else 0,
                'f4': round(formants[3], 1) if len(formants) > 3 else 0,
                'formants': [round(f, 1) for f in formants],
                'lpc_order': order
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze(self, audio_path: str) -> Dict:
        """
        Full formant analysis for an audio file.
        Returns MFCC, delta features, and formant estimates.
        """
        audio, sr = self.load_audio(audio_path)
        
        if audio is None:
            return {'error': 'Could not load audio'}
        
        mfcc = self.extract_mfcc(audio, sr)
        delta_mfcc = self.extract_delta_mfcc(audio, sr)
        formants = self.estimate_formants(audio, sr)
        
        # Additional spectral features
        spectral = {}
        if LIBROSA_AVAILABLE:
            try:
                spectral = {
                    'spectral_centroid': float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr))),
                    'spectral_bandwidth': float(np.mean(librosa.feature.spectral_bandwidth(y=audio, sr=sr))),
                    'spectral_rolloff': float(np.mean(librosa.feature.spectral_rolloff(y=audio, sr=sr))),
                    'zero_crossing_rate': float(np.mean(librosa.feature.zero_crossing_rate(audio)))
                }
            except:
                pass
        
        return {
            'mfcc': mfcc,
            'delta_mfcc': delta_mfcc,
            'formants': formants,
            'spectral': spectral,
            'duration': len(audio) / sr if audio is not None else 0,
            'sample_rate': sr
        }
    
    def compare_formants(self, user_audio: str, native_audio: str) -> Dict:
        """Compare formant patterns between user and native audio."""
        user = self.analyze(user_audio)
        native = self.analyze(native_audio)
        
        if 'error' in user or 'error' in native:
            return {'error': 'Analysis failed', 'user': user, 'native': native}
        
        # Compare formants
        user_f = user['formants']
        native_f = native['formants']
        
        similarities = {}
        for key in ['f1', 'f2', 'f3', 'f4']:
            u_val = user_f.get(key, 0)
            n_val = native_f.get(key, 0)
            if n_val > 0:
                diff_ratio = abs(u_val - n_val) / n_val
                similarities[key] = max(0, 100 - diff_ratio * 100)
            else:
                similarities[key] = 50
        
        overall = sum(similarities.values()) / len(similarities)
        
        return {
            'user_formants': user_f,
            'native_formants': native_f,
            'similarities': similarities,
            'overall_similarity': round(overall, 1)
        }


# Singleton
formant_analyzer = FormantAnalysisService()
