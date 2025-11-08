import React from "react";
import "../pages/Pages.css";

function Footer() {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <p>&copy; {new Date().getFullYear()} Thoth - AI-powered Literary Analysis</p>
        <div className="footer-links">
          <a href="about">About</a>
          <a href="privacy">Privacy</a>
          <a href="terms">Terms</a>
          <a href="contact">Contact</a>
        </div>
      </div>
    </footer>
  );
}

export default Footer;