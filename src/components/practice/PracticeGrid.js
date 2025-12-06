import React from 'react';
import PropTypes from 'prop-types';
import '../Practice.css';

/**
 * PracticeGrid component - Grid of practice modules
 * @param {Function} openModal - Function to open practice modals
 */
const PracticeGrid = ({ openModal }) => {
    const modules = [
        {
            id: 'conversation',
            icon: 'fa-comments',
            title: 'Conversation',
            description: 'Practice everyday English conversations with AI',
            color: '#4a90e2'
        },
        {
            id: 'pronunciation',
            icon: 'fa-microphone',
            title: 'Pronunciation',
            description: 'Perfect your British accent with voice feedback',
            color: '#28a745'
        },
        {
            id: 'speaking',
            icon: 'fa-volume-up',
            title: 'Speaking',
            description: 'Improve fluency through speaking exercises',
            color: '#ffc107'
        },
        {
            id: 'shadowing',
            icon: 'fa-headphones',
            title: 'Shadowing',
            description: 'Listen and repeat to master native patterns',
            color: '#dc3545'
        }
    ];

    return (
        <div className="practice-grid">
            {modules.map((module) => (
                <div
                    key={module.id}
                    className="practice-card"
                    onClick={() => openModal(module.id)}
                    style={{ '--card-color': module.color }}
                >
                    <div className="practice-icon">
                        <i className={`fas ${module.icon}`}></i>
                    </div>
                    <h3>{module.title}</h3>
                    <p>{module.description}</p>
                    <button className="start-btn">
                        Start Practice
                    </button>
                </div>
            ))}
        </div>
    );
};

PracticeGrid.propTypes = {
    openModal: PropTypes.func.isRequired
};

export default PracticeGrid;
