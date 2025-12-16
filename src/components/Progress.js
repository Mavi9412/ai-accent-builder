import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authAPI, accentAPI, progressAPI } from '../services/api';
import Chart from 'chart.js/auto';
import './Progress.css';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faChartLine,
  faFire,
  faTrophy,
  faClock,
  faChartBar,
  faCalendarCheck,
  faBolt,
  faStar,
  faFilePdf,
  faDownload
} from '@fortawesome/free-solid-svg-icons';
// Recharts imports
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
const Card = ({ children, className }) => <div className={className}>{children}</div>;
const CardContent = ({ children }) => <div>{children}</div>;

const Progress = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const [chartsInitialized, setChartsInitialized] = useState(false);
  const [pronunciationSessions, setPronunciationSessions] = useState([]);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Store chart instances
  const chartsRef = useRef({});

  // Store canvas refs
  const chartRefs = {
    skills: useRef(null),
    weekly: useRef(null),
    daily: useRef(null),
    monthly: useRef(null),
    module: useRef(null),
    time: useRef(null),
  };

  const [charts, setCharts] = useState({});

  useEffect(() => {
    // Check for saved sidebar state
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true') {
      setSidebarCollapsed(true);
    }

    // Fetch pronunciation sessions and dashboard stats
    const fetchData = async () => {
      try {
        const [sessions, stats] = await Promise.all([
          accentAPI.getSessions(),
          progressAPI.getDashboardStats()
        ]);
        setPronunciationSessions(sessions || []);
        setDashboardStats(stats);
      } catch (error) {
        console.error('Error fetching progress data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Separate effect for chart initialization
  useEffect(() => {
    if (!chartsInitialized) {
      const allRefsReady = Object.values(chartRefs).every(ref => ref.current !== null);

      if (allRefsReady) {
        initializeCharts();
        setChartsInitialized(true);
      }
    }

    return () => {
      // Cleanup charts on unmount
      Object.values(chartsRef.current).forEach(chart => {
        if (chart) {
          chart.destroy();
        }
      });
    };
  }, [chartsInitialized]);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
    localStorage.setItem('sidebarCollapsed', !sidebarCollapsed);
  };

  const toggleProfileDropdown = () => {
    setProfileDropdownOpen(!profileDropdownOpen);
  };

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      await progressAPI.exportPDF();
      alert('Progress report downloaded successfully!');
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export report. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const initializeCharts = () => {
    try {
      // Destroy existing charts before creating new ones
      Object.values(chartsRef.current).forEach(chart => {
        if (chart) {
          chart.destroy();
        }
      });
      chartsRef.current = {};

      const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#1a73e8',
              font: {
                size: 12
              }
            }
          }
        }
      };

      // Skills Progress Chart (Radar)
      if (chartRefs.skills.current && !charts.skills) {
        const ctx = chartRefs.skills.current.getContext('2d');
        const skillsChart = new Chart(ctx, {
          type: 'radar',
          data: {
            labels: ['Speaking', 'Listening', 'Reading', 'Writing', 'Grammar', 'Vocabulary'],
            datasets: [{
              label: 'Current Level',
              data: [85, 75, 90, 80, 85, 88],
              backgroundColor: 'rgba(26, 115, 232, 0.2)',
              borderColor: '#1a73e8',
              borderWidth: 2,
              pointBackgroundColor: '#1a73e8',
              pointBorderColor: '#fff',
              pointHoverBackgroundColor: '#fff',
              pointHoverBorderColor: '#1a73e8'
            }]
          },
          options: {
            ...commonOptions,
            scales: {
              r: {
                angleLines: {
                  color: 'rgba(26, 115, 232, 0.2)'
                },
                grid: {
                  color: 'rgba(26, 115, 232, 0.2)'
                },
                pointLabels: {
                  color: '#1a73e8'
                },
                ticks: {
                  color: '#1a73e8',
                  backdropColor: 'transparent'
                }
              }
            }
          }
        });
        setCharts(prev => ({ ...prev, skills: skillsChart }));
      }

      // Weekly Activity Chart (Bar)
      if (chartRefs.weekly.current && !charts.weekly) {
        const ctx = chartRefs.weekly.current.getContext('2d');
        const weeklyChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
              label: 'Minutes',
              data: [45, 60, 30, 75, 45, 90, 60],
              backgroundColor: '#1a73e8',
              borderRadius: 5
            }]
          },
          options: {
            ...commonOptions,
            scales: {
              y: {
                beginAtZero: true,
                grid: {
                  color: 'rgba(26, 115, 232, 0.1)'
                },
                ticks: {
                  color: '#1a73e8'
                }
              },
              x: {
                grid: {
                  display: false
                },
                ticks: {
                  color: '#1a73e8'
                }
              }
            }
          }
        });
        setCharts(prev => ({ ...prev, weekly: weeklyChart }));
      }

      // Daily Progress Chart (Line)
      if (chartRefs.daily.current && !charts.daily) {
        const ctx = chartRefs.daily.current.getContext('2d');
        const dailyChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: ['9AM', '11AM', '1PM', '3PM', '5PM', '7PM'],
            datasets: [{
              label: 'Accuracy',
              data: [75, 82, 78, 85, 88, 90],
              borderColor: '#1a73e8',
              backgroundColor: 'rgba(26, 115, 232, 0.1)',
              tension: 0.4,
              fill: true
            }]
          },
          options: {
            ...commonOptions,
            scales: {
              y: {
                beginAtZero: true,
                grid: {
                  color: 'rgba(26, 115, 232, 0.1)'
                },
                ticks: {
                  color: '#1a73e8'
                }
              },
              x: {
                grid: {
                  display: false
                },
                ticks: {
                  color: '#1a73e8'
                }
              }
            }
          }
        });
        setCharts(prev => ({ ...prev, daily: dailyChart }));
      }

      // Monthly Progress Chart (Bar)
      if (chartRefs.monthly.current && !charts.monthly) {
        const ctx = chartRefs.monthly.current.getContext('2d');
        const monthlyChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            datasets: [{
              label: 'Progress',
              data: [65, 75, 85, 90],
              backgroundColor: '#1a73e8',
              borderRadius: 5
            }]
          },
          options: {
            ...commonOptions,
            scales: {
              y: {
                beginAtZero: true,
                grid: {
                  color: 'rgba(26, 115, 232, 0.1)'
                },
                ticks: {
                  color: '#1a73e8'
                }
              },
              x: {
                grid: {
                  display: false
                },
                ticks: {
                  color: '#1a73e8'
                }
              }
            }
          }
        });
        setCharts(prev => ({ ...prev, monthly: monthlyChart }));
      }

      // Module Comparison Chart (Radar)
      if (chartRefs.module.current && !charts.module) {
        const ctx = chartRefs.module.current.getContext('2d');
        const moduleChart = new Chart(ctx, {
          type: 'radar',
          data: {
            labels: ['Speaking', 'Listening', 'Reading', 'Writing', 'Grammar'],
            datasets: [{
              label: 'Current',
              data: [85, 75, 90, 80, 85],
              backgroundColor: 'rgba(26, 115, 232, 0.2)',
              borderColor: '#1a73e8',
              borderWidth: 2
            }, {
              label: 'Previous',
              data: [75, 65, 80, 70, 75],
              backgroundColor: 'rgba(52, 168, 83, 0.2)',
              borderColor: '#34a853',
              borderWidth: 2
            }]
          },
          options: {
            ...commonOptions,
            scales: {
              r: {
                angleLines: {
                  color: 'rgba(26, 115, 232, 0.2)'
                },
                grid: {
                  color: 'rgba(26, 115, 232, 0.2)'
                },
                pointLabels: {
                  color: '#1a73e8'
                },
                ticks: {
                  color: '#1a73e8',
                  backdropColor: 'transparent'
                }
              }
            }
          }
        });
        setCharts(prev => ({ ...prev, module: moduleChart }));
      }

      // Learning Time Distribution Chart (Doughnut)
      if (chartRefs.time.current && !charts.time) {
        const ctx = chartRefs.time.current.getContext('2d');
        const timeChart = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: ['Speaking', 'Listening', 'Reading', 'Writing'],
            datasets: [{
              data: [35, 25, 20, 20],
              backgroundColor: [
                '#1a73e8',
                '#34a853',
                '#fbbc05',
                '#ea4335'
              ],
              borderWidth: 0
            }]
          },
          options: {
            ...commonOptions,
            cutout: '70%',
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  color: '#1a73e8',
                  font: {
                    size: 12
                  }
                }
              }
            }
          }
        });
        setCharts(prev => ({ ...prev, time: timeChart }));
      }
    } catch (error) {
      console.error('Error initializing charts:', error);
    }
  };

  // Add the new dataTemplates and ProgressCard/ProgressPage components
  const dataTemplates = [
    {
      title: "Conversation Practice",
      accuracy: "85%",
      timeSpent: "2.5h",
      sessions: "15",
      increase: "+15%",
      color: "#3b82f6",
      chartData: [
        { name: "Week 1", Accuracy: 70 },
        { name: "Week 2", Accuracy: 74 },
        { name: "Week 3", Accuracy: 78 },
        { name: "Week 4", Accuracy: 85 }
      ]
    },
    {
      title: "Pronunciation Training",
      accuracy: "78%",
      timeSpent: "1.8h",
      sessions: "12",
      increase: "+12%",
      color: "#22c55e",
      chartData: [
        { name: "Week 1", Accuracy: 65 },
        { name: "Week 2", Accuracy: 68 },
        { name: "Week 3", Accuracy: 72 },
        { name: "Week 4", Accuracy: 78 }
      ]
    },
    {
      title: "Speaking Exercises",
      accuracy: "82%",
      timeSpent: "2.2h",
      sessions: "20",
      increase: "+18%",
      color: "#facc15",
      chartData: [
        { name: "Week 1", Accuracy: 68 },
        { name: "Week 2", Accuracy: 72 },
        { name: "Week 3", Accuracy: 77 },
        { name: "Week 4", Accuracy: 82 }
      ]
    },
    {
      title: "Grammar Mastery",
      accuracy: "88%",
      timeSpent: "1.5h",
      sessions: "10",
      increase: "+10%",
      color: "#a855f7",
      chartData: [
        { name: "Week 1", Accuracy: 60 },
        { name: "Week 2", Accuracy: 70 },
        { name: "Week 3", Accuracy: 80 },
        { name: "Week 4", Accuracy: 88 }
      ]
    }
  ];

  const ProgressCard = ({ title, accuracy, timeSpent, sessions, increase, chartData, color }) => (
    <Card className="w-full md:w-1/3 p-4">
      <CardContent>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <span className="text-green-500 font-semibold">{increase}</span>
        </div>
        <div className="flex justify-between text-center mb-4">
          <div>
            <p className="text-xl font-bold">{accuracy}</p>
            <p className="text-gray-500">Accuracy</p>
          </div>
          <div>
            <p className="text-xl font-bold">{timeSpent}</p>
            <p className="text-gray-500">Time Spent</p>
          </div>
          <div>
            <p className="text-xl font-bold">{sessions}</p>
            <p className="text-gray-500">Sessions</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="Accuracy" stroke={color} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );

  function ProgressPage() {
    return (
      <div className="flex flex-wrap gap-4">
        {dataTemplates.map((item, index) => (
          <ProgressCard key={index} {...item} />
        ))}
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <h2>AI ACCENT</h2>
          <button className="toggle-sidebar" onClick={toggleSidebar}>
            <i className={`fas fa-${sidebarCollapsed ? 'chevron-right' : 'bars'}`}></i>
          </button>
        </div>
        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/dashboard" className="nav-link">
              <i className="fas fa-home"></i>
              <span>Dashboard</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/dashboard/lessons" className="nav-link">
              <i className="fas fa-book"></i>
              <span>Lessons</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/dashboard/practice" className="nav-link">
              <i className="fas fa-microphone-alt"></i>
              <span>Practice</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/dashboard/live-call" className="nav-link">
              <i className="fas fa-video"></i>
              <span>Live Call</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/dashboard/progress" className="nav-link active">
              <i className="fas fa-chart-line"></i>
              <span>Progress</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/dashboard/settings" className="nav-link">
              <i className="fas fa-cog"></i>
              <span>Settings</span>
            </Link>
          </li>
          <li className="nav-item">
            <a href="#" className="nav-link sign-out" onClick={async (e) => { e.preventDefault(); await authAPI.logout(); window.location.href = '/'; }}>
              <i className="fas fa-sign-out-alt"></i>
              <span>Sign Out</span>
            </a>
          </li>
        </ul>
      </div>

      <div className={`main-content ${sidebarCollapsed ? 'expanded' : ''}`}>
        <div className="progress-container">
          <div className="progress-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h1>Your Learning Progress</h1>
              <p>Track your achievements and monitor your language learning journey</p>
            </div>
            <button
              onClick={handleExportPDF}
              disabled={exporting}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                backgroundColor: exporting ? '#6b7280' : '#1a73e8',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: exporting ? 'not-allowed' : 'pointer',
                fontSize: '0.9rem',
                fontWeight: '600',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => !exporting && (e.target.style.backgroundColor = '#1557b0')}
              onMouseOut={(e) => !exporting && (e.target.style.backgroundColor = '#1a73e8')}
            >
              <FontAwesomeIcon icon={exporting ? faDownload : faFilePdf} spin={exporting} />
              {exporting ? 'Exporting...' : 'Export PDF Report'}
            </button>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">
                <FontAwesomeIcon icon={faChartLine} />
              </div>
              <div className="stat-content">
                <h3>Practice Sessions</h3>
                <p className="stat-number">{dashboardStats?.pronunciation_sessions || 0}</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">
                <FontAwesomeIcon icon={faStar} />
              </div>
              <div className="stat-content">
                <h3>Avg Score</h3>
                <p className="stat-number">{dashboardStats?.avg_pronunciation_score?.toFixed(0) || 0}%</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">
                <FontAwesomeIcon icon={faTrophy} />
              </div>
              <div className="stat-content">
                <h3>Words Practiced</h3>
                <p className="stat-number">{dashboardStats?.words_practiced || 0}</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">
                <FontAwesomeIcon icon={faClock} />
              </div>
              <div className="stat-content">
                <h3>Grammar Corrections</h3>
                <p className="stat-number">{dashboardStats?.grammar_corrections || 0}</p>
              </div>
            </div>
          </div>

          <div className="charts-grid">
            <div className="chart-card">
              <h3>Skill Progress</h3>
              <div className="chart-container">
                <canvas ref={chartRefs.skills} width={400} height={300}></canvas>
              </div>
            </div>
            <div className="chart-card">
              <h3>Weekly Activity</h3>
              <div className="chart-container">
                <canvas ref={chartRefs.weekly} width={400} height={300}></canvas>
              </div>
            </div>
            <div className="chart-card">
              <h3>Daily Progress Overview</h3>
              <div className="chart-container">
                <canvas ref={chartRefs.daily} width={400} height={300}></canvas>
              </div>
            </div>
            <div className="chart-card">
              <h3>Monthly Progress Trend</h3>
              <div className="chart-container">
                <canvas ref={chartRefs.monthly} width={400} height={300}></canvas>
              </div>
            </div>
            <div className="chart-card">
              <h3>Module Comparison</h3>
              <div className="chart-container">
                <canvas ref={chartRefs.module} width={400} height={300}></canvas>
              </div>
            </div>
            <div className="chart-card">
              <h3>Learning Time Distribution</h3>
              <div className="chart-container">
                <canvas ref={chartRefs.time} width={400} height={300}></canvas>
              </div>
            </div>
          </div>

          <div className="module-progress">
            <ProgressPage />
          </div>

          <div className="achievements">
            <h2>Recent Achievements</h2>
            <div className="achievements-grid">
              <div className="achievement-card">
                <div className="achievement-icon">
                  <FontAwesomeIcon icon={faChartBar} />
                </div>
                <div className="achievement-content">
                  <h3>Progress Master</h3>
                  <p>Completed 10 lessons in a row</p>
                </div>
              </div>
              <div className="achievement-card">
                <div className="achievement-icon">
                  <FontAwesomeIcon icon={faCalendarCheck} />
                </div>
                <div className="achievement-content">
                  <h3>Consistency King</h3>
                  <p>7-day learning streak</p>
                </div>
              </div>
              <div className="achievement-card">
                <div className="achievement-icon">
                  <FontAwesomeIcon icon={faBolt} />
                </div>
                <div className="achievement-content">
                  <h3>Speed Demon</h3>
                  <p>Completed 5 exercises in under 10 minutes</p>
                </div>
              </div>
              <div className="achievement-card">
                <div className="achievement-icon">
                  <FontAwesomeIcon icon={faStar} />
                </div>
                <div className="achievement-content">
                  <h3>Perfect Score</h3>
                  <p>Achieved 100% accuracy in a lesson</p>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Practice Sessions */}
          <div className="recent-sessions-section" style={{ marginTop: '2rem' }}>
            <h2>Recent Practice Sessions</h2>
            {pronunciationSessions.length > 0 ? (
              <div className="sessions-list" style={{ marginTop: '1rem', background: 'white', borderRadius: '12px', padding: '1rem', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #eee', textAlign: 'left' }}>
                      <th style={{ padding: '1rem' }}>Date</th>
                      <th style={{ padding: '1rem' }}>Words</th>
                      <th style={{ padding: '1rem' }}>Score</th>
                      <th style={{ padding: '1rem' }}>Errors</th>
                      <th style={{ padding: '1rem' }}>Text</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pronunciationSessions.slice(0, 10).map((session) => (
                      <tr key={session.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                        <td style={{ padding: '1rem' }}>{new Date(session.created_at).toLocaleDateString()}</td>
                        <td style={{ padding: '1rem' }}>{session.word_count || 0}</td>
                        <td style={{ padding: '1rem' }}>
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: '12px',
                            background: session.overall_score >= 80 ? '#dcfce7' : session.overall_score >= 60 ? '#fef9c3' : '#fee2e2',
                            color: session.overall_score >= 80 ? '#166534' : session.overall_score >= 60 ? '#854d0e' : '#991b1b',
                            fontWeight: '600'
                          }}>
                            {session.overall_score}%
                          </span>
                        </td>
                        <td style={{ padding: '1rem' }}>{session.error_count || 0}</td>
                        <td style={{ padding: '1rem', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {session.transcribed_text}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', background: 'white', borderRadius: '12px', color: '#64748b' }}>
                <p>No practice sessions yet. Start a Live Call to see your progress!</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="user-profile">
        <div className="profile-icon" onClick={toggleProfileDropdown}>
          <i className="fas fa-user"></i>
        </div>
        <div className={`profile-dropdown ${profileDropdownOpen ? 'show' : ''}`}>
          <Link to="/dashboard/settings" className="profile-dropdown-item" onClick={() => setProfileDropdownOpen(false)}>
            <i className="fas fa-user-circle"></i>
            <span>My Profile</span>
          </Link>
          <Link to="/dashboard" className="profile-dropdown-item" onClick={() => setProfileDropdownOpen(false)}>
            <i className="fas fa-home"></i>
            <span>Dashboard</span>
          </Link>
          <Link to="/dashboard/settings" className="profile-dropdown-item" onClick={() => setProfileDropdownOpen(false)}>
            <i className="fas fa-cog"></i>
            <span>Settings</span>
          </Link>
          <a href="#" onClick={async (e) => { e.preventDefault(); await authAPI.logout(); window.location.href = '/'; }} className="profile-dropdown-item logout-item">
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
        </div>
      </div>
    </div>
  );
};

export default Progress; 