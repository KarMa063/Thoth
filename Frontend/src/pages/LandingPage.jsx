import React, { useState } from "react";
import { Link } from "react-router-dom";
import "./Pages.css";

function Landing() {
  const [language, setLanguage] = useState("english");

  return (
    <div className="page-container">
      <div className="landing-page">
        <h1>Welcome to Thoth</h1>
        
        <div className="language-toggle">
          <button 
            className={`language-btn ${language === "english" ? "active" : ""}`}
            onClick={() => setLanguage("english")}
          >
            English
          </button>
          <button 
            className={`language-btn ${language === "nepali" ? "active" : ""}`}
            onClick={() => setLanguage("nepali")}
          >
            नेपाली
          </button>
        </div>
        
        {language === "english" ? (
          <p>
            Thoth is your AI-powered bilingual psycho-literary assistant. 
            Analyze writing styles, explore themes, and gain insights into your writing.
            Whether you write in English or Nepali, Thoth helps you understand your unique voice
            and compares your style with renowned authors.
          </p>
        ) : (
          <p>
            थोथ तपाईंको एआई-संचालित द्विभाषी साहित्यिक सहायक हो।
            लेखन शैलीहरू विश्लेषण गर्नुहोस्, विषयवस्तुहरू अन्वेषण गर्नुहोस्, र तपाईंको लेखनमा अन्तर्दृष्टि प्राप्त गर्नुहोस्।
            तपाईं अंग्रेजी वा नेपालीमा लेख्नुहुन्छ, थोथले तपाईंको अद्वितीय आवाज बुझ्न र तपाईंको शैलीलाई प्रसिद्ध लेखकहरूसँग तुलना गर्न मद्दत गर्दछ।
          </p>
        )}
        
        <div className="features-grid">
          <div className="feature-card">
            <h3>Style Analysis</h3>
            <p>Discover your writing style and how it compares to famous authors.</p>
          </div>
          <div className="feature-card">
            <h3>Theme Detection</h3>
            <p>Uncover the main themes and motifs in your writing.</p>
          </div>
          <div className="feature-card">
            <h3>Bilingual Support</h3>
            <p>Works with both English and Nepali text.</p>
          </div>
        </div>
        
        <div>
          <Link to="/login">
            <button className="analyze-btn">Get Started</button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Landing;
