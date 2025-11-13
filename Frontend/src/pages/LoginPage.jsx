import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { googleLogin, emailSignIn, emailSignUp } from "../firebase";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState("traditional");     // "traditional" | "google"
  const [mode, setMode] = useState("signin");        // "signin" | "signup"
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  if (user) nav("/home"); // already signed in

  async function handleGoogle() {
    try {
      setBusy(true);
      await googleLogin();
      nav("/home");
    } catch (e) {
      alert(e.message || "Google sign-in failed");
    } finally { setBusy(false); }
  }

  async function handleEmailSubmit(e) {
    e.preventDefault();
    if (!form.email || !form.password) return alert("Email and password are required.");
    try {
      setBusy(true);
      if (mode === "signup") {
        if (!form.name.trim()) return alert("Please enter your name.");
        await emailSignUp({ name: form.name.trim(), email: form.email.trim(), password: form.password });
      } else {
        await emailSignIn({ email: form.email.trim(), password: form.password });
      }
      nav("/home");
    } catch (e) {
      alert(e.message || "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container" style={{ maxWidth: 520, marginTop: 60, marginBottom: 60 }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <h1 style={{ marginBottom: 12 }}>Welcome to Thoth</h1>
        <p className="small" style={{ fontSize: "16px", color: "var(--muted)" }}>
          Sign in to start analyzing and transforming your writing
        </p>
      </div>
      
      <div className="panel fade-in">
        <div className="tab-group">
          <button 
            className={`tab-btn ${tab === "traditional" ? "active" : ""}`} 
            onClick={() => setTab("traditional")}
          >
            Email & Password
          </button>
          <button 
            className={`tab-btn ${tab === "google" ? "active" : ""}`} 
            onClick={() => setTab("google")}
          >
            Google Sign In
          </button>
        </div>

        {tab === "traditional" ? (
          <>
            <div className="mode-group">
              <button 
                className={`mode-btn ${mode === "signin" ? "active" : ""}`} 
                onClick={() => setMode("signin")}
              >
                Sign In
              </button>
              <button 
                className={`mode-btn ${mode === "signup" ? "active" : ""}`} 
                onClick={() => setMode("signup")}
              >
                Create Account
              </button>
            </div>

            <form onSubmit={handleEmailSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {mode === "signup" && (
                <div>
                  <label className="small">Full Name</label>
                  <input
                    className="input"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Enter your full name"
                    required
                  />
                </div>
              )}
              <div>
                <label className="small">Email Address</label>
                <input
                  className="input"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </div>
              <div>
                <label className="small">Password</label>
                <input
                  className="input"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Minimum 6 characters"
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  required
                />
              </div>
              <button 
                className="btn primary" 
                style={{ width: "100%", marginTop: 8 }} 
                disabled={busy}
                type="submit"
              >
                {busy ? (mode === "signup" ? "Creating Account…" : "Signing In…") : (mode === "signup" ? "Create Account" : "Sign In")}
              </button>
            </form>
          </>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, alignItems: "center" }}>
            <button 
              className="btn primary" 
              onClick={handleGoogle} 
              disabled={busy} 
              style={{ width: "100%", padding: "14px 20px", fontSize: "15px" }}
            >
              {busy ? "Signing in…" : "🔐 Sign in with Google"}
            </button>
            <p className="small" style={{ textAlign: "center", margin: 0, lineHeight: "1.6" }}>
              Quick and secure authentication using Firebase. Your data is protected and encrypted.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
