import React, { useState, useEffect } from 'react';
import { progressAPI } from '../services/api';

/**
 * StatsGrid component - Displays key metrics in a grid layout
 * Shows completed lessons, streak, progress and achievements
 */
const StatsGrid = () => {
  const [stats, setStats] = useState([
    { icon: 'fas fa-book', value: '0', label: 'Completed Lessons' },
    { icon: 'fas fa-fire', value: '0', label: 'Day Streak' },
    { icon: 'fas fa-chart-line', value: '0%', label: 'Overall Progress' },
    { icon: 'fas fa-trophy', value: '0', label: 'Achievements Unlocked' }
  ]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const dashboardStats = await progressAPI.getDashboardStats();
        setStats([
          {
            icon: 'fas fa-book',
            value: dashboardStats.completed_lessons?.toString() || '0',
            label: 'Completed Lessons'
          },
          {
            icon: 'fas fa-fire',
            value: dashboardStats.day_streak?.toString() || '0',
            label: 'Day Streak'
          },
          {
            icon: 'fas fa-chart-line',
            value: `${dashboardStats.overall_progress?.toFixed(0) || 0}%`,
            label: 'Overall Progress'
          },
          {
            icon: 'fas fa-trophy',
            value: dashboardStats.achievements_unlocked?.toString() || '0',
            label: 'Achievements Unlocked'
          }
        ]);
      } catch (error) {
        console.error('Error fetching dashboard stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="stats-grid">
        {stats.map((stat, index) => (
          <div className="stat-box" key={index}>
            <div className="stat-icon">
              <i className={stat.icon}></i>
            </div>
            <div className="stat-info">
              <h3>Loading...</h3>
              <p>{stat.label}</p>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="stats-grid">
      {stats.map((stat, index) => (
        <div className="stat-box" key={index}>
          <div className="stat-icon">
            <i className={stat.icon}></i>
          </div>
          <div className="stat-info">
            <h3>{stat.value}</h3>
            <p>{stat.label}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatsGrid; 