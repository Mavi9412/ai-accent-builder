import React from 'react';
import './About.css';

// StatBox component for displaying statistics
const StatBox = ({ icon, value, label }) => (
  <div className="stat-box">
    <div className="stat-icon">
      {icon}
    </div>
    <div className="stat-value">{value}</div>
    <div className="stat-label">{label}</div>
  </div>
);

// Main About component
const About = () => {
  return (
    <section id="about" className="about-section">
      {/* Header with title and subtitle */}
      <div className="about-header">
        <h2 className="about-heading">ABOUT AI ACCENT</h2>
        <div className="about-divider"></div>
        <p className="about-subheading">
          Learn more about our journey, mission, and the team behind our innovative language learning platform.
        </p>
      </div>

      {/* Main content card */}
      <div className="about-card">
        {/* Main description */}
        <p className="about-description">
          AI ACCENT is a cutting-edge language learning platform that uses artificial intelligence to help you improve your pronunciation 
          and fluency in English. Our innovative approach focuses on personalized accent reduction and conversation practice.
        </p>

        {/* Mission and Vision section */}
        <div className="mission-vision-container">
          {/* Mission box */}
          <div className="info-box mission-box">
            <h3 className="info-heading mission-heading">Our Mission</h3>
            <p className="info-text">
              To make language learning accessible, effective, and engaging for everyone through the power of artificial 
              intelligence and personalized learning experiences.
            </p>
          </div>

          {/* Vision box */}
          <div className="info-box vision-box">
            <h3 className="info-heading vision-heading">Our Vision</h3>
            <p className="info-text">
              A world where language barriers are eliminated and communication across cultures is seamless, natural, 
              and confident.
            </p>
          </div>
        </div>

        {/* Approach section */}
        <div className="approach-section">
          <h3 className="approach-heading">Our Approach</h3>
          <p className="approach-text">
            We combine the latest advancements in AI technology with proven language learning methodologies to create a personalized 
            learning experience that adapts to your specific needs, accent patterns, and learning pace.
          </p>

          {/* Stats section */}
          <div className="stats-container">
            <StatBox 
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512" width="24" height="24" fill="#4A89DC">
                  <path d="M144 0a80 80 0 1 1 0 160A80 80 0 1 1 144 0zM512 0a80 80 0 1 1 0 160A80 80 0 1 1 512 0zM0 298.7C0 239.8 47.8 192 106.7 192h42.7c15.9 0 31 3.5 44.6 9.7c-1.3 7.2-1.9 14.7-1.9 22.3c0 38.2 16.8 72.5 43.3 96c-.2 0-.4 0-.7 0H21.3C9.6 320 0 310.4 0 298.7zM405.3 320c-.2 0-.4 0-.7 0c26.6-23.5 43.3-57.8 43.3-96c0-7.6-.7-15-1.9-22.3c13.6-6.3 28.7-9.7 44.6-9.7h42.7C592.2 192 640 239.8 640 298.7c0 11.8-9.6 21.3-21.3 21.3H405.3zM224 224a96 96 0 1 1 192 0 96 96 0 1 1 -192 0zM128 485.3C128 411.7 187.7 352 261.3 352h117.4C452.3 352 512 411.7 512 485.3c0 14.7-11.9 26.7-26.7 26.7H154.7c-14.7 0-26.7-11.9-26.7-26.7z"/>
                </svg>
              } 
              value="50,000+" 
              label="Active Learners" 
            />
            <StatBox 
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="24" height="24" fill="#4A89DC">
                  <path d="M57.7 193l9.4 16.4c8.3 14.5 21.9 25.2 38 29.8L163 255.7c17.2 4.9 29 20.6 29 38.5v39.9c0 11 6.2 21 16 25.9s16 14.9 16 25.9v39c0 15.6 14.9 26.9 29.9 22.6c16.1-4.6 28.6-17.5 32.7-33.8l2.8-11.2c4.2-16.9 15.2-31.4 30.3-40l8.1-4.6c15-8.5 24.2-24.5 24.2-41.7v-8.3c0-12.7-5.1-24.9-14.1-33.9l-3.9-3.9c-9-9-21.2-14.1-33.9-14.1H257c-11.1 0-22.1-2.9-31.8-8.4l-34.5-19.7c-4.3-2.5-7.6-6.5-9.2-11.2c-3.2-9.6 1.1-20 10.2-24.5l5.9-3c6.6-3.3 14.3-3.9 21.3-1.5l23.2 7.7c8.2 2.7 17.2-.4 21.9-7.5c4.7-7 4.2-16.3-1.2-22.8l-13.6-16.3c-10-12-9.9-29.5 .3-41.3l15.7-18.3c8.8-10.3 10.2-25 3.5-36.7l-2.4-4.2c-3.5-.2-6.9-.3-10.4-.3C163.1 48 84.4 108.9 57.7 193zM464 256c0-36.8-9.6-71.4-26.4-101.5L412 164.8c-15.7 6.3-23.8 23.8-18.5 39.8l16.9 50.7c3.5 10.4 12 18.3 22.6 20.9l29.1 7.3c1.2-9 1.8-18.2 1.8-27.5zm48 0c0 141.4-114.6 256-256 256S0 397.4 0 256S114.6 0 256 0S512 114.6 512 256z"/>
                </svg>
              } 
              value="120+" 
              label="Countries" 
            />
            <StatBox 
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="24" height="24" fill="#4A89DC">
                  <path d="M256 48a208 208 0 1 1 0 416 208 208 0 1 1 0-416zm0 464A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM183.2 132.6c-1.3-2.8-4.1-4.6-7.2-4.6s-5.9 1.8-7.2 4.6l-16.6 34.7-37.1 5.6c-3 .5-5.5 2.7-6.3 5.6s0 6.1 2.3 8.3l27 27.3-6.4 38.1c-.5 3 .7 6.1 3.1 7.9s5.8 2 8.5 .6L184 239.4l33.7 18.1c2.8 1.5 6.1 1.3 8.5-.6s3.7-4.9 3.1-7.9l-6.4-38.1 27-27.3c2.3-2.3 3.1-5.5 2.3-8.3s-3.3-5.2-6.3-5.6l-37.1-5.6-16.6-34.7zm144 0c-1.3-2.8-4.1-4.6-7.2-4.6s-5.9 1.8-7.2 4.6l-16.6 34.7-37.1 5.6c-3 .5-5.5 2.7-6.3 5.6s0 6.1 2.3 8.3l27 27.3-6.4 38.1c-.5 3 .7 6.1 3.1 7.9s5.8 2 8.5 .6L384 239.4l33.7 18.1c2.8 1.5 6.1 1.3 8.5-.6s3.7-4.9 3.1-7.9l-6.4-38.1 27-27.3c2.3-2.3 3.1-5.5 2.3-8.3s-3.3-5.2-6.3-5.6l-37.1-5.6-16.6-34.7zM134.4 352.7c3.4-1.8 7.5-1.5 10.7 .6l26.7 18.3 26.7-18.3c3.1-2.1 7.2-2.4 10.7-.6s5.7 5.4 5.4 9.3l-5.1 30.5 21.7 21.9c2.8 2.8 3.7 6.9 2.4 10.6s-4.6 6.2-8.4 6.7l-29.8 4.5-13.3 27.9c-1.6 3.3-4.9 5.4-8.5 5.4s-6.9-2.1-8.5-5.4l-13.3-27.9-29.8-4.5c-3.8-.6-7.1-3-8.4-6.7s-.4-7.8 2.4-10.6l21.7-21.9-5.1-30.5c-.3-3.9 1.9-7.6 5.4-9.3z"/>
                </svg>
              }  
              value="96%" 
              label="Satisfaction Rate" 
            />
          </div>
        </div>
      </div>
    </section>
  );
};

export default About; 