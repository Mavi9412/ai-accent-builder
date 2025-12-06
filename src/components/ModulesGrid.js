import React, { useState, useEffect } from 'react';
import ModuleCard from './ModuleCard';
import { progressAPI } from '../services/api';

/**
 * ModulesGrid component - Displays learning modules in a grid layout
 */
const ModulesGrid = () => {
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchModules = async () => {
      try {
        const moduleProgress = await progressAPI.getModuleProgress();
        
        const formattedModules = moduleProgress.map(module => {
          const hours = Math.floor(module.time_spent_minutes / 60);
          const minutes = module.time_spent_minutes % 60;
          const timeSpent = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

          return {
            title: module.module_name,
            progress: Math.round(module.progress_percentage),
            stats: [
              { number: module.sessions_count?.toString() || '0', label: 'Sessions' },
              { number: `${Math.round(module.accuracy)}%`, label: 'Accuracy' },
              { number: timeSpent, label: 'Time Spent' }
            ]
          };
        });

        // If no modules, show default empty state
        if (formattedModules.length === 0) {
          setModules([
            {
              title: 'Conversation Practice',
              progress: 0,
              stats: [
                { number: '0', label: 'Sessions' },
                { number: '0%', label: 'Accuracy' },
                { number: '0m', label: 'Time Spent' }
              ]
            }
          ]);
        } else {
          setModules(formattedModules);
        }
      } catch (error) {
        console.error('Error fetching module progress:', error);
        // Set default modules on error
        setModules([
          {
            title: 'Conversation Practice',
            progress: 0,
            stats: [
              { number: '0', label: 'Sessions' },
              { number: '0%', label: 'Accuracy' },
              { number: '0m', label: 'Time Spent' }
            ]
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchModules();
  }, []);

  if (loading) {
    return (
      <div className="modules-grid">
        <div className="module-card">
          <p>Loading modules...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="modules-grid">
      {modules.map((module, index) => (
        <ModuleCard key={index} module={module} />
      ))}
    </div>
  );
};

export default ModulesGrid; 