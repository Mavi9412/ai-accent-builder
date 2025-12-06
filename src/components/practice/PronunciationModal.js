import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { accentAPI } from '../../services/api';

/**
 * PronunciationModal component - Modal for pronunciation practice with recording functionality
 * @param {Function} closeModal - Function to close the modal
 */
const PronunciationModal = ({ closeModal }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeFeedback, setActiveFeedback] = useState(null);
  const [analysisResults, setAnalysisResults] = useState([]);
  const [error, setError] = useState(null);
  const [userAudioUrl, setUserAudioUrl] = useState(null);
  const [isPlayingUser, setIsPlayingUser] = useState(false);

  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const audioDataRef = useRef([]);
  const userAudioRef = useRef(null);
  const currentAudioRef = useRef(null);
  const [playingAudioId, setPlayingAudioId] = useState(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
      if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
    };
  }, []);

  // Convert Float32Array to 16-bit PCM
  const floatTo16BitPCM = (float32Array) => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return buffer;
  };

  // Create WAV file from audio data
  const createWavFile = (audioData, sampleRate) => {
    const numChannels = 1;
    const bitsPerSample = 16;
    const bytesPerSample = bitsPerSample / 8;
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataLength = audioData.length * bytesPerSample;
    const bufferLength = 44 + dataLength;

    const buffer = new ArrayBuffer(bufferLength);
    const view = new DataView(buffer);

    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, bufferLength - 8, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(36, 'data');
    view.setUint32(40, dataLength, true);

    const pcmData = floatTo16BitPCM(audioData);
    const pcmView = new Uint8Array(pcmData);
    const wavView = new Uint8Array(buffer);
    wavView.set(pcmView, 44);

    return new Blob([buffer], { type: 'audio/wav' });
  };

  // Start recording
  const startRecording = async () => {
    try {
      setError(null);
      // Keep previous results - don't reset analysisResult
      audioDataRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true }
      });
      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioDataRef.current.push(...inputData);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
    } catch (err) {
      setError('Could not access microphone. Please allow microphone access.');
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (processorRef.current) { processorRef.current.disconnect(); processorRef.current = null; }
    if (audioContextRef.current) { audioContextRef.current.close(); audioContextRef.current = null; }
    if (mediaStreamRef.current) { mediaStreamRef.current.getTracks().forEach(track => track.stop()); mediaStreamRef.current = null; }
  };

  // Toggle recording state
  const toggleRecording = async () => {
    if (isRecording) {
      setIsRecording(false);
      const audioData = new Float32Array(audioDataRef.current);
      const wavBlob = createWavFile(audioData, 16000);

      // Save user audio for playback
      if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
      setUserAudioUrl(URL.createObjectURL(wavBlob));

      stopRecording();
      await analyzeRecording(wavBlob);
    } else {
      await startRecording();
    }
  };

  // Play user's recording
  const playUserAudio = () => {
    if (!userAudioUrl) return;
    if (userAudioRef.current) userAudioRef.current.pause();

    userAudioRef.current = new Audio(userAudioUrl);
    userAudioRef.current.onplay = () => setIsPlayingUser(true);
    userAudioRef.current.onended = () => setIsPlayingUser(false);
    userAudioRef.current.play();
  };

  // Analyze recording with backend API
  const analyzeRecording = async (blob) => {
    if (blob.size < 1000) {
      setError('Recording too short. Please speak for at least 1 second.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const audioFile = new File([blob], 'recording.wav', { type: 'audio/wav' });
      const result = await accentAPI.analyzeAudio(audioFile, 'british');
      // Add new result to the array (show below previous)
      setAnalysisResults(prev => [...prev, { ...result, audioUrl: URL.createObjectURL(blob), id: Date.now() }]);

      if (result.overall_score >= 80) setActiveFeedback('excellent');
      else if (result.overall_score >= 60) setActiveFeedback('good');
      else setActiveFeedback('needs-work');
    } catch (err) {
      setError(err.message || 'Failed to analyze. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle feedback selection
  const handleFeedback = (type) => {
    setActiveFeedback(type);
    console.log('Feedback given:', type);
  };

  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Pronunciation Training</h2>
          <button className="close-modal" onClick={closeModal}>&times;</button>
        </div>
        <div className="practice-area">
          <div className="chat-container">
            <div className="chat-message ai">
              <div className="message-content">
                Let's practice pronunciation. Click the record button and repeat after me: "The quick brown fox jumps over the lazy dog."
              </div>
            </div>

            {/* Show all analysis results */}
            {analysisResults.map((result, resultIndex) => (
              <React.Fragment key={result.id}>
                <div className="chat-message ai">
                  <div className="message-content" style={{
                    background: 'linear-gradient(135deg, #ffffff 0%, #f6f9fc 100%)',
                    border: '1px solid rgba(74, 144, 226, 0.15)',
                    padding: '0'
                  }}>
                    {/* Header with attempt number */}
                    <div style={{
                      background: 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                      padding: '12px 20px',
                      borderRadius: '10px 10px 0 0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <i className="fas fa-microphone-alt" style={{ color: 'white', fontSize: '18px' }}></i>
                        <span style={{ color: 'white', fontWeight: '600', fontSize: '16px' }}>Your Recording</span>
                      </div>
                      <div style={{
                        background: result.overall_score >= 80 ? 'linear-gradient(135deg, #28a745 0%, #20c997 100%)' :
                          result.overall_score >= 60 ? 'linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)' :
                            'linear-gradient(135deg, #dc3545 0%, #c82333 100%)',
                        padding: '6px 16px',
                        borderRadius: '20px',
                        color: 'white',
                        fontWeight: 'bold',
                        fontSize: '18px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
                      }}>
                        {Math.round(result.overall_score)}%
                      </div>
                    </div>

                    {/* Main content */}
                    <div style={{ padding: '20px' }}>
                      {/* Transcription */}
                      <div style={{
                        background: 'linear-gradient(135deg, #e8f4fd 0%, #d6e9f8 100%)',
                        borderRadius: '10px',
                        padding: '15px',
                        marginBottom: '20px',
                        borderLeft: '4px solid #4a90e2'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                          <i className="fas fa-quote-left" style={{ color: '#4a90e2', fontSize: '14px' }}></i>
                          <span style={{ fontSize: '12px', color: '#4a90e2', fontWeight: '600' }}>You said:</span>
                        </div>
                        <div style={{ fontSize: '15px', color: '#2c3e50', fontStyle: 'italic', lineHeight: '1.5' }}>
                          "{result.transcribed_text}"
                        </div>
                      </div>

                      {/* Score cards */}
                      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <div style={{
                          flex: '1',
                          minWidth: '120px',
                          background: 'white',
                          borderRadius: '12px',
                          padding: '15px',
                          textAlign: 'center',
                          border: '1px solid #e9ecef',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                        }}>
                          <div style={{
                            width: '45px',
                            height: '45px',
                            background: 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 10px auto'
                          }}>
                            <i className="fas fa-spell-check" style={{ color: 'white', fontSize: '18px' }}></i>
                          </div>
                          <div style={{
                            fontSize: '24px',
                            fontWeight: 'bold',
                            color: result.pronunciation_score >= 80 ? '#28a745' : result.pronunciation_score >= 60 ? '#fd7e14' : '#dc3545'
                          }}>
                            {Math.round(result.pronunciation_score)}%
                          </div>
                          <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '4px' }}>Pronunciation</div>
                        </div>

                        <div style={{
                          flex: '1',
                          minWidth: '120px',
                          background: 'white',
                          borderRadius: '12px',
                          padding: '15px',
                          textAlign: 'center',
                          border: '1px solid #e9ecef',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                        }}>
                          <div style={{
                            width: '45px',
                            height: '45px',
                            background: 'linear-gradient(135deg, #6f42c1 0%, #9b59b6 100%)',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 10px auto'
                          }}>
                            <i className="fas fa-wave-square" style={{ color: 'white', fontSize: '18px' }}></i>
                          </div>
                          <div style={{
                            fontSize: '24px',
                            fontWeight: 'bold',
                            color: result.rhythm_score >= 80 ? '#28a745' : result.rhythm_score >= 60 ? '#fd7e14' : '#dc3545'
                          }}>
                            {Math.round(result.rhythm_score)}%
                          </div>
                          <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '4px' }}>Rhythm</div>
                        </div>

                        <div style={{
                          flex: '1',
                          minWidth: '120px',
                          background: 'white',
                          borderRadius: '12px',
                          padding: '15px',
                          textAlign: 'center',
                          border: '1px solid #e9ecef',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                        }}>
                          <div style={{
                            width: '45px',
                            height: '45px',
                            background: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 10px auto'
                          }}>
                            <i className="fas fa-music" style={{ color: 'white', fontSize: '18px' }}></i>
                          </div>
                          <div style={{
                            fontSize: '24px',
                            fontWeight: 'bold',
                            color: result.intonation_score >= 80 ? '#28a745' : result.intonation_score >= 60 ? '#fd7e14' : '#dc3545'
                          }}>
                            {Math.round(result.intonation_score)}%
                          </div>
                          <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '4px' }}>Intonation</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Word-by-word feedback */}
                <div className="chat-message ai">
                  <div className="message-content">
                    <strong>Word Check:</strong>
                    <div style={{ marginTop: '10px' }}>
                      {result.word_feedback && result.word_feedback.map((wordInfo, index) => (
                        <div
                          key={index}
                          style={{
                            display: 'inline-block',
                            margin: '4px',
                            padding: '10px 14px',
                            borderRadius: '10px',
                            backgroundColor: wordInfo.is_correct ? '#d4edda' : '#f8d7da',
                            border: wordInfo.is_correct ? '2px solid #28a745' : '2px solid #dc3545',
                            textAlign: 'center',
                            minWidth: '90px',
                            verticalAlign: 'top'
                          }}
                        >
                          {/* Word with status */}
                          <div style={{
                            fontWeight: 'bold',
                            color: wordInfo.is_correct ? '#155724' : '#721c24',
                            fontSize: '16px',
                            marginBottom: '6px'
                          }}>
                            {wordInfo.word} {wordInfo.is_correct ? '✓' : '✗'}
                          </div>

                          {/* Syllable breakdown */}
                          <div style={{
                            fontSize: '12px',
                            color: '#4a90e2',
                            fontFamily: 'monospace',
                            fontWeight: '500'
                          }}>
                            {wordInfo.syllable_breakdown || wordInfo.word}
                          </div>

                          {/* IPA */}
                          <div style={{
                            fontSize: '11px',
                            color: '#666',
                            fontStyle: 'italic',
                            marginTop: '3px'
                          }}>
                            {wordInfo.ipa || ''}
                          </div>

                          {/* Show mistake comparison for incorrect words */}
                          {!wordInfo.is_correct && (
                            <div style={{
                              marginTop: '8px',
                              padding: '6px',
                              backgroundColor: '#fff3cd',
                              borderRadius: '6px',
                              fontSize: '11px',
                              textAlign: 'left'
                            }}>
                              <div style={{ color: '#856404', marginBottom: '3px' }}>
                                <strong>You said:</strong> "{wordInfo.transcribed_as || '—'}"
                              </div>
                              <div style={{ color: '#155724' }}>
                                <strong>Correct:</strong> "{wordInfo.word}"
                              </div>
                              {wordInfo.feedback && (
                                <div style={{ color: '#721c24', marginTop: '4px', fontSize: '10px' }}>
                                  💡 {wordInfo.feedback}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Play buttons - Your voice and Native speaker */}
                <div className="chat-message user">
                  <div className="message-content" style={{ background: 'transparent', padding: '0', boxShadow: 'none', border: 'none', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    {/* Your voice button */}
                    <button
                      onClick={() => {
                        const audioId = `user-${result.id}`;
                        if (playingAudioId === audioId) {
                          // Stop playing
                          if (currentAudioRef.current) {
                            currentAudioRef.current.pause();
                            currentAudioRef.current = null;
                          }
                          setPlayingAudioId(null);
                        } else {
                          // Stop any current audio
                          if (currentAudioRef.current) {
                            currentAudioRef.current.pause();
                          }
                          // Play new audio
                          const audio = new Audio(result.audioUrl);
                          currentAudioRef.current = audio;
                          audio.onended = () => setPlayingAudioId(null);
                          audio.play();
                          setPlayingAudioId(audioId);
                        }
                      }}
                      style={{
                        background: playingAudioId === `user-${result.id}`
                          ? 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)'
                          : 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                        color: 'white',
                        border: 'none',
                        padding: '12px 20px',
                        borderRadius: '25px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: '600',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: playingAudioId === `user-${result.id}`
                          ? '0 4px 15px rgba(220, 53, 69, 0.3)'
                          : '0 4px 15px rgba(74, 144, 226, 0.3)',
                        transition: 'all 0.3s ease'
                      }}
                    >
                      <i className={`fas ${playingAudioId === `user-${result.id}` ? 'fa-stop' : 'fa-user'}`} style={{ fontSize: '14px' }}></i>
                      {playingAudioId === `user-${result.id}` ? 'Stop' : 'Your Voice'}
                    </button>

                    {/* Native speaker button */}
                    <button
                      onClick={() => {
                        const audioId = `native-${result.id}`;
                        if (playingAudioId === audioId) {
                          // Stop playing
                          if (currentAudioRef.current) {
                            currentAudioRef.current.pause();
                            currentAudioRef.current = null;
                          }
                          setPlayingAudioId(null);
                        } else {
                          // Stop any current audio
                          if (currentAudioRef.current) {
                            currentAudioRef.current.pause();
                          }
                          // Play new audio
                          if (result.session_id) {
                            const audio = new Audio(`http://localhost:8000/api/accent/audio/public/${result.session_id}/corrected`);
                            currentAudioRef.current = audio;
                            audio.onended = () => setPlayingAudioId(null);
                            audio.play();
                            setPlayingAudioId(audioId);
                          }
                        }
                      }}
                      style={{
                        background: playingAudioId === `native-${result.id}`
                          ? 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)'
                          : 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
                        color: 'white',
                        border: 'none',
                        padding: '12px 20px',
                        borderRadius: '25px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: '600',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: playingAudioId === `native-${result.id}`
                          ? '0 4px 15px rgba(220, 53, 69, 0.3)'
                          : '0 4px 15px rgba(40, 167, 69, 0.3)',
                        transition: 'all 0.3s ease'
                      }}
                    >
                      <i className={`fas ${playingAudioId === `native-${result.id}` ? 'fa-stop' : 'fa-volume-up'}`} style={{ fontSize: '14px' }}></i>
                      {playingAudioId === `native-${result.id}` ? 'Stop' : 'Native Speaker'}
                    </button>
                  </div>
                </div>

                {/* Advanced Analysis Section */}
                {result.advanced_analysis && (
                  <div className="chat-message ai">
                    <div className="message-content" style={{
                      background: 'linear-gradient(135deg, #ffffff 0%, #f6f9fc 100%)',
                      border: '1px solid rgba(74, 144, 226, 0.2)',
                      borderTop: '4px solid #4a90e2'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                        <div style={{
                          width: '40px',
                          height: '40px',
                          background: 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                          borderRadius: '10px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          <i className="fas fa-chart-line" style={{ color: 'white', fontSize: '18px' }}></i>
                        </div>
                        <strong style={{ color: '#2c3e50', fontSize: '18px', fontWeight: '600' }}>Advanced Analysis</strong>
                      </div>

                      {/* Score Summary */}
                      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        <div style={{
                          background: 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                          color: 'white',
                          padding: '15px 20px',
                          borderRadius: '12px',
                          textAlign: 'center',
                          minWidth: '110px',
                          boxShadow: '0 4px 15px rgba(74, 144, 226, 0.3)'
                        }}>
                          <i className="fas fa-spell-check" style={{ fontSize: '20px', marginBottom: '8px', display: 'block' }}></i>
                          <div style={{ fontSize: '26px', fontWeight: 'bold' }}>{result.advanced_analysis.phoneme_score}%</div>
                          <div style={{ fontSize: '11px', opacity: 0.9, marginTop: '4px' }}>Phoneme Match</div>
                        </div>
                        <div style={{
                          background: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
                          color: 'white',
                          padding: '15px 20px',
                          borderRadius: '12px',
                          textAlign: 'center',
                          minWidth: '110px',
                          boxShadow: '0 4px 15px rgba(40, 167, 69, 0.3)'
                        }}>
                          <i className="fas fa-music" style={{ fontSize: '20px', marginBottom: '8px', display: 'block' }}></i>
                          <div style={{ fontSize: '26px', fontWeight: 'bold' }}>{result.advanced_analysis.prosody_score}%</div>
                          <div style={{ fontSize: '11px', opacity: 0.9, marginTop: '4px' }}>Prosody</div>
                        </div>
                        <div style={{
                          background: 'linear-gradient(135deg, #6f42c1 0%, #9b59b6 100%)',
                          color: 'white',
                          padding: '15px 20px',
                          borderRadius: '12px',
                          textAlign: 'center',
                          minWidth: '110px',
                          boxShadow: '0 4px 15px rgba(111, 66, 193, 0.3)'
                        }}>
                          <i className="fas fa-wave-square" style={{ fontSize: '20px', marginBottom: '8px', display: 'block' }}></i>
                          <div style={{ fontSize: '26px', fontWeight: 'bold' }}>{result.advanced_analysis.rhythm_similarity}%</div>
                          <div style={{ fontSize: '11px', opacity: 0.9, marginTop: '4px' }}>Rhythm</div>
                        </div>
                      </div>

                      {/* Detailed Category Scores */}
                      {result.advanced_analysis.detailed_scores && (
                        <div style={{ marginTop: '25px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                            <i className="fas fa-layer-group" style={{ color: '#4a90e2', fontSize: '16px' }}></i>
                            <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Detailed Analysis</span>
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
                            {Object.entries(result.advanced_analysis.detailed_scores).map(([key, data]) => (
                              <div key={key} style={{
                                background: 'white',
                                borderRadius: '12px',
                                padding: '15px',
                                border: '1px solid #e9ecef',
                                boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                                textAlign: 'center',
                                transition: 'transform 0.2s ease, box-shadow 0.2s ease'
                              }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.transform = 'translateY(-3px)';
                                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.12)';
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.transform = 'translateY(0)';
                                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)';
                                }}>
                                <div style={{
                                  width: '40px',
                                  height: '40px',
                                  background: data.score >= 80 ? 'linear-gradient(135deg, #28a745 0%, #20c997 100%)' :
                                    data.score >= 60 ? 'linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)' :
                                      'linear-gradient(135deg, #dc3545 0%, #c82333 100%)',
                                  borderRadius: '10px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  margin: '0 auto 10px auto'
                                }}>
                                  <i className={`fas ${data.icon}`} style={{ color: 'white', fontSize: '16px' }}></i>
                                </div>
                                <div style={{
                                  fontSize: '22px',
                                  fontWeight: 'bold',
                                  color: data.score >= 80 ? '#28a745' : data.score >= 60 ? '#fd7e14' : '#dc3545'
                                }}>
                                  {data.score}%
                                </div>
                                <div style={{ fontSize: '12px', fontWeight: '600', color: '#2c3e50', marginTop: '4px' }}>
                                  {data.label}
                                </div>
                                <div style={{ fontSize: '10px', color: '#6c757d', marginTop: '4px' }}>
                                  {data.description}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Phoneme Visualization */}
                      {result.advanced_analysis.word_analyses && result.advanced_analysis.word_analyses.length > 0 && (
                        <div style={{ marginTop: '25px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                            <i className="fas fa-th" style={{ color: '#4a90e2', fontSize: '16px' }}></i>
                            <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Phoneme Alignment</span>
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                            {result.advanced_analysis.word_analyses.map((wordAnalysis, wIdx) => (
                              <div key={wIdx} style={{
                                background: wordAnalysis.similarity >= 90 ? '#d4edda' : wordAnalysis.similarity >= 70 ? '#fff3cd' : '#f8d7da',
                                border: `2px solid ${wordAnalysis.similarity >= 90 ? '#28a745' : wordAnalysis.similarity >= 70 ? '#ffc107' : '#dc3545'}`,
                                borderRadius: '8px',
                                padding: '8px 12px',
                                textAlign: 'center',
                                minWidth: '80px'
                              }}>
                                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{wordAnalysis.word}</div>
                                <div style={{ fontSize: '20px', fontWeight: 'bold', color: wordAnalysis.similarity >= 90 ? '#28a745' : wordAnalysis.similarity >= 70 ? '#856404' : '#dc3545' }}>
                                  {wordAnalysis.similarity}%
                                </div>
                                {/* Show phoneme comparison */}
                                <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
                                  <div>User: {wordAnalysis.user_phonemes?.join(' ') || '—'}</div>
                                  <div>Target: {wordAnalysis.native_phonemes?.join(' ') || '—'}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Improvement Tips */}
                      {result.advanced_analysis.improvement_tips && result.advanced_analysis.improvement_tips.length > 0 && (
                        <div style={{ marginTop: '25px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                            <i className="fas fa-lightbulb" style={{ color: '#ffc107', fontSize: '16px' }}></i>
                            <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Improvement Tips</span>
                          </div>
                          {result.advanced_analysis.improvement_tips.slice(0, 5).map((tip, tIdx) => (
                            <div key={tIdx} style={{
                              background: tip.type === 'phoneme' ? '#e7f3ff' : '#f0f9ff',
                              borderLeft: `4px solid ${tip.type === 'phoneme' ? '#4a90e2' : '#17a2b8'}`,
                              padding: '10px 15px',
                              marginBottom: '8px',
                              borderRadius: '0 8px 8px 0',
                              fontSize: '13px'
                            }}>
                              {tip.word && <strong style={{ color: '#4a90e2' }}>{tip.word}: </strong>}
                              {tip.tip}
                              {tip.category && (
                                <span style={{
                                  marginLeft: '8px',
                                  background: tip.category === 'vowel' ? '#dc3545' : '#007bff',
                                  color: 'white',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '10px'
                                }}>
                                  {tip.category}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Need Practice Words */}
                      {result.advanced_analysis.needs_practice && result.advanced_analysis.needs_practice.length > 0 && (
                        <div style={{
                          marginTop: '20px',
                          padding: '14px 18px',
                          background: 'linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%)',
                          borderRadius: '10px',
                          border: '1px solid #ffc107',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}>
                          <i className="fas fa-exclamation-triangle" style={{ color: '#856404', fontSize: '18px' }}></i>
                          <div>
                            <strong style={{ color: '#856404', fontSize: '13px' }}>Practice these words:</strong>
                            <span style={{ marginLeft: '10px', color: '#856404', fontWeight: '500' }}>
                              {result.advanced_analysis.needs_practice.join(', ')}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </React.Fragment>
            ))}

            {/* Show error */}
            {error && (
              <div className="chat-message ai">
                <div className="message-content" style={{ color: 'red' }}>
                  ⚠️ {error}
                </div>
              </div>
            )}
          </div>

          <div className="recording-controls">
            <button
              className={`record-btn ${isRecording ? 'recording' : ''}`}
              onClick={toggleRecording}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? (
                <i className="fas fa-spinner fa-spin"></i>
              ) : (
                <i className={`fas ${isRecording ? 'fa-stop' : 'fa-microphone'}`}></i>
              )}
            </button>
            {isAnalyzing && <p style={{ textAlign: 'center', marginTop: '10px' }}>Analyzing...</p>}
          </div>
        </div>

        <div className="feedback-container">
          <h3 className="feedback-title">How was your pronunciation?</h3>
          <div className="feedback-buttons">
            <button
              className={`feedback-btn ${activeFeedback === 'excellent' ? 'active' : ''}`}
              onClick={() => handleFeedback('excellent')}
            >
              Excellent
            </button>
            <button
              className={`feedback-btn ${activeFeedback === 'good' ? 'active' : ''}`}
              onClick={() => handleFeedback('good')}
            >
              Good
            </button>
            <button
              className={`feedback-btn ${activeFeedback === 'needs-work' ? 'active' : ''}`}
              onClick={() => handleFeedback('needs-work')}
            >
              Needs Work
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

PronunciationModal.propTypes = {
  closeModal: PropTypes.func.isRequired
};

export default PronunciationModal;
