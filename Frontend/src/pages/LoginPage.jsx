import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Pages.css";

function Login({ onLogin }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin(true);
    navigate("/home"); 
  };

  return (
    <div className="page-container">
      <div className="login-form">
        <h1>Login to Thoth</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input 
              type="email" 
              id="email"
              className="form-control"
              placeholder="Enter your email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input 
              type="password" 
              id="password"
              className="form-control"
              placeholder="Enter your password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>
          
          <button type="submit" className="login-btn">Login</button>
        </form>
        
        <div style={{ marginTop: "1.5rem", textAlign: "center" }}>
          <p>Don't have an account? <Link to="/">Back to home</Link></p>
        </div>
      </div>
    </div>
  );
}

export default Login;
