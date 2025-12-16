"""
Production Pronunciation Model Training Script
=============================================
Trains a pronunciation assessment model using SpeechOcean762 dataset.

SpeechOcean762 Dataset:
- 5,000 English utterances from non-native speakers
- Labels: accuracy, fluency, completeness, prosody, total (1-10 scale)
- Download from: https://www.openslr.org/101/

Usage:
    python train_pronunciation_model.py --data_dir ./speechocean762

The trained model will be saved to: models/pronunciation_scorer.pt
"""

import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings("ignore")

# Check dependencies
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    print("ERROR: PyTorch required. Install with: pip install torch")
    TORCH_AVAILABLE = False

try:
    from transformers import Wav2Vec2Model, Wav2Vec2Processor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("ERROR: Transformers required. Install with: pip install transformers")
    TRANSFORMERS_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    print("ERROR: Librosa required. Install with: pip install librosa")
    LIBROSA_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(x, **kwargs): return x


# ============== DATA STRUCTURES ==============

@dataclass
class PronunciationSample:
    """Single pronunciation sample with labels"""
    audio_path: str
    text: str
    accuracy: float      # 1-10
    fluency: float       # 1-10
    completeness: float  # 1-10
    prosody: float       # 1-10
    total: float         # 1-10


# ============== DATASET ==============

class SpeechOcean762Dataset(Dataset):
    """
    SpeechOcean762 Dataset Loader
    
    Expected structure:
    speechocean762/
    ├── WAVE/
    │   ├── SPEAKER0001/
    │   │   ├── 000001.wav
    │   │   └── ...
    │   └── ...
    ├── train/
    │   └── manifest.json
    └── test/
        └── manifest.json
    """
    
    def __init__(self, data_dir: str, split: str = "train", 
                 sample_rate: int = 16000, max_duration: float = 10.0):
        self.data_dir = Path(data_dir)
        self.split = split
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        self.samples = []
        
        self._load_manifest()
    
    def _load_manifest(self):
        """Load dataset from SpeechOcean762 format"""
        # SpeechOcean762 format:
        # - train/wav.scp: utterance_id path_to_wav
        # - resource/scores.json: {utterance_id: {accuracy, fluency, completeness, prosodic}}
        
        wav_scp_path = self.data_dir / self.split / "wav.scp"
        scores_path = self.data_dir / "resource" / "scores.json"
        
        if not wav_scp_path.exists():
            print(f"WARNING: wav.scp not found at {wav_scp_path}")
            self._create_manifest_from_structure()
            return
        
        if not scores_path.exists():
            print(f"WARNING: scores.json not found at {scores_path}")
            self._create_manifest_from_structure()
            return
        
        # Load scores
        print(f"Loading scores from {scores_path}...")
        with open(scores_path, 'r', encoding='utf-8') as f:
            scores_data = json.load(f)
        
        # Load wav.scp
        print(f"Loading audio paths from {wav_scp_path}...")
        with open(wav_scp_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    utt_id = parts[0]
                    wav_path = ' '.join(parts[1:])  # Handle paths with spaces
                    
                    # Make path absolute
                    if not os.path.isabs(wav_path):
                        wav_path = str(self.data_dir / wav_path)
                    
                    if not os.path.exists(wav_path):
                        continue
                    
                    # Get scores for this utterance
                    if utt_id in scores_data:
                        score = scores_data[utt_id]
                        # Calculate total from word-level scores if not present
                        total = score.get('total', 
                            (score.get('accuracy', 5) + score.get('fluency', 5) + 
                             score.get('completeness', 5) + score.get('prosodic', 5)) / 4
                        )
                        
                        self.samples.append(PronunciationSample(
                            audio_path=wav_path,
                            text="",
                            accuracy=float(score.get('accuracy', 5)) / 10,  # Normalize 0-1
                            fluency=float(score.get('fluency', 5)) / 10,
                            completeness=float(score.get('completeness', 10)) / 10,
                            prosody=float(score.get('prosodic', 5)) / 10,  # Note: 'prosodic' in data
                            total=float(total) / 10
                        ))
        
        print(f"Loaded {len(self.samples)} samples for {self.split}")
        
        # Print sample distribution
        if len(self.samples) > 0:
            acc_scores = [s.accuracy for s in self.samples]
            print(f"  Accuracy range: {min(acc_scores)*10:.1f} - {max(acc_scores)*10:.1f}")
    
    def _create_manifest_from_structure(self):
        """Fallback: Create manifest by scanning directory structure"""
        wave_dir = self.data_dir / "WAVE"
        if not wave_dir.exists():
            wave_dir = self.data_dir
        
        for wav_file in wave_dir.rglob("*.wav"):
            self.samples.append(PronunciationSample(
                audio_path=str(wav_file),
                text="",
                accuracy=0.5,
                fluency=0.5,
                completeness=0.5,
                prosody=0.5,
                total=0.5
            ))
        
        print(f"Found {len(self.samples)} audio files (no labels)")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load audio
        try:
            audio, sr = librosa.load(sample.audio_path, sr=self.sample_rate, 
                                      duration=self.max_duration)
        except Exception as e:
            print(f"Error loading {sample.audio_path}: {e}")
            audio = np.zeros(int(self.sample_rate * 1.0))
        
        # Pad/trim to fixed length
        target_len = int(self.sample_rate * self.max_duration)
        if len(audio) < target_len:
            audio = np.pad(audio, (0, target_len - len(audio)))
        else:
            audio = audio[:target_len]
        
        # Create label tensor
        labels = np.array([
            sample.accuracy,
            sample.fluency,
            sample.completeness,
            sample.prosody,
            sample.total
        ], dtype=np.float32)
        
        return {
            'audio': torch.tensor(audio, dtype=torch.float32),
            'labels': torch.tensor(labels, dtype=torch.float32),
            'text': sample.text
        }


# ============== MODEL ==============

class PronunciationScorer(nn.Module):
    """
    Neural network for pronunciation scoring.
    
    Architecture:
    Wav2Vec2 features → Linear layers → 5 scores
    
    Predicts: accuracy, fluency, completeness, prosody, total
    """
    
    def __init__(self, wav2vec2_model: str = "facebook/wav2vec2-base-960h",
                 hidden_size: int = 256, dropout: float = 0.2):
        super().__init__()
        
        # Feature extractor (frozen)
        self.wav2vec2 = Wav2Vec2Model.from_pretrained(wav2vec2_model)
        self.wav2vec2.freeze_feature_extractor()
        
        # Get output dimension
        wav2vec_dim = self.wav2vec2.config.hidden_size  # Usually 768
        
        # Scorer network
        self.scorer = nn.Sequential(
            nn.Linear(wav2vec_dim, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, 5),  # 5 scores
            nn.Sigmoid()  # Output 0-1
        )
        
        # Attention pooling
        self.attention = nn.Linear(wav2vec_dim, 1)
    
    def forward(self, audio: torch.Tensor) -> torch.Tensor:
        """
        Args:
            audio: (batch, time) raw audio waveform
            
        Returns:
            scores: (batch, 5) pronunciation scores
        """
        # Extract Wav2Vec2 features
        with torch.no_grad():
            outputs = self.wav2vec2(audio)
            hidden_states = outputs.last_hidden_state  # (batch, seq, dim)
        
        # Attention pooling over sequence
        attn_weights = torch.softmax(self.attention(hidden_states), dim=1)
        pooled = torch.sum(hidden_states * attn_weights, dim=1)  # (batch, dim)
        
        # Score prediction
        scores = self.scorer(pooled)
        
        return scores


class LightweightPronunciationScorer(nn.Module):
    """
    Lightweight scorer using acoustic features instead of Wav2Vec2.
    Faster training, suitable for limited compute.
    """
    
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


# ============== FEATURE EXTRACTOR ==============

def extract_acoustic_features(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Extract 26 acoustic features for lightweight model"""
    if not LIBROSA_AVAILABLE or len(audio) == 0:
        return np.zeros(26)
    
    try:
        features = []
        
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
        print(f"Feature extraction error: {e}")
        return np.zeros(26)


# ============== TRAINING ==============

def train_lightweight_model(data_dir: str, output_dir: str, 
                           epochs: int = 50, batch_size: int = 32,
                           learning_rate: float = 0.001):
    """
    Train lightweight pronunciation scorer on acoustic features.
    Faster alternative to Wav2Vec2-based training.
    """
    print("=" * 60)
    print("LIGHTWEIGHT PRONUNCIATION SCORER TRAINING")
    print("=" * 60)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    print("\nLoading dataset...")
    train_dataset = SpeechOcean762Dataset(data_dir, split="train")
    
    if len(train_dataset) == 0:
        print("ERROR: No training samples found!")
        return None
    
    # Extract features for all samples
    print("Extracting acoustic features...")
    all_features = []
    all_labels = []
    
    for i in tqdm(range(len(train_dataset)), desc="Extracting"):
        sample = train_dataset[i]
        audio = sample['audio'].numpy()
        features = extract_acoustic_features(audio, train_dataset.sample_rate)
        all_features.append(features)
        all_labels.append(sample['labels'].numpy())
    
    X = np.array(all_features)
    y = np.array(all_labels)
    
    # Replace NaN and Inf values with 0
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.5, posinf=1.0, neginf=0.0)
    
    print(f"Features shape: {X.shape}, Labels shape: {y.shape}")
    print(f"Features NaN count: {np.isnan(X).sum()}, Labels NaN count: {np.isnan(y).sum()}")
    
    # Normalize features
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-8
    X = (X - X_mean) / X_std
    
    # Train/val split
    n_train = int(len(X) * 0.8)
    indices = np.random.permutation(len(X))
    train_idx, val_idx = indices[:n_train], indices[n_train:]
    
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    
    # Convert to tensors
    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32)
    X_val = torch.tensor(X_val, dtype=torch.float32)
    y_val = torch.tensor(y_val, dtype=torch.float32)
    
    # Create model
    model = LightweightPronunciationScorer(input_size=26, hidden_size=128)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)
    
    # Training loop
    print(f"\nTraining for {epochs} epochs...")
    best_val_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        
        # Mini-batch training
        perm = torch.randperm(len(X_train))
        total_loss = 0
        n_batches = 0
        
        for i in range(0, len(X_train), batch_size):
            batch_idx = perm[i:i+batch_size]
            batch_X = X_train[batch_idx]
            batch_y = y_train[batch_idx]
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
        
        avg_train_loss = total_loss / n_batches
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val)
            val_loss = criterion(val_outputs, y_val).item()
        
        scheduler.step(val_loss)
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}, Val Loss: {val_loss:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'model_state_dict': model.state_dict(),
                'feature_mean': X_mean,
                'feature_std': X_std,
                'input_size': 26,
                'hidden_size': 128
            }, output_path / 'pronunciation_scorer.pt')
    
    print(f"\nTraining complete! Best validation loss: {best_val_loss:.4f}")
    print(f"Model saved to: {output_path / 'pronunciation_scorer.pt'}")
    
    # Evaluate on validation set
    model.eval()
    with torch.no_grad():
        val_preds = model(X_val).numpy()
    
    # Calculate Pearson correlation
    from scipy.stats import pearsonr
    score_names = ['accuracy', 'fluency', 'completeness', 'prosody', 'total']
    print("\nPearson Correlation with human ratings:")
    for i, name in enumerate(score_names):
        corr, _ = pearsonr(val_preds[:, i], y_val[:, i].numpy())
        print(f"  {name}: {corr:.3f}")
    
    return model


def train_wav2vec2_model(data_dir: str, output_dir: str,
                         epochs: int = 20, batch_size: int = 8,
                         learning_rate: float = 1e-4):
    """
    Train Wav2Vec2-based pronunciation scorer.
    Requires GPU and more compute.
    """
    if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
        print("ERROR: PyTorch and Transformers required for Wav2Vec2 training")
        return None
    
    print("=" * 60)
    print("WAV2VEC2 PRONUNCIATION SCORER TRAINING")
    print("=" * 60)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    print("\nLoading dataset...")
    train_dataset = SpeechOcean762Dataset(data_dir, split="train", max_duration=5.0)
    
    if len(train_dataset) == 0:
        print("ERROR: No training samples found!")
        return None
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Create model
    print("\nLoading Wav2Vec2 model...")
    model = PronunciationScorer()
    model.to(device)
    
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.scorer.parameters(), lr=learning_rate)
    
    # Training loop
    print(f"\nTraining for {epochs} epochs...")
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for batch in tqdm(train_loader, desc=f"Epoch {epoch+1}"):
            audio = batch['audio'].to(device)
            labels = batch['labels'].to(device)
            
            optimizer.zero_grad()
            outputs = model(audio)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        avg_loss = total_loss / len(train_loader)
        print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")
        
        # Save checkpoint
        torch.save({
            'model_state_dict': model.state_dict(),
            'epoch': epoch
        }, output_path / 'pronunciation_scorer_wav2vec2.pt')
    
    print(f"\nTraining complete!")
    print(f"Model saved to: {output_path / 'pronunciation_scorer_wav2vec2.pt'}")
    
    return model


# ============== MAIN ==============

def main():
    parser = argparse.ArgumentParser(description="Train pronunciation assessment model")
    parser.add_argument('--data_dir', type=str, required=True,
                       help="Path to SpeechOcean762 dataset")
    parser.add_argument('--output_dir', type=str, default='./models',
                       help="Output directory for trained model")
    parser.add_argument('--model', type=str, default='lightweight',
                       choices=['lightweight', 'wav2vec2'],
                       help="Model type to train")
    parser.add_argument('--epochs', type=int, default=50,
                       help="Number of training epochs")
    parser.add_argument('--batch_size', type=int, default=32,
                       help="Batch size")
    parser.add_argument('--lr', type=float, default=0.001,
                       help="Learning rate")
    
    args = parser.parse_args()
    
    if args.model == 'lightweight':
        train_lightweight_model(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr
        )
    else:
        train_wav2vec2_model(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr
        )


if __name__ == "__main__":
    main()
