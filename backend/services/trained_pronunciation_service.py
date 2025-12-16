"""
Trained Pronunciation Service
=============================
Loads and uses a trained pronunciation assessment model.

This service loads the model trained by train_pronunciation_model.py
and provides production-quality pronunciation scoring.
"""

import os
import numpy as np
from typing import Dict, Optional
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# Dependencies
TORCH_AVAILABLE = False
LIBROSA_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    pass

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    pass


# ============== MODEL DEFINITION ==============

class TrainedPronunciationScorer(nn.Module):
    """Trained pronunciation scorer model"""
    
    def __init__(self, input_size: int = 26, hidden_size: int = 128):
        super().__init__()
        
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size // 2, 5),
            nn.Sigmoid()
        )
    
    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


# ============== FEATURE EXTRACTION ==============

def extract_acoustic_features(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Extract 26 acoustic features"""
    if not LIBROSA_AVAILABLE or len(audio) == 0:
        return np.zeros(26)
    
    try:
        features = []
        
        # Normalize audio
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        
        # MFCCs (13)
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        features.extend(np.mean(mfccs, axis=1))
        
        # Pitch (2)
        f0, voiced, _ = librosa.pyin(audio, fmin=75, fmax=500, sr=sr)
        f0_clean = f0[~np.isnan(f0)] if f0 is not None and len(f0) > 0 else np.array([150])
        features.append(np.mean(f0_clean))
        features.append(np.std(f0_clean))
        
        # Energy (2)
        rms = librosa.feature.rms(y=audio)[0]
        features.append(np.mean(rms))
        features.append(np.std(rms))
        
        # ZCR (2)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        features.append(np.mean(zcr))
        features.append(np.std(zcr))
        
        # Spectral (4)
        sc = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        features.append(np.mean(sc))
        features.append(np.std(sc))
        features.append(np.mean(rolloff))
        features.append(np.std(rolloff))
        
        # Duration (1)
        features.append(len(audio) / sr)
        
        # Voiced ratio (1)
        voiced_ratio = np.sum(voiced) / len(voiced) if len(voiced) > 0 else 0.5
        features.append(voiced_ratio)
        
        # Silence ratio (1)
        silence = np.sum(rms < np.mean(rms) * 0.1) / len(rms)
        features.append(silence)
        
        return np.array(features, dtype=np.float32)
        
    except Exception as e:
        print(f"[TrainedScorer] Feature extraction error: {e}")
        return np.zeros(26)


# ============== TRAINED SERVICE ==============

class TrainedPronunciationService:
    """
    Production pronunciation assessment using trained model.
    
    Usage:
        from services.trained_pronunciation_service import trained_scorer
        
        scores = trained_scorer.score(audio_array)
        # Returns: {'accuracy': 0.85, 'fluency': 0.78, ...}
    """
    
    def __init__(self, model_path: Optional[str] = None, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.model = None
        self.feature_mean = None
        self.feature_std = None
        self.is_loaded = False
        
        # Default model path
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 'models', 'pronunciation_scorer.pt'
            )
        
        self.model_path = model_path
        self._load_model()
    
    def _load_model(self):
        """Load trained model from file"""
        if not TORCH_AVAILABLE:
            print("[TrainedScorer] PyTorch not available")
            return
        
        if not os.path.exists(self.model_path):
            print(f"[TrainedScorer] Model not found at {self.model_path}")
            print("[TrainedScorer] Using untrained model - train with train_pronunciation_model.py")
            self._init_untrained_model()
            return
        
        try:
            checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)
            
            input_size = checkpoint.get('input_size', 26)
            hidden_size = checkpoint.get('hidden_size', 128)
            
            self.model = TrainedPronunciationScorer(input_size, hidden_size)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            
            self.feature_mean = checkpoint.get('feature_mean')
            self.feature_std = checkpoint.get('feature_std')
            
            self.is_loaded = True
            print("[TrainedScorer] Trained model loaded successfully ✓")
            
        except Exception as e:
            print(f"[TrainedScorer] Error loading model: {e}")
            self._init_untrained_model()
    
    def _init_untrained_model(self):
        """Initialize untrained model as fallback"""
        if TORCH_AVAILABLE:
            self.model = TrainedPronunciationScorer(26, 128)
            self.model.eval()
            self.feature_mean = np.zeros(26)
            self.feature_std = np.ones(26)
            print("[TrainedScorer] Using untrained model (random initialization)")
    
    def score(self, audio: np.ndarray, sample_rate: int = None, use_hybrid: bool = True) -> Dict[str, float]:
        """
        Score pronunciation from audio using hybrid approach.
        
        Args:
            audio: Audio waveform (numpy array)
            sample_rate: Sample rate (default: 16000)
            use_hybrid: If True, combine trained model + heuristics (recommended)
            
        Returns:
            Dictionary with scores: accuracy, fluency, completeness, prosody, total
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        # Resample if needed
        if sample_rate != self.sample_rate:
            import librosa
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=self.sample_rate)
        
        # Extract features
        features = extract_acoustic_features(audio, self.sample_rate)
        features_raw = features.copy()  # Keep raw features for heuristics
        
        # Normalize features for model
        if self.feature_mean is not None and self.feature_std is not None:
            features = (features - self.feature_mean) / (self.feature_std + 1e-8)
        
        # Get trained model predictions
        if self.model is not None and TORCH_AVAILABLE and self.is_loaded:
            with torch.no_grad():
                feat_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
                model_scores = self.model(feat_tensor).numpy()[0]
        else:
            model_scores = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        
        # Get heuristic scores
        heuristic_scores = self._compute_heuristic_scores(features_raw, audio)
        
        # Combine with hybrid approach
        if use_hybrid and self.is_loaded:
            # Weighted ensemble: 60% trained, 40% heuristic for better generalization
            # Trained model is better for fluency/completeness/total
            # Heuristics are better for accuracy/prosody
            weights = {
                'accuracy': (0.4, 0.6),    # More heuristic weight
                'fluency': (0.7, 0.3),     # More trained weight
                'completeness': (0.7, 0.3),
                'prosody': (0.4, 0.6),     # More heuristic weight
                'total': (0.55, 0.45)
            }
            
            final_scores = []
            for i, key in enumerate(['accuracy', 'fluency', 'completeness', 'prosody', 'total']):
                w_trained, w_heuristic = weights[key]
                combined = w_trained * model_scores[i] + w_heuristic * heuristic_scores[i]
                final_scores.append(combined)
            
            scores = np.array(final_scores)
            method = 'hybrid'
        elif self.is_loaded:
            scores = model_scores
            method = 'trained_model'
        else:
            scores = heuristic_scores
            method = 'heuristic'
        
        return {
            'accuracy': float(scores[0]) * 100,
            'fluency': float(scores[1]) * 100,
            'completeness': float(scores[2]) * 100,
            'prosody': float(scores[3]) * 100,
            'total': float(scores[4]) * 100,
            'is_trained': self.is_loaded,
            'method': method
        }
    
    def _compute_heuristic_scores(self, features: np.ndarray, audio: np.ndarray) -> np.ndarray:
        """Compute heuristic-based scores from acoustic features"""
        import librosa
        
        # Normalize audio
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        
        # Basic features
        rms = librosa.feature.rms(y=audio)[0]
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        
        # Energy-based scores
        energy_score = min(1.0, max(0, np.mean(rms) * 5 + 0.5))
        activity_score = min(1.0, max(0, (1 - np.sum(rms < 0.01) / len(rms))))
        
        # Pitch-based
        try:
            f0, voiced, _ = librosa.pyin(audio, fmin=75, fmax=500, sr=16000)
            voiced_ratio = np.sum(voiced) / len(voiced) if len(voiced) > 0 else 0.5
            f0_clean = f0[~np.isnan(f0)] if f0 is not None else np.array([150])
            pitch_variation = np.std(f0_clean) / (np.mean(f0_clean) + 1e-8) if len(f0_clean) > 0 else 0.2
            pitch_score = min(1.0, max(0, voiced_ratio * 0.7 + min(pitch_variation, 0.3)))
        except:
            voiced_ratio = 0.5
            pitch_score = 0.5
        
        # Spectral stability (good pronunciation has stable spectral features)
        try:
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=16000)[0]
            spectral_stability = 1.0 - min(1.0, np.std(spectral_centroid) / (np.mean(spectral_centroid) + 1e-8))
        except:
            spectral_stability = 0.5
        
        # Calculate scores
        accuracy = (energy_score * 0.3 + activity_score * 0.3 + spectral_stability * 0.4)
        fluency = (activity_score * 0.5 + pitch_score * 0.3 + (1 - np.mean(zcr) * 10) * 0.2)
        fluency = max(0, min(1, fluency))
        completeness = activity_score * 0.8 + energy_score * 0.2
        prosody = (pitch_score * 0.5 + energy_score * 0.3 + spectral_stability * 0.2)
        total = (accuracy + fluency + completeness + prosody) / 4
        
        return np.array([accuracy, fluency, completeness, prosody, total])
    
    def _heuristic_scoring(self, features: np.ndarray) -> np.ndarray:
        """Fallback heuristic scoring if model not loaded"""
        # Unnormalize if needed
        if self.feature_mean is not None:
            features = features * self.feature_std + self.feature_mean
        
        voiced_ratio = max(0, min(1, features[25]))
        silence_ratio = max(0, min(1, features[26] if len(features) > 26 else 0.2))
        energy = max(0, features[16])
        
        accuracy = 0.5 + voiced_ratio * 0.3 + (1 - silence_ratio) * 0.2
        fluency = 0.5 + voiced_ratio * 0.25 + (1 - silence_ratio) * 0.25
        completeness = 0.6 + (1 - silence_ratio) * 0.3
        prosody = 0.5 + min(1, abs(features[14]) / 50) * 0.3  # F0 variation
        total = (accuracy + fluency + completeness + prosody) / 4
        
        return np.array([accuracy, fluency, completeness, prosody, total])
    
    def analyze(self, audio: np.ndarray, target_text: str = "",
                sample_rate: int = None) -> Dict:
        """
        Full pronunciation analysis.
        
        For compatibility with ml_pronunciation_service interface.
        """
        scores = self.score(audio, sample_rate)
        
        return {
            'method': scores['method'],
            'is_trained': scores['is_trained'],
            'overall_score': scores['total'],
            'score': scores['total'],
            'prosody_scores': {
                'fluency': scores['fluency'],
                'pronunciation': scores['accuracy'],
                'completeness': scores['completeness'],
                'prosody': scores['prosody'],
                'overall': scores['total']
            }
        }


# ============== SINGLETON INSTANCE ==============

trained_scorer = TrainedPronunciationService()


# ============== TESTING ==============

if __name__ == "__main__":
    print("Testing Trained Pronunciation Service...")
    
    # Create test audio
    sr = 16000
    t = np.linspace(0, 2.0, sr * 2)
    test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Test scoring
    scores = trained_scorer.score(test_audio)
    
    print(f"\nScores (is_trained={scores['is_trained']}):")
    print(f"  Accuracy:     {scores['accuracy']:.1f}%")
    print(f"  Fluency:      {scores['fluency']:.1f}%")
    print(f"  Completeness: {scores['completeness']:.1f}%")
    print(f"  Prosody:      {scores['prosody']:.1f}%")
    print(f"  Total:        {scores['total']:.1f}%")
