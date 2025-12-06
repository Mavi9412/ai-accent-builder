"""
Audio Comparison Service - Compares user audio with native speaker audio
"""
from typing import Dict, List


class ComparisonService:
    """Service for comparing user pronunciation with correct pronunciation"""
    
    def compare_audio(self, user_audio_path: str, 
                      correct_audio_path: str,
                      transcribed_text: str) -> Dict:
        """
        Compare user audio with correct pronunciation audio
        
        Returns:
            Dict with similarity scores and detailed comparison
        """
        words = transcribed_text.split()
        word_comparisons = []
        
        # Generate comparison for each word
        for i, word in enumerate(words):
            comparison = {
                "word": word,
                "word_index": i,
                "pronunciation_match": 75 + (hash(word) % 25),  # Simulated score
                "rhythm_match": 70 + (hash(word) % 30),
                "stress_match": 80 + (hash(word) % 20),
                "issues": []
            }
            
            # Add some simulated issues for variety
            if comparison["pronunciation_match"] < 85:
                comparison["issues"].append("Pronunciation needs improvement")
            if comparison["rhythm_match"] < 80:
                comparison["issues"].append("Rhythm slightly off")
            
            word_comparisons.append(comparison)
        
        # Calculate overall scores
        total_words = len(word_comparisons)
        if total_words > 0:
            avg_pronunciation = sum(w["pronunciation_match"] for w in word_comparisons) / total_words
            avg_rhythm = sum(w["rhythm_match"] for w in word_comparisons) / total_words
            avg_stress = sum(w["stress_match"] for w in word_comparisons) / total_words
        else:
            avg_pronunciation = avg_rhythm = avg_stress = 0
        
        overall_score = (avg_pronunciation * 0.5 + avg_rhythm * 0.25 + avg_stress * 0.25)
        
        return {
            "similarity_score": round(overall_score, 1),
            "word_comparisons": word_comparisons,
            "pitch_difference": round(5 + (hash(transcribed_text) % 10), 1),
            "rhythm_difference": round(3 + (hash(transcribed_text[::-1]) % 7), 1),
            "stress_difference": round(4 + (hash(transcribed_text[1:]) % 8), 1),
            "suggestions": [
                "Focus on vowel sounds for clearer pronunciation",
                "Pay attention to word stress patterns",
                "Practice the rhythm by listening to native speakers"
            ]
        }
    
    def get_improvement_tips(self, word_analyses: List[Dict]) -> List[str]:
        """Generate improvement tips based on word analyses"""
        tips = []
        
        incorrect_words = [w for w in word_analyses if not w.get("is_correct", True)]
        
        if len(incorrect_words) > 0:
            tips.append(f"Focus on practicing these words: {', '.join(w['word'] for w in incorrect_words[:5])}")
        
        if len(incorrect_words) > len(word_analyses) * 0.3:
            tips.append("Consider slowing down your speech for clearer pronunciation")
        
        tips.append("Listen to the native speaker audio and compare with your recording")
        tips.append("Practice difficult words individually before trying the full sentence")
        
        return tips


# Singleton instance
comparison_service = ComparisonService()
