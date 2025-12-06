import React from 'react';

/**
 * AchievementGrid component - Displays user achievements and badges
 */
const AchievementGrid = () => {
  // Sample achievement data - in a real app, this would come from an API
  const achievements = [
    {
      id: 1,
      title: 'Perfect Week',
      description: 'Complete activities for 7 consecutive days',
      icon: 'fas fa-calendar-check',
      unlocked: true,
      progress: 100,
      target: 7,
      current: 7
    },
    {
      id: 2,
      title: 'Pronunciation Pro',
      description: 'Achieve 90% accuracy in 20 pronunciation exercises',
      icon: 'fas fa-microphone-alt',
      unlocked: true,
      progress: 100,
      target: 20,
      current: 20
    },
    {
      id: 3,
      title: 'Conversation Master',
      description: 'Complete 15 conversation practice sessions',
      icon: 'fas fa-comments',
      unlocked: true,
      progress: 100,
      target: 15,
      current: 15
    },
    {
      id: 4,
      title: 'Grammar Guru',
      description: 'Score 85% or higher on 10 grammar quizzes',
      icon: 'fas fa-spell-check',
      unlocked: false,
      progress: 60,
      target: 10,
      current: 6
    },
    {
      id: 5,
      title: 'Vocabulary Builder',
      description: 'Learn 500 new words',
      icon: 'fas fa-book-open',
      unlocked: false,
      progress: 72,
      target: 500,
      current: 360
    },
    {
      id: 6,
      title: 'Daily Streak: 30 Days',
      description: 'Study for 30 consecutive days',
      icon: 'fas fa-fire',
      unlocked: false,
      progress: 50,
      target: 30,
      current: 15
    },
    {
      id: 7,
      title: 'First Lesson',
      description: 'Complete your first lesson',
      icon: 'fas fa-graduation-cap',
      unlocked: true,
      progress: 100,
      target: 1,
      current: 1
    },
    {
      id: 8,
      title: 'Social Learner',
      description: 'Invite 3 friends to join the platform',
      icon: 'fas fa-user-plus',
      unlocked: false,
      progress: 33,
      target: 3,
      current: 1
    }
  ];

  return (
    <div className="achievements-container">
      <h3 className="section-title">Your Achievements</h3>
      
      <div className="achievements-summary">
        <div className="achievement-stat">
          <div className="stat-value">{achievements.filter(a => a.unlocked).length}</div>
          <div className="stat-label">Unlocked</div>
        </div>
        <div className="achievement-stat">
          <div className="stat-value">{achievements.length - achievements.filter(a => a.unlocked).length}</div>
          <div className="stat-label">Locked</div>
        </div>
        <div className="achievement-stat">
          <div className="stat-value">{Math.round(achievements.filter(a => a.unlocked).length / achievements.length * 100)}%</div>
          <div className="stat-label">Completed</div>
        </div>
      </div>
      
      <div className="achievements-grid">
        {achievements.map(achievement => (
          <div 
            key={achievement.id} 
            className={`achievement-card ${!achievement.unlocked ? 'achievement-locked' : ''}`}
          >
            <div className="achievement-header">
              <div className="achievement-icon">
                <i className={achievement.icon}></i>
              </div>
              <div 
                className={`achievement-status ${achievement.unlocked ? 'unlocked' : 'locked'}`}
              >
                {achievement.unlocked ? 'Unlocked' : 'Locked'}
              </div>
            </div>
            <div className="achievement-info">
              <h3 className="achievement-title">{achievement.title}</h3>
              <p className="achievement-description">{achievement.description}</p>
              <div className="achievement-progress">
                <div 
                  className="progress-bar" 
                  style={{ width: `${achievement.progress}%` }}
                ></div>
              </div>
              <div className="progress-text">
                <span>Progress</span>
                <span>{achievement.current}/{achievement.target}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Add some additional styles specific to this component
const achievementStyles = `
  .achievements-container {
    margin-top: 10px;
  }
  
  .achievements-summary {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
    background: #f8fafc;
    padding: 20px;
    border-radius: var(--border-radius);
    justify-content: center;
  }
  
  .achievement-stat {
    text-align: center;
    padding: 0 20px;
  }
  
  .achievement-stat:not(:last-child) {
    border-right: 1px solid #e2e8f0;
  }
  
  .achievement-stat .stat-value {
    font-size: 2rem;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 5px;
  }
  
  .achievement-stat .stat-label {
    color: var(--light-text);
    font-size: 0.9rem;
  }
  
  @media (max-width: 768px) {
    .achievements-summary {
      padding: 15px;
    }
    
    .achievement-stat {
      padding: 0 15px;
    }
    
    .achievement-stat .stat-value {
      font-size: 1.5rem;
    }
  }
`;

// Inject the styles
const styleTag = document.createElement('style');
styleTag.innerHTML = achievementStyles;
document.head.appendChild(styleTag);

export default AchievementGrid; 