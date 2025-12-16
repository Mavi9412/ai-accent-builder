"""
Real-Time Pronunciation WebSocket Endpoint
==========================================

INTEGRATION INSTRUCTIONS:
Add this to your main.py after the existing /ws/transcribe endpoint.

This endpoint provides:
1. Real-time phoneme alignment updates
2. Live prosody scores
3. Per-phoneme visualization data
"""

# ========================== ADD TO main.py ==========================

# Add these imports at the top of main.py
"""
from services.hybrid_pronunciation_service import hybrid_service
import struct
"""

# Add this WebSocket endpoint after /ws/transcribe

WEBSOCKET_ENDPOINT_CODE = '''
@app.websocket("/ws/pronunciation")
async def websocket_pronunciation(websocket: WebSocket):
    """
    WebSocket endpoint for real-time pronunciation evaluation.
    
    PROTOCOL:
    1. Client connects
    2. Client sends JSON: {"type": "init", "target_text": "Hello, how are you?"}
    3. Client streams audio chunks (16-bit PCM, 16kHz, 512 samples/chunk)
    4. Server sends real-time updates:
       - {"type": "phoneme", "data": {...}}
       - {"type": "prosody", "data": {...}}
       - {"type": "word_complete", "data": {...}}
    5. Client sends {"type": "stop"}
    6. Server sends {"type": "final", "data": {...}}
    
    CLIENT INTEGRATION (JavaScript):
    
        const ws = new WebSocket('ws://localhost:8000/ws/pronunciation');
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'init',
                target_text: 'Hello, how are you?'
            }));
        };
        
        // Stream audio chunks
        audioProcessor.onaudioprocess = (e) => {
            const float32 = e.inputBuffer.getChannelData(0);
            const int16 = new Int16Array(float32.length);
            for (let i = 0; i < float32.length; i++) {
                int16[i] = Math.max(-32768, Math.min(32767, float32[i] * 32768));
            }
            ws.send(int16.buffer);
        };
        
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'phoneme') {
                updatePhonemeDisplay(msg.data);
            } else if (msg.type === 'prosody') {
                updateProsodyScores(msg.data);
            }
        };
    """
    await websocket.accept()
    
    try:
        from services.hybrid_pronunciation_service import hybrid_service
        import numpy as np
        
        # Wait for initialization message
        init_data = await websocket.receive_json()
        
        if init_data.get('type') != 'init':
            await websocket.send_json({
                'type': 'error',
                'message': 'Expected init message with target_text'
            })
            return
        
        target_text = init_data.get('target_text', '')
        if not target_text:
            await websocket.send_json({
                'type': 'error',
                'message': 'target_text is required'
            })
            return
        
        # Initialize hybrid service
        hybrid_service.reset()
        hybrid_service.set_target_text(target_text)
        
        # Set up callbacks for real-time updates
        async def on_phoneme_update(phoneme_results):
            await websocket.send_json({
                'type': 'phoneme',
                'data': {
                    'phonemes': [
                        {
                            'index': p.index,
                            'target': p.target_phoneme,
                            'detected': p.detected_phoneme,
                            'target_ipa': p.target_ipa,
                            'detected_ipa': p.detected_ipa,
                            'status': p.status.value,
                            'score': 100 if p.status.value == 'correct' else 0,
                            'timing': p.timing_status.value
                        }
                        for p in phoneme_results
                    ]
                }
            })
        
        async def on_prosody_update(prosody_scores):
            await websocket.send_json({
                'type': 'prosody',
                'data': {
                    'fluency': prosody_scores.fluency,
                    'stress': prosody_scores.stress_accuracy,
                    'rhythm': prosody_scores.rhythm,
                    'intonation': prosody_scores.intonation,
                    'overall': prosody_scores.overall
                }
            })
        
        hybrid_service.on_phoneme_update = on_phoneme_update
        hybrid_service.on_prosody_update = on_prosody_update
        
        await websocket.send_json({
            'type': 'ready',
            'message': 'Ready for audio streaming',
            'target_phonemes': [
                {'phoneme': p['phoneme'], 'ipa': p['ipa'], 'word': p['word']}
                for p in hybrid_service.target_phonemes
            ]
        })
        
        # Process streaming audio
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=30.0
                )
                
                # Check message type
                if message.get('type') == 'websocket.disconnect':
                    break
                
                if 'bytes' in message:
                    # Binary audio data (16-bit PCM)
                    audio_bytes = message['bytes']
                    
                    # Convert bytes to numpy array
                    int16_array = np.frombuffer(audio_bytes, dtype=np.int16)
                    float32_array = int16_array.astype(np.float32) / 32768.0
                    
                    # Process chunk
                    result = await hybrid_service.process_chunk(float32_array)
                    
                    if result.get('status') == 'processing':
                        # Send current state
                        await websocket.send_json({
                            'type': 'update',
                            'data': result
                        })
                
                elif 'text' in message:
                    # JSON message
                    data = json.loads(message['text'])
                    
                    if data.get('type') == 'stop':
                        # Get final result
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
        hybrid_service.reset()
    except Exception as e:
        print(f"Pronunciation WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                'type': 'error',
                'message': str(e)
            })
        except:
            pass
'''

print("=" * 60)
print("ADD THIS CODE TO backend/main.py")
print("=" * 60)
print(WEBSOCKET_ENDPOINT_CODE)
