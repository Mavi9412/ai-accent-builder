import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './Sidebar';
import './LiveCall.css';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
    faChartLine, faMusic, faWaveSquare, faCheckCircle, faStar,
    faGlobe, faLanguage, faLink, faPencilAlt, faBullseye,
    faVolumeUp, faPlay, faPlayCircle, faHistory, faClock,
    faComments, faSpellCheck, faMicrophone, faHeadphones,
    faLightbulb, faQuestionCircle, faArrowRight, faFont, faFilePdf, faDownload,
    faTimesCircle
} from '@fortawesome/free-solid-svg-icons';
const API_BASE = 'http://localhost:8000';

const LiveCall = () => {
    const [isMuted, setIsMuted] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [messages, setMessages] = useState([
        {
            sender: 'ai',
            text: "Hello! I'm your AI language partner. Let's practice speaking together. How are you today?"
        }
    ]);
    const [newMessage, setNewMessage] = useState('');

    // Recording state
    const [isRecording, setIsRecording] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);

    // Analysis results
    const [analysisResult, setAnalysisResult] = useState(null);
    const [wordAnalyses, setWordAnalyses] = useState([]);
    const [selectedWord, setSelectedWord] = useState(null);
    const [wordPlots, setWordPlots] = useState({});
    const [followUpQuestion, setFollowUpQuestion] = useState(null);

    // Multiple practice history (like PronunciationModal)
    const [practiceHistory, setPracticeHistory] = useState([]);
    const [selectedHistoryIndex, setSelectedHistoryIndex] = useState(null);
    const [practiceMode, setPracticeMode] = useState('free'); // 'free' or 'guided'
    const [targetSentence, setTargetSentence] = useState('');

    // Audio playback
    const [isPlayingUser, setIsPlayingUser] = useState(false);
    const [isPlayingRef, setIsPlayingRef] = useState(false);

    // PDF Export
    const [isExporting, setIsExporting] = useState(false);

    // Refs
    const conversationContainerRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const recordingTimerRef = useRef(null);
    const streamRef = useRef(null);
    const userAudioRef = useRef(null);
    const refAudioRef = useRef(null);

    useEffect(() => {
        initializeAudio();
        const savedSidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
        setSidebarCollapsed(savedSidebarState);

        return () => {
            if (recordingTimerRef.current) {
                clearInterval(recordingTimerRef.current);
            }
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    const toggleSidebar = () => {
        const newState = !sidebarCollapsed;
        setSidebarCollapsed(newState);
        localStorage.setItem('sidebarCollapsed', newState);
    };

    const initializeAudio = async () => {
        try {
            // Request audio-only permission
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            console.log('Microphone access granted');
        } catch (error) {
            console.error('Microphone access denied:', error);
            setMessages(prev => [...prev, {
                sender: 'ai',
                text: '⚠️ Microphone access is required. Please allow microphone access in your browser settings and refresh the page.'
            }]);
        }
    };

    const startRecording = async () => {
        try {
            // Reuse existing stream if available, otherwise request new one
            let stream = streamRef.current;

            if (!stream || !stream.getAudioTracks().length) {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                streamRef.current = stream;
            }

            // Check for audio tracks
            const audioTracks = stream.getAudioTracks();
            if (!audioTracks.length) {
                throw new Error('No audio tracks available');
            }

            // Create audio-only stream for recording
            const audioStream = new MediaStream(audioTracks);

            // Try audio/wav first (no FFmpeg needed), fallback to webm
            let mimeType = 'audio/webm;codecs=opus';
            if (MediaRecorder.isTypeSupported('audio/wav')) {
                mimeType = 'audio/wav';
            } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
                mimeType = 'audio/ogg';
            }
            console.log('Recording with mimeType:', mimeType);

            mediaRecorderRef.current = new MediaRecorder(audioStream, { mimeType });
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorderRef.current.onstop = async () => {
                // Determine file extension based on mimeType
                const ext = mimeType.includes('wav') ? '.wav' : mimeType.includes('ogg') ? '.ogg' : '.webm';
                const audioBlob = new Blob(audioChunksRef.current, { type: mimeType.split(';')[0] });
                console.log('Recording stopped, blob size:', audioBlob.size, 'format:', ext);
                if (audioBlob.size > 1000) {  // Minimum viable audio size
                    await analyzeRecording(audioBlob, ext);
                } else {
                    setMessages(prev => [...prev, {
                        sender: 'ai',
                        text: 'Recording too short or empty. Please speak for at least 1-2 seconds.'
                    }]);
                }
            };

            mediaRecorderRef.current.start(100);
            setIsRecording(true);
            setRecordingTime(0);

            recordingTimerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (error) {
            console.error('Error starting recording:', error);
        }
    };

    const stopRecording = () => {
        // Stop the media recorder
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }

        // Stop ALL audio tracks to release the microphone
        if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => {
                track.stop();
                console.log('Stopped track:', track.kind);
            });
        }

        // Also stop the main stream reference
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => {
                track.stop();
                console.log('Stopped main stream track:', track.kind);
            });
            streamRef.current = null;
        }

        setIsRecording(false);
        if (recordingTimerRef.current) {
            clearInterval(recordingTimerRef.current);
        }

        console.log('Recording stopped and microphone released');
        // Note: Do NOT re-initialize audio here - mic will be requested when user clicks Start again
    };

    const analyzeRecording = async (audioBlob, ext = '.webm') => {
        setIsAnalyzing(true);

        try {
            const token = localStorage.getItem('token');
            const formData = new FormData();
            formData.append('file', audioBlob, `recording${ext}`);
            formData.append('target_accent', 'british');
            formData.append('target_text', ''); // Free practice mode
            formData.append('fast_mode', 'true'); // Skip heavy ML models for speed

            const response = await fetch(`${API_BASE}/api/accent/analyze-enhanced`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => null);
                if (response.status === 401 || response.status === 403) {
                    throw new Error('Please log in to use this feature.');
                }
                throw new Error(errData?.detail || 'Analysis failed');
            }

            const result = await response.json();
            console.log('Analysis result:', result);

            setAnalysisResult(result);
            setWordAnalyses(result.word_analyses || []);

            // Save to practice history for multiple attempts comparison
            const historyEntry = {
                id: Date.now(),
                timestamp: new Date().toLocaleTimeString(),
                result: result,
                audioUrl: audioBlob ? URL.createObjectURL(audioBlob) : null,
                overallScore: result.overall_score,
                transcribedText: result.transcribed_text
            };
            setPracticeHistory(prev => [...prev, historyEntry]);
            setSelectedHistoryIndex(null); // Show latest result

            // Set follow-up question
            if (result.followup_question) {
                console.log('[LiveCall] followup_question received:', JSON.stringify(result.followup_question, null, 2));
                setFollowUpQuestion(result.followup_question);
            }

            // Add AI response with analysis
            const aiMessage = {
                sender: 'ai',
                text: `I analyzed your speech! Your overall score is ${result.overall_score}%. `,
                analysisData: result
            };
            setMessages(prev => [...prev, aiMessage]);

            // Add follow-up question as next message
            if (result.followup_question?.question) {
                setTimeout(() => {
                    setMessages(prev => [...prev, {
                        sender: 'ai',
                        text: result.followup_question.question
                    }]);
                }, 1500);
            }

        } catch (error) {
            console.error('Analysis error:', error);
            setMessages(prev => [...prev, {
                sender: 'ai',
                text: error.message || 'Sorry, I had trouble analyzing your speech. Please try again.'
            }]);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const selectWord = useCallback(async (word) => {
        // Toggle: if clicking the same word, close it
        if (selectedWord && selectedWord.word === word.word) {
            setSelectedWord(null);
            return;
        }

        setSelectedWord(word);

        // Fetch word visualization if session exists
        if (analysisResult?.session_id) {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch(
                    `${API_BASE}/api/accent/word-visualization/${analysisResult.session_id}/${word.word_index}`,
                    {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }
                );

                if (response.ok) {
                    const plotData = await response.json();
                    setWordPlots(plotData.plots || {});
                }
            } catch (error) {
                console.error('Error fetching word plots:', error);
            }
        }
    }, [analysisResult?.session_id, selectedWord]);

    const playWordAudio = async (type) => {
        if (!analysisResult?.session_id || !selectedWord) {
            console.log('Cannot play: no session or word selected');
            return;
        }

        const setPlaying = type === 'user' ? setIsPlayingUser : setIsPlayingRef;
        const audioRefToUse = type === 'user' ? userAudioRef : refAudioRef;

        try {
            const token = localStorage.getItem('token');
            const url = `${API_BASE}/api/accent/word-audio/${analysisResult.session_id}/${selectedWord.word_index}/${type}`;
            console.log('Playing word audio:', url);

            // Create new Audio object if ref is null
            if (!audioRefToUse.current) {
                audioRefToUse.current = new Audio();
            }

            // Stop current audio if playing
            audioRefToUse.current.pause();
            audioRefToUse.current.currentTime = 0;

            // Set source and play
            audioRefToUse.current.src = url;
            setPlaying(true);

            audioRefToUse.current.onended = () => setPlaying(false);
            audioRefToUse.current.onerror = (e) => {
                console.error('Audio playback error:', e);
                setPlaying(false);
            };

            await audioRefToUse.current.play();
        } catch (error) {
            console.error('Error playing audio:', error);
            setPlaying(false);
        }
    };

    const sendMessage = () => {
        if (newMessage.trim()) {
            const userMessage = {
                sender: 'user',
                text: newMessage.trim()
            };
            setMessages(prev => [...prev, userMessage]);
            setNewMessage('');

            // Simulate AI response
            setTimeout(() => {
                const responses = [
                    "That's interesting! Can you tell me more about that?",
                    "I understand. How do you feel about that?",
                    "Great! Let's practice some more vocabulary related to that topic.",
                    "Would you like to try a different conversation topic?",
                    "Your pronunciation is improving! Keep practicing."
                ];
                const aiMessage = {
                    sender: 'ai',
                    text: responses[Math.floor(Math.random() * responses.length)]
                };
                setMessages(prev => [...prev, aiMessage]);
            }, 1000);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    };

    const toggleMute = () => setIsMuted(!isMuted);
    const endCall = () => window.location.href = '/dashboard';

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getScoreColor = (score) => {
        if (score >= 80) return '#2ECC71';  // Theme green - good
        if (score >= 60) return '#F1C40F';  // Theme yellow/orange - medium
        return '#E74C3C';  // Theme red - needs work
    };

    const handleExportPDF = async () => {
        if (!analysisResult) {
            alert('No analysis available to export. Please complete a practice session first.');
            return;
        }

        setIsExporting(true);
        try {
            const token = localStorage.getItem('token');

            // Prepare word analyses with all fields
            const wordAnalysesData = (analysisResult.word_analyses || wordAnalyses || []).map((wa, idx) => ({
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

            // Prepare scores
            const scores = analysisResult.scores || {
                pronunciation: analysisResult.pronunciation_score || analysisResult.overall_score || 0,
                rhythm: analysisResult.rhythm_score || 70,
                intonation: analysisResult.intonation_score || 70,
                stress: analysisResult.stress_score || 70
            };

            // Prepare followup question
            const followup = analysisResult.followup_question || followUpQuestion;
            const followupData = followup ? {
                question: followup.question || followup.followup || '',
                correction: followup.correction || '',
                accent_tip: followup.accent_tip || '',
                vocabulary_tip: followup.vocabulary_tip || '',
                next_practice_sentence: followup.next_practice_sentence || followup.practice_sentence || ''
            } : null;

            // Complete export data
            const exportData = {
                session_id: analysisResult.session_id || Date.now(),
                transcribed_text: analysisResult.transcribed_text || '',
                target_text: analysisResult.target_text || analysisResult.transcribed_text || '',
                overall_score: analysisResult.overall_score || 0,
                scores: scores,
                word_analyses: wordAnalysesData,
                word_count: analysisResult.word_count || wordAnalysesData.length,
                error_count: analysisResult.error_count || wordAnalysesData.filter(w => !w.is_correct).length,
                followup_question: followupData,
                audio_duration: analysisResult.audio_duration || 0,
                grammar_analysis: analysisResult.grammar_analysis || null,
                dialect_analysis: analysisResult.dialect_analysis || null,
                advanced_analysis: analysisResult.advanced_analysis || null
            };

            console.log('[Export PDF] Sending:', exportData);

            const response = await fetch(`${API_BASE}/api/report/generate-pdf`, {
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

            // Download the PDF
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
        }
    };

    return (
        <div className="dashboard-container">
            <Sidebar
                isCollapsed={sidebarCollapsed}
                toggleSidebar={toggleSidebar}
            />
            <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
                <div className="call-container enhanced-call">
                    {/* Main Audio/Analysis Area */}
                    <div className="video-analysis-grid">
                        <div className="video-container">
                            <div className="main-video">
                                {/* Microphone indicator instead of video */}
                                <div className="ai-avatar">
                                    <i className={`fas fa-${isRecording ? 'microphone-alt' : 'robot'}`}></i>
                                </div>

                                {/* Recording Indicator */}
                                {isRecording && (
                                    <div className="recording-indicator">
                                        <span className="recording-dot"></span>
                                        Recording: {formatTime(recordingTime)}
                                    </div>
                                )}

                                {/* Analyzing Indicator */}
                                {isAnalyzing && (
                                    <div className="analyzing-overlay">
                                        <div className="analyzing-spinner"></div>
                                        <span>Analyzing your speech...</span>
                                    </div>
                                )}
                            </div>

                            {/* Recording Controls */}
                            <div className="recording-controls">
                                {!isRecording ? (
                                    <button
                                        className="record-btn"
                                        onClick={startRecording}
                                        disabled={isAnalyzing}
                                    >
                                        <i className="fas fa-microphone"></i>
                                        Start Speaking
                                    </button>
                                ) : (
                                    <button
                                        className="record-btn recording"
                                        onClick={stopRecording}
                                    >
                                        <i className="fas fa-stop"></i>
                                        Stop Recording
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Analysis Results Panel */}
                        {analysisResult && (
                            <div className="analysis-panel">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                    <h3 style={{ margin: 0 }}>Analysis Results</h3>
                                    <button
                                        onClick={handleExportPDF}
                                        disabled={isExporting || !analysisResult?.session_id}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.5rem 1rem',
                                            backgroundColor: isExporting ? '#6b7280' : '#1a73e8',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: isExporting ? 'not-allowed' : 'pointer',
                                            fontSize: '0.85rem',
                                            fontWeight: '600',
                                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                        }}
                                    >
                                        <FontAwesomeIcon icon={isExporting ? faDownload : faFilePdf} spin={isExporting} />
                                        {isExporting ? 'Exporting...' : 'Export PDF'}
                                    </button>
                                </div>

                                {/* Overall Scores */}
                                <div className="scores-grid">
                                    <div className="score-card">
                                        <span className="score-label">Overall</span>
                                        <span
                                            className="score-value"
                                            style={{ color: getScoreColor(analysisResult.overall_score) }}
                                        >
                                            {analysisResult.overall_score}%
                                        </span>
                                    </div>
                                    <div className="score-card">
                                        <span className="score-label">Pronunciation</span>
                                        <span
                                            className="score-value"
                                            style={{ color: getScoreColor(analysisResult.scores?.pronunciation) }}
                                        >
                                            {analysisResult.scores?.pronunciation}%
                                        </span>
                                    </div>
                                    <div className="score-card">
                                        <span className="score-label">Rhythm</span>
                                        <span
                                            className="score-value"
                                            style={{ color: getScoreColor(analysisResult.scores?.rhythm) }}
                                        >
                                            {analysisResult.scores?.rhythm}%
                                        </span>
                                    </div>
                                    <div className="score-card">
                                        <span className="score-label">Intonation</span>
                                        <span
                                            className="score-value"
                                            style={{ color: getScoreColor(analysisResult.scores?.intonation) }}
                                        >
                                            {analysisResult.scores?.intonation}%
                                        </span>
                                    </div>
                                </div>

                                {/* Word-Level Analysis */}
                                <div className="word-analysis-section">
                                    <h4>Word-Level Breakdown</h4>
                                    <div className="word-badges">
                                        {wordAnalyses.map((word, idx) => (
                                            <button
                                                key={idx}
                                                className={`word-badge ${word.is_correct ? 'correct' : 'incorrect'} ${selectedWord?.word_index === word.word_index ? 'selected' : ''}`}
                                                onClick={() => selectWord(word)}
                                                title={word.feedback || 'Click for details'}
                                            >
                                                {word.word}
                                                <span className="word-score">{Math.round(word.score)}%</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Selected Word Details - Comprehensive FYP View */}
                                {selectedWord && (
                                    <div className="selected-word-panel">
                                        <h4>Word Analysis: "{selectedWord.word}"</h4>

                                        {/* 1. Pronunciation Features */}
                                        <div className="analysis-section">
                                            <h5><FontAwesomeIcon icon={faChartLine} className="section-icon" /> Pronunciation Features</h5>
                                            <table className="metrics-table">
                                                <thead>
                                                    <tr>
                                                        <th>Feature</th>
                                                        <th>User Value</th>
                                                        <th>RP Value</th>
                                                        <th>Score</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td>Phonemes</td>
                                                        <td>{selectedWord.transcribed_phonemes || selectedWord.expected_phonemes || 'N/A'}</td>
                                                        <td>{selectedWord.expected_phonemes || 'N/A'}</td>
                                                        <td style={{ color: getScoreColor(selectedWord.score) }}>{Math.round(selectedWord.score)}%</td>
                                                    </tr>
                                                    <tr>
                                                        <td>IPA</td>
                                                        <td colSpan="2">{selectedWord.ipa || 'N/A'}</td>
                                                        <td>-</td>
                                                    </tr>
                                                    <tr>
                                                        <td>Syllables</td>
                                                        <td colSpan="2">{selectedWord.syllables?.join('-') || 'N/A'}</td>
                                                        <td>{selectedWord.syllables?.length || 0} syllables</td>
                                                    </tr>
                                                    <tr>
                                                        <td>Word Stress</td>
                                                        <td colSpan="2">{selectedWord.stress_pattern || 'N/A'}</td>
                                                        <td>{selectedWord.stress_correct ? <><FontAwesomeIcon icon={faCheckCircle} style={{ color: '#2ECC71' }} /> Correct</> : <><FontAwesomeIcon icon={faQuestionCircle} style={{ color: '#F1C40F' }} /> Check</>}</td>
                                                    </tr>
                                                    <tr>
                                                        <td>Duration</td>
                                                        <td>{selectedWord.duration ? `${selectedWord.duration.toFixed(2)}s` : 'N/A'}</td>
                                                        <td>{selectedWord.expected_duration ? `${selectedWord.expected_duration.toFixed(2)}s` : 'N/A'}</td>
                                                        <td>{selectedWord.duration_diff ? `${selectedWord.duration_diff > 0 ? '+' : ''}${selectedWord.duration_diff.toFixed(2)}s` : '-'}</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* 2. Accent Features (from advanced_analysis) */}
                                        {analysisResult?.advanced_analysis && (
                                            <div className="analysis-section">
                                                <h5><FontAwesomeIcon icon={faMusic} className="section-icon" /> Accent Features</h5>
                                                <table className="metrics-table">
                                                    <thead>
                                                        <tr>
                                                            <th>Feature</th>
                                                            <th>Value</th>
                                                            <th>Score</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        <tr>
                                                            <td>Pitch Correlation</td>
                                                            <td>{analysisResult.advanced_analysis.scores?.pitch_correlation?.toFixed(1) || 'N/A'}%</td>
                                                            <td style={{ color: getScoreColor(analysisResult.advanced_analysis.scores?.pitch_correlation) }}>
                                                                {analysisResult.advanced_analysis.scores?.pitch_correlation >= 80 ? <FontAwesomeIcon icon={faCheckCircle} style={{ color: '#2ECC71' }} /> : <FontAwesomeIcon icon={faQuestionCircle} style={{ color: '#F1C40F' }} />}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td>MFCC Similarity</td>
                                                            <td>{analysisResult.advanced_analysis.scores?.mfcc_similarity?.toFixed(1) || 'N/A'}%</td>
                                                            <td style={{ color: getScoreColor(analysisResult.advanced_analysis.scores?.mfcc_similarity) }}>
                                                                {analysisResult.advanced_analysis.scores?.mfcc_similarity >= 80 ? <FontAwesomeIcon icon={faCheckCircle} style={{ color: '#2ECC71' }} /> : <FontAwesomeIcon icon={faQuestionCircle} style={{ color: '#F1C40F' }} />}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td>Rhythm Timing</td>
                                                            <td>{analysisResult.scores?.rhythm || 'N/A'}%</td>
                                                            <td style={{ color: getScoreColor(analysisResult.scores?.rhythm) }}>
                                                                {analysisResult.scores?.rhythm >= 80 ? <FontAwesomeIcon icon={faCheckCircle} style={{ color: '#2ECC71' }} /> : <FontAwesomeIcon icon={faQuestionCircle} style={{ color: '#F1C40F' }} />}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td>Intonation</td>
                                                            <td>{analysisResult.scores?.intonation || 'N/A'}%</td>
                                                            <td style={{ color: getScoreColor(analysisResult.scores?.intonation) }}>
                                                                {analysisResult.scores?.intonation >= 80 ? <FontAwesomeIcon icon={faCheckCircle} style={{ color: '#2ECC71' }} /> : <FontAwesomeIcon icon={faQuestionCircle} style={{ color: '#F1C40F' }} />}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td>Stress Pattern</td>
                                                            <td>{analysisResult.scores?.stress || 'N/A'}%</td>
                                                            <td style={{ color: getScoreColor(analysisResult.scores?.stress) }}>
                                                                {analysisResult.scores?.stress >= 80 ? <FontAwesomeIcon icon={faCheckCircle} style={{ color: '#2ECC71' }} /> : <FontAwesomeIcon icon={faQuestionCircle} style={{ color: '#F1C40F' }} />}
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}

                                        {/* 3. Dialect Features */}
                                        {analysisResult?.dialect_analysis && (
                                            <div className="analysis-section">
                                                <h5><FontAwesomeIcon icon={faComments} className="section-icon" /> Dialect Analysis</h5>
                                                <table className="metrics-table">
                                                    <tbody>
                                                        <tr>
                                                            <td>Dialect Detected</td>
                                                            <td colSpan="2">{analysisResult.dialect_analysis.primary_dialect?.toUpperCase() || 'RP'}</td>
                                                        </tr>
                                                        <tr>
                                                            <td>RP Compliance</td>
                                                            <td colSpan="2" style={{ color: getScoreColor(analysisResult.dialect_analysis.rp_compliance) }}>
                                                                {analysisResult.dialect_analysis.rp_compliance?.toFixed(1)}%
                                                            </td>
                                                        </tr>
                                                        {analysisResult.dialect_analysis.detected_features?.length > 0 && (
                                                            <tr>
                                                                <td>Regional Markers</td>
                                                                <td colSpan="2">
                                                                    {analysisResult.dialect_analysis.detected_features.map((f, i) => (
                                                                        <span key={i} className="feature-tag">{f.description}</span>
                                                                    ))}
                                                                </td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}

                                        {/* 4. L1 Influence */}
                                        {analysisResult?.l1_influence && (
                                            <div className="analysis-section">
                                                <h5><FontAwesomeIcon icon={faGlobe} className="section-icon" /> L1 Influence</h5>
                                                <table className="metrics-table">
                                                    <tbody>
                                                        <tr>
                                                            <td>Detected L1</td>
                                                            <td colSpan="2">{analysisResult.l1_influence.likely_l1 || 'None detected'}</td>
                                                        </tr>
                                                        <tr>
                                                            <td>Influence Score</td>
                                                            <td colSpan="2">{analysisResult.l1_influence.influence_score || 0}% (lower is better)</td>
                                                        </tr>
                                                        {analysisResult.l1_influence.recommendations?.length > 0 && (
                                                            <tr>
                                                                <td>Recommendations</td>
                                                                <td colSpan="2">
                                                                    <ul className="recommendations-list">
                                                                        {analysisResult.l1_influence.recommendations.slice(0, 2).map((r, i) => (
                                                                            <li key={i}>{r}</li>
                                                                        ))}
                                                                    </ul>
                                                                </td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}

                                        {/* 5. Connected Speech */}
                                        {analysisResult?.connected_speech && (
                                            <div className="analysis-section">
                                                <h5><FontAwesomeIcon icon={faLink} className="section-icon" /> Connected Speech</h5>
                                                <table className="metrics-table">
                                                    <tbody>
                                                        <tr>
                                                            <td>Fluency Score</td>
                                                            <td colSpan="2" style={{ color: getScoreColor(analysisResult.connected_speech.fluency_score) }}>
                                                                {analysisResult.connected_speech.fluency_score}%
                                                            </td>
                                                        </tr>
                                                        {analysisResult.connected_speech.tips?.length > 0 && (
                                                            <tr>
                                                                <td>Tips</td>
                                                                <td colSpan="2">{analysisResult.connected_speech.tips[0]}</td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}

                                        {/* 6. Grammar */}
                                        {analysisResult?.grammar_analysis && (
                                            <div className="analysis-section">
                                                <h5><FontAwesomeIcon icon={faSpellCheck} className="section-icon" /> Grammar</h5>
                                                <table className="metrics-table">
                                                    <tbody>
                                                        <tr>
                                                            <td>Errors Found</td>
                                                            <td colSpan="2" style={{ color: analysisResult.grammar_analysis.error_count === 0 ? '#4caf50' : '#ff9800' }}>
                                                                {analysisResult.grammar_analysis.error_count || 0}
                                                            </td>
                                                        </tr>
                                                        {analysisResult.grammar_analysis.errors?.length > 0 && (
                                                            <tr>
                                                                <td>Issues</td>
                                                                <td colSpan="2">
                                                                    {analysisResult.grammar_analysis.errors.map((e, i) => (
                                                                        <div key={i} className="grammar-error">{e.message}</div>
                                                                    ))}
                                                                </td>
                                                            </tr>
                                                        )}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}

                                        {/* 7. AI Tutor Feedback (from Gemini) */}
                                        {(followUpQuestion || analysisResult?.followup_question) && (
                                            <div className="analysis-section" style={{
                                                background: 'linear-gradient(135deg, #f8f4ff 0%, #e8e0f7 100%)',
                                                borderLeft: '4px solid #6f42c1'
                                            }}>
                                                <h5 style={{ color: '#6f42c1' }}>
                                                    <FontAwesomeIcon icon={faComments} className="section-icon" style={{ color: '#6f42c1' }} />
                                                    AI Tutor Feedback
                                                </h5>

                                                {/* Correction */}
                                                {(followUpQuestion?.correction || analysisResult?.followup_question?.correction) && (
                                                    <div style={{ marginBottom: '12px', padding: '10px', background: '#fff', borderRadius: '8px', borderLeft: '3px solid #dc3545' }}>
                                                        <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#dc3545', textTransform: 'uppercase', marginBottom: '4px' }}>
                                                            <FontAwesomeIcon icon={faTimesCircle} style={{ marginRight: '5px' }} />Correction
                                                        </div>
                                                        <div style={{ fontSize: '13px', color: '#6c757d', marginBottom: '4px' }}>
                                                            You said: "{analysisResult?.transcribed_text}"
                                                        </div>
                                                        <div style={{ fontSize: '14px', color: '#155724', background: '#d4edda', padding: '8px', borderRadius: '4px' }}>
                                                            <FontAwesomeIcon icon={faCheckCircle} style={{ marginRight: '6px', color: '#28a745' }} />
                                                            {followUpQuestion?.correction || analysisResult?.followup_question?.correction}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Vocabulary Upgrades */}
                                                {(followUpQuestion?.vocab_formal || followUpQuestion?.vocab_informal || followUpQuestion?.vocab_british ||
                                                    analysisResult?.followup_question?.vocab_formal || analysisResult?.followup_question?.vocab_informal || analysisResult?.followup_question?.vocab_british) && (
                                                        <div style={{ marginBottom: '12px' }}>
                                                            <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#0d6efd', textTransform: 'uppercase', marginBottom: '8px' }}>
                                                                <FontAwesomeIcon icon={faSpellCheck} style={{ marginRight: '5px' }} />Vocabulary Upgrades
                                                            </div>
                                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '6px' }}>
                                                                {(followUpQuestion?.vocab_formal || analysisResult?.followup_question?.vocab_formal) && (
                                                                    <div style={{ background: '#cfe2ff', padding: '6px 10px', borderRadius: '6px' }}>
                                                                        <span style={{ fontSize: '9px', fontWeight: 'bold', color: '#084298' }}>FORMAL</span>
                                                                        <div style={{ fontSize: '12px', color: '#0d6efd' }}>{followUpQuestion?.vocab_formal || analysisResult?.followup_question?.vocab_formal}</div>
                                                                    </div>
                                                                )}
                                                                {(followUpQuestion?.vocab_informal || analysisResult?.followup_question?.vocab_informal) && (
                                                                    <div style={{ background: '#fff3cd', padding: '6px 10px', borderRadius: '6px' }}>
                                                                        <span style={{ fontSize: '9px', fontWeight: 'bold', color: '#856404' }}>INFORMAL</span>
                                                                        <div style={{ fontSize: '12px', color: '#856404' }}>{followUpQuestion?.vocab_informal || analysisResult?.followup_question?.vocab_informal}</div>
                                                                    </div>
                                                                )}
                                                                {(followUpQuestion?.vocab_british || analysisResult?.followup_question?.vocab_british) && (
                                                                    <div style={{ background: '#f8d7da', padding: '6px 10px', borderRadius: '6px' }}>
                                                                        <span style={{ fontSize: '9px', fontWeight: 'bold', color: '#842029' }}>BRITISH</span>
                                                                        <div style={{ fontSize: '12px', color: '#842029' }}>{followUpQuestion?.vocab_british || analysisResult?.followup_question?.vocab_british}</div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}

                                                {/* Accent Tip */}
                                                {(followUpQuestion?.accent_tip || analysisResult?.followup_question?.accent_tip) && (
                                                    <div style={{ marginBottom: '12px', padding: '10px', background: '#fff', borderRadius: '8px', borderLeft: '3px solid #6f42c1' }}>
                                                        <div style={{ fontSize: '10px', fontWeight: 'bold', color: '#6f42c1', textTransform: 'uppercase', marginBottom: '4px' }}>
                                                            <FontAwesomeIcon icon={faMusic} style={{ marginRight: '5px' }} />Accent Tip
                                                        </div>
                                                        <div style={{ fontSize: '13px', color: '#4a148c' }}>
                                                            {followUpQuestion?.accent_tip || analysisResult?.followup_question?.accent_tip}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Follow-up Question */}
                                                {(followUpQuestion?.question || analysisResult?.followup_question?.question) && (
                                                    <div style={{ padding: '10px', background: 'linear-gradient(135deg, #4A90E2 0%, #357ABD 100%)', borderRadius: '8px' }}>
                                                        <div style={{ fontSize: '10px', fontWeight: 'bold', color: 'rgba(255,255,255,0.8)', textTransform: 'uppercase', marginBottom: '4px' }}>
                                                            <FontAwesomeIcon icon={faComments} style={{ marginRight: '5px' }} />Conversation
                                                        </div>
                                                        <div style={{ fontSize: '14px', fontWeight: '600', color: 'white', fontStyle: 'italic' }}>
                                                            "{followUpQuestion?.question || analysisResult?.followup_question?.question}"
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        {/* Pronunciation Tips */}
                                        {selectedWord.tips?.length > 0 && (
                                            <div className="analysis-section tips-section">
                                                <h5><FontAwesomeIcon icon={faLightbulb} className="section-icon" /> Tips for "{selectedWord.word}"</h5>
                                                <ul>
                                                    {selectedWord.tips.map((tip, i) => (
                                                        <li key={i}>{tip}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {/* A/B Playback Controls */}
                                        <div className="playback-controls">
                                            <button
                                                className={`play-btn user ${isPlayingUser ? 'playing' : ''}`}
                                                onClick={() => playWordAudio('user')}
                                                disabled={isPlayingUser}
                                            >
                                                <i className="fas fa-play"></i> Your Voice
                                            </button>
                                            <button
                                                className={`play-btn ref ${isPlayingRef ? 'playing' : ''}`}
                                                onClick={() => playWordAudio('reference')}
                                                disabled={isPlayingRef}
                                            >
                                                <i className="fas fa-play"></i> British RP
                                            </button>
                                        </div>

                                        {/* Visualization Tabs */}
                                        {Object.keys(wordPlots).length > 0 && (
                                            <div className="visualization-tabs">
                                                <h5><FontAwesomeIcon icon={faChartLine} className="section-icon" /> Visual Analysis</h5>
                                                <div className="plot-grid">
                                                    {wordPlots.waveform && (
                                                        <div className="plot-container">
                                                            <span className="plot-label">Waveform (User vs RP)</span>
                                                            <img
                                                                src={`${API_BASE}${wordPlots.waveform}`}
                                                                alt="Waveform comparison"
                                                                className="plot-image"
                                                            />
                                                        </div>
                                                    )}
                                                    {wordPlots.spectrogram && (
                                                        <div className="plot-container">
                                                            <span className="plot-label">Spectrogram</span>
                                                            <img
                                                                src={`${API_BASE}${wordPlots.spectrogram}`}
                                                                alt="Spectrogram"
                                                                className="plot-image"
                                                            />
                                                        </div>
                                                    )}
                                                    {wordPlots.pitch_contour && (
                                                        <div className="plot-container">
                                                            <span className="plot-label">Pitch Contour</span>
                                                            <img
                                                                src={`${API_BASE}${wordPlots.pitch_contour}`}
                                                                alt="Pitch contour"
                                                                className="plot-image"
                                                            />
                                                        </div>
                                                    )}
                                                    {wordPlots.energy && (
                                                        <div className="plot-container">
                                                            <span className="plot-label">Energy (RMS)</span>
                                                            <img
                                                                src={`${API_BASE}${wordPlots.energy}`}
                                                                alt="Energy comparison"
                                                                className="plot-image"
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Follow-up Question with Voice */}
                                {followUpQuestion && (
                                    <div className="followup-section">
                                        <div className="followup-header">
                                            <h4><FontAwesomeIcon icon={faBullseye} className="section-icon" /> Practice This:</h4>
                                            <button
                                                className="followup-voice-btn"
                                                onClick={() => {
                                                    const utterance = new SpeechSynthesisUtterance(followUpQuestion.question);
                                                    const voices = window.speechSynthesis.getVoices();
                                                    const britishVoice = voices.find(v =>
                                                        v.lang === 'en-GB' || v.name.includes('British')
                                                    ) || voices.find(v => v.lang.startsWith('en'));
                                                    if (britishVoice) utterance.voice = britishVoice;
                                                    utterance.lang = 'en-GB';
                                                    utterance.rate = 0.9;
                                                    window.speechSynthesis.speak(utterance);
                                                }}
                                                title="Listen to the question"
                                            >
                                                <i className="fas fa-volume-up"></i> Listen
                                            </button>
                                        </div>
                                        <p className="followup-question">{followUpQuestion.question}</p>

                                        {/* Error Type Badge */}
                                        {followUpQuestion.error_type && (
                                            <span className={`drill-type-badge ${followUpQuestion.error_type}`}>
                                                {followUpQuestion.error_type === 'phoneme' && <><FontAwesomeIcon icon={faFont} /> Phoneme Drill</>}
                                                {followUpQuestion.error_type === 'stress' && <><FontAwesomeIcon icon={faMusic} /> Stress Pattern</>}
                                                {followUpQuestion.error_type === 'intonation' && <><FontAwesomeIcon icon={faChartLine} /> Intonation</>}
                                                {followUpQuestion.error_type === 'grammar' && <><FontAwesomeIcon icon={faPencilAlt} /> Grammar</>}
                                                {followUpQuestion.error_type === 'success' && <><FontAwesomeIcon icon={faStar} /> Great Job!</>}
                                            </span>
                                        )}

                                        {/* Minimal Pair Practice */}
                                        {followUpQuestion.target_phoneme && (
                                            <div className="drill-card minimal-pair">
                                                <h5><FontAwesomeIcon icon={faVolumeUp} /> Minimal Pair Practice</h5>
                                                <p className="drill-instruction">Can you hear the difference?</p>
                                                <div className="minimal-pair-words">
                                                    <button
                                                        className="pair-word"
                                                        onClick={() => {
                                                            const utt = new SpeechSynthesisUtterance(followUpQuestion.target_word);
                                                            utt.lang = 'en-GB';
                                                            utt.rate = 0.8;
                                                            window.speechSynthesis.speak(utt);
                                                        }}
                                                    >
                                                        <i className="fas fa-play"></i>
                                                        {followUpQuestion.target_word}
                                                    </button>
                                                    <span className="vs">vs</span>
                                                    {followUpQuestion.practice_words?.[0] && (
                                                        <button
                                                            className="pair-word"
                                                            onClick={() => {
                                                                const utt = new SpeechSynthesisUtterance(followUpQuestion.practice_words[0]);
                                                                utt.lang = 'en-GB';
                                                                utt.rate = 0.8;
                                                                window.speechSynthesis.speak(utt);
                                                            }}
                                                        >
                                                            <i className="fas fa-play"></i>
                                                            {followUpQuestion.practice_words[0]}
                                                        </button>
                                                    )}
                                                </div>
                                                {followUpQuestion.phoneme_description && (
                                                    <p className="phoneme-tip"><FontAwesomeIcon icon={faLightbulb} /> {followUpQuestion.phoneme_description}</p>
                                                )}
                                            </div>
                                        )}

                                        {/* Drill Sentence */}
                                        {followUpQuestion.drill_sentence && (
                                            <div className="drill-card drill-sentence">
                                                <h5><FontAwesomeIcon icon={faComments} /> Practice Sentence</h5>
                                                <div className="sentence-with-audio">
                                                    <p>"{followUpQuestion.drill_sentence}"</p>
                                                    <button
                                                        className="sentence-play-btn"
                                                        onClick={() => {
                                                            const utt = new SpeechSynthesisUtterance(followUpQuestion.drill_sentence);
                                                            utt.lang = 'en-GB';
                                                            utt.rate = 0.85;
                                                            window.speechSynthesis.speak(utt);
                                                        }}
                                                    >
                                                        <i className="fas fa-volume-up"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        )}

                                        {/* Next Sentence Suggestion */}
                                        {followUpQuestion.next_sentence && (
                                            <div className="drill-card next-sentence">
                                                <h5><FontAwesomeIcon icon={faArrowRight} /> Try This Next</h5>
                                                <div className="sentence-with-audio">
                                                    <p>"{followUpQuestion.next_sentence}"</p>
                                                    <button
                                                        className="sentence-play-btn"
                                                        onClick={() => {
                                                            const utt = new SpeechSynthesisUtterance(followUpQuestion.next_sentence);
                                                            utt.lang = 'en-GB';
                                                            utt.rate = 0.85;
                                                            window.speechSynthesis.speak(utt);
                                                        }}
                                                    >
                                                        <i className="fas fa-volume-up"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        )}

                                        {/* Practice Words Chips */}
                                        {followUpQuestion.practice_words?.length > 0 && (
                                            <div className="practice-words-section">
                                                <h5><FontAwesomeIcon icon={faBullseye} /> Practice These Words:</h5>
                                                <div className="word-chips">
                                                    {followUpQuestion.practice_words.map((word, idx) => (
                                                        <button
                                                            key={idx}
                                                            className="word-chip"
                                                            onClick={() => {
                                                                const utt = new SpeechSynthesisUtterance(word);
                                                                utt.lang = 'en-GB';
                                                                utt.rate = 0.8;
                                                                window.speechSynthesis.speak(utt);
                                                            }}
                                                        >
                                                            <i className="fas fa-play-circle"></i> {word}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Difficulty Indicator */}
                                        {followUpQuestion.difficulty && (
                                            <div className="difficulty-badge">
                                                Difficulty: <span className={`difficulty-${followUpQuestion.difficulty}`}>
                                                    {followUpQuestion.difficulty}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Practice History Panel - Multiple Attempts */}
                                {practiceHistory.length > 0 && (
                                    <div className="analysis-section">
                                        <h5><FontAwesomeIcon icon={faHistory} /> Practice History ({practiceHistory.length} attempts)</h5>
                                        <div className="practice-history-list">
                                            {practiceHistory.map((entry, idx) => (
                                                <div
                                                    key={entry.id}
                                                    className={`history-item ${selectedHistoryIndex === idx ? 'selected' : ''}`}
                                                    onClick={() => {
                                                        setSelectedHistoryIndex(idx);
                                                        setAnalysisResult(entry.result);
                                                        setWordAnalyses(entry.result.word_analyses || []);
                                                        setSelectedWord(null);
                                                    }}
                                                >
                                                    <div className="history-item-header">
                                                        <span className="attempt-number">#{idx + 1}</span>
                                                        <span className="attempt-time">{entry.timestamp}</span>
                                                        <span
                                                            className="attempt-score"
                                                            style={{ color: getScoreColor(entry.overallScore) }}
                                                        >
                                                            {entry.overallScore}%
                                                        </span>
                                                    </div>
                                                    <div className="history-item-text">
                                                        {entry.transcribedText?.substring(0, 50)}
                                                        {entry.transcribedText?.length > 50 ? '...' : ''}
                                                    </div>
                                                    {entry.audioUrl && (
                                                        <button
                                                            className="history-play-btn"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                const audio = new Audio(entry.audioUrl);
                                                                audio.play();
                                                            }}
                                                        >
                                                            <i className="fas fa-play"></i> Play
                                                        </button>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                        {practiceHistory.length > 1 && (
                                            <div className="history-comparison">
                                                <div className="comparison-stat">
                                                    <span>Best Score:</span>
                                                    <span style={{ color: '#4caf50', fontWeight: 'bold' }}>
                                                        {Math.max(...practiceHistory.map(h => h.overallScore))}%
                                                    </span>
                                                </div>
                                                <div className="comparison-stat">
                                                    <span>Improvement:</span>
                                                    <span style={{
                                                        color: practiceHistory[practiceHistory.length - 1].overallScore > practiceHistory[0].overallScore
                                                            ? '#4caf50' : '#ff9800',
                                                        fontWeight: 'bold'
                                                    }}>
                                                        {practiceHistory[practiceHistory.length - 1].overallScore - practiceHistory[0].overallScore > 0 ? '+' : ''}
                                                        {(practiceHistory[practiceHistory.length - 1].overallScore - practiceHistory[0].overallScore).toFixed(1)}%
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Conversation Area */}
                    <div className="conversation-area">
                        <div className="conversation-container" ref={conversationContainerRef}>
                            {messages.map((message, index) => (
                                <div key={index} className={`message ${message.sender}`}>
                                    <div className="message-avatar">
                                        <i className={`fas fa-${message.sender === 'ai' ? 'robot' : 'user'}`}></i>
                                    </div>
                                    <div className="message-content">
                                        {message.text}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Hidden audio elements */}
                    <audio ref={userAudioRef} hidden />
                    <audio ref={refAudioRef} hidden />
                </div>
            </div>
        </div>
    );
};

export default LiveCall;