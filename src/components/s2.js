// src/components/Hero.js
import React from 'react';
import './s2.css'; // Import CSS styling

const Hero = () => {
  return (
    <section className="hero-section">
      {/* Heading */}
      <h2 className="hero-title">Start Your Language Journey Today</h2>

      {/* Subtitle */}
      <p className="hero-subtitle">
        Join our innovative approach to language learning
      </p>

      {/* Call-to-action buttons */}
      <div className="hero-buttons">
        <button className="btn-start">Get Started Free</button>
        {/* <button className="btn-learn">Learn More</button> */}
      </div>
    </section>
  );
};

export default Hero;
