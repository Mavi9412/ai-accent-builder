import React, { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

/**
 * ModuleCard component - Displays an individual learning module card with progress
 * @param {Object} module - Module data containing title, progress, and stats
 */
const ModuleCard = ({ module }) => {
  const cardRef = useRef(null);
  
  // Add hover effects to module cards
  useEffect(() => {
    const card = cardRef.current;
    
    const handleMouseEnter = () => {
      card.style.transform = 'translateY(-10px)';
    };
    
    const handleMouseLeave = () => {
      card.style.transform = 'translateY(0)';
    };
    
    if (card) {
      card.addEventListener('mouseenter', handleMouseEnter);
      card.addEventListener('mouseleave', handleMouseLeave);
    }
    
    return () => {
      if (card) {
        card.removeEventListener('mouseenter', handleMouseEnter);
        card.removeEventListener('mouseleave', handleMouseLeave);
      }
    };
  }, []);

  return (
    <div className="module-card" ref={cardRef}>
      <div className="module-header">
        <h3>{module.title}</h3>
        <div className="module-progress">
          <div className="progress-bar" style={{ width: `${module.progress}%` }}></div>
        </div>
      </div>
      <div className="module-content">
        <div className="module-stats">
          {module.stats.map((stat, index) => (
            <div className="module-stat" key={index}>
              <div className="number">{stat.number}</div>
              <div className="label">{stat.label}</div>
            </div>
          ))}
        </div>
        <div className="module-actions">
          <button className="module-btn">
            <i className="fas fa-play"></i>
            Continue
          </button>
          <button className="module-btn">
            <i className="fas fa-redo"></i>
            Review
          </button>
        </div>
      </div>
    </div>
  );
};

ModuleCard.propTypes = {
  module: PropTypes.shape({
    title: PropTypes.string.isRequired,
    progress: PropTypes.number.isRequired,
    stats: PropTypes.arrayOf(
      PropTypes.shape({
        number: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
      })
    ).isRequired
  }).isRequired
};

export default ModuleCard; 