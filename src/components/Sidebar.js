import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import PropTypes from 'prop-types';

/**
 * Sidebar navigation component
 * @param {boolean} isCollapsed - Whether sidebar is in collapsed state
 * @param {function} toggleSidebar - Function to toggle sidebar state
 */
const Sidebar = ({ isCollapsed, toggleSidebar }) => {
  const location = useLocation();
  const path = location.pathname;
  
  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <h2>AI ACCENT</h2>
        <button className="toggle-sidebar" onClick={toggleSidebar}>
          <i className={`fas ${isCollapsed ? 'fa-chevron-right' : 'fa-bars'}`}></i>
        </button>
      </div>
      <ul className="nav-menu">
        <li className="nav-item">
          <Link to="/dashboard" className={`nav-link ${path === '/dashboard' ? 'active' : ''}`}>
            <i className="fas fa-home"></i>
            <span>Dashboard</span>
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/dashboard/lessons" className={`nav-link ${path === '/dashboard/lessons' ? 'active' : ''}`}>
            <i className="fas fa-book"></i>
            <span>Lessons</span>
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/dashboard/practice" className={`nav-link ${path === '/dashboard/practice' ? 'active' : ''}`}>
            <i className="fas fa-microphone-alt"></i>
            <span>Practice</span>
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/dashboard/live-call" className={`nav-link ${path === '/dashboard/live-call' ? 'active' : ''}`}>
            <i className="fas fa-video"></i>
            <span>Live Call</span>
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/dashboard/progress" className={`nav-link ${path === '/dashboard/progress' ? 'active' : ''}`}>
            <i className="fas fa-chart-line"></i>
            <span>Progress</span>
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/dashboard/settings" className={`nav-link ${path === '/dashboard/settings' ? 'active' : ''}`}>
            <i className="fas fa-cog"></i>
            <span>Settings</span>
          </Link>
        </li>
        <li className="nav-item">
          <Link to="/" className="nav-link">
            <i className="fas fa-sign-out-alt"></i>
            <span>Sign Out</span>
          </Link>
        </li>
      </ul>
    </div>
  );
};

Sidebar.propTypes = {
  isCollapsed: PropTypes.bool.isRequired,
  toggleSidebar: PropTypes.func.isRequired
};

export default Sidebar; 