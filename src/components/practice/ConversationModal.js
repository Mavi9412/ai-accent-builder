import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

/**
 * ConversationModal component - Modal for conversation practice with AI
 * @param {Function} closeModal - Function to close the modal
 */
const ConversationModal = ({ closeModal }) => {
  const [messages, setMessages] = useState([
    {
      type: 'ai',
      content: "Hello! I'm your AI conversation partner. How can I help you practice today?"
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [activeFeedback, setActiveFeedback] = useState(null);
  const chatContainerRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle sending messages
  const handleSendMessage = () => {
    if (inputValue.trim()) {
      // Add user message
      const updatedMessages = [
        ...messages,
        { type: 'user', content: inputValue.trim() }
      ];
      setMessages(updatedMessages);
      setInputValue('');
      
      // Simulate AI response after a short delay
      setTimeout(() => {
        setMessages([
          ...updatedMessages,
          { 
            type: 'ai', 
            content: "That's a great point! Let's continue our conversation. What else would you like to discuss?"
          }
        ]);
      }, 1000);
    }
  };

  // Handle pressing enter to send
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  // Handle feedback selection and save practice session
  const handleFeedback = async (type) => {
    setActiveFeedback(type);
    
    try {
      const { progressAPI } = await import('../../services/api');
      // Calculate session duration (simplified - in real app, track start/end time)
      const durationMinutes = Math.floor(messages.length * 0.5); // Estimate
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

  return (
    <div className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Conversation Practice</h2>
          <button className="close-modal" onClick={closeModal}>&times;</button>
        </div>
        <div className="practice-area">
          <div className="chat-container" ref={chatContainerRef}>
            {messages.map((message, index) => (
              <div key={index} className={`chat-message ${message.type}`}>
                <div className="message-content">
                  {message.content}
                </div>
              </div>
            ))}
          </div>
          <div className="message-input">
            <input 
              type="text" 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
            />
            <button onClick={handleSendMessage}>Send</button>
          </div>
        </div>
        <div className="feedback-container">
          <h3 className="feedback-title">Was this conversation helpful?</h3>
          <div className="feedback-buttons">
            <button 
              className={`feedback-btn ${activeFeedback === 'helpful' ? 'active' : ''}`}
              onClick={() => handleFeedback('helpful')}
            >
              Helpful
            </button>
            <button 
              className={`feedback-btn ${activeFeedback === 'neutral' ? 'active' : ''}`}
              onClick={() => handleFeedback('neutral')}
            >
              Neutral
            </button>
            <button 
              className={`feedback-btn ${activeFeedback === 'not-helpful' ? 'active' : ''}`}
              onClick={() => handleFeedback('not-helpful')}
            >
              Not Helpful
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

ConversationModal.propTypes = {
  closeModal: PropTypes.func.isRequired
};

export default ConversationModal; 