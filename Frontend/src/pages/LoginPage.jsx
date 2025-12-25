import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { googleLogin, githubLogin, emailSignIn, emailSignUp } from "../firebase";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState("traditional");
  const [mode, setMode] = useState("signin");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  if (user) nav("/home");

  async function handleGoogle() {
    try {
      setBusy(true);
      await googleLogin();
      nav("/home");
    } catch (e) {
      alert(e.message || "Google sign-in failed");
    } finally { setBusy(false); }
  }

  async function handleGithub() {
    try {
      setBusy(true);
      await githubLogin();
      nav("/home");
    } catch (e) {
      console.error(e);
      if (e.code === "auth/account-exists-with-different-credential") {
        alert("An account with this email already exists using a different sign-in method (likely Google or Email). Please sign in using your original method.");
      } else {
        alert(e.message || "GitHub sign-in failed");
      }
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
    <div className="center" style={{ minHeight: "100vh", padding: "2rem" }}>
      <div className="panel fade-in" style={{ width: "100%", maxWidth: 480 }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{ marginBottom: 8, fontSize: "2.5rem" }}>
            <span className="gradient-text">Welcome Back</span>
          </h1>
          <p className="small" style={{ fontSize: "16px" }}>
            Sign in to your intelligent workspace
          </p>
        </div>

        <div style={{ display: "flex", gap: "1rem", marginBottom: 32, padding: 4, background: "var(--bg-secondary)", borderRadius: 12 }}>
          <button
            className="btn"
            style={{ flex: 1, background: tab === "traditional" ? "var(--card-bg)" : "transparent", color: tab === "traditional" ? "var(--text-primary)" : "var(--text-secondary)", boxShadow: tab === "traditional" ? "var(--card-shadow)" : "none" }}
            onClick={() => setTab("traditional")}
          >
            Email
          </button>
          <button
            className="btn"
            style={{ flex: 1, background: tab === "social" ? "var(--card-bg)" : "transparent", color: tab === "social" ? "var(--text-primary)" : "var(--text-secondary)", boxShadow: tab === "social" ? "var(--card-shadow)" : "none" }}
            onClick={() => setTab("social")}
          >
            Social
          </button>
        </div>

        {tab === "traditional" ? (
          <>
            <form onSubmit={handleEmailSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {mode === "signup" && (
                <div>
                  <label className="small" style={{ display: "block", marginBottom: 8, fontWeight: 500 }}>Full Name</label>
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
                <label className="small" style={{ display: "block", marginBottom: 8, fontWeight: 500 }}>Email Address</label>
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
                <label className="small" style={{ display: "block", marginBottom: 8, fontWeight: 500 }}>Password</label>
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
                {busy ? "Processing..." : (mode === "signup" ? "Create Account" : "Sign In")}
              </button>
            </form>

            <div style={{ marginTop: 24, textAlign: "center" }}>
              <button
                className="btn ghost"
                onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
                style={{ fontSize: "0.9rem", padding: "8px 16px" }}
              >
                {mode === "signin" ? "No account? Create one" : "Already have an account? Sign in"}
              </button>
            </div>
          </>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <button
              className="btn"
              onClick={handleGoogle}
              disabled={busy}
              style={{ width: "100%", justifyContent: "center", background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--text-primary)" }}
            >
              <span style={{ fontSize: "1.2rem" }}>🔮</span> Continue with Google
            </button>

            <button
              className="btn"
              onClick={handleGithub}
              disabled={busy}
              style={{ width: "100%", justifyContent: "center", background: "#24292e", color: "white", border: "none" }}
            >
              <span style={{ fontSize: "1.2rem" }}>🐙</span> Continue with GitHub
            </button>

            <p className="small" style={{ textAlign: "center", marginTop: 16, lineHeight: "1.6" }}>
              Quick and secure authentication using Firebase.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
