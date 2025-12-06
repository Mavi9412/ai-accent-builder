import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../Sidebar';
import { useAuth } from '../../contexts/AuthContext';
import { userAPI } from '../../services/api';
import './Settings.css';

/**
 * Settings component - Main settings page for user preferences and account management
 * This component allows users to:
 * - Update their profile information
 * - Manage notification preferences
 * - Change their password
 * - Configure application preferences
 * - Delete their account
 */
const Settings = () => {
  const navigate = useNavigate();
  const { user, logout, updateUser } = useAuth();
  
  // -------------- STATE MANAGEMENT --------------
  // Controls the sidebar collapsed/expanded state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Controls the visibility of the profile dropdown menu
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  
  // -------------- FORM STATE --------------
  // State for profile settings form fields
  const [profileForm, setProfileForm] = useState({
    fullName: user?.full_name || '',         // User's full name
    email: user?.email || '', // User's email address
    language: user?.language || 'english'           // User's preferred learning language
  });
  
  // State for password change form fields
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',  // User's current password for verification
    newPassword: '',      // User's desired new password
    confirmPassword: ''   // Confirmation of new password to ensure accuracy
  });
  
  // State for notification preferences toggles
  const [notifications, setNotifications] = useState({
    email: true,   // Email notifications enabled/disabled
    push: true,    // Push notifications enabled/disabled
    daily: false   // Daily reminder notifications enabled/disabled
  });
  
  // State for application preference toggles
  const [preferences, setPreferences] = useState({
    darkMode: false,          // Dark mode theme enabled/disabled
    soundEffects: true,       // Sound effects enabled/disabled
    progressTracking: true    // Progress tracking enabled/disabled
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  // -------------- EVENT HANDLERS --------------
  /**
   * Toggles sidebar between collapsed and expanded states
   * Also saves the state to localStorage for persistence
   */
  const toggleSidebar = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    localStorage.setItem('sidebarCollapsed', newState);
  };

  /**
   * Toggles the profile dropdown menu visibility
   */
  const toggleProfileDropdown = () => {
    setShowProfileDropdown(!showProfileDropdown);
  };
  
  /**
   * Handles changes to profile form input fields
   * Updates the profileForm state with new values
   * @param {Object} e - Event object from input change
   */
  const handleProfileChange = (e) => {
    const { id, value } = e.target;
    setProfileForm({
      ...profileForm,
      [id]: value
    });
  };
  
  /**
   * Handles changes to password form input fields
   * Updates the passwordForm state with new values
   * @param {Object} e - Event object from input change
   */
  const handlePasswordChange = (e) => {
    const { id, value } = e.target;
    setPasswordForm({
      ...passwordForm,
      [id]: value
    });
  };
  
  /**
   * Handles changes to notification toggle switches
   * Toggles the specified notification type
   * @param {string} type - The notification type to toggle (email, push, daily)
   */
  const handleNotificationChange = (type) => {
    setNotifications({
      ...notifications,
      [type]: !notifications[type]
    });
  };
  
  /**
   * Handles changes to preference toggle switches
   * Toggles the specified preference setting
   * @param {string} type - The preference type to toggle (darkMode, soundEffects, progressTracking)
   */
  const handlePreferenceChange = (type) => {
    setPreferences({
      ...preferences,
      [type]: !preferences[type]
    });
  };
  
  /**
   * Handles profile form submission
   * @param {Object} e - Form submission event
   */
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const updatedUser = await userAPI.updateProfile({
        full_name: profileForm.fullName,
        email: profileForm.email,
        language: profileForm.language
      });
      
      updateUser(updatedUser);
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Failed to update profile' });
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Handles password form submission
   * @param {Object} e - Form submission event
   */
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });
    
    // Validate that new password and confirm password match
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match!' });
      setLoading(false);
      return;
    }

    if (passwordForm.newPassword.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters' });
      setLoading(false);
      return;
    }
    
    try {
      await userAPI.changePassword(passwordForm.currentPassword, passwordForm.newPassword);
      setMessage({ type: 'success', text: 'Password updated successfully!' });
      
      // Reset form fields after successful submission
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Failed to update password' });
    } finally {
      setLoading(false);
    }
  };
  
  /**
   * Handles account deletion request
   */
  const handleDeleteAccount = async () => {
    // Show confirmation dialog to prevent accidental deletions
    const confirmed = window.confirm('Are you sure you want to delete your account? This action cannot be undone.');
    
    if (confirmed) {
      setLoading(true);
      try {
        await userAPI.deleteAccount();
        logout();
        navigate('/');
      } catch (error) {
        setMessage({ type: 'error', text: error.message || 'Failed to delete account' });
        setLoading(false);
      }
    }
  };

  /**
   * Save settings when toggles change
   */
  useEffect(() => {
    const saveSettings = async () => {
      try {
        await userAPI.updateSettings({
          email_notifications: notifications.email,
          push_notifications: notifications.push,
          daily_reminders: notifications.daily,
          dark_mode: preferences.darkMode,
          sound_effects: preferences.soundEffects,
          progress_tracking: preferences.progressTracking
        });
      } catch (error) {
        console.error('Error saving settings:', error);
      }
    };

    // Only save if settings have been loaded (not on initial mount)
    if (user) {
      saveSettings();
    }
  }, [notifications, preferences]);

  // -------------- SIDE EFFECTS --------------
  /**
   * Effect for handling outside clicks and sidebar state persistence
   * - Closes profile dropdown when clicking outside
   * - Loads saved sidebar state from localStorage
   * - Loads user settings from API
   */
  useEffect(() => {
    // Load user settings
    const loadSettings = async () => {
      try {
        const settings = await userAPI.getSettings();
        setNotifications({
          email: settings.email_notifications,
          push: settings.push_notifications,
          daily: settings.daily_reminders
        });
        setPreferences({
          darkMode: settings.dark_mode,
          soundEffects: settings.sound_effects,
          progressTracking: settings.progress_tracking
        });
      } catch (error) {
        console.error('Error loading settings:', error);
      }
    };

    loadSettings();

    // Handler to close dropdown when clicking outside
    const handleClickOutside = (event) => {
      const dropdown = document.getElementById('profileDropdown');
      const profileIcon = document.querySelector('.profile-icon');
      
      if (dropdown && profileIcon && 
          !profileIcon.contains(event.target) && 
          !dropdown.contains(event.target)) {
        setShowProfileDropdown(false);
      }
    };

    // Add click event listener for detecting outside clicks
    document.addEventListener('click', handleClickOutside);
    
    // Load saved sidebar state from localStorage on component mount
    const savedSidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
    setSidebarCollapsed(savedSidebarState);
    
    // Clean up event listener when component unmounts
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, []);

  // -------------- COMPONENT RENDERING --------------
  return (
    <div className="settings-page">
      {/* Sidebar navigation component */}
      <Sidebar 
        isCollapsed={sidebarCollapsed} 
        toggleSidebar={toggleSidebar}
      />

      {/* Main content area */}
      <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
        <div className="settings-container">
          {/* Settings page header */}
          <div className="settings-header">
            <h1>Settings</h1>
            <p>Customize your learning experience and manage your account</p>
            {message.text && (
              <div className={`message ${message.type}`} style={{
                padding: '10px',
                margin: '10px 0',
                borderRadius: '4px',
                backgroundColor: message.type === 'success' ? '#d4edda' : '#f8d7da',
                color: message.type === 'success' ? '#155724' : '#721c24'
              }}>
                {message.text}
              </div>
            )}
          </div>

          {/* Settings cards grid layout */}
          <div className="settings-grid">
            {/* --------- PROFILE SETTINGS CARD --------- */}
            <div className="settings-card">
              <h2><i className="fas fa-user"></i> Profile Settings</h2>
              <form onSubmit={handleProfileSubmit}>
                {/* Full Name field */}
                <div className="form-group">
                  <label htmlFor="fullName">Full Name</label>
                  <input 
                    type="text" 
                    id="fullName" 
                    value={profileForm.fullName} 
                    onChange={handleProfileChange}
                  />
                </div>
                
                {/* Email Address field */}
                <div className="form-group">
                  <label htmlFor="email">Email Address</label>
                  <input 
                    type="email" 
                    id="email" 
                    value={profileForm.email} 
                    onChange={handleProfileChange}
                  />
                </div>
                
                {/* Learning Language dropdown */}
                <div className="form-group">
                  <label htmlFor="language">Learning Language</label>
                  <select 
                    id="language" 
                    value={profileForm.language} 
                    onChange={handleProfileChange}
                  >
                    <option value="english">English</option>
                    <option value="spanish">Spanish</option>
                    <option value="french">French</option>
                    <option value="german">German</option>
                  </select>
                </div>
                
                {/* Profile form buttons */}
                <div className="button-group">
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button type="reset" className="btn btn-secondary" disabled={loading}>Reset</button>
                </div>
              </form>
            </div>

            {/* --------- NOTIFICATION SETTINGS CARD --------- */}
            <div className="settings-card">
              <h2><i className="fas fa-bell"></i> Notification Settings</h2>
              <div className="notification-list">
                {/* Email Notifications toggle */}
                <div className="notification-item">
                  <div className="notification-info">
                    <i className="fas fa-envelope"></i>
                    <span>Email Notifications</span>
                  </div>
                  <label className="toggle-switch">
                    <input 
                      type="checkbox" 
                      checked={notifications.email} 
                      onChange={() => handleNotificationChange('email')}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
                
                {/* Push Notifications toggle */}
                <div className="notification-item">
                  <div className="notification-info">
                    <i className="fas fa-mobile-alt"></i>
                    <span>Push Notifications</span>
                  </div>
                  <label className="toggle-switch">
                    <input 
                      type="checkbox" 
                      checked={notifications.push} 
                      onChange={() => handleNotificationChange('push')}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
                
                {/* Daily Reminders toggle */}
                <div className="notification-item">
                  <div className="notification-info">
                    <i className="fas fa-calendar-alt"></i>
                    <span>Daily Reminders</span>
                  </div>
                  <label className="toggle-switch">
                    <input 
                      type="checkbox" 
                      checked={notifications.daily} 
                      onChange={() => handleNotificationChange('daily')}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
              </div>
            </div>

            {/* --------- SECURITY SETTINGS CARD --------- */}
            <div className="settings-card">
              <h2><i className="fas fa-lock"></i> Security Settings</h2>
              <form onSubmit={handlePasswordSubmit}>
                {/* Current Password field */}
                <div className="form-group">
                  <label htmlFor="currentPassword">Current Password</label>
                  <input 
                    type="password" 
                    id="currentPassword" 
                    value={passwordForm.currentPassword} 
                    onChange={handlePasswordChange}
                  />
                </div>
                
                {/* New Password field */}
                <div className="form-group">
                  <label htmlFor="newPassword">New Password</label>
                  <input 
                    type="password" 
                    id="newPassword" 
                    value={passwordForm.newPassword} 
                    onChange={handlePasswordChange}
                  />
                </div>
                
                {/* Confirm New Password field */}
                <div className="form-group">
                  <label htmlFor="confirmPassword">Confirm New Password</label>
                  <input 
                    type="password" 
                    id="confirmPassword" 
                    value={passwordForm.confirmPassword} 
                    onChange={handlePasswordChange}
                  />
                </div>
                
                {/* Password form button */}
                <div className="button-group">
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? 'Updating...' : 'Update Password'}
                  </button>
                </div>
              </form>
            </div>

            {/* --------- PREFERENCES CARD --------- */}
            <div className="settings-card">
              <h2><i className="fas fa-cog"></i> Preferences</h2>
              
              {/* Dark Mode toggle */}
              <div className="toggle-group">
                <div className="toggle-label">
                  <i className="fas fa-moon"></i>
                  <span>Dark Mode</span>
                </div>
                <label className="toggle-switch">
                  <input 
                    type="checkbox" 
                    checked={preferences.darkMode} 
                    onChange={() => handlePreferenceChange('darkMode')}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              
              {/* Sound Effects toggle */}
              <div className="toggle-group">
                <div className="toggle-label">
                  <i className="fas fa-volume-up"></i>
                  <span>Sound Effects</span>
                </div>
                <label className="toggle-switch">
                  <input 
                    type="checkbox" 
                    checked={preferences.soundEffects} 
                    onChange={() => handlePreferenceChange('soundEffects')}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              
              {/* Progress Tracking toggle */}
              <div className="toggle-group">
                <div className="toggle-label">
                  <i className="fas fa-chart-line"></i>
                  <span>Progress Tracking</span>
                </div>
                <label className="toggle-switch">
                  <input 
                    type="checkbox" 
                    checked={preferences.progressTracking} 
                    onChange={() => handlePreferenceChange('progressTracking')}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              
              {/* Delete Account button */}
              <div className="button-group">
                <button 
                  className="btn btn-danger" 
                  onClick={handleDeleteAccount}
                  disabled={loading}
                >
                  {loading ? 'Deleting...' : 'Delete Account'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* User Profile Dropdown Menu */}
      <div className="user-profile">
        {/* Profile icon with notification badge */}
        <div className="profile-icon" onClick={toggleProfileDropdown}>
          <i className="fas fa-user"></i>
          <span className="notification-badge">3</span>
        </div>
        
        {/* Dropdown menu for user profile options */}
        <div className={`profile-dropdown ${showProfileDropdown ? 'show' : ''}`} id="profileDropdown">
          <a href="profile.html" className="profile-dropdown-item">
            <i className="fas fa-user-circle"></i>
            <span>My Profile</span>
          </a>
          <a href="settings.html" className="profile-dropdown-item">
            <i className="fas fa-cog"></i>
            <span>Settings</span>
          </a>
          <a href="notifications.html" className="profile-dropdown-item">
            <i className="fas fa-bell"></i>
            <span>Notifications</span>
            <span className="notification-badge" style={{marginLeft: 'auto'}}>3</span>
          </a>
          <a href="index.html" className="profile-dropdown-item">
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
        </div>
      </div>
    </div>
  );
};

export default Settings; 