import React, { useState } from 'react';
import PropTypes from 'prop-types';

/**
 * ProgressChart component - Displays progress metrics in chart form
 */
const ProgressChart = () => {
  const [timeRange, setTimeRange] = useState('week');
  const [chartType, setChartType] = useState('progress');
  
  // Handle time range change
  const handleTimeRangeChange = (range) => {
    setTimeRange(range);
  };
  
  // Handle chart type change
  const handleChartTypeChange = (type) => {
    setChartType(type);
  };

  return (
    <div className="chart-container">
      {/* Chart header with controls */}
      <div className="chart-header">
        <h3 className="chart-title">
          {chartType === 'progress' ? 'Learning Progress' : 
           chartType === 'accuracy' ? 'Pronunciation Accuracy' : 
           'Time Spent Learning'}
        </h3>
        
        <div className="chart-controls">
          <div className="time-controls">
            <button 
              className={`chart-control-btn ${timeRange === 'week' ? 'active' : ''}`}
              onClick={() => handleTimeRangeChange('week')}
            >
              Week
            </button>
            <button 
              className={`chart-control-btn ${timeRange === 'month' ? 'active' : ''}`}
              onClick={() => handleTimeRangeChange('month')}
            >
              Month
            </button>
            <button 
              className={`chart-control-btn ${timeRange === 'year' ? 'active' : ''}`}
              onClick={() => handleTimeRangeChange('year')}
            >
              Year
            </button>
          </div>
          
          <div className="type-controls">
            <button 
              className={`chart-control-btn ${chartType === 'progress' ? 'active' : ''}`}
              onClick={() => handleChartTypeChange('progress')}
            >
              Progress
            </button>
            <button 
              className={`chart-control-btn ${chartType === 'accuracy' ? 'active' : ''}`}
              onClick={() => handleChartTypeChange('accuracy')}
            >
              Accuracy
            </button>
            <button 
              className={`chart-control-btn ${chartType === 'time' ? 'active' : ''}`}
              onClick={() => handleChartTypeChange('time')}
            >
              Time
            </button>
          </div>
        </div>
      </div>
      
      {/* Chart visualization - In a real app, you would use Chart.js or similar */}
      <div className="chart-visualization">
        {/* Placeholder for actual chart implementation */}
        <div className="chart-placeholder">
          <div className="placeholder-bars">
            {[...Array(7)].map((_, index) => (
              <div 
                key={index} 
                className="placeholder-bar" 
                style={{ 
                  height: `${Math.floor(Math.random() * 50) + 30}%`,
                  backgroundColor: `rgba(74, 144, 226, ${0.5 + (index * 0.07)})`
                }}
              />
            ))}
          </div>
          <div className="placeholder-labels">
            {timeRange === 'week' && (
              <>
                <span>Mon</span>
                <span>Tue</span>
                <span>Wed</span>
                <span>Thu</span>
                <span>Fri</span>
                <span>Sat</span>
                <span>Sun</span>
              </>
            )}
            {timeRange === 'month' && (
              <>
                <span>Week 1</span>
                <span>Week 2</span>
                <span>Week 3</span>
                <span>Week 4</span>
                <span>Week 5</span>
              </>
            )}
            {timeRange === 'year' && (
              <>
                <span>Jan</span>
                <span>Mar</span>
                <span>May</span>
                <span>Jul</span>
                <span>Sep</span>
                <span>Nov</span>
              </>
            )}
          </div>
        </div>
        <p className="chart-message">
          {chartType === 'progress' && timeRange === 'week' && 
            'Your progress has improved by 15% this week. Keep up the good work!'}
          {chartType === 'accuracy' && timeRange === 'week' && 
            'Your pronunciation accuracy has been consistent this week with an average of 82%.'}
          {chartType === 'time' && timeRange === 'week' && 
            'You spent a total of 5.2 hours learning this week, 20% more than last week!'}
        </p>
      </div>
    </div>
  );
};

// Add additional styling for the chart placeholder
const chartStyles = `
  .chart-visualization {
    margin-top: 20px;
  }
  
  .chart-placeholder {
    height: 250px;
    width: 100%;
    background-color: #f8fafc;
    border-radius: 8px;
    padding: 20px;
    display: flex;
    flex-direction: column;
  }
  
  .placeholder-bars {
    flex: 1;
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    padding-bottom: 10px;
  }
  
  .placeholder-bar {
    width: 40px;
    border-radius: 4px 4px 0 0;
    transition: all 0.3s ease;
  }
  
  .placeholder-bar:hover {
    filter: brightness(1.1);
  }
  
  .placeholder-labels {
    display: flex;
    justify-content: space-around;
    padding-top: 10px;
    border-top: 1px solid #e2e8f0;
    color: var(--light-text);
    font-size: 0.8rem;
  }
  
  .chart-message {
    margin-top: 15px;
    text-align: center;
    color: var(--secondary-color);
    font-size: 0.9rem;
  }
`;

// Inject the styles
const styleTag = document.createElement('style');
styleTag.innerHTML = chartStyles;
document.head.appendChild(styleTag);

export default ProgressChart; 