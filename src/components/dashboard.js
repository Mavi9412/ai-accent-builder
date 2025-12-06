// src/components/dashboard.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import StatsGrid from './StatsGrid';
import ModulesGrid from './ModulesGrid';
import AnalyticsSection from './AnalyticsSection';
import { useAuth } from '../contexts/AuthContext';
import './dashboard.css';

/**
 * Main Dashboard component for the AI ACCENT learning platform
 * Displays user information, learning stats, modules and analytics charts
 */
const Dashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);

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
    
    // Check for saved sidebar state on component mount
    const savedSidebarState = localStorage.getItem('sidebarCollapsed') === 'true';
    setSidebarCollapsed(savedSidebarState);
    
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, []);

  return (
    <div className="dashboard-container">
      <Sidebar 
        isCollapsed={sidebarCollapsed} 
        toggleSidebar={toggleSidebar} 
      />

      <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
        <div className="dashboard">
          <div className="dashboard-header">
            <div className="user-welcome">
              <div className="user-avatar">
                <i className="fas fa-user"></i>
              </div>
              <div className="user-info">
                <h2>Welcome back, {user?.full_name || 'User'}!</h2>
                <div className="level-badge">{user?.level || 'B2 - Upper Intermediate'}</div>
              </div>
            </div>
            <div className="user-profile">
              <div className="profile-icon" onClick={toggleProfileDropdown}>
                <i className="fas fa-user"></i>
                <span className="notification-badge">3</span>
              </div>
              <div className={`profile-dropdown ${showProfileDropdown ? 'show' : ''}`} id="profileDropdown">
                <a href="profile.html" className="profile-dropdown-item">
                  <i className="fas fa-user-circle"></i>
                  <span>My Profile</span>
                </a>
                <a href="#" onClick={(e) => { e.preventDefault(); navigate('/dashboard/settings'); }} className="profile-dropdown-item">
                  <i className="fas fa-cog"></i>
                  <span>Settings</span>
                </a>
                <a href="#" onClick={(e) => { e.preventDefault(); navigate('/dashboard/progress'); }} className="profile-dropdown-item">
                  <i className="fas fa-bell"></i>
                  <span>Progress</span>
                </a>
                <a href="#" onClick={(e) => { e.preventDefault(); logout(); navigate('/'); }} className="profile-dropdown-item">
                  <i className="fas fa-sign-out-alt"></i>
                  <span>Logout</span>
                </a>
              </div>
            </div>
          </div>

          <StatsGrid />
          <ModulesGrid />
          <AnalyticsSection />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
