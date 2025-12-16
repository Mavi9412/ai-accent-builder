"""
AI Accent Builder - FastAPI Backend
Complete REST API for pronunciation training and accent analysis
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

# Import routers
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.courses import router as courses_router
from routers.progress import router as progress_router
from routers.grammar import router as grammar_router
from routers.report import router as report_router
from controllers.accent import router as accent_router

# Create FastAPI app
app = FastAPI(
    title="AI Accent Builder API",
    description="Backend API for pronunciation training and British accent learning",
    version="1.0.0"
)

# CORS middleware - allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Create uploads directory if it doesn't exist
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "audio").mkdir(exist_ok=True)
(uploads_dir / "generated_audio").mkdir(exist_ok=True)

# Mount static files for audio playback
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(courses_router)
app.include_router(progress_router)
app.include_router(grammar_router)
app.include_router(report_router)
app.include_router(accent_router)


@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "status": "running",
        "message": "AI Accent Builder API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ==================== LIVE TRANSCRIPTION WEBSOCKET ====================
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import tempfile
import wave
import struct

@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcription.
    Client sends audio chunks, server returns transcribed text progressively.
    """
    await websocket.accept()
    
    try:
        from services.stt_service import stt_service
        
        audio_buffer = bytearray()
        chunk_count = 0
        last_transcription = ""
        
        await websocket.send_json({
            "type": "connected",
            "message": "Ready for audio streaming"
        })
        
        while True:
            try:
                # Receive audio data (binary)
                data = await asyncio.wait_for(
                    websocket.receive_bytes(),
                    timeout=30.0
                )
                
                audio_buffer.extend(data)
                chunk_count += 1
                
                # Process every ~1 second of audio (16kHz, 16-bit = 32000 bytes/sec)
                if len(audio_buffer) >= 32000:
                    # Save buffer to temp file for transcription
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        temp_path = f.name
                        # Write WAV header
                        with wave.open(temp_path, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(16000)
                            wav_file.writeframes(bytes(audio_buffer))
                    
                    # Transcribe
                    try:
                        result = stt_service.transcribe(temp_path)
                        new_text = result.get("transcribed_text", "")
                        
                        if new_text and new_text != last_transcription:
                            await websocket.send_json({
                                "type": "transcription",
                                "text": new_text,
                                "is_final": False,
                                "confidence": result.get("confidence", 0.9)
                            })
                            last_transcription = new_text
                    except Exception as e:
                        print(f"Transcription error: {e}")
                    
                    # Clean up
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                    
                    # Keep last 0.5 seconds of audio for context
                    audio_buffer = audio_buffer[-16000:]
                    
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})
                
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass


# ==================== REAL-TIME PRONUNCIATION WEBSOCKET ====================

@app.websocket("/ws/pronunciation")
async def websocket_pronunciation(websocket: WebSocket):
    """
    WebSocket endpoint for real-time pronunciation evaluation.
    
    Protocol:
    1. Client sends: {"type": "init", "target_text": "Hello, how are you?"}
    2. Client streams audio (16-bit PCM, 16kHz)
    3. Server sends real-time phoneme/prosody updates
    4. Client sends: {"type": "stop"}
    5. Server sends final result
    """
    print("[WS_PRON] ========== NEW CONNECTION ==========")
    await websocket.accept()
    print("[WS_PRON] Connection accepted")
    
    try:
        from services.hybrid_pronunciation_service import hybrid_service
        import numpy as np
        import json
        
        # Wait for initialization
        print("[WS_PRON] Waiting for init message...")
        init_msg = await websocket.receive_json()
        print(f"[WS_PRON] Received init: {init_msg}")
        
        if init_msg.get('type') != 'init':
            await websocket.send_json({
                'type': 'error',
                'message': 'Expected init message with target_text'
            })
            return
        
        target_text = init_msg.get('target_text', '')
        if not target_text:
            await websocket.send_json({
                'type': 'error',
                'message': 'target_text is required'
            })
            return
        
        # Initialize hybrid service
        hybrid_service.reset()
        hybrid_service.set_target_text(target_text)
        
        await websocket.send_json({
            'type': 'ready',
            'message': 'Ready for audio streaming',
            'target_phonemes': [
                {'phoneme': p['phoneme'], 'ipa': p['ipa'], 'word': p['word']}
                for p in hybrid_service.target_phonemes
            ],
            'total_phonemes': len(hybrid_service.target_phonemes)
        })
        print(f"[WS_PRON] Sent ready message. Waiting for audio chunks...")
        
        chunk_count = 0
        
        # Process streaming audio
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=30.0
                )
                
                if message.get('type') == 'websocket.disconnect':
                    print("[WS_PRON] Client disconnected")
                    break
                
                if 'bytes' in message:
                    # Binary audio (16-bit PCM)
                    audio_bytes = message['bytes']
                    int16_array = np.frombuffer(audio_bytes, dtype=np.int16)
                    float32_array = int16_array.astype(np.float32) / 32768.0
                    
                    chunk_count += 1
                    if chunk_count % 10 == 1:  # Log every 10th chunk
                        print(f"[WS_PRON] Chunk #{chunk_count}: {len(float32_array)} samples, energy={np.sqrt(np.mean(float32_array**2)):.4f}")
                    
                    # Process chunk
                    result = await hybrid_service.process_chunk(float32_array)
                    
                    if result.get('status') == 'processing':
                        await websocket.send_json({
                            'type': 'update',
                            'data': result
                        })
                
                elif 'text' in message:
                    data = json.loads(message['text'])
                    
                    if data.get('type') == 'stop':
                        # Final result
                        final_result = hybrid_service.get_final_result()
                        
                        await websocket.send_json({
                            'type': 'final',
                            'data': {
                                'overall_score': final_result.overall_score,
                                'phoneme_accuracy': final_result.phoneme_accuracy,
                                'timing_accuracy': final_result.timing_accuracy,
                                'prosody_scores': {
                                    'fluency': final_result.prosody_scores.fluency,
                                    'stress': final_result.prosody_scores.stress_accuracy,
                                    'rhythm': final_result.prosody_scores.rhythm,
                                    'intonation': final_result.prosody_scores.intonation,
                                    'overall': final_result.prosody_scores.overall
                                }
                            }
                        })
                        break
                        
            except asyncio.TimeoutError:
                await websocket.send_json({'type': 'keepalive'})
        
        hybrid_service.reset()
        
    except WebSocketDisconnect:
        print("Pronunciation WebSocket disconnected")
    except Exception as e:
        print(f"Pronunciation WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({'type': 'error', 'message': str(e)})
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
