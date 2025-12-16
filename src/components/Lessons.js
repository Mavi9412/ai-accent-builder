// src/components/Lessons.js
import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import CourseGrid from './lessons/CourseGrid';
import LessonList from './lessons/LessonList';
import { authAPI } from '../services/api';
import './Lessons.css'; // Will create this file next

/**
 * Lessons component - Main lessons page showing available courses and lesson details
 */
const Lessons = () => {
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
    <div className="lessons-page">
      {/* Reuse the Sidebar component */}
      <Sidebar
        isCollapsed={sidebarCollapsed}
        toggleSidebar={toggleSidebar}
      />

      {/* Main content */}
      <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
        <div className="lessons-container">
          {/* Lessons header section */}
          <div className="lessons-header">
            <h1>Language Learning Courses</h1>
            <p>Explore our comprehensive courses designed to help you master the language</p>
          </div>

          {/* Course grid section */}
          <CourseGrid />

          {/* Lesson list section */}
          <LessonList />
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
    </div>
  );
};

export default Lessons; 