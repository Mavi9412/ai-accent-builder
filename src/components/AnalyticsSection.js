import React, { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';

// Register all Chart.js components
Chart.register(...registerables);

/**
 * AnalyticsSection component - Renders learning analytics charts
 * Uses Chart.js for visualization of user learning data
 */
const AnalyticsSection = () => {
  // Refs for each chart canvas
  const skillsChartRef = useRef(null);
  const progressChartRef = useRef(null);
  const timeChartRef = useRef(null);
  const accuracyChartRef = useRef(null);
  
  // Chart instance refs to clean up on unmount
  const chartInstancesRef = useRef({});

  // Common chart options
  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 20,
          usePointStyle: true,
          pointStyle: 'circle',
          font: {
            size: 12,
            weight: '500'
          }
        }
      }
    }
  };

  useEffect(() => {
    // Initialize charts when component mounts
    // Skills Chart (Radar Chart)
    if (skillsChartRef.current) {
      const ctx = skillsChartRef.current.getContext('2d');
      chartInstancesRef.current.skills = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: ['Speaking', 'Listening', 'Reading', 'Writing', 'Grammar', 'Vocabulary'],
          datasets: [{
            label: 'Current Level',
            data: [85, 78, 90, 82, 88, 75],
            backgroundColor: 'rgba(67, 97, 238, 0.2)',
            borderColor: 'rgba(67, 97, 238, 1)',
            pointBackgroundColor: 'rgba(67, 97, 238, 1)',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(67, 97, 238, 1)',
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          }, {
            label: 'Previous Level',
            data: [75, 70, 82, 75, 80, 68],
            backgroundColor: 'rgba(247, 37, 133, 0.2)',
            borderColor: 'rgba(247, 37, 133, 1)',
            pointBackgroundColor: 'rgba(247, 37, 133, 1)',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(247, 37, 133, 1)',
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          }]
        },
        options: {
          ...commonOptions,
          scales: {
            r: {
              angleLines: { 
                display: true,
                color: 'rgba(0, 0, 0, 0.1)'
              },
              grid: {
                color: 'rgba(0, 0, 0, 0.1)'
              },
              pointLabels: {
                font: {
                  size: 12,
                  weight: '500'
                }
              },
              suggestedMin: 0,
              suggestedMax: 100,
              ticks: {
                stepSize: 20,
                backdropColor: 'transparent'
              }
            }
          }
        }
      });
    }

    // Progress Chart (Bar Chart)
    if (progressChartRef.current) {
      const ctx = progressChartRef.current.getContext('2d');
      chartInstancesRef.current.progress = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['Conversation', 'Pronunciation', 'Speaking', 'Shadowing', 'Role-play'],
          datasets: [{
            label: 'Current Progress',
            data: [85, 78, 82, 80, 75],
            backgroundColor: [
              'rgba(67, 97, 238, 0.8)',
              'rgba(247, 37, 133, 0.8)',
              'rgba(255, 158, 0, 0.8)',
              'rgba(76, 201, 240, 0.8)',
              'rgba(255, 214, 10, 0.8)'
            ],
            borderRadius: 8,
            borderWidth: 0,
            barThickness: 20
          }, {
            label: 'Previous Progress',
            data: [75, 70, 75, 72, 68],
            backgroundColor: [
              'rgba(67, 97, 238, 0.4)',
              'rgba(247, 37, 133, 0.4)',
              'rgba(255, 158, 0, 0.4)',
              'rgba(76, 201, 240, 0.4)',
              'rgba(255, 214, 10, 0.4)'
            ],
            borderRadius: 8,
            borderWidth: 0,
            barThickness: 20
          }]
        },
        options: {
          ...commonOptions,
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              grid: {
                color: 'rgba(0, 0, 0, 0.05)'
              },
              ticks: {
                font: {
                  size: 12
                }
              }
            },
            x: {
              grid: {
                display: false
              },
              ticks: {
                font: {
                  size: 12
                }
              }
            }
          }
        }
      });
    }

    // Time Distribution Chart (Doughnut Chart)
    if (timeChartRef.current) {
      const ctx = timeChartRef.current.getContext('2d');
      chartInstancesRef.current.time = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: ['Conversation', 'Pronunciation', 'Speaking', 'Shadowing', 'Role-play'],
          datasets: [{
            data: [30, 25, 20, 15, 10],
            backgroundColor: [
              'rgba(67, 97, 238, 0.8)',
              'rgba(247, 37, 133, 0.8)',
              'rgba(255, 158, 0, 0.8)',
              'rgba(76, 201, 240, 0.8)',
              'rgba(255, 214, 10, 0.8)'
            ],
            borderWidth: 0,
            borderRadius: 5,
            hoverOffset: 10
          }]
        },
        options: {
          ...commonOptions,
          cutout: '65%',
          plugins: {
            ...commonOptions.plugins,
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `${context.label}: ${context.raw}%`;
                }
              }
            }
          }
        }
      });
    }

    // Accuracy Trends Chart (Line Chart)
    if (accuracyChartRef.current) {
      const ctx = accuracyChartRef.current.getContext('2d');
      chartInstancesRef.current.accuracy = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
          datasets: [{
            label: 'Speaking Accuracy',
            data: [65, 70, 75, 85],
            borderColor: 'rgba(67, 97, 238, 1)',
            backgroundColor: 'rgba(67, 97, 238, 0.1)',
            tension: 0.4,
            fill: true,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          }, {
            label: 'Pronunciation Accuracy',
            data: [60, 68, 72, 78],
            borderColor: 'rgba(247, 37, 133, 1)',
            backgroundColor: 'rgba(247, 37, 133, 0.1)',
            tension: 0.4,
            fill: true,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          }, {
            label: 'Grammar Accuracy',
            data: [70, 75, 82, 88],
            borderColor: 'rgba(255, 158, 0, 1)',
            backgroundColor: 'rgba(255, 158, 0, 0.1)',
            tension: 0.4,
            fill: true,
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6
          }]
        },
        options: {
          ...commonOptions,
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              grid: {
                color: 'rgba(0, 0, 0, 0.05)'
              },
              ticks: {
                font: {
                  size: 12
                }
              }
            },
            x: {
              grid: {
                display: false
              },
              ticks: {
                font: {
                  size: 12
                }
              }
            }
          }
        }
      });
    }

    // Cleanup function to destroy chart instances when component unmounts
    return () => {
      Object.values(chartInstancesRef.current).forEach(chart => {
        if (chart) {
          chart.destroy();
        }
      });
    };
  }, []);

  return (
    <div className="analytics-section">
      <div className="analytics-header">
        <h2>Learning Analytics</h2>
      </div>
      <div className="charts-grid">
        <div className="chart-card">
          <h3><i className="fas fa-chart-radar"></i>Skill Level Comparison</h3>
          <div className="chart-container">
            <canvas ref={skillsChartRef}></canvas>
          </div>
        </div>
        <div className="chart-card">
          <h3><i className="fas fa-chart-column"></i>Progress Overview</h3>
          <div className="chart-container">
            <canvas ref={progressChartRef}></canvas>
          </div>
        </div>
        <div className="chart-card">
          <h3><i className="fas fa-chart-pie"></i>Learning Time Distribution</h3>
          <div className="chart-container">
            <canvas ref={timeChartRef}></canvas>
          </div>
        </div>
        <div className="chart-card">
          <h3><i className="fas fa-chart-line"></i>Accuracy Trends</h3>
          <div className="chart-container">
            <canvas ref={accuracyChartRef}></canvas>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsSection; 