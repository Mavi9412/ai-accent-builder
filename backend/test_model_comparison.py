"""
Model Comparison Test
=====================
Compares: Trained only, Heuristic only, and Hybrid approach
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("MODEL COMPARISON: Trained vs Heuristic vs HYBRID")
print("=" * 70)

# Load test samples from SpeechOcean762
data_dir = Path("data/speechocean762")
scores_path = data_dir / "resource" / "scores.json"
wav_scp_path = data_dir / "test" / "wav.scp"

print("\nLoading test dataset...")

with open(scores_path, 'r', encoding='utf-8') as f:
    scores_data = json.load(f)

test_samples = []
with open(wav_scp_path, 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 2:
            utt_id = parts[0]
            wav_path = ' '.join(parts[1:])
            if not os.path.isabs(wav_path):
                wav_path = str(data_dir / wav_path)
            if os.path.exists(wav_path) and utt_id in scores_data:
                test_samples.append({
                    'utt_id': utt_id,
                    'wav_path': wav_path,
                    'scores': scores_data[utt_id]
                })

print(f"Loaded {len(test_samples)} test samples")
test_samples = test_samples[:100]
print(f"Using {len(test_samples)} samples for comparison")

# Import models
print("\n" + "-" * 70)
print("Loading models...")
print("-" * 70)

import librosa
from services.trained_pronunciation_service import TrainedPronunciationService

trained_service = TrainedPronunciationService()
print(f"✓ Trained Model: loaded={trained_service.is_loaded}")

# Run comparison
print("\n" + "-" * 70)
print("Running comparison...")
print("-" * 70)

# Store predictions
trained_preds = {'accuracy': [], 'fluency': [], 'completeness': [], 'prosody': [], 'total': []}
hybrid_preds = {'accuracy': [], 'fluency': [], 'completeness': [], 'prosody': [], 'total': []}
ground_truth = {'accuracy': [], 'fluency': [], 'completeness': [], 'prosody': [], 'total': []}

for i, sample in enumerate(test_samples):
    if (i + 1) % 20 == 0:
        print(f"Processing {i+1}/{len(test_samples)}...")
    
    try:
        audio, sr = librosa.load(sample['wav_path'], sr=16000, duration=10.0)
    except:
        continue
    
    # Ground truth
    gt = sample['scores']
    ground_truth['accuracy'].append(float(gt.get('accuracy', 5)) * 10)
    ground_truth['fluency'].append(float(gt.get('fluency', 5)) * 10)
    ground_truth['completeness'].append(float(gt.get('completeness', 10)) * 10)
    ground_truth['prosody'].append(float(gt.get('prosodic', 5)) * 10)
    total_gt = (gt.get('accuracy', 5) + gt.get('fluency', 5) + 
                gt.get('completeness', 10) + gt.get('prosodic', 5)) / 4 * 10
    ground_truth['total'].append(total_gt)
    
    # Trained only
    trained_result = trained_service.score(audio, sr, use_hybrid=False)
    trained_preds['accuracy'].append(trained_result['accuracy'])
    trained_preds['fluency'].append(trained_result['fluency'])
    trained_preds['completeness'].append(trained_result['completeness'])
    trained_preds['prosody'].append(trained_result['prosody'])
    trained_preds['total'].append(trained_result['total'])
    
    # Hybrid
    hybrid_result = trained_service.score(audio, sr, use_hybrid=True)
    hybrid_preds['accuracy'].append(hybrid_result['accuracy'])
    hybrid_preds['fluency'].append(hybrid_result['fluency'])
    hybrid_preds['completeness'].append(hybrid_result['completeness'])
    hybrid_preds['prosody'].append(hybrid_result['prosody'])
    hybrid_preds['total'].append(hybrid_result['total'])

# Calculate metrics
from scipy.stats import pearsonr

print("\n" + "=" * 70)
print("RESULTS: Pearson Correlation with Human Ratings (higher = better)")
print("=" * 70)
print(f"\n{'Score Type':<15} {'Trained Only':>15} {'HYBRID':>15} {'Winner':>15}")
print("-" * 70)

trained_wins = 0
hybrid_wins = 0

for score_type in ['accuracy', 'fluency', 'completeness', 'prosody', 'total']:
    gt = np.array(ground_truth[score_type])
    trained = np.array(trained_preds[score_type])
    hybrid = np.array(hybrid_preds[score_type])
    
    trained_corr, _ = pearsonr(trained, gt)
    hybrid_corr, _ = pearsonr(hybrid, gt)
    
    trained_corr = 0 if np.isnan(trained_corr) else trained_corr
    hybrid_corr = 0 if np.isnan(hybrid_corr) else hybrid_corr
    
    if hybrid_corr > trained_corr:
        winner = "HYBRID ✓"
        hybrid_wins += 1
    elif trained_corr > hybrid_corr:
        winner = "TRAINED"
        trained_wins += 1
    else:
        winner = "TIE"
    
    print(f"{score_type:<15} {trained_corr:>15.3f} {hybrid_corr:>15.3f} {winner:>15}")

print("-" * 70)

# MAE
print("\n" + "=" * 70)
print("RESULTS: Mean Absolute Error (lower = better)")
print("=" * 70)
print(f"\n{'Score Type':<15} {'Trained Only':>15} {'HYBRID':>15} {'Winner':>15}")
print("-" * 70)

trained_mae_wins = 0
hybrid_mae_wins = 0

for score_type in ['accuracy', 'fluency', 'completeness', 'prosody', 'total']:
    gt = np.array(ground_truth[score_type])
    trained = np.array(trained_preds[score_type])
    hybrid = np.array(hybrid_preds[score_type])
    
    trained_mae = np.mean(np.abs(trained - gt))
    hybrid_mae = np.mean(np.abs(hybrid - gt))
    
    if hybrid_mae < trained_mae:
        winner = "HYBRID ✓"
        hybrid_mae_wins += 1
    elif trained_mae < hybrid_mae:
        winner = "TRAINED"
        trained_mae_wins += 1
    else:
        winner = "TIE"
    
    print(f"{score_type:<15} {trained_mae:>15.1f} {hybrid_mae:>15.1f} {winner:>15}")

print("-" * 70)

# Summary
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
print(f"\nPearson Correlation: HYBRID wins {hybrid_wins}/5, Trained wins {trained_wins}/5")
print(f"Mean Absolute Error: HYBRID wins {hybrid_mae_wins}/5, Trained wins {trained_mae_wins}/5")

overall_hybrid = hybrid_wins + hybrid_mae_wins
overall_trained = trained_wins + trained_mae_wins

print("\n" + "-" * 70)
if overall_hybrid > overall_trained:
    print(f"🏆 HYBRID IS THE WINNER ({overall_hybrid} vs {overall_trained})")
elif overall_trained > overall_hybrid:
    print(f"🏆 TRAINED ONLY IS THE WINNER ({overall_trained} vs {overall_hybrid})")
else:
    print(f"🤝 TIE ({overall_hybrid} vs {overall_trained})")
print("-" * 70)
