import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './Sidebar';
import './LiveCall.css';

const LiveCall = () => {
    const [isMuted, setIsMuted] = useState(false);
    const [isVideoOff, setIsVideoOff] = useState(false);
    const [isScreenSharing, setIsScreenSharing] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [messages, setMessages] = useState([
        {
            sender: 'ai',
            text: "Hello! I'm your AI language partner. Let's practice speaking together. How are you today?"
        }
    ]);
    const [newMessage, setNewMessage] = useState('');
    const localVideoRef = useRef(null);
    const conversationContainerRef = useRef(null);

    useEffect(() => {
        initializeVideo();
        // Check for saved sidebar state
        const savedSidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
        setSidebarCollapsed(savedSidebarState);
    }, []);

    const toggleSidebar = () => {
        const newState = !sidebarCollapsed;
        setSidebarCollapsed(newState);
        localStorage.setItem('sidebarCollapsed', newState);
    };

    const initializeVideo = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            if (localVideoRef.current) {
                localVideoRef.current.srcObject = stream;
            }
        } catch (error) {
            console.error('Error accessing media devices:', error);
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

    const toggleMute = () => {
        setIsMuted(!isMuted);
    };

    const toggleVideo = () => {
        setIsVideoOff(!isVideoOff);
    };

    const toggleScreen = () => {
        setIsScreenSharing(!isScreenSharing);
    };

    const endCall = () => {
        window.location.href = '/dashboard';
    };

    return (
        <div className="dashboard-container">
            <Sidebar 
                isCollapsed={sidebarCollapsed} 
                toggleSidebar={toggleSidebar} 
            />
            <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
                <div className="call-container">
                    <div className="video-container">
                        <div className="main-video">
                            <video ref={localVideoRef} autoPlay muted></video>
                            <div className="ai-avatar">
                                <i className="fas fa-robot"></i>
                            </div>
                        </div>
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
                        <div className="message-input">
                            <input
                                type="text"
                                value={newMessage}
                                onChange={(e) => setNewMessage(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Type your message..."
                            />
                            <button onClick={sendMessage}>
                                <i className="fas fa-paper-plane"></i>
                            </button>
                        </div>
                        <div className="video-controls">
                            <button className={`control-btn ${isMuted ? 'muted' : ''}`} onClick={toggleMute}>
                                <i className={`fas fa-microphone${isMuted ? '-slash' : ''}`}></i>
                            </button>
                            <button className={`control-btn ${isVideoOff ? 'video-off' : ''}`} onClick={toggleVideo}>
                                <i className={`fas fa-video${isVideoOff ? '-slash' : ''}`}></i>
                            </button>
                            <button className="control-btn" onClick={toggleScreen}>
                                <i className={`fas fa-${isScreenSharing ? 'stop-circle' : 'desktop'}`}></i>
                            </button>
                            <button className="control-btn end-call" onClick={endCall}>
                                <i className="fas fa-phone-slash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LiveCall; 