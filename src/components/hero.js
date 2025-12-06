// src/components/Hero.js
import React from 'react';
import { useNavigate } from 'react-router-dom';
import './hero.css'; // Import CSS styling

const Hero = () => {
  const navigate = useNavigate();

  const handleStartLearning = () => {
    navigate('/signup');
  };

  const handleLearnMore = () => {
    // Scroll to features section if on the same page
    const featuresSection = document.querySelector('.features-section');
    if (featuresSection) {
      featuresSection.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="hero-section">
      {/* Heading */}
      <h1 className="hero-title">Master English with AI</h1>

      {/* Subtitle */}
      <p className="hero-subtitle">
        Experience personalized language learning powered by advanced AI technology
      </p>

      {/* Call-to-action buttons */}
      <div className="hero-buttons">
        <button className="btn-start" onClick={handleStartLearning}>Start Learning Free</button>
        <button className="btn-learn" onClick={handleLearnMore}>Learn More</button>
      </div>
    </section>
  );
};

export default Hero;
