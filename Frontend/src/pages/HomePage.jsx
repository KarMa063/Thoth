import React, { useState, useEffect } from "react";
import Footer from "../components/Footer";
import "./Pages.css";

function Home({ onLogout }) {
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("english");
  const [results, setResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = () => {
    if (!text.trim()) return;
    
    setIsAnalyzing(true);
    
    setTimeout(() => {
      setResults({
        authorMatch: {
          english: "George Orwell",
          nepali: "Laxmi Prasad Devkota",
          similarity: "78%"
        },
        themes: ["Nature", "Identity", "Conflict", "Transformation"],
        sentiment: "Mostly positive with elements of reflection",
        complexity: "Moderate to high",
        uniqueWords: 127
      });
      setIsAnalyzing(false);
    }, 1500);
  };

  return (
    <div className="page-container">
      <div className="dashboard">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Thoth Analysis Dashboard</h1>
          <button className="logout-btn" onClick={() => onLogout(false)}>
            Logout
          </button>
        </div>
        
        <div className="analysis-section">
          <h2>Analyze Your Writing</h2>
          <p>
            Paste your text below and Thoth will analyze it to identify themes, 
            writing style, and compare it with renowned authors in your chosen language.
          </p>
          
          <div className="language-toggle" style={{ justifyContent: "flex-start", marginBottom: "1rem" }}>
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
          
          <textarea 
            className="text-input"
            placeholder={language === "english" 
              ? "Enter your text here (minimum 100 words for best results)..." 
              : "यहाँ आफ्नो पाठ प्रविष्ट गर्नुहोस् (उत्तम परिणामहरूको लागि कम्तिमा १०० शब्दहरू)..."}
            value={text}
            onChange={(e) => setText(e.target.value)}
          ></textarea>
          
          <button 
            className="analyze-btn" 
            onClick={handleAnalyze}
            disabled={isAnalyzing || !text.trim()}
          >
            {isAnalyzing ? "Analyzing..." : "Analyze Text"}
          </button>
        </div>
        
        {results && (
          <div className="analysis-section results-container">
            <h2>Analysis Results</h2>
            
            <div className="results-grid">
              <div className="result-card">
                <h3>Author Match</h3>
                <p>Your writing style is similar to:</p>
                <p><strong>{language === "english" ? results.authorMatch.english : results.authorMatch.nepali}</strong></p>
                <p>Similarity: {results.authorMatch.similarity}</p>
              </div>
              
              <div className="result-card">
                <h3>Themes Detected</h3>
                <ul>
                  {results.themes.map((theme, index) => (
                    <li key={index}>{theme}</li>
                  ))}
                </ul>
              </div>
              
              <div className="result-card">
                <h3>Sentiment Analysis</h3>
                <p>{results.sentiment}</p>
              </div>
              
              <div className="result-card">
                <h3>Complexity</h3>
                <p>Reading level: {results.complexity}</p>
                <p>Unique words: {results.uniqueWords}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;
