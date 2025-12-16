from database import SessionLocal
from models import AccentSession, WordAnalysis
import sys

try:
    db = SessionLocal()
    session = db.query(AccentSession).order_by(AccentSession.created_at.desc()).first()
    
    if not session:
        print("No sessions found in database.")
    else:
        print(f"\n=== LATEST LIVE SESSION (ID: {session.id}) ===")
        print(f"Time: {session.created_at}")
        print(f"Text: \"{session.transcribed_text}\"")
        print(f"Overall Score: {session.overall_score}%")
        print(f"Pronunciation: {session.pronunciation_score}%")
        print(f"Grammar Errors: {session.error_count}")
        print(f"Word Count: {session.word_count}")
        
        words = db.query(WordAnalysis).filter(WordAnalysis.session_id == session.id).all()
        print(f"\n=== WORD ANALYSIS ({len(words)} words) ===")
        for w in words:
            status = "✅" if w.is_correct else "❌"
            print(f"{status} {w.word:<15} Score: {w.pronunciation_score:<5} Expected: {w.expected_phonemes}")
            
    db.close()
except Exception as e:
    print(f"Error: {e}")
