// src/components/Practice.js
import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import PracticeGrid from './practice/PracticeGrid';
import ConversationModal from './practice/ConversationModal';
import PronunciationModal from './practice/PronunciationModal';
import { authAPI } from '../services/api';
import './Practice.css';

/**
 * Practice component - Main practice page showing different practice modules
 */
const Practice = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  const [activeModal, setActiveModal] = useState(null);

  // Toggle sidebar expanded/collapsed state
  const toggleSidebar = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    localStorage.setItem('sidebarCollapsed', newState);
  };

  // Toggle profile dropdown visibility
  const toggleProfileDropdown = () => {
    setShowProfileDropdown(!showProfileDropdown);
  };

  // Open and close modal functions
  const openModal = (type) => {
    setActiveModal(type);
  };

  const closeModal = () => {
    setActiveModal(null);
  };

  // Close modal when clicking outside
  const handleOutsideClick = (event) => {
    if (event.target.classList.contains('modal')) {
      closeModal();
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const dropdown = document.getElementById('profileDropdown');
      const profileIcon = document.querySelector('.profile-icon');

      if (dropdown && profileIcon &&
        !profileIcon.contains(event.target) &&
        !dropdown.contains(event.target)) {
        setShowProfileDropdown(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    window.addEventListener('click', handleOutsideClick);

    // Check for saved sidebar state on component mount
    const savedSidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
    setSidebarCollapsed(savedSidebarState);

    return () => {
      document.removeEventListener('click', handleClickOutside);
      window.removeEventListener('click', handleOutsideClick);
    };
  }, []);

  return (
    <div className="practice-page">
      {/* Reuse the Sidebar component */}
      <Sidebar
        isCollapsed={sidebarCollapsed}
        toggleSidebar={toggleSidebar}
      />

      {/* Main content */}
      <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
        <div className="practice-container">
          {/* Practice header section */}
          <div className="practice-header">
            <h1>Practice Modules</h1>
            <p>Choose a practice module to improve your language skills</p>
          </div>

          {/* Practice grid section */}
          <PracticeGrid openModal={openModal} />
        </div>
      </div>

      {/* User Profile Dropdown */}
      <div className="user-profile">
        <div className="profile-icon" onClick={toggleProfileDropdown}>
          <i className="fas fa-user"></i>
        </div>
        <div className={`profile-dropdown ${showProfileDropdown ? 'show' : ''}`} id="profileDropdown">
          <a href="#" onClick={(e) => { e.preventDefault(); window.location.href = '/dashboard/settings'; }} className="profile-dropdown-item">
            <i className="fas fa-user-circle"></i>
            <span>My Profile</span>
          </a>
          <a href="#" onClick={(e) => { e.preventDefault(); window.location.href = '/dashboard'; }} className="profile-dropdown-item">
            <i className="fas fa-home"></i>
            <span>Dashboard</span>
          </a>
          <a href="#" onClick={(e) => { e.preventDefault(); window.location.href = '/dashboard/settings'; }} className="profile-dropdown-item">
            <i className="fas fa-cog"></i>
            <span>Settings</span>
          </a>
          <a href="#" onClick={async (e) => { e.preventDefault(); await authAPI.logout(); window.location.href = '/'; }} className="profile-dropdown-item logout-item">
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
        </div>
      </div>

      {/* Practice Modals */}
      {activeModal === 'conversation' && (
        <ConversationModal closeModal={closeModal} />
      )}
      {activeModal === 'pronunciation' && (
        <PronunciationModal closeModal={closeModal} />
      )}
      {/* Other modals would be added here */}
      {activeModal === 'speaking' && (
        <div id="speakingModal" className="modal">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Speaking Exercises</h2>
              <button className="close-modal" onClick={closeModal}>&times;</button>
            </div>
            <div className="practice-area">
              <div className="chat-container">
                <div className="chat-message ai">
                  <div className="message-content">
                    Let's practice speaking about your favorite hobby. Click the record button when you're ready.
                  </div>
                </div>
              </div>
              <div className="recording-controls">
                <button className="record-btn">
                  <i className="fas fa-microphone"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {activeModal === 'shadowing' && (
        <div id="shadowingModal" className="modal">
          <div className="modal-content">
            <div className="modal-header">
              <h2>Shadowing Practice</h2>
              <button className="close-modal" onClick={closeModal}>&times;</button>
            </div>
            <div className="practice-area">
              <div className="chat-container">
                <div className="chat-message ai">
                  <div className="message-content">
                    Listen to the audio and try to repeat it with the same pronunciation and intonation.
                  </div>
                </div>
              </div>
              <div className="recording-controls">
                <button className="record-btn">
                  <i className="fas fa-microphone"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Practice; 