import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { emailSignIn, emailSignUp, githubLogin, googleLogin } from "../firebase";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const errorTimeoutRef = useRef(null);
  const [tab, setTab] = useState("email");
  const [mode, setMode] = useState("signin");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  useEffect(() => {
    return () => clearTimeout(errorTimeoutRef.current);
  }, []);

  if (user) return <Navigate to="/home" replace />;

  function showError(message) {
    clearTimeout(errorTimeoutRef.current);
    setError(message);
    errorTimeoutRef.current = setTimeout(() => setError(""), 5000);
  }

  async function handleGoogle() {
    try {
      setBusy(true);
      setError("");
      await googleLogin();
      nav("/home");
    } catch (err) {
      showError(err.message || "Google sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleGithub() {
    try {
      setBusy(true);
      setError("");
      await githubLogin();
      nav("/home");
    } catch (err) {
      if (err.code === "auth/account-exists-with-different-credential") {
        showError("An account with this email already exists. Use the original sign-in method.");
      } else {
        showError(err.message || "GitHub sign-in failed");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleEmailSubmit(event) {
    event.preventDefault();
    if (!form.email || !form.password) {
      showError("Email and password are required.");
      return;
    }

    if (mode === "signup" && !form.name.trim()) {
      showError("Please enter your name.");
      return;
    }

    try {
      setBusy(true);
      setError("");
      if (mode === "signup") {
        await emailSignUp({
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
        });
      } else {
        await emailSignIn({
          email: form.email.trim(),
          password: form.password,
        });
      }
      nav("/home");
    } catch (err) {
      showError(err.message || "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="auth-page center">
      <div className="auth-shell">
        <header className="auth-header fade-in">
          <Link to="/" className="auth-logo">
            Thoth
          </Link>
          <h1>{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
          <p className="text-muted">
            {mode === "signup"
              ? "Create a workspace account to test the system"
              : "Sign in to continue to your workspace"}
          </p>
        </header>

        <section className="panel auth-panel fade-in">
          {error && <div className="error-inline">{error}</div>}

          <div className="tab-group">
            <button
              className={`tab-btn ${tab === "email" ? "active" : ""}`}
              type="button"
              onClick={() => setTab("email")}
            >
              Email
            </button>
            <button
              className={`tab-btn ${tab === "social" ? "active" : ""}`}
              type="button"
              onClick={() => setTab("social")}
            >
              Social
            </button>
          </div>

          {tab === "email" ? (
            <>
              <form className="auth-form" onSubmit={handleEmailSubmit}>
                {mode === "signup" && (
                  <div>
                    <label className="panel-label">Full Name</label>
                    <input
                      className="input"
                      value={form.name}
                      onChange={(event) => updateForm("name", event.target.value)}
                      placeholder="Your full name"
                      required
                    />
                  </div>
                )}

                <div>
                  <label className="panel-label">Email Address</label>
                  <input
                    className="input"
                    type="email"
                    value={form.email}
                    onChange={(event) => updateForm("email", event.target.value)}
                    placeholder="you@example.com"
                    autoComplete="email"
                    required
                  />
                </div>

                <div>
                  <label className="panel-label">Password</label>
                  <input
                    className="input"
                    type="password"
                    value={form.password}
                    onChange={(event) => updateForm("password", event.target.value)}
                    placeholder="Minimum 6 characters"
                    autoComplete={mode === "signup" ? "new-password" : "current-password"}
                    required
                  />
                </div>

                <button className="btn primary auth-submit" disabled={busy} type="submit">
                  {busy ? "Processing..." : mode === "signup" ? "Create Account" : "Sign In"}
                </button>
              </form>

              <div className="auth-mode-switch">
                <button
                  className="btn ghost"
                  type="button"
                  onClick={() => {
                    setMode(mode === "signin" ? "signup" : "signin");
                    setError("");
                  }}
                >
                  {mode === "signin"
                    ? "No account? Create one"
                    : "Already have an account? Sign in"}
                </button>
              </div>
            </>
          ) : (
            <div className="social-auth">
              <button className="btn" type="button" onClick={handleGoogle} disabled={busy}>
                <span>G</span> Continue with Google
              </button>
              <button className="btn" type="button" onClick={handleGithub} disabled={busy}>
                <span>GH</span> Continue with GitHub
              </button>
              <p className="text-hint">
                Secured by Firebase Authentication
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
