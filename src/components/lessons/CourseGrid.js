import React, { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

/**
 * CourseCard component - Individual course card showing title, description and stats
 * @param {Object} course - Course data containing title, icon, description, and stats
 */
const CourseCard = ({ course }) => {
  const cardRef = useRef(null);

  // Add hover effects to course cards
  useEffect(() => {
    const card = cardRef.current;
    
    const handleMouseEnter = () => {
      if (card) card.style.transform = 'translateY(-10px)';
    };
    
    const handleMouseLeave = () => {
      if (card) card.style.transform = 'translateY(0)';
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
    <div className="course-card" ref={cardRef}>
      <div className="course-icon">
        <i className={course.icon}></i>
      </div>
      <h3>{course.title}</h3>
      <p>{course.description}</p>
      <div className="course-stats">
        {course.stats.map((stat, index) => (
          <div className="course-stat" key={index}>
            <div className="number">{stat.number}</div>
            <div className="label">{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

CourseCard.propTypes = {
  course: PropTypes.shape({
    title: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    stats: PropTypes.arrayOf(
      PropTypes.shape({
        number: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
      })
    ).isRequired
  }).isRequired
};

/**
 * CourseGrid component - Grid of available courses
 */
const CourseGrid = () => {
  const [courses, setCourses] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchCourses = async () => {
      try {
        const { courseAPI } = await import('../../services/api');
        const coursesData = await courseAPI.getAll();
        
        const formattedCourses = coursesData.map(course => ({
          id: course.id,
          title: course.title,
          icon: course.icon || "fas fa-book",
          description: course.description || "",
          stats: [
            { number: course.lesson_count?.toString() || "0", label: "Lessons" },
            { number: `${course.duration_hours || 0}h`, label: "Duration" }
          ]
        }));

        setCourses(formattedCourses);
      } catch (error) {
        console.error('Error fetching courses:', error);
        // Set default courses on error
        setCourses([
          {
            title: "Beginner's Guide",
            icon: "fas fa-book",
            description: "Start your language learning journey with fundamental concepts and basic vocabulary",
            stats: [
              { number: "0", label: "Lessons" },
              { number: "0h", label: "Duration" }
            ]
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  if (loading) {
    return (
      <div className="course-grid">
        <div className="course-card">
          <p>Loading courses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="course-grid">
      {courses.map((course, index) => (
        <CourseCard key={course.id || index} course={course} />
      ))}
    </div>
  );
};

export default CourseGrid; 