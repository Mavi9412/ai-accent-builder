import React from 'react';

/**
 * ActivityList component - Displays a list of recent learning activities
 */
const ActivityList = () => {
  // Sample activity data - in a real app, this would come from an API
  const activities = [
    {
      id: 1,
      type: 'lesson',
      title: 'Completed "Greetings and Introductions" lesson',
      time: 'Today, 10:15 AM',
      duration: '25 min',
      result: 'Completed',
      score: '92%',
      scoreType: 'excellent'
    },
    {
      id: 2,
      type: 'practice',
      title: 'Pronunciation practice: Vowel sounds',
      time: 'Today, 9:30 AM',
      duration: '15 min',
      result: 'Completed',
      score: '84%',
      scoreType: 'good'
    },
    {
      id: 3,
      type: 'conversation',
      title: 'Conversation practice: At the restaurant',
      time: 'Yesterday, 6:45 PM',
      duration: '18 min',
      result: 'Completed',
      score: '78%',
      scoreType: 'good'
    },
    {
      id: 4,
      type: 'quiz',
      title: 'Verb tenses quiz',
      time: 'Yesterday, 5:20 PM',
      duration: '12 min',
      result: 'Completed',
      score: '95%',
      scoreType: 'excellent'
    },
    {
      id: 5,
      type: 'practice',
      title: 'Speaking practice: Describing your day',
      time: '2 days ago, 11:10 AM',
      duration: '20 min',
      result: 'Completed',
      score: '72%',
      scoreType: 'needs-work'
    },
    {
      id: 6,
      type: 'lesson',
      title: 'Completed "Weather and Seasons" lesson',
      time: '3 days ago, 2:30 PM',
      duration: '28 min',
      result: 'Completed',
      score: '88%',
      scoreType: 'good'
    },
    {
      id: 7,
      type: 'achievement',
      title: 'Unlocked "Week Streak" achievement',
      time: '4 days ago, 9:15 AM',
      duration: '-',
      result: 'Achievement',
      score: '-',
      scoreType: ''
    }
  ];

  // Get the appropriate icon for each activity type
  const getActivityIcon = (type) => {
    switch (type) {
      case 'lesson':
        return 'fas fa-book';
      case 'practice':
        return 'fas fa-microphone-alt';
      case 'conversation':
        return 'fas fa-comments';
      case 'quiz':
        return 'fas fa-tasks';
      case 'achievement':
        return 'fas fa-trophy';
      default:
        return 'fas fa-clipboard-list';
    }
  };

  return (
    <div className="activity-list">
      <h3 className="section-title">Recent Activities</h3>
      
      {activities.map((activity) => (
        <div className="activity-item" key={activity.id}>
          <div className="activity-icon">
            <i className={getActivityIcon(activity.type)}></i>
          </div>
          <div className="activity-details">
            <div className="activity-title">{activity.title}</div>
            <div className="activity-meta">
              <div className="activity-time">
                <i className="fas fa-clock"></i> {activity.time}
              </div>
              {activity.duration !== '-' && (
                <div className="activity-time">
                  <i className="fas fa-hourglass-half"></i> {activity.duration}
                </div>
              )}
              {activity.result !== '-' && (
                <div className="activity-result">
                  <i className="fas fa-check-circle"></i> {activity.result}
                </div>
              )}
            </div>
          </div>
          {activity.score !== '-' && (
            <div className={`activity-score score-${activity.scoreType}`}>
              {activity.score}
            </div>
          )}
        </div>
      ))}
      
      <div className="view-more-container">
        <button className="view-more-btn">
          <i className="fas fa-history"></i> View More Activities
        </button>
      </div>
    </div>
  );
};

// Add some additional styles specific to this component
const activityStyles = `
  .section-title {
    color: var(--secondary-color);
    margin-bottom: 20px;
    font-size: 1.2rem;
  }
  
  .view-more-container {
    text-align: center;
    margin-top: 20px;
    padding-top: 15px;
    border-top: 1px solid #E2E8F0;
  }
  
  .view-more-btn {
    background: none;
    border: 2px solid var(--primary-color);
    color: var(--primary-color);
    padding: 8px 20px;
    border-radius: 30px;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  
  .view-more-btn:hover {
    background: var(--primary-color);
    color: white;
  }
`;

// Inject the styles
const styleTag = document.createElement('style');
styleTag.innerHTML = activityStyles;
document.head.appendChild(styleTag);

export default ActivityList; 