import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './signup.css';

const Signup = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
    // Clear error when user types
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords don't match!");
      return;
    }
    
    if (formData.password.length < 6) {
      setError("Password should be at least 6 characters");
      return;
    }

    if (!formData.fullName || !formData.email) {
      setError("Please fill in all fields");
      return;
    }

    setLoading(true);

    try {
      const result = await register({
        full_name: formData.fullName,
        email: formData.email,
        password: formData.password,
        language: 'english'
      });
      
      if (result.success) {
        // Redirect to dashboard after successful signup
        navigate('/dashboard');
      } else {
        setError(result.error || 'Registration failed. Please try again.');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
      console.error('Signup error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-box">
        <h2>Create Account</h2>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <input
              type="text"
              name="fullName"
              placeholder="Full Name"
              value={formData.fullName}
              onChange={handleChange}
              required
            />
          </div>
          <div className="input-group">
            <input
              type="email"
              name="email"
              placeholder="Email Address"
              value={formData.email}
              onChange={handleChange}
              required
            />
          </div>
          <div className="input-group">
            <input
              type="password"
              name="password"
              placeholder="Password"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>
          <div className="input-group">
            <input
              type="password"
              name="confirmPassword"
              placeholder="Confirm Password"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
            />
          </div>
          <button type="submit" className="signup-button" disabled={loading}>
            {loading ? 'Signing up...' : 'Sign Up'}
          </button>
        </form>
        
        <div className="divider">
          <span>or sign up with</span>
        </div>
        
        <div className="social-signup">
          <button className="social-button google">
            <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" alt="Google" />
            Google
          </button>
          <button className="social-button facebook">
            <img src="https://cdn-icons-png.flaticon.com/512/5968/5968764.png" alt="Facebook" />
            Facebook
          </button>
          <button className="social-button apple">
            <img src="https://cdn-icons-png.flaticon.com/512/0/747.png" alt="Apple" />
            Apple
          </button>
        </div>
        
        <p className="login-link">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default Signup;
