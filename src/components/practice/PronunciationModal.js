import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { accentAPI } from '../../services/api';
import './PronunciationModal.css';

// Theme colors - matching your app's design system
const THEME = {
  primary: '#4A90E2',
  primaryDark: '#357ABD',
  primaryLight: '#e7f3ff',
  secondary: '#2C3E50',
  success: '#2ECC71',
  successDark: '#27ae60',
  successLight: '#d4edda',
  warning: '#F1C40F',
  warningDark: '#d4ac0d',
  warningLight: '#fff3cd',
  danger: '#E74C3C',
  dangerDark: '#c0392b',
  dangerLight: '#f8d7da',
  background: '#F8FAFC',
  text: '#2C3E50',
  textLight: '#7F8C8D',
  border: '#E2E8F0'
};

// Practice sentences are now loaded from backend via accentAPI.getSentences()

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
  const [selectedCategory, setSelectedCategory] = useState(null); // Set after loading
  const [selectedSentence, setSelectedSentence] = useState(null); // null means no sentence selected
  const [isPlayingNative, setIsPlayingNative] = useState(false);
  const [isLoadingNative, setIsLoadingNative] = useState(false);
  const nativeAudioRef = useRef(null);

  // Sentences from backend
  const [sentences, setSentences] = useState({});
  const [isLoadingSentences, setIsLoadingSentences] = useState(true);
  const [sentencesError, setSentencesError] = useState(null);

  // Phonetics display
  const [sentencePhonetics, setSentencePhonetics] = useState(null);
  const [isLoadingPhonetics, setIsLoadingPhonetics] = useState(false);
  const [showPhonetics, setShowPhonetics] = useState(false);

  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const audioDataRef = useRef([]);
  const userAudioRef = useRef(null);
  const currentAudioRef = useRef(null);
  const [playingAudioId, setPlayingAudioId] = useState(null);

  // PDF Export
  const [isExporting, setIsExporting] = useState(false);
  const [exportingResultId, setExportingResultId] = useState(null);

  // Live transcription state
  const [liveTranscript, setLiveTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const wsRef = useRef(null);
  const audioSendIntervalRef = useRef(null);

  // Real-time pronunciation state
  const [realTimePhonemes, setRealTimePhonemes] = useState([]);
  const [realTimeProsody, setRealTimeProsody] = useState({
    fluency: 0, stress: 0, rhythm: 0, intonation: 0, overall: 0
  });
  const [targetPhonemes, setTargetPhonemes] = useState([]);
  const pronWsRef = useRef(null);

  // Fetch sentences from backend on mount
  useEffect(() => {
    const fetchSentences = async () => {
      try {
        setIsLoadingSentences(true);
        const response = await accentAPI.getSentences();
        setSentences(response.categories || {});
        // Set default category to first one
        const categories = Object.keys(response.categories || {});
        if (categories.length > 0) {
          setSelectedCategory(categories[0]);
        }
      } catch (err) {
        console.error('Failed to fetch sentences:', err);
        setSentencesError('Failed to load practice sentences');
        // Fallback to empty
        setSentences({});
      } finally {
        setIsLoadingSentences(false);
      }
    };
    fetchSentences();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
      if (userAudioUrl) URL.revokeObjectURL(userAudioUrl);
      if (nativeAudioRef.current) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Fetch phonetics when sentence is selected
  useEffect(() => {
    const fetchPhonetics = async () => {
      if (!selectedSentence) {
        setSentencePhonetics(null);
        return;
      }
      try {
        setIsLoadingPhonetics(true);
        const response = await accentAPI.getSentencePhonetics(selectedSentence.text);
        setSentencePhonetics(response.words || []);
      } catch (err) {
        console.error('Failed to fetch phonetics:', err);
        setSentencePhonetics(null);
      } finally {
        setIsLoadingPhonetics(false);
      }
    };
    fetchPhonetics();
  }, [selectedSentence]);

  // Play native voice pronunciation using SpeechSynthesis
  const playNativeVoice = () => {
    if (isPlayingNative) {
      // Stop if already playing
      window.speechSynthesis.cancel();
      setIsPlayingNative(false);
      return;
    }

    setIsLoadingNative(true);

    const utterance = new SpeechSynthesisUtterance(selectedSentence.text);

    // Try to find a British English voice
    const voices = window.speechSynthesis.getVoices();
    const britishVoice = voices.find(voice =>
      voice.lang === 'en-GB' ||
      voice.name.includes('British') ||
      voice.name.includes('UK')
    ) || voices.find(voice => voice.lang.startsWith('en'));

    if (britishVoice) {
      utterance.voice = britishVoice;
    }

    utterance.lang = 'en-GB';
    utterance.rate = 0.9; // Slightly slower for clarity
    utterance.pitch = 1;

    utterance.onstart = () => {
      setIsLoadingNative(false);
      setIsPlayingNative(true);
    };

    utterance.onend = () => {
      setIsPlayingNative(false);
    };

    utterance.onerror = () => {
      setIsLoadingNative(false);
      setIsPlayingNative(false);
    };

    window.speechSynthesis.speak(utterance);
  };

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

  // Start recording (simplified - live transcript shows after stop)
  const startRecording = async () => {
    try {
      setError(null);
      audioDataRef.current = [];
      setLiveTranscript('');
      setIsTranscribing(true);
      setRealTimePhonemes([]);
      setRealTimeProsody({ fluency: 0, stress: 0, rhythm: 0, intonation: 0, overall: 0 });

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true }
      });
      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      // Connect to pronunciation WebSocket for real-time feedback
      // Use selected sentence or default free practice sentence
      const targetText = selectedSentence?.text || 'The quick brown fox jumps over the lazy dog.';

      try {
        console.log('[PronWS] Connecting to ws://localhost:8000/ws/pronunciation');
        pronWsRef.current = new WebSocket('ws://localhost:8000/ws/pronunciation');

        pronWsRef.current.onopen = () => {
          console.log('[PronWS] Connected! Sending init with:', targetText);
          pronWsRef.current.send(JSON.stringify({
            type: 'init',
            target_text: targetText
          }));
        };

        pronWsRef.current.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          console.log('[PronWS] Message received:', msg.type, msg);
          if (msg.type === 'ready') {
            console.log('[PronWS] Ready! Target phonemes:', msg.target_phonemes?.length);
            setTargetPhonemes(msg.target_phonemes || []);
          } else if (msg.type === 'update' && msg.data) {
            console.log('[PronWS] Update! Phonemes:', msg.data.phoneme_results?.length, 'Prosody:', msg.data.prosody_scores);
            if (msg.data.phoneme_results) {
              setRealTimePhonemes(msg.data.phoneme_results);
            }
            if (msg.data.prosody_scores) {
              setRealTimeProsody(msg.data.prosody_scores);
            }
          } else if (msg.type === 'final' && msg.data) {
            console.log('[PronWS] Final result:', msg.data);
            setRealTimeProsody(msg.data.prosody_scores || {});
          }
        };

        pronWsRef.current.onerror = (err) => {
          console.log('[PronWS] WebSocket error:', err);
        };

        pronWsRef.current.onclose = () => {
          console.log('[PronWS] WebSocket closed');
        };
      } catch (wsErr) {
        console.log('[PronWS] Could not connect:', wsErr);
      }

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioDataRef.current.push(...inputData);

        // Stream to pronunciation WebSocket
        if (pronWsRef.current && pronWsRef.current.readyState === WebSocket.OPEN) {
          const int16 = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            int16[i] = Math.max(-32768, Math.min(32767, Math.floor(inputData[i] * 32768)));
          }
          pronWsRef.current.send(int16.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
    } catch (err) {
      setError('Could not access microphone. Please allow microphone access.');
      setIsTranscribing(false);
    }
  };

  // Stop recording and close WebSocket
  const stopRecording = () => {
    if (processorRef.current) { processorRef.current.disconnect(); processorRef.current = null; }
    if (audioContextRef.current) { audioContextRef.current.close(); audioContextRef.current = null; }
    if (mediaStreamRef.current) { mediaStreamRef.current.getTracks().forEach(track => track.stop()); mediaStreamRef.current = null; }

    // Close transcription WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Close pronunciation WebSocket
    if (pronWsRef.current) {
      pronWsRef.current.send(JSON.stringify({ type: 'stop' }));
      setTimeout(() => {
        if (pronWsRef.current) {
          pronWsRef.current.close();
          pronWsRef.current = null;
        }
      }, 500);
    }
    setIsTranscribing(false);
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

  // Analyze recording with backend API - with progress simulation
  const [analysisProgress, setAnalysisProgress] = useState({ progress: 0, message: '' });

  const analyzeRecording = async (blob) => {
    if (blob.size < 1000) {
      setError('Recording too short. Please speak for at least 1 second.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setAnalysisProgress({ progress: 0, message: 'Starting analysis...' });

    try {
      const audioFile = new File([blob], 'recording.wav', { type: 'audio/wav' });
      const targetSentence = selectedSentence ? selectedSentence.text : '__FREE_PRACTICE__';

      // Try streaming API first, fallback to regular if fails
      let result;
      try {
        result = await accentAPI.analyzeAudioStream(
          audioFile,
          'british',
          targetSentence,
          (progressData) => {
            setAnalysisProgress({
              progress: progressData.progress || 0,
              message: progressData.message || 'Processing...',
              stage: progressData.stage,
              data: progressData.data
            });
            // Show transcribed text as soon as it's available
            if (progressData.data?.text) {
              setLiveTranscript(progressData.data.text);
            }
          }
        );
      } catch (streamErr) {
        console.log('Streaming failed, using regular endpoint:', streamErr.message);
        // Fallback to regular endpoint with simulated progress
        setAnalysisProgress({ progress: 20, message: 'Uploading audio...' });
        await new Promise(r => setTimeout(r, 300));
        setAnalysisProgress({ progress: 40, message: 'Transcribing speech...' });

        result = await accentAPI.analyzeAudio(audioFile, 'british', targetSentence);

        // Show transcribed text immediately after receiving result
        if (result.transcribed_text) {
          setLiveTranscript(result.transcribed_text);
        }

        setAnalysisProgress({ progress: 90, message: 'Finalizing...' });
        await new Promise(r => setTimeout(r, 200));
      }

      // Show final transcribed text
      if (result.transcribed_text) {
        setLiveTranscript(result.transcribed_text);
      }

      // Add new result to the array
      setAnalysisResults(prev => [...prev, { ...result, audioUrl: URL.createObjectURL(blob), id: Date.now() }]);

      if (result.overall_score >= 80) setActiveFeedback('excellent');
      else if (result.overall_score >= 60) setActiveFeedback('good');
      else setActiveFeedback('needs-work');
    } catch (err) {
      setError(err.message || 'Failed to analyze. Please try again.');
    } finally {
      setIsAnalyzing(false);
      setAnalysisProgress({ progress: 100, message: 'Complete!' });
      setTimeout(() => setAnalysisProgress({ progress: 0, message: '' }), 500);
    }
  };

  // Handle feedback selection
  const handleFeedback = (type) => {
    setActiveFeedback(type);
    console.log('Feedback given:', type);
  };

  // Export PDF report for a specific result
  const handleExportPDF = async (result) => {
    if (!result) return;

    setIsExporting(true);
    setExportingResultId(result.id);

    try {
      const token = localStorage.getItem('token');

      // Prepare word analyses with all fields
      const wordAnalyses = (result.word_analyses || []).map((wa, idx) => ({
        word: wa.word || '',
        word_index: wa.word_index ?? idx,
        score: wa.score || wa.pronunciation_score || 70,
        is_correct: wa.is_correct !== undefined ? wa.is_correct : (wa.score >= 60),
        expected_phonemes: wa.expected_phonemes || wa.ipa || '',
        transcribed_phonemes: wa.transcribed_phonemes || wa.actual_phonemes || '',
        feedback: wa.feedback || wa.suggestion || '',
        duration: wa.duration || null,
        stress_correct: wa.stress_correct,
        timing_status: wa.timing_status || null
      }));

      // Prepare scores object
      const scores = result.scores || {
        pronunciation: result.pronunciation_score || result.overall_score || 0,
        rhythm: result.rhythm_score || 70,
        intonation: result.intonation_score || 70,
        stress: result.stress_score || 70
      };

      // Prepare followup question data
      const followupQuestion = result.followup_question ? {
        question: result.followup_question.question || result.followup_question.followup || '',
        correction: result.followup_question.correction || '',
        accent_tip: result.followup_question.accent_tip || '',
        vocabulary_tip: result.followup_question.vocabulary_tip || '',
        next_practice_sentence: result.followup_question.next_practice_sentence || result.followup_question.practice_sentence || ''
      } : null;

      // Build complete export request
      const exportData = {
        session_id: result.session_id || result.id || Date.now(),
        transcribed_text: result.transcribed_text || '',
        target_text: selectedSentence?.text || result.target_text || result.transcribed_text || '',
        overall_score: result.overall_score || 0,
        scores: scores,
        word_analyses: wordAnalyses,
        word_count: result.word_count || wordAnalyses.length,
        error_count: result.error_count || wordAnalyses.filter(w => !w.is_correct).length,
        followup_question: followupQuestion,
        audio_duration: result.audio_duration || 0,
        grammar_analysis: result.grammar_analysis || null,
        dialect_analysis: result.dialect_analysis || null,
        advanced_analysis: result.advanced_analysis || null
      };

      console.log('[Export PDF] Sending data:', exportData);

      const response = await fetch('http://localhost:8000/api/report/generate-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify(exportData)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to export PDF (${response.status})`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pronunciation_report_${exportData.session_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      console.log('[Export PDF] Download successful!');
    } catch (error) {
      console.error('[Export PDF] Error:', error);
      alert(`Failed to export report: ${error.message}`);
    } finally {
      setIsExporting(false);
      setExportingResultId(null);
    }
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
            {/* Category-based Sentence Display */}
            <div className="chat-message ai">
              <div className="message-content" style={{ padding: 0 }}>
                {/* Header */}
                <div className="pm-header">
                  <div className="pm-header-title">
                    <i className="fas fa-microphone-alt"></i>
                    <span>Practice Sentences</span>
                  </div>
                  <div className="pm-header-subtitle">
                    Choose a category and click on any sentence to practice
                  </div>
                </div>

                {/* Content */}
                <div style={{ padding: '20px' }}>
                  {/* SELECTED SENTENCE - Prominent Display (only when sentence is selected) */}
                  {selectedSentence ? (
                    <div style={{
                      background: 'linear-gradient(135deg, #e8f4fd 0%, #d6e9f8 100%)',
                      borderRadius: '12px',
                      padding: '20px',
                      marginBottom: '20px',
                      border: `2px solid ${THEME.primary}`,
                      boxShadow: '0 4px 15px rgba(74, 144, 226, 0.12)'
                    }}>
                      <div className="pm-sentence-header">
                        <div className="pm-sentence-label">
                          <i className="fas fa-bullseye"></i>
                          <span>Selected Sentence</span>
                        </div>
                        <div className="pm-sentence-badges">
                          <span className="pm-badge pm-badge-primary">{selectedCategory}</span>
                          <span className={`pm-badge ${selectedSentence.difficulty === 'Easy' ? 'pm-badge-success' :
                            selectedSentence.difficulty === 'Medium' ? 'pm-badge-warning' : 'pm-badge-danger'
                            }`}>{selectedSentence.difficulty}</span>
                          <button
                            onClick={() => setSelectedSentence(null)}
                            style={{
                              background: 'transparent',
                              border: `1px solid ${THEME.danger}`,
                              color: THEME.danger,
                              borderRadius: '50%',
                              width: '26px',
                              height: '26px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '12px',
                              marginLeft: '5px',
                              transition: 'all 0.2s ease'
                            }}
                            title="Unselect sentence"
                          >
                            <i className="fas fa-times"></i>
                          </button>
                        </div>
                      </div>
                      <div className="pm-sentence-text">
                        <i className="fas fa-quote-left"></i>
                        <span style={{ flex: 1 }}>{selectedSentence.text}</span>
                        <i className="fas fa-quote-right"></i>
                        <button
                          className={`pm-play-btn ${isPlayingNative ? 'playing' : ''}`}
                          onClick={playNativeVoice}
                          disabled={isLoadingNative}
                          title={isPlayingNative ? 'Stop' : 'Listen to native pronunciation'}
                        >
                          <i className={`fas ${isLoadingNative ? 'fa-spinner fa-spin' : isPlayingNative ? 'fa-stop' : 'fa-volume-up'}`}></i>
                        </button>
                      </div>
                      <div className="pm-sentence-info">
                        <div>
                          <i className="fas fa-info-circle"></i>
                          Click the green button to hear native pronunciation
                        </div>
                        <div className="highlight">
                          <i className="fas fa-microphone"></i>
                          Then record yourself below
                        </div>
                      </div>

                      <button
                        className={`pm-phonetics-toggle ${showPhonetics ? 'active' : ''}`}
                        onClick={() => setShowPhonetics(!showPhonetics)}
                      >
                        <i className={`fas ${showPhonetics ? 'fa-chevron-up' : 'fa-language'}`}></i>
                        {isLoadingPhonetics ? 'Loading...' : showPhonetics ? 'Hide Phonetics' : 'Show IPA & Syllables'}
                      </button>

                      {/* Phonetics Display */}
                      {showPhonetics && sentencePhonetics && (
                        <div className="pm-phonetics-display">
                          <div className="pm-phonetics-title">
                            <i className="fas fa-language"></i>
                            Word-by-Word Phonetics
                          </div>
                          <div className="pm-phonetics-words">
                            {sentencePhonetics.map((wordInfo, idx) => (
                              <div key={idx} className="pm-phonetic-word">
                                <div className="word">{wordInfo.word}</div>
                                <div className="ipa">{wordInfo.ipa}</div>
                                <div className="syllables">{wordInfo.syllables?.join(' · ') || '-'}</div>
                                <div className="respelling">{wordInfo.respelling}</div>
                                <button
                                  className="pm-word-audio-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const utterance = new SpeechSynthesisUtterance(wordInfo.word);
                                    utterance.lang = 'en-GB';
                                    utterance.rate = 0.8;
                                    window.speechSynthesis.speak(utterance);
                                  }}
                                  title={`Hear "${wordInfo.word}"`}
                                >
                                  <i className="fas fa-volume-up"></i>
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* REAL-TIME PHONEME DISPLAY - Shows during recording */}
                      {(isRecording || realTimePhonemes.length > 0) && (
                        <div style={{
                          marginTop: '15px',
                          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
                          borderRadius: '12px',
                          padding: '15px',
                          border: '2px solid #667eea'
                        }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '12px'
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div style={{
                                width: '10px',
                                height: '10px',
                                borderRadius: '50%',
                                background: isRecording ? '#ff4757' : '#2ed573',
                                animation: isRecording ? 'pulse 1s infinite' : 'none'
                              }}></div>
                              <span style={{ color: 'white', fontWeight: '600', fontSize: '12px' }}>
                                {isRecording ? '🎤 LIVE PHONEME ANALYSIS' : '✅ ANALYSIS COMPLETE'}
                              </span>
                            </div>
                            <span style={{
                              color: '#667eea',
                              fontSize: '11px',
                              fontFamily: 'monospace'
                            }}>
                              {realTimePhonemes.length}/{targetPhonemes.length} phonemes
                            </span>
                          </div>

                          {/* Target Phoneme Sequence */}
                          <div style={{ marginBottom: '10px' }}>
                            <div style={{ fontSize: '10px', color: '#a0a0a0', marginBottom: '6px' }}>TARGET:</div>
                            <div style={{
                              display: 'flex',
                              flexWrap: 'wrap',
                              gap: '4px'
                            }}>
                              {targetPhonemes.map((p, i) => {
                                const detected = realTimePhonemes[i];
                                const status = detected ? detected.status : 'pending';
                                return (
                                  <div key={i} style={{
                                    background: status === 'correct' ? 'rgba(46, 213, 115, 0.2)' :
                                      status === 'substitution' ? 'rgba(255, 71, 87, 0.2)' :
                                        'rgba(255, 255, 255, 0.1)',
                                    border: `1px solid ${status === 'correct' ? '#2ed573' :
                                      status === 'substitution' ? '#ff4757' : '#555'}`,
                                    borderRadius: '6px',
                                    padding: '4px 8px',
                                    minWidth: '35px',
                                    textAlign: 'center',
                                    transition: 'all 0.3s ease'
                                  }}>
                                    <div style={{
                                      fontSize: '11px',
                                      fontWeight: 'bold',
                                      color: status === 'correct' ? '#2ed573' :
                                        status === 'substitution' ? '#ff4757' : '#fff',
                                      fontFamily: 'monospace'
                                    }}>
                                      {p.phoneme}
                                    </div>
                                    <div style={{
                                      fontSize: '8px',
                                      color: '#888',
                                      marginTop: '2px'
                                    }}>
                                      {status === 'correct' ? '✓' :
                                        status === 'substitution' ? '✗' :
                                          status === 'pending' ? '○' : ''}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>

                          {/* Real-Time Prosody Bars */}
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(4, 1fr)',
                            gap: '8px',
                            marginTop: '12px'
                          }}>
                            {[
                              { key: 'fluency', label: 'Fluency', icon: '🎯' },
                              { key: 'stress', label: 'Stress', icon: '💪' },
                              { key: 'rhythm', label: 'Rhythm', icon: '🎵' },
                              { key: 'intonation', label: 'Tone', icon: '📈' }
                            ].map(({ key, label, icon }) => {
                              const score = realTimeProsody[key] || 0;
                              return (
                                <div key={key} style={{ textAlign: 'center' }}>
                                  <div style={{ fontSize: '16px', marginBottom: '4px' }}>{icon}</div>
                                  <div style={{
                                    height: '8px',
                                    background: '#333',
                                    borderRadius: '4px',
                                    overflow: 'hidden'
                                  }}>
                                    <div style={{
                                      width: `${score}%`,
                                      height: '100%',
                                      background: score >= 70 ? 'linear-gradient(90deg, #2ed573, #7bed9f)' :
                                        score >= 50 ? 'linear-gradient(90deg, #ffc107, #ffda79)' :
                                          'linear-gradient(90deg, #ff4757, #ff6b81)',
                                      transition: 'width 0.3s ease'
                                    }}></div>
                                  </div>
                                  <div style={{
                                    fontSize: '9px',
                                    color: '#a0a0a0',
                                    marginTop: '4px'
                                  }}>{label}</div>
                                  <div style={{
                                    fontSize: '12px',
                                    fontWeight: 'bold',
                                    color: score >= 70 ? '#2ed573' : score >= 50 ? '#ffc107' : '#ff4757'
                                  }}>{Math.round(score)}%</div>
                                </div>
                              );
                            })}
                          </div>

                          {/* Overall Score */}
                          <div style={{
                            marginTop: '12px',
                            padding: '8px 15px',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            borderRadius: '8px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}>
                            <span style={{ color: 'white', fontWeight: '600', fontSize: '11px' }}>
                              OVERALL PROSODY
                            </span>
                            <span style={{
                              color: 'white',
                              fontWeight: 'bold',
                              fontSize: '18px',
                              textShadow: '0 2px 4px rgba(0,0,0,0.3)'
                            }}>
                              {Math.round(realTimeProsody.overall || 0)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* No sentence selected - Use default free practice */
                    <div style={{
                      background: 'linear-gradient(135deg, #e8f4fd 0%, #d6e9f8 100%)',
                      borderRadius: '12px',
                      padding: '20px',
                      marginBottom: '20px',
                      border: '2px solid #4a90e2',
                      boxShadow: '0 4px 12px rgba(74,144,226,0.15)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <i className="fas fa-star" style={{ color: '#4a90e2', fontSize: '18px' }}></i>
                          <span style={{ fontWeight: '700', fontSize: '14px', color: '#2c3e50', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Free Practice Mode</span>
                        </div>
                        <span style={{
                          background: 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                          color: 'white',
                          padding: '4px 12px',
                          borderRadius: '15px',
                          fontSize: '11px',
                          fontWeight: '600'
                        }}>Default</span>
                      </div>
                      <div style={{
                        fontSize: '18px',
                        color: '#2c3e50',
                        fontWeight: '600',
                        lineHeight: '1.6',
                        padding: '10px 0',
                        display: 'flex',
                        alignItems: 'center',
                        flexWrap: 'wrap'
                      }}>
                        <i className="fas fa-quote-left" style={{ color: '#4a90e2', marginRight: '10px', fontSize: '14px' }}></i>
                        <span style={{ flex: 1 }}>The quick brown fox jumps over the lazy dog.</span>
                        <i className="fas fa-quote-right" style={{ color: '#4a90e2', marginLeft: '10px', fontSize: '14px' }}></i>
                        {/* Native Voice Play Button for default */}
                        <button
                          onClick={() => {
                            if (isPlayingNative) {
                              window.speechSynthesis.cancel();
                              setIsPlayingNative(false);
                              return;
                            }
                            setIsLoadingNative(true);
                            const utterance = new SpeechSynthesisUtterance("The quick brown fox jumps over the lazy dog.");
                            const voices = window.speechSynthesis.getVoices();
                            const britishVoice = voices.find(v => v.lang === 'en-GB' || v.name.includes('British')) || voices.find(v => v.lang.startsWith('en'));
                            if (britishVoice) utterance.voice = britishVoice;
                            utterance.lang = 'en-GB';
                            utterance.rate = 0.9;
                            utterance.onstart = () => { setIsLoadingNative(false); setIsPlayingNative(true); };
                            utterance.onend = () => setIsPlayingNative(false);
                            utterance.onerror = () => { setIsLoadingNative(false); setIsPlayingNative(false); };
                            window.speechSynthesis.speak(utterance);
                          }}
                          disabled={isLoadingNative}
                          style={{
                            marginLeft: '15px',
                            width: '42px',
                            height: '42px',
                            borderRadius: '50%',
                            border: 'none',
                            background: isPlayingNative
                              ? 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)'
                              : 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                            color: 'white',
                            cursor: isLoadingNative ? 'wait' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 3px 10px rgba(74,144,226,0.3)',
                            transition: 'all 0.2s ease',
                            flexShrink: 0
                          }}
                          title={isPlayingNative ? 'Stop' : 'Listen to native pronunciation'}
                        >
                          <i className={`fas ${isLoadingNative ? 'fa-spinner fa-spin' : isPlayingNative ? 'fa-stop' : 'fa-volume-up'}`}
                            style={{ fontSize: '16px' }}></i>
                        </button>
                      </div>
                      <div style={{
                        fontSize: '12px',
                        color: '#2c3e50',
                        marginTop: '15px',
                        background: 'rgba(255,255,255,0.7)',
                        padding: '12px',
                        borderRadius: '8px'
                      }}>
                        <div style={{ fontWeight: '600', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <i className="fas fa-magic"></i>
                          How Free Practice Works:
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '11px' }}>
                          <div><i className="fas fa-microphone" style={{ marginRight: '8px', color: '#dc3545' }}></i>1. Say anything in English</div>
                          <div><i className="fas fa-file-alt" style={{ marginRight: '8px', color: '#4a90e2' }}></i>2. We transcribe your speech</div>
                          <div><i className="fas fa-volume-up" style={{ marginRight: '8px', color: '#28a745' }}></i>3. Generate native pronunciation</div>
                          <div><i className="fas fa-check-circle" style={{ marginRight: '8px', color: '#4a90e2' }}></i>4. Compare and give feedback</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Loading State for Sentences */}
                  {isLoadingSentences ? (
                    <div style={{
                      textAlign: 'center',
                      padding: '40px',
                      color: '#6c757d'
                    }}>
                      <i className="fas fa-spinner fa-spin" style={{ fontSize: '32px', marginBottom: '15px' }}></i>
                      <div>Loading practice sentences...</div>
                    </div>
                  ) : sentencesError ? (
                    <div style={{
                      textAlign: 'center',
                      padding: '20px',
                      color: '#dc3545',
                      background: '#f8d7da',
                      borderRadius: '8px',
                      marginBottom: '15px'
                    }}>
                      <i className="fas fa-exclamation-circle" style={{ marginRight: '8px' }}></i>
                      {sentencesError}
                    </div>
                  ) : (
                    <>
                      {/* Category Tabs */}
                      <div className="pm-category-tabs">
                        {Object.keys(sentences).map(category => (
                          <button
                            key={category}
                            className={`pm-category-tab ${selectedCategory === category ? 'active' : ''}`}
                            onClick={() => {
                              setSelectedCategory(category);
                              setSelectedSentence(null);
                              setAnalysisResults([]);
                            }}
                          >
                            <i className={`fas ${category === 'Greetings' ? 'fa-hand-wave' :
                              category === 'Everyday' ? 'fa-mug-hot' :
                                category === 'Numbers' ? 'fa-hashtag' :
                                  category === 'Questions' ? 'fa-question-circle' :
                                    category === 'TH Sounds' ? 'fa-language' :
                                      category === 'Vowels' ? 'fa-circle' :
                                        category === 'Consonants' ? 'fa-font' :
                                          category === 'Business' ? 'fa-briefcase' :
                                            'fa-graduation-cap'
                              }`}></i>
                            {category}
                          </button>
                        ))}
                      </div>

                      {/* Sentences in Selected Category */}
                      <div className="pm-sentence-list">
                        {selectedCategory && sentences[selectedCategory] && sentences[selectedCategory].map((sentence, index) => (
                          <div
                            key={sentence.id}
                            className={`pm-sentence-item ${selectedSentence && selectedSentence.id === sentence.id ? 'selected' : ''}`}
                            onClick={() => {
                              if (selectedSentence && selectedSentence.id === sentence.id) {
                                setSelectedSentence(null);
                              } else {
                                setSelectedSentence(sentence);
                              }
                              setAnalysisResults([]);
                            }}
                          >
                            <div className="pm-sentence-item-header">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className="pm-sentence-number">{index + 1}</span>
                                <span className={`pm-difficulty-badge pm-difficulty-${sentence.difficulty.toLowerCase()}`}>
                                  {sentence.difficulty}
                                </span>
                              </div>
                              {selectedSentence && selectedSentence.id === sentence.id && (
                                <span className="pm-badge pm-badge-primary">
                                  <i className="fas fa-check" style={{ marginRight: '4px' }}></i>
                                  Selected
                                </span>
                              )}
                            </div>
                            <div className="pm-sentence-item-text">
                              "{sentence.text}"
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Show all analysis results */}
            {
              analysisResults.map((result, resultIndex) => (
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
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          {/* Export PDF Button */}
                          <button
                            onClick={() => handleExportPDF(result)}
                            disabled={isExporting && exportingResultId === result.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '6px 12px',
                              background: isExporting && exportingResultId === result.id
                                ? 'rgba(255,255,255,0.3)'
                                : 'rgba(255,255,255,0.2)',
                              border: '1px solid rgba(255,255,255,0.4)',
                              borderRadius: '20px',
                              color: 'white',
                              fontSize: '12px',
                              fontWeight: '600',
                              cursor: isExporting && exportingResultId === result.id ? 'not-allowed' : 'pointer',
                              transition: 'all 0.2s ease'
                            }}
                            title="Download PDF Report"
                          >
                            <i className={`fas ${isExporting && exportingResultId === result.id ? 'fa-spinner fa-spin' : 'fa-file-pdf'}`}></i>
                            {isExporting && exportingResultId === result.id ? 'Exporting...' : 'Export PDF'}
                          </button>
                          {/* Score Badge */}
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
                      </div>

                      {/* Main content - simplified view */}
                      <div style={{ padding: '20px' }}>
                        {/* Simple Transcription */}
                        <div style={{
                          background: 'linear-gradient(135deg, #e8f4fd 0%, #d6e9f8 100%)',
                          borderRadius: '10px',
                          padding: '15px',
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

                        {/* Quick Stats Summary - compact */}
                        <div style={{
                          marginTop: '15px',
                          display: 'flex',
                          gap: '15px',
                          flexWrap: 'wrap',
                          justifyContent: 'center'
                        }}>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '11px', color: '#6c757d' }}>Words</div>
                            <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#4a90e2' }}>
                              {result.word_count - result.error_count}/{result.word_count}
                            </div>
                          </div>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '11px', color: '#6c757d' }}>Pronunciation</div>
                            <div style={{ fontSize: '18px', fontWeight: 'bold', color: result.pronunciation_score >= 80 ? '#28a745' : result.pronunciation_score >= 60 ? '#fd7e14' : '#dc3545' }}>
                              {Math.round(result.pronunciation_score)}%
                            </div>
                          </div>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '11px', color: '#6c757d' }}>Fluency</div>
                            <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#4a90e2' }}>
                              {Math.round((result.rhythm_score + result.intonation_score) / 2)}%
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Word-by-word feedback with Phoneme Alignment */}
                  <div className="chat-message ai">
                    <div className="message-content">
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        marginBottom: '15px',
                        paddingBottom: '10px',
                        borderBottom: '2px solid #e9ecef'
                      }}>
                        <i className="fas fa-align-left" style={{ color: '#4a90e2', fontSize: '18px' }}></i>
                        <strong style={{ fontSize: '16px', color: '#2c3e50' }}>Phoneme Alignment</strong>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {result.word_feedback && result.word_feedback.map((wordInfo, index) => {
                          // Determine if it's a vowel error (simulated based on score)
                          const isVowelError = !wordInfo.is_correct && wordInfo.score > 50;
                          const bgColor = wordInfo.is_correct ? '#d4edda' : isVowelError ? '#fff3cd' : '#f8d7da';
                          const borderColor = wordInfo.is_correct ? '#28a745' : isVowelError ? '#fd7e14' : '#dc3545';
                          const textColor = wordInfo.is_correct ? '#155724' : isVowelError ? '#856404' : '#721c24';

                          return (
                            <div
                              key={index}
                              style={{
                                background: bgColor,
                                border: `2px solid ${borderColor}`,
                                borderRadius: '12px',
                                padding: '12px 16px',
                                minWidth: '100px',
                                textAlign: 'center',
                                position: 'relative'
                              }}
                            >
                              {/* Word */}
                              <div style={{
                                fontWeight: 'bold',
                                fontSize: '15px',
                                color: textColor,
                                marginBottom: '6px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '6px'
                              }}>
                                {wordInfo.word}
                                <span style={{
                                  fontSize: '12px',
                                  opacity: 0.8
                                }}>
                                  {wordInfo.is_correct ? '✓' : isVowelError ? '◐' : '✗'}
                                </span>
                              </div>

                              {/* Phoneme Display */}
                              <div style={{
                                background: 'rgba(255,255,255,0.7)',
                                borderRadius: '8px',
                                padding: '8px',
                                marginBottom: '6px',
                                textAlign: 'center'
                              }}>
                                <div style={{ fontSize: '11px', color: '#4a90e2', fontFamily: 'monospace', letterSpacing: '1px' }}>
                                  {wordInfo.expected_phonemes || '—'}
                                </div>
                              </div>

                              {/* IPA */}
                              <div style={{
                                fontSize: '12px',
                                color: '#4a90e2',
                                fontFamily: 'serif',
                                marginBottom: '4px'
                              }}>
                                {wordInfo.ipa || ''}
                              </div>

                              {/* Syllable breakdown */}
                              <div style={{
                                fontSize: '10px',
                                color: '#4a90e2',
                                fontFamily: 'monospace'
                              }}>
                                {wordInfo.syllable_breakdown || wordInfo.word}
                              </div>



                              {/* Feedback for errors */}
                              {!wordInfo.is_correct && (
                                <div style={{
                                  marginTop: '8px',
                                  padding: '6px',
                                  background: 'rgba(255,255,255,0.8)',
                                  borderRadius: '6px',
                                  fontSize: '9px',
                                  textAlign: 'left',
                                  color: '#495057'
                                }}>
                                  {wordInfo.transcribed_as && wordInfo.transcribed_as !== wordInfo.word && (
                                    <div style={{ marginBottom: '2px' }}>
                                      <span style={{ color: '#dc3545' }}>Heard:</span> "{wordInfo.transcribed_as}"
                                    </div>
                                  )}
                                  {wordInfo.feedback && (
                                    <div style={{ color: '#4a90e2' }}>
                                      💡 {wordInfo.feedback}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Timing Comparison Section - NEW */}
                  {result.timing_comparison && result.timing_comparison.words && result.timing_comparison.words.length > 0 && (
                    <div className="chat-message ai">
                      <div className="message-content" style={{
                        background: 'linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%)',
                        border: '1px solid rgba(74, 144, 226, 0.2)',
                        borderTop: '4px solid #4a90e2'
                      }}>
                        {/* Header */}
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
                            <i className="fas fa-clock" style={{ color: 'white', fontSize: '18px' }}></i>
                          </div>
                          <div>
                            <strong style={{ color: '#2c3e50', fontSize: '16px' }}>Timing Comparison</strong>
                            <div style={{ fontSize: '11px', color: '#6c757d' }}>Your pace vs Native Speaker</div>
                          </div>
                          {/* Summary badges */}
                          <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                            <span style={{
                              background: '#28a745',
                              color: 'white',
                              padding: '4px 10px',
                              borderRadius: '12px',
                              fontSize: '11px',
                              fontWeight: '600'
                            }}>
                              ✓ {result.timing_comparison.on_time_count} On Time
                            </span>
                            <span style={{
                              background: '#ffc107',
                              color: '#856404',
                              padding: '4px 10px',
                              borderRadius: '12px',
                              fontSize: '11px',
                              fontWeight: '600'
                            }}>
                              ⚡ {result.timing_comparison.early_count} Early
                            </span>
                            <span style={{
                              background: '#dc3545',
                              color: 'white',
                              padding: '4px 10px',
                              borderRadius: '12px',
                              fontSize: '11px',
                              fontWeight: '600'
                            }}>
                              🐢 {result.timing_comparison.late_count} Late
                            </span>
                          </div>
                        </div>

                        {/* Overall Timing Summary */}
                        <div style={{
                          background: result.timing_comparison.total_difference_ms <= 200
                            ? 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)'
                            : result.timing_comparison.total_difference_ms > 0
                              ? 'linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%)'
                              : 'linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%)',
                          borderRadius: '10px',
                          padding: '15px',
                          marginBottom: '20px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '15px'
                        }}>
                          <div style={{
                            fontSize: '28px',
                            fontWeight: 'bold',
                            color: result.timing_comparison.total_difference_ms <= 200 ? '#155724' :
                              result.timing_comparison.total_difference_ms > 0 ? '#721c24' : '#856404'
                          }}>
                            {result.timing_comparison.total_difference_ms > 0 ? '+' : ''}
                            {result.timing_comparison.total_difference_ms}ms
                          </div>
                          <div>
                            <div style={{ fontWeight: '600', color: '#2c3e50' }}>
                              {result.timing_comparison.summary}
                            </div>
                            <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '4px' }}>
                              Native: {result.timing_comparison.total_native_ms}ms |
                              You: {result.timing_comparison.total_user_ms}ms
                            </div>
                          </div>
                        </div>

                        {/* Word-by-Word Timing Grid */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                          {result.timing_comparison.words.map((wordTiming, wtIdx) => {
                            const statusColor = wordTiming.timing_status === 'on_time' ? '#28a745' :
                              wordTiming.timing_status === 'early' ? '#ffc107' : '#dc3545';
                            const statusBg = wordTiming.timing_status === 'on_time' ? '#d4edda' :
                              wordTiming.timing_status === 'early' ? '#fff3cd' : '#f8d7da';

                            return (
                              <div key={wtIdx} style={{
                                background: 'white',
                                border: `2px solid ${statusColor}`,
                                borderRadius: '12px',
                                padding: '12px',
                                minWidth: '130px',
                                boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                              }}>
                                {/* Word header */}
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  marginBottom: '10px'
                                }}>
                                  <span style={{ fontWeight: 'bold', fontSize: '14px', color: '#2c3e50' }}>
                                    {wordTiming.word}
                                  </span>
                                  <span style={{
                                    background: statusColor,
                                    color: wordTiming.timing_status === 'early' ? '#856404' : 'white',
                                    padding: '2px 6px',
                                    borderRadius: '8px',
                                    fontSize: '9px',
                                    fontWeight: 'bold'
                                  }}>
                                    {wordTiming.timing_status === 'on_time' ? '✓' :
                                      wordTiming.timing_status === 'early' ? '⚡' : '🐢'}
                                  </span>
                                </div>

                                {/* Timing bars */}
                                <div style={{ marginBottom: '8px' }}>
                                  {/* Native timing bar */}
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                    <span style={{ fontSize: '9px', color: '#28a745', width: '40px' }}>Native:</span>
                                    <div style={{
                                      flex: 1,
                                      height: '6px',
                                      background: '#e9ecef',
                                      borderRadius: '3px',
                                      overflow: 'hidden'
                                    }}>
                                      <div style={{
                                        width: '100%',
                                        height: '100%',
                                        background: '#28a745',
                                        borderRadius: '3px'
                                      }}></div>
                                    </div>
                                    <span style={{ fontSize: '9px', color: '#28a745', minWidth: '35px' }}>
                                      {wordTiming.native_duration_ms}ms
                                    </span>
                                  </div>
                                  {/* User timing bar */}
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span style={{ fontSize: '9px', color: '#4a90e2', width: '40px' }}>You:</span>
                                    <div style={{
                                      flex: 1,
                                      height: '6px',
                                      background: '#e9ecef',
                                      borderRadius: '3px',
                                      overflow: 'hidden'
                                    }}>
                                      <div style={{
                                        width: `${Math.min(100, (wordTiming.user_duration_ms / wordTiming.native_duration_ms) * 100)}%`,
                                        height: '100%',
                                        background: statusColor,
                                        borderRadius: '3px'
                                      }}></div>
                                    </div>
                                    <span style={{ fontSize: '9px', color: statusColor, minWidth: '35px' }}>
                                      {wordTiming.user_duration_ms}ms
                                    </span>
                                  </div>
                                </div>

                                {/* Timing difference label */}
                                <div style={{
                                  background: statusBg,
                                  padding: '4px 8px',
                                  borderRadius: '6px',
                                  textAlign: 'center',
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  color: wordTiming.timing_status === 'on_time' ? '#155724' :
                                    wordTiming.timing_status === 'early' ? '#856404' : '#721c24'
                                }}>
                                  {wordTiming.timing_label}
                                </div>

                                {/* Extra/Missing sounds alerts */}
                                {(wordTiming.extra_sounds.length > 0 || wordTiming.missing_sounds.length > 0) && (
                                  <div style={{ marginTop: '8px' }}>
                                    {wordTiming.extra_sounds.map((es, esIdx) => (
                                      <div key={esIdx} style={{
                                        fontSize: '10px',
                                        color: '#dc3545',
                                        background: '#f8d7da',
                                        padding: '2px 6px',
                                        borderRadius: '4px',
                                        marginBottom: '2px'
                                      }}>
                                        ⚠️ {es}
                                      </div>
                                    ))}
                                    {wordTiming.missing_sounds.map((ms, msIdx) => (
                                      <div key={msIdx} style={{
                                        fontSize: '10px',
                                        color: '#856404',
                                        background: '#fff3cd',
                                        padding: '2px 6px',
                                        borderRadius: '4px',
                                        marginBottom: '2px'
                                      }}>
                                        ⚠️ {ms}
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Syllable info */}
                                <div style={{ marginTop: '6px', fontSize: '10px', color: '#6c757d', textAlign: 'center' }}>
                                  {wordTiming.syllable_count} syllable{wordTiming.syllable_count > 1 ? 's' : ''}
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* Mistake Summary */}
                        {result.timing_comparison.words.filter(w => !w.is_correct).length > 0 && (
                          <div style={{
                            marginTop: '20px',
                            background: 'linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%)',
                            borderRadius: '10px',
                            padding: '15px',
                            border: '1px solid #f5c6cb'
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                              <i className="fas fa-exclamation-triangle" style={{ color: '#721c24', fontSize: '16px' }}></i>
                              <strong style={{ color: '#721c24', fontSize: '14px' }}>Mistakes to Fix</strong>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                              {result.timing_comparison.words.filter(w => !w.is_correct).map((errorWord, ewIdx) => (
                                <div key={ewIdx} style={{
                                  background: 'white',
                                  padding: '8px 12px',
                                  borderRadius: '8px',
                                  border: '1px solid #dc3545'
                                }}>
                                  <div style={{ fontWeight: 'bold', color: '#dc3545', marginBottom: '4px' }}>
                                    {errorWord.word}
                                    {errorWord.ipa && <span style={{ fontSize: '11px', color: '#4a90e2', marginLeft: '5px' }}>{errorWord.ipa}</span>}
                                  </div>
                                  {errorWord.feedback && (
                                    <div style={{ fontSize: '11px', color: '#495057' }}>
                                      💡 {errorWord.feedback}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Play buttons - Your voice and Native speaker (Male/Female) */}
                  <div className="chat-message user">
                    <div className="message-content" style={{ background: 'transparent', padding: '0', boxShadow: 'none', border: 'none', display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      {/* Your Voice button */}
                      <button
                        className={`pm-audio-btn pm-audio-btn-user ${playingAudioId === `user-${result.id}` ? 'playing' : ''}`}
                        onClick={() => {
                          const audioId = `user-${result.id}`;
                          if (playingAudioId === audioId) {
                            if (currentAudioRef.current) {
                              currentAudioRef.current.pause();
                              currentAudioRef.current = null;
                            }
                            setPlayingAudioId(null);
                          } else {
                            if (currentAudioRef.current) {
                              currentAudioRef.current.pause();
                            }
                            const audio = new Audio(result.audioUrl);
                            currentAudioRef.current = audio;
                            audio.onended = () => setPlayingAudioId(null);
                            audio.play();
                            setPlayingAudioId(audioId);
                          }
                        }}
                      >
                        <i className={`fas ${playingAudioId === `user-${result.id}` ? 'fa-stop' : 'fa-user-circle'}`}></i>
                        {playingAudioId === `user-${result.id}` ? 'Stop' : 'Your Voice'}
                      </button>

                      {/* Native Male button */}
                      <button
                        className={`pm-audio-btn pm-audio-btn-male ${playingAudioId === `native-male-${result.id}` ? 'playing' : ''}`}
                        onClick={() => {
                          const audioId = `native-male-${result.id}`;
                          if (playingAudioId === audioId) {
                            if (currentAudioRef.current) {
                              currentAudioRef.current.pause();
                              currentAudioRef.current = null;
                            }
                            setPlayingAudioId(null);
                          } else {
                            if (currentAudioRef.current) {
                              currentAudioRef.current.pause();
                            }
                            if (result.session_id) {
                              const audio = new Audio(`http://localhost:8000/api/accent/audio/public/${result.session_id}/corrected`);
                              currentAudioRef.current = audio;
                              audio.onended = () => setPlayingAudioId(null);
                              audio.play();
                              setPlayingAudioId(audioId);
                            }
                          }
                        }}
                      >
                        <i className={`fas ${playingAudioId === `native-male-${result.id}` ? 'fa-stop' : 'fa-male'}`}></i>
                        {playingAudioId === `native-male-${result.id}` ? 'Stop' : 'Native Male'}
                      </button>

                      {/* Native Female button */}
                      <button
                        className={`pm-audio-btn pm-audio-btn-female ${playingAudioId === `native-female-${result.id}` ? 'playing' : ''}`}
                        onClick={() => {
                          const audioId = `native-female-${result.id}`;
                          if (playingAudioId === audioId) {
                            if (currentAudioRef.current) {
                              currentAudioRef.current.pause();
                              currentAudioRef.current = null;
                            }
                            setPlayingAudioId(null);
                          } else {
                            if (currentAudioRef.current) {
                              currentAudioRef.current.pause();
                            }
                            const utterance = new SpeechSynthesisUtterance(result.transcribed_text || selectedSentence?.text || '');
                            const voices = window.speechSynthesis.getVoices();
                            const femaleVoice = voices.find(v =>
                              v.name.toLowerCase().includes('female') ||
                              v.name.toLowerCase().includes('zira') ||
                              v.name.toLowerCase().includes('susan') ||
                              v.name.toLowerCase().includes('hazel') ||
                              (v.lang.startsWith('en') && !v.name.toLowerCase().includes('david'))
                            );
                            if (femaleVoice) utterance.voice = femaleVoice;
                            utterance.lang = 'en-GB';
                            utterance.rate = 0.9;
                            utterance.onend = () => setPlayingAudioId(null);
                            window.speechSynthesis.cancel();
                            window.speechSynthesis.speak(utterance);
                            setPlayingAudioId(audioId);
                          }
                        }}
                      >
                        <i className={`fas ${playingAudioId === `native-female-${result.id}` ? 'fa-stop' : 'fa-female'}`}></i>
                        {playingAudioId === `native-female-${result.id}` ? 'Stop' : 'Native Female'}
                      </button>
                    </div>
                  </div>

                  {/* Advanced Analysis Section */}
                  {result.advanced_analysis && (
                    <div className="chat-message ai">
                      <div className="pm-advanced-section">
                        <div className="pm-section-header">
                          <div className="pm-section-icon">
                            <i className="fas fa-chart-line"></i>
                          </div>
                          <span className="pm-section-title">Advanced Analysis</span>
                        </div>

                        {/* Score Summary */}
                        <div className="pm-score-cards">
                          <div className="pm-score-card" style={{ background: `linear-gradient(135deg, ${THEME.primary} 0%, ${THEME.primaryDark} 100%)` }}>
                            <i className="fas fa-spell-check"></i>
                            <div className="score">{result.advanced_analysis.phoneme_score}%</div>
                            <div className="label">Phoneme Match</div>
                          </div>
                          <div className="pm-score-card" style={{ background: `linear-gradient(135deg, ${THEME.success} 0%, ${THEME.successDark} 100%)` }}>
                            <i className="fas fa-music"></i>
                            <div className="score">{result.advanced_analysis.prosody_score}%</div>
                            <div className="label">Prosody</div>
                          </div>
                          <div className="pm-score-card" style={{ background: `linear-gradient(135deg, ${THEME.primary} 0%, ${THEME.primaryDark} 100%)` }}>
                            <i className="fas fa-wave-square"></i>
                            <div className="score">{result.advanced_analysis.rhythm_similarity}%</div>
                            <div className="label">Rhythm</div>
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

                        {/* Voice Feature Comparison - Your Voice vs Native */}
                        {result.advanced_analysis.voice_comparison && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                              <i className="fas fa-microphone-alt" style={{ color: '#4a90e2', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Voice Feature Comparison</span>
                            </div>

                            {/* Side by side comparison cards */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                              {/* Your Voice */}
                              <div style={{
                                background: 'linear-gradient(135deg, #e7f3ff 0%, #dbeafe 100%)',
                                borderRadius: '12px',
                                padding: '15px',
                                border: '2px solid #4a90e2'
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                                  <i className="fas fa-user" style={{ color: '#4a90e2' }}></i>
                                  <strong style={{ color: '#4a90e2' }}>Your Voice</strong>
                                </div>
                                <div style={{ display: 'grid', gap: '8px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Duration:</span>
                                    <strong style={{ color: '#2c3e50' }}>{result.advanced_analysis.voice_comparison.user_voice?.duration?.toFixed(2) || 0}s</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Pitch (avg):</span>
                                    <strong style={{ color: '#2c3e50' }}>{result.advanced_analysis.voice_comparison.user_voice?.pitch_mean?.toFixed(0) || 0} Hz</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Pitch (var):</span>
                                    <strong style={{ color: '#2c3e50' }}>±{result.advanced_analysis.voice_comparison.user_voice?.pitch_std?.toFixed(0) || 0} Hz</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Energy:</span>
                                    <strong style={{ color: '#2c3e50' }}>{(result.advanced_analysis.voice_comparison.user_voice?.energy_mean * 100)?.toFixed(1) || 0}</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Tempo:</span>
                                    <strong style={{ color: '#2c3e50' }}>{result.advanced_analysis.voice_comparison.user_voice?.tempo?.toFixed(0) || 0} BPM</strong>
                                  </div>
                                </div>
                              </div>

                              {/* Native Voice */}
                              <div style={{
                                background: 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)',
                                borderRadius: '12px',
                                padding: '15px',
                                border: '2px solid #28a745'
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                                  <i className="fas fa-crown" style={{ color: '#28a745' }}></i>
                                  <strong style={{ color: '#28a745' }}>Native Voice</strong>
                                </div>
                                <div style={{ display: 'grid', gap: '8px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Duration:</span>
                                    <strong style={{ color: '#2c3e50' }}>{result.advanced_analysis.voice_comparison.native_voice?.duration?.toFixed(2) || 0}s</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Pitch (avg):</span>
                                    <strong style={{ color: '#2c3e50' }}>{result.advanced_analysis.voice_comparison.native_voice?.pitch_mean?.toFixed(0) || 0} Hz</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Pitch (var):</span>
                                    <strong style={{ color: '#2c3e50' }}>±{result.advanced_analysis.voice_comparison.native_voice?.pitch_std?.toFixed(0) || 0} Hz</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Energy:</span>
                                    <strong style={{ color: '#2c3e50' }}>{(result.advanced_analysis.voice_comparison.native_voice?.energy_mean * 100)?.toFixed(1) || 0}</strong>
                                  </div>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                    <span style={{ color: '#6c757d' }}>Tempo:</span>
                                    <strong style={{ color: '#2c3e50' }}>{result.advanced_analysis.voice_comparison.native_voice?.tempo?.toFixed(0) || 0} BPM</strong>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Similarity Bars */}
                            {result.advanced_analysis.voice_comparison.comparison && (
                              <div style={{ marginTop: '15px', background: 'white', borderRadius: '10px', padding: '15px', border: '1px solid #e9ecef' }}>
                                <div style={{ fontSize: '12px', fontWeight: '600', color: '#2c3e50', marginBottom: '10px' }}>Feature Similarity</div>
                                {['pitch_similarity', 'rhythm_similarity', 'duration_similarity', 'energy_similarity', 'spectral_similarity'].map((key) => {
                                  const value = result.advanced_analysis.voice_comparison.comparison[key] || 0;
                                  const label = key.replace('_similarity', '').replace('_', ' ');
                                  const color = value >= 80 ? '#28a745' : value >= 60 ? '#ffc107' : '#dc3545';
                                  return (
                                    <div key={key} style={{ marginBottom: '8px' }}>
                                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '3px' }}>
                                        <span style={{ textTransform: 'capitalize' }}>{label}</span>
                                        <span style={{ fontWeight: '600', color }}>{value}%</span>
                                      </div>
                                      <div style={{ height: '6px', background: '#e9ecef', borderRadius: '3px', overflow: 'hidden' }}>
                                        <div style={{ width: `${value}%`, height: '100%', background: color, borderRadius: '3px', transition: 'width 0.5s ease' }}></div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Real Acoustic Signal Analysis - NEW */}
                        {result.advanced_analysis.real_acoustic_analysis && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                              <i className="fas fa-wave-square" style={{ color: '#6f42c1', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Real Signal Analysis</span>
                              <span style={{
                                background: '#28a745',
                                color: 'white',
                                fontSize: '9px',
                                padding: '2px 6px',
                                borderRadius: '8px',
                                marginLeft: '8px'
                              }}>SIGNAL-BASED</span>
                            </div>

                            {/* Overall Signal Score */}
                            <div style={{
                              background: 'linear-gradient(135deg, #6f42c1 0%, #9b59b6 100%)',
                              borderRadius: '12px',
                              padding: '15px 20px',
                              marginBottom: '15px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              color: 'white'
                            }}>
                              <div>
                                <div style={{ fontSize: '12px', opacity: 0.9 }}>Overall Signal Score</div>
                                <div style={{ fontSize: '28px', fontWeight: 'bold' }}>
                                  {result.advanced_analysis.real_acoustic_analysis.overall_score}%
                                </div>
                              </div>
                              <div style={{ textAlign: 'right', fontSize: '11px', opacity: 0.9 }}>
                                <div>✓ MFCC Spectral Analysis</div>
                                <div>✓ F0 Pitch (Parselmouth)</div>
                                <div>✓ DTW Comparison</div>
                              </div>
                            </div>

                            {/* Signal Analysis Scores Grid */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
                              {result.advanced_analysis.real_acoustic_analysis.scores &&
                                Object.entries(result.advanced_analysis.real_acoustic_analysis.scores).map(([key, value]) => {
                                  const labels = {
                                    prosody: { name: 'Prosody (MFCC)', icon: 'fa-music' },
                                    intonation: { name: 'Intonation (F0)', icon: 'fa-chart-line' },
                                    stress: { name: 'Stress (RMS)', icon: 'fa-bolt' },
                                    rhythm_timing: { name: 'Rhythm', icon: 'fa-clock' },
                                    connected_speech: { name: 'Connected', icon: 'fa-link' }
                                  };
                                  const info = labels[key] || { name: key, icon: 'fa-chart-bar' };
                                  const color = value >= 80 ? '#28a745' : value >= 60 ? '#ffc107' : '#dc3545';

                                  return (
                                    <div key={key} style={{
                                      background: 'white',
                                      borderRadius: '10px',
                                      padding: '12px',
                                      textAlign: 'center',
                                      border: '1px solid #e9ecef',
                                      boxShadow: '0 2px 6px rgba(0,0,0,0.05)'
                                    }}>
                                      <i className={`fas ${info.icon}`} style={{ color: '#6f42c1', fontSize: '16px', marginBottom: '6px' }}></i>
                                      <div style={{ fontSize: '20px', fontWeight: 'bold', color }}>{value}%</div>
                                      <div style={{ fontSize: '9px', color: '#6c757d', marginTop: '4px' }}>{info.name}</div>
                                    </div>
                                  );
                                })}
                            </div>

                            {/* Pitch Analysis Details */}
                            {result.advanced_analysis.real_acoustic_analysis.pitch_analysis && (
                              <div style={{ marginTop: '15px', background: '#f8f9fa', borderRadius: '10px', padding: '12px' }}>
                                <div style={{ fontSize: '11px', fontWeight: '600', color: '#2c3e50', marginBottom: '8px' }}>
                                  <i className="fas fa-chart-area" style={{ marginRight: '6px', color: '#6f42c1' }}></i>
                                  Pitch (F0) Comparison
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '11px' }}>
                                  <div>
                                    <span style={{ color: '#6c757d' }}>Your Pitch:</span>
                                    <strong style={{ marginLeft: '5px' }}>
                                      {result.advanced_analysis.real_acoustic_analysis.pitch_analysis.user_pitch?.pitch_mean?.toFixed(0) || 0} Hz
                                    </strong>
                                    <span style={{ color: '#adb5bd', marginLeft: '3px' }}>
                                      (±{result.advanced_analysis.real_acoustic_analysis.pitch_analysis.user_pitch?.pitch_std?.toFixed(0) || 0})
                                    </span>
                                  </div>
                                  <div>
                                    <span style={{ color: '#6c757d' }}>Native Pitch:</span>
                                    <strong style={{ marginLeft: '5px' }}>
                                      {result.advanced_analysis.real_acoustic_analysis.pitch_analysis.native_pitch?.pitch_mean?.toFixed(0) || 0} Hz
                                    </strong>
                                    <span style={{ color: '#adb5bd', marginLeft: '3px' }}>
                                      (±{result.advanced_analysis.real_acoustic_analysis.pitch_analysis.native_pitch?.pitch_std?.toFixed(0) || 0})
                                    </span>
                                  </div>
                                </div>
                                <div style={{ marginTop: '8px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginBottom: '3px' }}>
                                    <span>DTW Similarity</span>
                                    <span style={{ fontWeight: '600', color: '#6f42c1' }}>
                                      {result.advanced_analysis.real_acoustic_analysis.pitch_analysis.similarity?.toFixed(1) || 0}%
                                    </span>
                                  </div>
                                  <div style={{ height: '6px', background: '#e9ecef', borderRadius: '3px', overflow: 'hidden' }}>
                                    <div style={{
                                      width: `${result.advanced_analysis.real_acoustic_analysis.pitch_analysis.similarity || 0}%`,
                                      height: '100%',
                                      background: 'linear-gradient(90deg, #6f42c1, #9b59b6)',
                                      borderRadius: '3px'
                                    }}></div>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Feature Availability */}
                            {result.advanced_analysis.real_acoustic_analysis.features_available && (
                              <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                {Object.entries(result.advanced_analysis.real_acoustic_analysis.features_available).map(([lib, available]) => (
                                  <span key={lib} style={{
                                    background: available ? '#d4edda' : '#f8d7da',
                                    color: available ? '#155724' : '#721c24',
                                    fontSize: '9px',
                                    padding: '3px 8px',
                                    borderRadius: '10px'
                                  }}>
                                    {available ? '✓' : '✗'} {lib}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Real Phoneme Alignment - NEW: Shows ACTUAL phonemes from audio */}
                        {result.advanced_analysis.real_phoneme_alignment && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                              <i className="fas fa-check-double" style={{ color: THEME.primary, fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Real Phoneme Alignment</span>
                              <span style={{ background: THEME.success, color: 'white', fontSize: '9px', padding: '2px 6px', borderRadius: '8px' }}>AUDIO</span>
                            </div>

                            {/* Score Card */}
                            <div style={{
                              background: `linear-gradient(135deg, ${result.advanced_analysis.real_phoneme_alignment.score >= 80 ? '#28a745' : result.advanced_analysis.real_phoneme_alignment.score >= 60 ? '#ffc107' : '#dc3545'} 0%, ${result.advanced_analysis.real_phoneme_alignment.score >= 80 ? '#20c997' : result.advanced_analysis.real_phoneme_alignment.score >= 60 ? '#fd7e14' : '#c82333'} 100%)`,
                              color: 'white',
                              borderRadius: '12px',
                              padding: '15px',
                              marginBottom: '12px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}>
                              <div>
                                <div style={{ fontSize: '28px', fontWeight: 'bold' }}>
                                  {result.advanced_analysis.real_phoneme_alignment.score}%
                                </div>
                                <div style={{ fontSize: '11px', opacity: 0.9 }}>Real Phoneme Match</div>
                              </div>
                              <div style={{ textAlign: 'right', fontSize: '12px' }}>
                                <div>✓ {result.advanced_analysis.real_phoneme_alignment.matches} matches</div>
                                <div>✗ {result.advanced_analysis.real_phoneme_alignment.mismatches} mismatches</div>
                              </div>
                            </div>

                            {/* User vs Target Phonemes */}
                            <div style={{ background: '#f8f9fa', borderRadius: '10px', padding: '15px', border: '1px solid #e9ecef' }}>
                              {/* Target Row */}
                              <div style={{ marginBottom: '12px' }}>
                                <div style={{ fontSize: '11px', color: THEME.success, fontWeight: '600', marginBottom: '6px' }}>
                                  <i className="fas fa-bullseye" style={{ marginRight: '5px' }}></i>TARGET (Expected)
                                </div>
                                <div style={{
                                  fontFamily: 'monospace',
                                  fontSize: '16px',
                                  background: 'white',
                                  padding: '10px',
                                  borderRadius: '8px',
                                  border: `2px solid ${THEME.success}`,
                                  letterSpacing: '2px'
                                }}>
                                  {result.advanced_analysis.real_phoneme_alignment.target_phoneme_string || 'N/A'}
                                </div>
                              </div>

                              {/* User Row */}
                              <div style={{ marginBottom: '12px' }}>
                                <div style={{ fontSize: '11px', color: THEME.primary, fontWeight: '600', marginBottom: '6px' }}>
                                  <i className="fas fa-microphone" style={{ marginRight: '5px' }}></i>YOUR VOICE (Detected)
                                </div>
                                <div style={{
                                  fontFamily: 'monospace',
                                  fontSize: '16px',
                                  background: 'white',
                                  padding: '10px',
                                  borderRadius: '8px',
                                  border: `2px solid ${THEME.primary}`,
                                  letterSpacing: '2px'
                                }}>
                                  {result.advanced_analysis.real_phoneme_alignment.user_phoneme_string || 'N/A'}
                                </div>
                              </div>

                              {/* Alignment Details */}
                              {result.advanced_analysis.real_phoneme_alignment.alignment?.alignments && (
                                <div style={{ marginTop: '15px' }}>
                                  <div style={{ fontSize: '11px', fontWeight: '600', color: '#495057', marginBottom: '8px' }}>
                                    <i className="fas fa-align-left" style={{ marginRight: '5px' }}></i>PHONEME-BY-PHONEME
                                  </div>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                    {result.advanced_analysis.real_phoneme_alignment.alignment.alignments.map((align, idx) => (
                                      <div key={idx} style={{
                                        padding: '8px 10px',
                                        borderRadius: '8px',
                                        background: align.match ? '#d4edda' : '#f8d7da',
                                        border: `1px solid ${align.match ? '#c3e6cb' : '#f5c6cb'}`,
                                        textAlign: 'center',
                                        minWidth: '55px'
                                      }}>
                                        {/* Per-phoneme score */}
                                        <div style={{
                                          fontSize: '10px',
                                          fontWeight: 'bold',
                                          color: align.match ? '#28a745' : '#dc3545',
                                          marginBottom: '3px'
                                        }}>
                                          {align.match ? '100%' : '0%'}
                                        </div>
                                        <div style={{
                                          fontSize: '14px',
                                          fontWeight: 'bold',
                                          color: align.match ? THEME.success : THEME.danger
                                        }}>
                                          {align.user_phoneme}
                                        </div>
                                        <div style={{ fontSize: '9px', color: '#6c757d', margin: '2px 0' }}>
                                          {align.match ? '✓' : '↓'}
                                        </div>
                                        <div style={{
                                          fontSize: '12px',
                                          color: '#495057'
                                        }}>
                                          {align.target_phoneme}
                                        </div>
                                        {!align.match && align.error_type && (
                                          <div style={{
                                            fontSize: '8px',
                                            color: THEME.danger,
                                            marginTop: '3px'
                                          }}>
                                            {align.error_type.replace('_', ' ')}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Per-Word Analysis Cards */}
                              {result.advanced_analysis.real_phoneme_alignment.word_analyses &&
                                result.advanced_analysis.real_phoneme_alignment.word_analyses.length > 0 && (
                                  <div style={{ marginTop: '15px' }}>
                                    <div style={{ fontSize: '11px', fontWeight: '600', color: '#495057', marginBottom: '8px' }}>
                                      <i className="fas fa-th-list" style={{ marginRight: '5px' }}></i>
                                      PER-WORD ANALYSIS
                                    </div>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
                                      {result.advanced_analysis.real_phoneme_alignment.word_analyses.map((wa, idx) => (
                                        <div key={idx} style={{
                                          background: wa.is_correct ? '#d4edda' : '#f8d7da',
                                          borderRadius: '10px',
                                          padding: '12px',
                                          border: `2px solid ${wa.is_correct ? '#28a745' : '#dc3545'}`
                                        }}>
                                          {/* Word header */}
                                          <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            marginBottom: '8px'
                                          }}>
                                            <span style={{
                                              fontWeight: 'bold',
                                              fontSize: '14px',
                                              color: '#2c3e50'
                                            }}>
                                              {wa.word}
                                            </span>
                                            <span style={{
                                              fontSize: '12px',
                                              fontWeight: 'bold',
                                              color: wa.is_correct ? '#28a745' : '#dc3545'
                                            }}>
                                              {wa.phoneme_score}%
                                            </span>
                                          </div>

                                          {/* Target phonemes */}
                                          <div style={{ fontSize: '10px', color: '#6c757d', marginBottom: '2px' }}>
                                            TARGET:
                                          </div>
                                          <div style={{
                                            fontFamily: 'monospace',
                                            fontSize: '11px',
                                            color: THEME.success,
                                            marginBottom: '6px'
                                          }}>
                                            {wa.target_phoneme_string || '-'}
                                          </div>

                                          {/* Detected phonemes */}
                                          <div style={{ fontSize: '10px', color: '#6c757d', marginBottom: '2px' }}>
                                            DETECTED:
                                          </div>
                                          <div style={{
                                            fontFamily: 'monospace',
                                            fontSize: '11px',
                                            color: wa.is_correct ? THEME.success : THEME.danger
                                          }}>
                                            {wa.detected_phoneme_string || '-'}
                                          </div>

                                          {/* Error stats */}
                                          {(wa.substitution_count > 0 || wa.insertion_count > 0 || wa.deletion_count > 0) && (
                                            <div style={{
                                              marginTop: '8px',
                                              fontSize: '9px',
                                              display: 'flex',
                                              gap: '6px',
                                              flexWrap: 'wrap'
                                            }}>
                                              {wa.substitution_count > 0 && (
                                                <span style={{
                                                  background: '#ffc107',
                                                  color: '#212529',
                                                  padding: '2px 5px',
                                                  borderRadius: '4px'
                                                }}>
                                                  {wa.substitution_count} sub
                                                </span>
                                              )}
                                              {wa.insertion_count > 0 && (
                                                <span style={{
                                                  background: '#17a2b8',
                                                  color: 'white',
                                                  padding: '2px 5px',
                                                  borderRadius: '4px'
                                                }}>
                                                  {wa.insertion_count} ins
                                                </span>
                                              )}
                                              {wa.deletion_count > 0 && (
                                                <span style={{
                                                  background: '#dc3545',
                                                  color: 'white',
                                                  padding: '2px 5px',
                                                  borderRadius: '4px'
                                                }}>
                                                  {wa.deletion_count} del
                                                </span>
                                              )}
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                              {/* ML Prosody Scores */}
                              {result.advanced_analysis.real_phoneme_alignment.prosody_scores && (
                                <div style={{ marginTop: '15px' }}>
                                  <div style={{ fontSize: '11px', fontWeight: '600', color: '#495057', marginBottom: '8px' }}>
                                    <i className="fas fa-chart-line" style={{ marginRight: '5px' }}></i>
                                    ML PROSODY ANALYSIS
                                  </div>
                                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                                    {['fluency', 'stress', 'rhythm', 'intonation'].map((key) => {
                                      const score = result.advanced_analysis.real_phoneme_alignment.prosody_scores[key] || 0;
                                      return (
                                        <div key={key} style={{
                                          background: `linear-gradient(135deg, ${score >= 70 ? '#d4edda' : score >= 50 ? '#fff3cd' : '#f8d7da'} 0%, white 100%)`,
                                          borderRadius: '10px',
                                          padding: '12px',
                                          textAlign: 'center',
                                          border: `2px solid ${score >= 70 ? '#28a745' : score >= 50 ? '#ffc107' : '#dc3545'}`
                                        }}>
                                          <div style={{ fontSize: '20px', fontWeight: 'bold', color: score >= 70 ? '#28a745' : score >= 50 ? '#856404' : '#dc3545' }}>
                                            {Math.round(score)}%
                                          </div>
                                          <div style={{ fontSize: '10px', color: '#6c757d', textTransform: 'capitalize', marginTop: '4px' }}>
                                            {key}
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </div>
                                  {/* Overall prosody */}
                                  <div style={{
                                    marginTop: '10px',
                                    padding: '10px',
                                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                    borderRadius: '8px',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                  }}>
                                    <span style={{ color: 'white', fontWeight: '600', fontSize: '12px' }}>
                                      Overall Prosody
                                    </span>
                                    <span style={{ color: 'white', fontWeight: 'bold', fontSize: '18px' }}>
                                      {Math.round(result.advanced_analysis.real_phoneme_alignment.prosody_scores.overall || 0)}%
                                    </span>
                                  </div>
                                </div>
                              )}

                              {/* Method indicator */}
                              <div style={{ marginTop: '12px', fontSize: '10px', color: '#6c757d', textAlign: 'right' }}>
                                <i className="fas fa-info-circle" style={{ marginRight: '4px' }}></i>
                                Method: {result.advanced_analysis.real_phoneme_alignment.method}
                                {result.advanced_analysis.real_phoneme_alignment.substitutions > 0 && (
                                  <span style={{ marginLeft: '10px', color: '#ffc107' }}>
                                    {result.advanced_analysis.real_phoneme_alignment.substitutions} substitutions
                                  </span>
                                )}
                                {result.advanced_analysis.real_phoneme_alignment.insertions > 0 && (
                                  <span style={{ marginLeft: '10px', color: '#17a2b8' }}>
                                    {result.advanced_analysis.real_phoneme_alignment.insertions} insertions
                                  </span>
                                )}
                                {result.advanced_analysis.real_phoneme_alignment.deletions > 0 && (
                                  <span style={{ marginLeft: '10px', color: '#dc3545' }}>
                                    {result.advanced_analysis.real_phoneme_alignment.deletions} deletions
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* British English IPA - NEW */}
                        {result.advanced_analysis.british_phonemes && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                              <i className="fas fa-language" style={{ color: '#dc3545', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>British English IPA</span>
                              <span style={{ background: '#dc3545', color: 'white', fontSize: '9px', padding: '2px 6px', borderRadius: '8px' }}>UK</span>
                            </div>
                            <div style={{ background: '#fff5f5', borderRadius: '10px', padding: '12px', border: '1px solid #f5c6cb' }}>
                              <div style={{ fontSize: '18px', fontFamily: 'Doulos SIL, Gentium, serif', letterSpacing: '1px', color: '#2c3e50' }}>
                                /{result.advanced_analysis.british_phonemes.combined_ipa}/
                              </div>
                              <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {result.advanced_analysis.british_phonemes.words?.map((w, i) => (
                                  <div key={i} style={{
                                    background: 'white',
                                    padding: '6px 10px',
                                    borderRadius: '6px',
                                    fontSize: '11px',
                                    border: '1px solid #e9ecef'
                                  }}>
                                    <div style={{ fontWeight: '600' }}>{w.word}</div>
                                    <div style={{ color: '#dc3545', fontFamily: 'Doulos SIL, Gentium, serif' }}>{w.british_ipa}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Stress Pattern Analysis - NEW */}
                        {result.advanced_analysis.stress_analysis && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                              <i className="fas fa-arrows-alt-v" style={{ color: '#17a2b8', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Stress Patterns</span>
                            </div>
                            <div style={{ background: '#e7f5ff', borderRadius: '10px', padding: '12px', border: '1px solid #bee5eb' }}>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                {result.advanced_analysis.stress_analysis.words?.map((w, i) => (
                                  <div key={i} style={{
                                    background: 'white',
                                    padding: '8px 12px',
                                    borderRadius: '8px',
                                    textAlign: 'center',
                                    minWidth: '80px'
                                  }}>
                                    <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>{w.formatted}</div>
                                    <div style={{ fontSize: '10px', color: '#6c757d' }}>{w.syllable_count} syllables</div>
                                    <div style={{
                                      marginTop: '4px',
                                      fontSize: '12px',
                                      letterSpacing: '3px',
                                      color: '#17a2b8'
                                    }}>{w.stress_string}</div>
                                  </div>
                                ))}
                              </div>
                              <div style={{ marginTop: '10px', fontSize: '10px', color: '#6c757d' }}>
                                ˈ = primary stress &nbsp; ˌ = secondary stress &nbsp; · = unstressed
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Formant Analysis - NEW */}
                        {result.advanced_analysis.formant_analysis?.comparison && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                              <i className="fas fa-wave-square" style={{ color: '#6610f2', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Formant Analysis (Vowel Quality)</span>
                              <span style={{ fontSize: '10px', color: '#6c757d' }}>F1-F4</span>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                              {/* User Formants */}
                              <div style={{ background: '#e7f3ff', borderRadius: '10px', padding: '12px', border: '1px solid #c5dcf7' }}>
                                <div style={{ fontWeight: '600', color: '#4a90e2', marginBottom: '8px', fontSize: '12px' }}>
                                  <i className="fas fa-user" style={{ marginRight: '6px' }}></i>Your Formants
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '11px' }}>
                                  {['f1', 'f2', 'f3', 'f4'].map(f => (
                                    <div key={f} style={{ textAlign: 'center', background: 'white', padding: '6px', borderRadius: '6px' }}>
                                      <div style={{ fontWeight: '600', textTransform: 'uppercase' }}>{f}</div>
                                      <div>{result.advanced_analysis.formant_analysis.comparison?.user_formants?.[f] || 0} Hz</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                              {/* Native Formants */}
                              <div style={{ background: '#d4edda', borderRadius: '10px', padding: '12px', border: '1px solid #c3e6cb' }}>
                                <div style={{ fontWeight: '600', color: '#28a745', marginBottom: '8px', fontSize: '12px' }}>
                                  <i className="fas fa-crown" style={{ marginRight: '6px' }}></i>Native Formants
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', fontSize: '11px' }}>
                                  {['f1', 'f2', 'f3', 'f4'].map(f => (
                                    <div key={f} style={{ textAlign: 'center', background: 'white', padding: '6px', borderRadius: '6px' }}>
                                      <div style={{ fontWeight: '600', textTransform: 'uppercase' }}>{f}</div>
                                      <div>{result.advanced_analysis.formant_analysis.comparison?.native_formants?.[f] || 0} Hz</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                            {/* Formant Similarity */}
                            <div style={{ marginTop: '10px', background: 'white', borderRadius: '8px', padding: '10px', border: '1px solid #e9ecef' }}>
                              <div style={{ fontSize: '11px', fontWeight: '600', marginBottom: '6px' }}>Formant Similarity</div>
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                {['f1', 'f2', 'f3', 'f4'].map(f => {
                                  const sim = result.advanced_analysis.formant_analysis.comparison?.similarities?.[f] || 0;
                                  const color = sim >= 80 ? '#28a745' : sim >= 60 ? '#ffc107' : '#dc3545';
                                  return (
                                    <div key={f}>
                                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginBottom: '2px' }}>
                                        <span style={{ textTransform: 'uppercase' }}>{f}</span>
                                        <span style={{ fontWeight: '600', color }}>{sim.toFixed(0)}%</span>
                                      </div>
                                      <div style={{ height: '4px', background: '#e9ecef', borderRadius: '2px', overflow: 'hidden' }}>
                                        <div style={{ width: `${sim}%`, height: '100%', background: color }}></div>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Advanced Word-Level Phoneme Analysis - NEW */}
                        {result.advanced_analysis.advanced_sentence_analysis && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                              <i className="fas fa-microscope" style={{ color: '#fd7e14', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Word-Level Audio Analysis</span>
                              <span style={{ background: '#fd7e14', color: 'white', fontSize: '9px', padding: '2px 6px', borderRadius: '8px' }}>
                                {result.advanced_analysis.advanced_sentence_analysis.sentence_score}%
                              </span>
                            </div>

                            {/* Summary Stats */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '12px' }}>
                              <div style={{ background: '#fff3cd', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#856404' }}>
                                  {result.advanced_analysis.advanced_sentence_analysis.correct_words}/{result.advanced_analysis.advanced_sentence_analysis.word_count}
                                </div>
                                <div style={{ fontSize: '10px', color: '#856404' }}>Correct Words</div>
                              </div>
                              <div style={{ background: '#d4edda', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#155724' }}>
                                  {result.advanced_analysis.advanced_sentence_analysis.vowel_score}%
                                </div>
                                <div style={{ fontSize: '10px', color: '#155724' }}>Vowel Score</div>
                              </div>
                              <div style={{ background: '#cce5ff', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#004085' }}>
                                  {result.advanced_analysis.advanced_sentence_analysis.consonant_score}%
                                </div>
                                <div style={{ fontSize: '10px', color: '#004085' }}>Consonant Score</div>
                              </div>
                              <div style={{ background: '#f8d7da', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#721c24' }}>
                                  {result.advanced_analysis.advanced_sentence_analysis.total_vowel_errors + result.advanced_analysis.advanced_sentence_analysis.total_consonant_errors}
                                </div>
                                <div style={{ fontSize: '10px', color: '#721c24' }}>Total Errors</div>
                              </div>
                            </div>

                            {/* Word Results */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                              {result.advanced_analysis.advanced_sentence_analysis.results?.map((word, i) => {
                                const score = word.word_score || 0;
                                const bgColor = score >= 80 ? '#d4edda' : score >= 50 ? '#fff3cd' : '#f8d7da';
                                const borderColor = score >= 80 ? '#28a745' : score >= 50 ? '#ffc107' : '#dc3545';

                                return (
                                  <div key={i} style={{
                                    background: bgColor,
                                    border: `2px solid ${borderColor}`,
                                    borderRadius: '10px',
                                    padding: '10px 14px',
                                    minWidth: '100px',
                                    textAlign: 'center'
                                  }}>
                                    <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '4px' }}>
                                      {word.word}
                                    </div>
                                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: borderColor }}>
                                      {score}%
                                    </div>
                                    <div style={{ fontSize: '10px', color: '#6c757d', marginTop: '4px' }}>
                                      {word.target_ipa && <span>/{word.target_ipa}/</span>}
                                    </div>
                                    <div style={{ fontSize: '9px', color: '#6c757d', marginTop: '2px', display: 'flex', justifyContent: 'center', gap: '6px' }}>
                                      <span>MFCC: {word.mfcc_score}%</span>
                                      <span>F0: {word.pitch_score}%</span>
                                    </div>
                                    {(word.vowel_errors > 0 || word.consonant_errors > 0) && (
                                      <div style={{ fontSize: '8px', color: '#dc3545', marginTop: '3px' }}>
                                        {word.vowel_errors > 0 && <span>V:{word.vowel_errors} </span>}
                                        {word.consonant_errors > 0 && <span>C:{word.consonant_errors}</span>}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* Phoneme Visualization */}
                        {result.advanced_analysis.word_analyses && result.advanced_analysis.word_analyses.length > 0 && (
                          <div style={{ marginTop: '25px' }}>
                            <div style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              marginBottom: '15px',
                              paddingBottom: '10px',
                              borderBottom: '2px solid #e9ecef'
                            }}>
                              <i className="fas fa-align-left" style={{ color: '#4a90e2', fontSize: '16px' }}></i>
                              <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>Phoneme Alignment</span>
                              <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px', fontSize: '10px' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <span style={{ width: '10px', height: '10px', background: '#28a745', borderRadius: '50%' }}></span>
                                  Match
                                </span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <span style={{ width: '10px', height: '10px', background: '#fd7e14', borderRadius: '50%' }}></span>
                                  Vowel Error
                                </span>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <span style={{ width: '10px', height: '10px', background: '#dc3545', borderRadius: '50%' }}></span>
                                  Mismatch
                                </span>
                              </div>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                              {result.advanced_analysis.word_analyses.map((wordAnalysis, wIdx) => {
                                const isVowelError = wordAnalysis.similarity >= 50 && wordAnalysis.similarity < 90;
                                const bgColor = wordAnalysis.similarity >= 90 ? '#d4edda' : isVowelError ? '#fff3cd' : '#f8d7da';
                                const borderColor = wordAnalysis.similarity >= 90 ? '#28a745' : isVowelError ? '#fd7e14' : '#dc3545';
                                const textColor = wordAnalysis.similarity >= 90 ? '#155724' : isVowelError ? '#856404' : '#721c24';

                                return (
                                  <div key={wIdx} style={{
                                    background: bgColor,
                                    border: `2px solid ${borderColor}`,
                                    borderRadius: '10px',
                                    padding: '10px 14px',
                                    textAlign: 'center',
                                    minWidth: '90px',
                                    position: 'relative'
                                  }}>
                                    {/* Score badge */}
                                    <div style={{
                                      position: 'absolute',
                                      top: '-8px',
                                      right: '-8px',
                                      background: borderColor,
                                      color: 'white',
                                      fontSize: '9px',
                                      fontWeight: 'bold',
                                      padding: '2px 5px',
                                      borderRadius: '8px'
                                    }}>
                                      {wordAnalysis.similarity}%
                                    </div>

                                    {/* Word */}
                                    <div style={{ fontWeight: 'bold', fontSize: '14px', color: textColor, marginBottom: '6px' }}>
                                      {wordAnalysis.word} {wordAnalysis.similarity >= 90 ? '✓' : isVowelError ? '◐' : '✗'}
                                    </div>

                                    {/* User vs Target Phonemes */}
                                    <div style={{
                                      background: 'rgba(255,255,255,0.8)',
                                      borderRadius: '6px',
                                      padding: '6px',
                                      fontSize: '10px',
                                      fontFamily: 'monospace',
                                      marginBottom: '6px'
                                    }}>
                                      <div style={{ marginBottom: '3px' }}>
                                        <span style={{ color: '#4a90e2', fontWeight: '600' }}>User:</span>{' '}
                                        <span style={{ color: '#495057' }}>{wordAnalysis.user_phonemes?.join(' ') || '—'}</span>
                                      </div>
                                      <div>
                                        <span style={{ color: '#28a745', fontWeight: '600' }}>Target:</span>{' '}
                                        <span style={{ color: '#495057' }}>{wordAnalysis.native_phonemes?.join(' ') || '—'}</span>
                                      </div>
                                    </div>

                                    {/* IPA Transcription */}
                                    {wordAnalysis.ipa && (
                                      <div style={{
                                        fontSize: '12px',
                                        color: '#4a90e2',
                                        fontFamily: 'serif',
                                        marginBottom: '4px'
                                      }}>
                                        {wordAnalysis.ipa}
                                      </div>
                                    )}

                                    {/* Syllable Breakdown */}
                                    {wordAnalysis.syllables && (
                                      <div style={{
                                        fontSize: '10px',
                                        color: '#4a90e2',
                                        fontFamily: 'monospace'
                                      }}>
                                        {wordAnalysis.syllables}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
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
                                borderLeft: `4px solid ${tip.type === 'phoneme' ? '#4a90e2' : '#4a90e2'}`,
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

                  {/* Tutor Feedback Section - NEW */}
                  {result.followup_question && (
                    <div className="chat-message ai">
                      <div className="pm-advanced-section" style={{ borderTop: '4px solid #6f42c1' }}>
                        <div className="pm-section-header">
                          <div className="pm-section-icon" style={{ background: '#6f42c1' }}>
                            <i className="fas fa-chalkboard-teacher"></i>
                          </div>
                          <span className="pm-section-title" style={{ color: '#6f42c1' }}>Tutor Feedback</span>
                        </div>

                        <div style={{ background: '#f8f9fa', borderRadius: '12px', padding: '18px', border: '1px solid #dee2e6' }}>

                          {/* Correction */}
                          {result.followup_question.correction && (
                            <div style={{ marginBottom: '15px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#dc3545', marginBottom: '4px', textTransform: 'uppercase' }}>
                                <i className="fas fa-times-circle" style={{ marginRight: '5px' }}></i>Correction Needed
                              </div>
                              <div style={{ fontSize: '15px', color: '#495057', marginBottom: '4px' }}>
                                You said: "{result.transcribed_text}"
                              </div>
                              <div style={{ fontSize: '15px', fontWeight: '500', color: '#155724', background: '#d4edda', padding: '10px', borderRadius: '8px', borderLeft: '4px solid #28a745' }}>
                                <i className="fas fa-check" style={{ marginRight: '8px', color: '#28a745' }}></i>
                                {result.followup_question.correction}
                              </div>
                            </div>
                          )}

                          {/* Vocabulary Upgrades */}
                          {(result.followup_question.vocab_formal || result.followup_question.vocab_informal || result.followup_question.vocab_british) && (
                            <div style={{ marginBottom: '15px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#0d6efd', marginBottom: '8px', textTransform: 'uppercase' }}>
                                <i className="fas fa-book" style={{ marginRight: '5px' }}></i>Vocabulary Upgrades
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
                                {result.followup_question.vocab_formal && (
                                  <div style={{ background: 'white', padding: '8px', borderRadius: '6px', border: '1px solid #cfe2ff' }}>
                                    <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#0d6efd', display: 'block' }}>FORMAL</span>
                                    <span style={{ fontSize: '13px', color: '#2c3e50' }}>{result.followup_question.vocab_formal}</span>
                                  </div>
                                )}
                                {result.followup_question.vocab_informal && (
                                  <div style={{ background: 'white', padding: '8px', borderRadius: '6px', border: '1px solid #ffe69c' }}>
                                    <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#ffc107', display: 'block' }}>INFORMAL</span>
                                    <span style={{ fontSize: '13px', color: '#2c3e50' }}>{result.followup_question.vocab_informal}</span>
                                  </div>
                                )}
                                {result.followup_question.vocab_british && (
                                  <div style={{ background: 'white', padding: '8px', borderRadius: '6px', border: '1px solid #f5c6cb' }}>
                                    <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#dc3545', display: 'block' }}>BRITISH SLANG</span>
                                    <span style={{ fontSize: '13px', color: '#2c3e50' }}>{result.followup_question.vocab_british}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Accent Tip */}
                          {result.followup_question.accent_tip && (
                            <div style={{ marginBottom: '15px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#6f42c1', marginBottom: '4px', textTransform: 'uppercase' }}>
                                <i className="fas fa-microphone" style={{ marginRight: '5px' }}></i>Accent Tip
                              </div>
                              <div style={{ background: '#f3e5f5', padding: '10px', borderRadius: '8px', color: '#4a148c', fontSize: '13px', borderLeft: '4px solid #9c27b0' }}>
                                {result.followup_question.accent_tip}
                              </div>
                            </div>
                          )}

                          {/* Follow-up Question */}
                          {result.followup_question.question && (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#fd7e14', marginBottom: '4px', textTransform: 'uppercase' }}>
                                <i className="fas fa-comment-dots" style={{ marginRight: '5px' }}></i>Conversation
                              </div>
                              <div style={{ fontSize: '16px', fontWeight: '600', color: '#2c3e50', fontStyle: 'italic' }}>
                                "{result.followup_question.question}"
                              </div>
                            </div>
                          )}

                        </div>
                      </div>
                    </div>
                  )}
                </React.Fragment>
              ))
            }

            {/* Show error */}
            {
              error && (
                <div className="chat-message ai">
                  <div className="message-content" style={{ color: 'red' }}>
                    ⚠️ {error}
                  </div>
                </div>
              )
            }
          </div >

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

            {/* Live Transcription Display - shows during recording AND analysis */}
            {(isRecording || (isAnalyzing && liveTranscript)) && (
              <div style={{
                marginTop: '15px',
                padding: '15px 20px',
                background: 'linear-gradient(135deg, #e8f4fd 0%, #d6e9f8 100%)',
                borderRadius: 'var(--border-radius, 12px)',
                border: '2px solid #4a90e2',
                minHeight: '60px',
                position: 'relative',
                boxShadow: '0 2px 8px rgba(74, 144, 226, 0.15)'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginBottom: '10px'
                }}>
                  <i className={isRecording ? "fas fa-microphone" : "fas fa-comment-dots"}
                    style={{
                      color: isRecording ? '#e53935' : '#4a90e2',
                      fontSize: '16px',
                      animation: isRecording ? 'pulse 1s infinite' : 'none'
                    }}></i>
                  <span style={{
                    fontSize: '12px',
                    fontWeight: '600',
                    color: '#4a90e2',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    {isRecording ? 'Recording...' : 'Transcribed Text'}
                  </span>
                  {isRecording && (
                    <div style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: '#e53935',
                      animation: 'pulse 1s infinite',
                      marginLeft: 'auto'
                    }}></div>
                  )}
                </div>
                <div style={{
                  fontSize: '16px',
                  color: '#2c3e50',
                  fontWeight: '500',
                  minHeight: '24px',
                  lineHeight: '1.5'
                }}>
                  {liveTranscript || (
                    <span style={{ color: '#7fb3d8', fontStyle: 'italic' }}>
                      {isRecording ? 'Listening... speak clearly' : 'Processing your speech...'}
                    </span>
                  )}
                </div>
              </div>
            )}
            {isAnalyzing && (
              <div style={{
                textAlign: 'center',
                marginTop: '15px',
                padding: '20px',
                background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
                borderRadius: 'var(--border-radius, 12px)',
                border: '1px solid #e2e8f0',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  marginBottom: '12px'
                }}>
                  <i className={
                    analysisProgress.stage === 'transcribing' ? 'fas fa-headphones fa-pulse' :
                      analysisProgress.stage === 'generating_tts' ? 'fas fa-volume-up' :
                        analysisProgress.stage === 'analyzing_basic' ? 'fas fa-spell-check' :
                          analysisProgress.stage === 'analyzing_acoustic' ? 'fas fa-chart-line' :
                            analysisProgress.stage === 'scores_ready' ? 'fas fa-star' :
                              analysisProgress.stage === 'complete' ? 'fas fa-check-circle' :
                                'fas fa-spinner fa-spin'
                  } style={{ color: '#4a90e2', fontSize: '20px' }}></i>
                  <span style={{ fontWeight: '600', color: '#2c3e50', fontSize: '14px' }}>
                    {analysisProgress.message || 'Analyzing...'}
                  </span>
                </div>
                <div style={{
                  background: '#e2e8f0',
                  borderRadius: '10px',
                  height: '10px',
                  overflow: 'hidden',
                  marginBottom: '8px'
                }}>
                  <div style={{
                    width: `${analysisProgress.progress || 0}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #4a90e2, #357ABD)',
                    borderRadius: '10px',
                    transition: 'width 0.3s ease-out'
                  }}></div>
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', fontWeight: '500' }}>
                  {analysisProgress.progress || 0}% complete
                </div>
              </div>
            )}
          </div>
        </div >

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
      </div >
    </div >
  );
};

PronunciationModal.propTypes = {
  closeModal: PropTypes.func.isRequired
};

export default PronunciationModal;
