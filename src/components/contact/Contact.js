import React, { useState } from 'react';
import './Contact.css';

// Contact Info Card component - reusable for Email, Phone, Location, and Chat sections
const ContactInfoCard = ({ icon, title, children, buttonText, buttonAction }) => (
  <div className="contact-info-card">
    {/* Icon at the top of the card */}
    <div className="contact-icon">
      {icon}
    </div>
    
    {/* Title of the card (Email, Phone, etc.) */}
    <h3 className="contact-card-title">{title}</h3>
    
    {/* Content specific to each card type - passed as children */}
    <div className="contact-card-content">
      {children}
    </div>
    
    {/* Button at the bottom of the card - text and action are customizable */}
    {buttonText && (
      <button className="contact-card-button" onClick={buttonAction}>
        {buttonText}
      </button>
    )}
  </div>
);

// Main Contact component
const Contact = () => {
  // State for form fields
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
    agreeToPrivacy: false
  });
  
  // State to track character count for message
  const [charCount, setCharCount] = useState(0);
  
  // Handle input changes
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // For text inputs, update value; for checkbox, update checked state
    const inputValue = type === 'checkbox' ? checked : value;
    
    // Update form data state
    setFormData({
      ...formData,
      [name]: inputValue
    });
    
    // Update character count for message field
    if (name === 'message') {
      setCharCount(value.length);
    }
  };
  
  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
    // Here you would typically send the data to a server
    alert('Thank you for your message! We will get back to you soon.');
  };
  
  // Handle form reset
  const handleReset = () => {
    setFormData({
      name: '',
      email: '',
      subject: '',
      message: '',
      agreeToPrivacy: false
    });
    setCharCount(0);
  };

  return (
    <section id="contact" className="contact-section">
      {/* Header with title and subtitle */}
      <div className="contact-header">
        <h2 className="contact-heading">CONTACT US</h2>
        <div className="contact-divider"></div>
        <p className="contact-subheading">
          We'd love to hear from you! Reach out for any questions or feedback
        </p>
      </div>

      {/* Contact info cards and form container */}
      <div className="contact-content">
        {/* Left side with contact info cards */}
        <div className="contact-info">
          {/* Email Card */}
          <ContactInfoCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="24" height="24" fill="#4A89DC">
                <path d="M48 64C21.5 64 0 85.5 0 112c0 15.1 7.1 29.3 19.2 38.4L236.8 313.6c11.4 8.5 27 8.5 38.4 0L492.8 150.4c12.1-9.1 19.2-23.3 19.2-38.4c0-26.5-21.5-48-48-48H48zM0 176V384c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V176L294.4 339.2c-22.8 17.1-54 17.1-76.8 0L0 176z"/>
              </svg>
            } 
            title="Email" 
            buttonText="Send Email"
            buttonAction={() => window.location.href="mailto:info@aiaccent.com"}
          >
            <p className="contact-info-text">info@aiaccent.com</p>
            <p className="contact-info-text">support@aiaccent.com</p>
          </ContactInfoCard>
          
          {/* Phone Card */}
          <ContactInfoCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="24" height="24" fill="#4A89DC">
                <path d="M164.9 24.6c-7.7-18.6-28-28.5-47.4-23.2l-88 24C12.1 30.2 0 46 0 64C0 311.4 200.6 512 448 512c18 0 33.8-12.1 38.6-29.5l24-88c5.3-19.4-4.6-39.7-23.2-47.4l-96-40c-16.3-6.8-35.2-2.1-46.3 11.6L304.7 368C234.3 334.7 177.3 277.7 144 207.3L193.3 167c13.7-11.2 18.4-30 11.6-46.3l-40-96z"/>
              </svg>
            } 
            title="Phone" 
            buttonText="Call Us"
            buttonAction={() => window.location.href="tel:+15551234567"}
          >
            <p className="contact-info-text">+1 (555) 123-4567</p>
            <p className="contact-info-text contact-hours">Mon-Fri, 9am-5pm EST</p>
          </ContactInfoCard>
          
          {/* Location Card */}
          <ContactInfoCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512" width="24" height="24" fill="#4A89DC">
                <path d="M215.7 499.2C267 435 384 279.4 384 192C384 86 298 0 192 0S0 86 0 192c0 87.4 117 243 168.3 307.2c12.3 15.3 35.1 15.3 47.4 0zM192 128a64 64 0 1 1 0 128 64 64 0 1 1 0-128z"/>
              </svg>
            } 
            title="Location" 
            buttonText="View Map"
            buttonAction={() => window.open("https://maps.google.com", "_blank")}
          >
            <p className="contact-info-text">123 AI Drive</p>
            <p className="contact-info-text">Tech City, TC 10101</p>
          </ContactInfoCard>
          
          {/* Live Chat Card */}
          <ContactInfoCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512" width="24" height="24" fill="#4A89DC">
                <path d="M208 0C322.9 0 416 78.8 416 176C416 273.2 322.9 352 208 352C189.3 352 171.2 349.7 153.9 345.8C123.3 364.8 79.13 384 24.95 384C14.97 384 5.93 378.1 2.018 368.9C-1.896 359.7-.0074 349.1 6.739 341.9C7.26 341.5 29.38 317.4 45.73 285.9C17.18 255.8 0 217.6 0 176C0 78.8 93.13 0 208 0zM164.6 298.1C179.2 302.3 193.8 304 208 304C296.2 304 368 246.6 368 176C368 105.4 296.2 48 208 48C119.8 48 48 105.4 48 176C48 211.2 65.71 237.2 80.57 252.9L104.1 277.8L88.31 308.1C84.74 314.1 80.73 321.9 76.55 328.5C94.26 323.4 111.7 315.5 128.7 304.1L145.4 294.6L164.6 298.1zM441.6 128.2C552 132.4 640 209.5 640 304C640 345.6 622.8 383.8 594.3 413.9C610.6 445.4 632.7 469.5 633.3 469.9C640 477.1 641.9 487.7 637.1 496.9C634.1 506.1 625 512 615 512C560.9 512 516.7 492.8 486.1 473.8C468.8 477.7 450.7 480 432 480C350 480 279.1 439.8 245.2 381.5C262.5 379.2 279.1 375.3 294.9 369.9C322.9 407.1 373.9 432 432 432C446.2 432 460.8 430.3 475.4 426.1L494.6 422.6L511.3 432.1C528.3 443.5 545.7 451.4 563.5 456.5C559.3 449.9 555.3 442.1 551.7 436.1L535.9 405.8L559.4 380.9C574.3 365.3 592 339.2 592 304C592 237.7 528.7 183.1 447.1 176.6L447.1 176.8C447.4 183.1 448 189.3 448 176C448 159.1 445.5 142.5 441.6 128.2H441.6z"/>
              </svg>
            } 
            title="Live Chat" 
            buttonText="Start Chat"
            buttonAction={() => alert("Chat functionality would open here")}
          >
            <p className="contact-info-text">Available 24/7</p>
            <p className="contact-info-text">Get instant support</p>
          </ContactInfoCard>
        </div>
        
        {/* Right side with contact form */}
        <div className="contact-form-container">
          <form className="contact-form" onSubmit={handleSubmit}>
            {/* Name field */}
            <div className="form-group">
              <label htmlFor="name">Your Name</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Enter your full name"
                required
              />
            </div>
            
            {/* Email field */}
            <div className="form-group">
              <label htmlFor="email">Your Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="Enter your email address"
                required
              />
            </div>
            
            {/* Subject dropdown */}
            <div className="form-group">
              <label htmlFor="subject">Subject</label>
              <select
                id="subject"
                name="subject"
                value={formData.subject}
                onChange={handleInputChange}
                required
              >
                <option value="" disabled>Select a subject</option>
                <option value="general">General Inquiry</option>
                <option value="support">Technical Support</option>
                <option value="billing">Billing Question</option>
                <option value="feedback">Feedback</option>
              </select>
            </div>
            
            {/* Message textarea */}
            <div className="form-group">
              <label htmlFor="message">Message</label>
              <textarea
                id="message"
                name="message"
                value={formData.message}
                onChange={handleInputChange}
                placeholder="Type your message here..."
                rows="5"
                maxLength="500"
                required
              ></textarea>
              <div className="char-count">{charCount}/500 characters</div>
            </div>
            
            {/* Privacy policy checkbox - Updated to match the image */}
            <div className="form-group privacy-group">
              <div className="checkbox-wrapper">
                <input
                  type="checkbox"
                  id="privacy"
                  name="agreeToPrivacy"
                  checked={formData.agreeToPrivacy}
                  onChange={handleInputChange}
                  required
                />
                <label htmlFor="privacy">
                  I agree to the processing of my data as per the <a href="#" className="privacy-link">Privacy Policy</a>
                </label>
              </div>
            </div>
            
            {/* Form buttons */}
            <div className="form-buttons">
              <button type="button" className="reset-button" onClick={handleReset}>
                Reset
              </button>
              <button type="submit" className="submit-button">
                Send Message
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="16" height="16" fill="currentColor" className="send-icon">
                  <path d="M498.1 5.6c10.1 7 15.4 19.1 13.5 31.2l-64 416c-1.5 9.7-7.4 18.2-16 23s-18.9 5.4-28 1.6L284 427.7l-68.5 74.1c-8.9 9.7-22.9 12.9-35.2 8.1S160 493.2 160 480V396.4c0-4 1.5-7.8 4.2-10.7L331.8 202.8c5.8-6.3 5.6-16-.4-22s-15.7-6.4-22-.7L106 360.8 17.7 316.6C7.1 311.3 .3 300.7 0 288.9s5.9-22.8 16.1-28.7l448-256c10.7-6.1 23.9-5.5 34 1.4z"/>
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
};

export default Contact; 