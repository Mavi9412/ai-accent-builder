import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Header.css';

const Header = () => {
  const navigate = useNavigate();

  const scrollToSection = (sectionId) => {
    // Navigate to home page first if not already there
    if (window.location.pathname !== '/') {
      navigate('/');
      // Add a small delay to ensure navigation completes before scrolling
      setTimeout(() => {
        const section = document.getElementById(sectionId);
        if (section) {
          section.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    } else {
      // Already on home page, just scroll
      const section = document.getElementById(sectionId);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <header className="header">
      <Link to="/" className="logo-link">
        <div className="logo">AI ACCENT</div>
      </Link>
      <nav className="nav-links">
        <a href="#features" onClick={(e) => { e.preventDefault(); scrollToSection('features'); }}>Features</a>
        <a href="#research" onClick={(e) => { e.preventDefault(); scrollToSection('research'); }}>Research</a>
        <a href="#about" onClick={(e) => { e.preventDefault(); scrollToSection('about'); }}>About</a>
        <a href="#contact" onClick={(e) => { e.preventDefault(); scrollToSection('contact'); }}>Contact</a>
      </nav>
      {/* <div className="auth-buttons">
        <button className="sign-in">Sign In</button>
        <button className="get-started">Get Started</button>
      </div> */}
      
       <div className="auth-buttons">
        <Link to="/login">
          <button className="sign-in">Sign In</button>
        </Link>
        <Link to="/signup">
          <button className="get-started">Get Started</button>
        </Link>
      </div>
    </header>
  );
};

export default Header; 