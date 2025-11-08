import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import Landing from "./pages/LandingPage";
import Login from "./pages/LoginPage";
import Home from "./pages/HomePage";
import Footer from "./components/Footer";
import ThemeToggle from "./components/ThemeToggle";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  
  // Check localStorage for login state on component mount
  useEffect(() => {
    const loggedInStatus = localStorage.getItem('isLoggedIn');
    if (loggedInStatus === 'true') {
      setIsLoggedIn(true);
    }
  }, []);
  
  // Update handler to store login state in localStorage
  const handleLoginStatus = (status) => {
    setIsLoggedIn(status);
    localStorage.setItem('isLoggedIn', status.toString());
  };

  return (
    <Router>
      <div className="app-wrapper">
        <ThemeToggle />
        <div className="app-content">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login onLogin={handleLoginStatus} />} />
            <Route
              path="/home"
              element={
                isLoggedIn ? (
                  <Home onLogout={handleLoginStatus} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </div>
        <Footer />
      </div>
    </Router>
  );
}

export default App;
