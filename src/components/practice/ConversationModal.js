import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { grammarAPI } from '../../services/api';

/**
 * ConversationModal component - Modal for conversation practice with AI
 * Features: Grammar checking, spelling, style suggestions, word alternatives
 * @param {Function} closeModal - Function to close the modal
 */
const ConversationModal = ({ closeModal }) => {
  const [messages, setMessages] = useState([
    {
      type: 'ai',
      content: "Hello! I'm your AI conversation partner. Type a message and I'll check your grammar, spelling, and suggest improvements!"
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [activeFeedback, setActiveFeedback] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showGrammarPanel, setShowGrammarPanel] = useState(false);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const chatContainerRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle sending messages with grammar check
  const handleSendMessage = async () => {
    if (inputValue.trim()) {
      const userText = inputValue.trim();

      // Add user message
      const userMessage = { type: 'user', content: userText };
      setMessages(prev => [...prev, userMessage]);
      setInputValue('');
      setIsAnalyzing(true);

      try {
        // Call grammar API for full analysis
        const analysis = await grammarAPI.fullCheck(userText);
        setCurrentAnalysis(analysis);

        // Build structured response - only show errors/suggestions/warnings
        const grammarErrors = analysis.grammar?.grammar_errors || [];
        const spellingErrors = analysis.grammar?.spelling_errors || [];
        const styleErrors = analysis.grammar?.style_suggestions || [];
        const missingParts = analysis.nlp_analysis?.missing_parts || [];
        const score = analysis.overall_score || 0;
        const allErrors = [...grammarErrors, ...spellingErrors];

        // Create structured message with inline errors
        const aiMessageData = {
          type: 'ai',
          isStructured: true,
          originalText: userText,
          errors: allErrors,
          styleErrors: styleErrors,
          warnings: missingParts,
          correctedText: analysis.grammar?.corrected_text,
          score: Math.round(score),
          hasErrors: allErrors.length > 0 || styleErrors.length > 0 || missingParts.length > 0
        };

        // Add AI message
        setMessages(prev => [...prev, aiMessageData]);

        setShowGrammarPanel(true);

      } catch (error) {
        console.error('Grammar check error:', error);
        setMessages(prev => [...prev, {
          type: 'ai',
          content: "I couldn't analyze your message right now. Let's continue our conversation! What else would you like to discuss?"
        }]);
      } finally {
        setIsAnalyzing(false);
      }
    }
  };

  // Handle pressing enter to send
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isAnalyzing) {
      handleSendMessage();
    }
  };

  // Handle feedback selection and save practice session
  const handleFeedback = async (type) => {
    setActiveFeedback(type);

    try {
      const { progressAPI } = await import('../../services/api');
      const durationMinutes = Math.floor(messages.length * 0.5);
      const accuracy = type === 'helpful' ? 85 : type === 'neutral' ? 70 : 50;

      await progressAPI.createPracticeSession({
        practice_type: 'conversation',
        accuracy: accuracy,
        duration_minutes: durationMinutes,
        notes: `Feedback: ${type}`
      });
    } catch (error) {
      console.error('Error saving practice session:', error);
    }
  };

  // Render message content with formatting
  const renderMessageContent = (content) => {
    // Split by newlines and bold markers
    return content.split('\n').map((line, idx) => {
      // Handle bold text **text**
      const parts = line.split(/(\*\*.*?\*\*)/g);
      return (
        <div key={idx} style={{ marginBottom: idx < content.split('\n').length - 1 ? '8px' : 0 }}>
          {parts.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
            }
            return <span key={pIdx}>{part}</span>;
          })}
        </div>
      );
    });
  };

  return (
    <div className="modal" style={{ overflow: 'auto' }}>
      <div className="modal-content" style={{ maxWidth: '900px', maxHeight: '85vh', overflow: 'auto', margin: '30px auto' }}>
        <div className="modal-header" style={{
          background: 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
          margin: '-30px -30px 20px -30px',
          padding: '20px 30px',
          borderRadius: '12px 12px 0 0'
        }}>
          <h2 style={{ color: 'white', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <i className="fas fa-comments"></i>
            Conversation Practice
            <span style={{
              fontSize: '12px',
              background: 'rgba(255,255,255,0.2)',
              padding: '4px 10px',
              borderRadius: '10px',
              marginLeft: '10px'
            }}>
              Grammar Check Active
            </span>
          </h2>
          <button className="close-modal" onClick={closeModal} style={{ color: 'white' }}>&times;</button>
        </div>

        {/* Grammar Features Info */}
        <div style={{
          background: 'linear-gradient(135deg, #e8f4fd 0%, #d6e9f8 100%)',
          borderRadius: '10px',
          padding: '12px 15px',
          marginBottom: '15px',
          display: 'flex',
          alignItems: 'center',
          gap: '15px',
          flexWrap: 'wrap',
          border: '1px solid #4a90e2'
        }}>
          <span style={{ fontWeight: '600', color: '#2c3e50' }}>
            <i className="fas fa-magic" style={{ marginRight: '5px', color: '#4a90e2' }}></i>
            Features:
          </span>
          <span style={{ fontSize: '12px', color: '#495057', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <i className="fas fa-spell-check" style={{ color: '#4a90e2' }}></i> Grammar & Spelling
          </span>
          <span style={{ fontSize: '12px', color: '#495057', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <i className="fas fa-lightbulb" style={{ color: '#357ABD' }}></i> Style Suggestions
          </span>
          <span style={{ fontSize: '12px', color: '#495057', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <i className="fas fa-sync-alt" style={{ color: '#4a90e2' }}></i> Word Alternatives
          </span>
          <span style={{ fontSize: '12px', color: '#495057', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <i className="fas fa-brain" style={{ color: '#4a90e2' }}></i> AI Rephrasing
          </span>
        </div>

        <div className="practice-area" style={{ background: '#f8f9fa', borderRadius: '12px', padding: '15px' }}>
          <div className="chat-container" ref={chatContainerRef} style={{
            height: '350px',
            overflowY: 'auto',
            padding: '10px',
            background: 'white',
            borderRadius: '10px',
            border: '1px solid #e9ecef'
          }}>
            {messages.map((message, index) => (
              <div key={index} className={`chat-message ${message.type}`} style={{
                marginBottom: '15px',
                display: 'flex',
                justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start'
              }}>
                <div className="message-content" style={{
                  maxWidth: '80%',
                  padding: '12px 16px',
                  borderRadius: message.type === 'user' ? '15px 15px 5px 15px' : '15px 15px 15px 5px',
                  background: message.type === 'user'
                    ? 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)'
                    : 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                  color: message.type === 'user' ? 'white' : '#2c3e50',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  fontSize: '14px',
                  lineHeight: '1.5'
                }}>
                  {message.type === 'ai' ? (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <i className="fas fa-user-graduate" style={{ color: '#4a90e2' }}></i>
                        <span style={{ fontWeight: '600', fontSize: '12px', color: '#4a90e2' }}>AI Grammar Coach</span>
                      </div>
                      {message.isStructured ? (
                        <div>
                          <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{
                              background: message.score >= 80 ? '#28a745' : message.score >= 60 ? '#ffc107' : '#dc3545',
                              color: 'white',
                              padding: '3px 10px',
                              borderRadius: '12px',
                              fontSize: '12px',
                              fontWeight: '600'
                            }}>
                              Score: {message.score}%
                            </span>
                            {!message.hasErrors && (
                              <span style={{ color: '#28a745', fontSize: '13px' }}>
                                <i className="fas fa-check-circle" style={{ marginRight: '4px' }}></i>
                                Great job! No issues found.
                              </span>
                            )}
                          </div>
                          {message.originalText && (
                            <div style={{ background: '#f8f9fa', padding: '8px 12px', borderRadius: '8px', marginBottom: '10px', fontSize: '13px', borderLeft: '3px solid #4a90e2' }}>
                              <strong>Your text:</strong> {message.originalText}
                            </div>
                          )}
                          {message.errors && message.errors.length > 0 && (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontWeight: '600', color: '#dc3545', marginBottom: '5px', fontSize: '12px' }}>
                                <i className="fas fa-times-circle" style={{ marginRight: '5px' }}></i>Errors Found:
                              </div>
                              {message.errors.map((error, idx) => (
                                <div key={idx} style={{ background: '#fff5f5', padding: '8px 10px', borderRadius: '6px', marginBottom: '5px', fontSize: '12px', borderLeft: '3px solid #dc3545' }}>
                                  <span style={{ color: '#dc3545', fontWeight: '500' }}>"{error.text || error.word}"</span>
                                  <span style={{ color: '#6c757d' }}> → </span>
                                  <span style={{ color: '#28a745', fontWeight: '500' }}>{error.suggestion || (error.suggestions && error.suggestions[0]) || 'Check this'}</span>
                                  {error.message && <div style={{ color: '#6c757d', marginTop: '3px' }}>{error.message}</div>}
                                </div>
                              ))}
                            </div>
                          )}
                          {message.styleErrors && message.styleErrors.length > 0 && (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontWeight: '600', color: '#4a90e2', marginBottom: '5px', fontSize: '12px' }}>
                                <i className="fas fa-lightbulb" style={{ marginRight: '5px' }}></i>Style Suggestions:
                              </div>
                              {message.styleErrors.map((suggestion, idx) => (
                                <div key={idx} style={{ background: '#e8f4fd', padding: '8px 10px', borderRadius: '6px', marginBottom: '5px', fontSize: '12px', borderLeft: '3px solid #4a90e2' }}>
                                  {suggestion.message || suggestion.text || suggestion}
                                </div>
                              ))}
                            </div>
                          )}
                          {message.warnings && message.warnings.length > 0 && (
                            <div style={{ marginBottom: '10px' }}>
                              <div style={{ fontWeight: '600', color: '#357ABD', marginBottom: '5px', fontSize: '12px' }}>
                                <i className="fas fa-exclamation-triangle" style={{ marginRight: '5px' }}></i>Suggestions:
                              </div>
                              {message.warnings.map((warning, idx) => (
                                <div key={idx} style={{ background: '#e8f4fd', padding: '8px 10px', borderRadius: '6px', marginBottom: '5px', fontSize: '12px', borderLeft: '3px solid #357ABD' }}>
                                  {typeof warning === 'string' ? warning : warning.message || warning.text}
                                </div>
                              ))}
                            </div>
                          )}
                          {message.correctedText && message.correctedText !== message.originalText && (
                            <div style={{ background: '#e8f5e9', padding: '8px 12px', borderRadius: '8px', fontSize: '13px', borderLeft: '3px solid #28a745' }}>
                              <strong style={{ color: '#28a745' }}>Suggested:</strong> {message.correctedText}
                            </div>
                          )}
                        </div>
                      ) : (
                        renderMessageContent(message.content || '')
                      )}
                    </div>
                  ) : (
                    message.content
                  )}
                </div>
              </div>
            ))}

            {/* Analyzing indicator */}
            {isAnalyzing && (
              <div className="chat-message ai" style={{ marginBottom: '15px' }}>
                <div className="message-content" style={{
                  padding: '12px 16px',
                  borderRadius: '15px 15px 15px 5px',
                  background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#4a90e2' }}>
                    <i className="fas fa-spinner fa-spin"></i>
                    <span>Analyzing grammar, spelling, and style...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input area */}
          <div className="message-input" style={{
            marginTop: '15px',
            display: 'flex',
            gap: '10px'
          }}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (I'll check your grammar!)"
              disabled={isAnalyzing}
              style={{
                flex: 1,
                padding: '14px 18px',
                borderRadius: '25px',
                border: '2px solid #e9ecef',
                fontSize: '14px',
                transition: 'border-color 0.2s ease',
                outline: 'none'
              }}
            />
            <button
              onClick={handleSendMessage}
              disabled={isAnalyzing || !inputValue.trim()}
              style={{
                padding: '14px 25px',
                borderRadius: '25px',
                border: 'none',
                background: isAnalyzing ? '#6c757d' : 'linear-gradient(135deg, #4a90e2 0%, #357ABD 100%)',
                color: 'white',
                fontWeight: '600',
                cursor: isAnalyzing ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
              }}
            >
              {isAnalyzing ? (
                <>
                  <i className="fas fa-spinner fa-spin"></i>
                  Checking...
                </>
              ) : (
                <>
                  <i className="fas fa-paper-plane"></i>
                  Send
                </>
              )}
            </button>
          </div>
        </div>

        {/* Current Analysis Panel */}
        {currentAnalysis && showGrammarPanel && (
          <div style={{
            marginTop: '15px',
            background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
            borderRadius: '12px',
            padding: '15px',
            border: '1px solid #e9ecef'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '12px'
            }}>
              <span style={{ fontWeight: '600', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <i className="fas fa-chart-bar" style={{ color: '#4a90e2' }}></i>
                Last Analysis Summary
              </span>
              <button
                onClick={() => setShowGrammarPanel(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#6c757d',
                  cursor: 'pointer',
                  fontSize: '16px'
                }}
              >
                <i className="fas fa-times"></i>
              </button>
            </div>

            <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
              {/* Score */}
              <div style={{
                background: currentAnalysis.overall_score >= 80 ? '#d4edda' :
                  currentAnalysis.overall_score >= 60 ? '#fff3cd' : '#f8d7da',
                padding: '10px 15px',
                borderRadius: '10px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2c3e50' }}>
                  {Math.round(currentAnalysis.overall_score || 0)}
                </div>
                <div style={{ fontSize: '11px', color: '#6c757d' }}>Score</div>
              </div>

              {/* Grammar Errors */}
              <div style={{
                background: '#e8f4fd',
                padding: '10px 15px',
                borderRadius: '10px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#4a90e2' }}>
                  {currentAnalysis.grammar?.grammar_errors?.length || 0}
                </div>
                <div style={{ fontSize: '11px', color: '#6c757d' }}>Grammar</div>
              </div>

              {/* Spelling Errors */}
              <div style={{
                background: '#e8f4fd',
                padding: '10px 15px',
                borderRadius: '10px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#357ABD' }}>
                  {currentAnalysis.grammar?.spelling_errors?.length || 0}
                </div>
                <div style={{ fontSize: '11px', color: '#6c757d' }}>Spelling</div>
              </div>

              {/* Word Count */}
              <div style={{
                background: '#e8f4fd',
                padding: '10px 15px',
                borderRadius: '10px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#4a90e2' }}>
                  {currentAnalysis.nlp_analysis?.word_count || 0}
                </div>
                <div style={{ fontSize: '11px', color: '#6c757d' }}>Words</div>
              </div>

              {/* Complexity */}
              <div style={{
                background: '#e8f4fd',
                padding: '10px 15px',
                borderRadius: '10px',
                textAlign: 'center',
                minWidth: '80px'
              }}>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#4a90e2', textTransform: 'capitalize' }}>
                  {currentAnalysis.nlp_analysis?.complexity?.level || 'N/A'}
                </div>
                <div style={{ fontSize: '11px', color: '#6c757d' }}>Complexity</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

ConversationModal.propTypes = {
  closeModal: PropTypes.func.isRequired
};

export default ConversationModal;
