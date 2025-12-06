import React, { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

/**
 * LessonItem component - Individual lesson row showing details and status
 * @param {Object} lesson - Lesson data containing title, description, status, and icon
 */
const LessonItem = ({ lesson }) => {
  const itemRef = useRef(null);
  
  // Add click animation to lesson items
  useEffect(() => {
    const item = itemRef.current;
    
    const handleClick = () => {
      if (item) {
        item.style.transform = 'scale(0.98)';
        setTimeout(() => {
          item.style.transform = 'scale(1)';
        }, 150);
      }
    };
    
    if (item) {
      item.addEventListener('click', handleClick);
    }
    
    return () => {
      if (item) {
        item.removeEventListener('click', handleClick);
      }
    };
  }, []);

  // Determine button text and disabled state based on lesson status
  const getButtonDetails = () => {
    switch(lesson.status) {
      case 'completed':
        return { text: 'Review', disabled: false };
      case 'in-progress':
        return { text: 'Continue', disabled: false };
      case 'locked':
      default:
        return { text: 'Start', disabled: true };
    }
  };
  
  const buttonDetails = getButtonDetails();

  return (
    <div className="lesson-item" ref={itemRef}>
      <div className="lesson-icon">
        <i className={lesson.status === 'locked' ? 'fas fa-lock' : 'fas fa-play'}></i>
      </div>
      <div className="lesson-info">
        <h4>{lesson.title}</h4>
        <p>{lesson.description}</p>
      </div>
      <div className="lesson-status">
        <span className={`status-badge ${lesson.status}`}>
          {lesson.status.charAt(0).toUpperCase() + lesson.status.slice(1).replace('-', ' ')}
        </span>
        <button 
          className="start-btn" 
          disabled={buttonDetails.disabled}
          onClick={() => {
            if (!buttonDetails.disabled) {
              console.log(`${buttonDetails.text} lesson: ${lesson.title}`);
              // Here you would navigate to the lesson page or show a modal
            }
          }}
        >
          {buttonDetails.text}
        </button>
      </div>
    </div>
  );
};

LessonItem.propTypes = {
  lesson: PropTypes.shape({
    title: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    status: PropTypes.oneOf(['completed', 'in-progress', 'locked']).isRequired
  }).isRequired
};

/**
 * LessonList component - List of lessons for the current course
 */
const LessonList = () => {
  const [lessons, setLessons] = React.useState([]);
  const [currentCourse, setCurrentCourse] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [userProgress, setUserProgress] = React.useState([]);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const { courseAPI, lessonAPI, progressAPI } = await import('../../services/api');
        
        // Get first course
        const courses = await courseAPI.getAll();
        if (courses.length > 0) {
          setCurrentCourse(courses[0]);
          
          // Get lessons for the first course
          const lessonsData = await lessonAPI.getByCourse(courses[0].id);
          
          // Get user progress
          const progressData = await progressAPI.getLessonProgress();
          setUserProgress(progressData);

          // Map lessons with progress status
          const lessonsWithStatus = lessonsData.map(lesson => {
            const progress = progressData.find(p => p.lesson_id === lesson.id);
            let status = 'locked';
            
            if (progress) {
              if (progress.status === 'completed') {
                status = 'completed';
              } else if (progress.status === 'in_progress' || progress.progress_percentage > 0) {
                status = 'in-progress';
              }
            } else if (lessonsData.indexOf(lesson) === 0) {
              // First lesson is always available
              status = 'locked';
            }

            return {
              id: lesson.id,
              title: lesson.title,
              description: lesson.description || "",
              status: status
            };
          });

          setLessons(lessonsWithStatus);
        }
      } catch (error) {
        console.error('Error fetching lessons:', error);
        setLessons([
          {
            title: "Introduction to Basic Vocabulary",
            description: "Learn essential words and phrases for everyday communication",
            status: "locked"
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="lesson-list">
        <h2>Loading lessons...</h2>
      </div>
    );
  }

  return (
    <div className="lesson-list">
      <h2>Current Course: {currentCourse?.title || "Select a Course"}</h2>
      {lessons.length > 0 ? (
        lessons.map((lesson, index) => (
          <LessonItem key={lesson.id || index} lesson={lesson} />
        ))
      ) : (
        <p>No lessons available yet.</p>
      )}
    </div>
  );
};

export default LessonList; 