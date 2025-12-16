import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Login from './components/login.js';
import Signup from './components/signup.js';
import Header from './components/header/Header.js';
import Hero from './components/hero.js';
import Features from './components/feature.js';
import Research from './research.js';
import S2 from './components/s2.js';
import About from './components/about/About.js';
import Contact from './components/contact/Contact.js';
import Footer from './components/footer/Footer.js';
import Dashboard from './components/dashboard';
import Lessons from './components/Lessons';
import Practice from './components/Practice';
import Settings from './components/settings/Settings';
import LiveCall from './components/LiveCall';
import Progress from './components/Progress';
import ProtectedRoute from './components/ProtectedRoute';

/**
 * Main App component with routing configuration
 * Landing page, Login, Signup, Dashboard routes, and feature pages
 */
function App() {
  // Initialize dark mode from localStorage on app startup
  useEffect(() => {
    const savedDarkMode = localStorage.getItem('darkMode');
    if (savedDarkMode === 'true') {
      document.body.classList.add('dark-mode');
    }
  }, []);

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={
            <>
              <Header />
              <Hero />
              <Features />
              <Research />
              <S2 />
              <About />
              <Contact />
              <Footer />
            </>
          } />
          <Route path="/login" element={
            <>
              <Header />
              <Login />
              <Footer />
            </>
          } />
          <Route path="/signup" element={
            <>
              <Header />
              <Signup />
              <Footer />
            </>
          } />
          {/* Dashboard routes - Protected */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/lessons" element={
            <ProtectedRoute>
              <Lessons />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/practice" element={
            <ProtectedRoute>
              <Practice />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/settings" element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/live-call" element={
            <ProtectedRoute>
              <LiveCall />
            </ProtectedRoute>
          } />
          <Route path="/dashboard/progress" element={
            <ProtectedRoute>
              <Progress />
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
