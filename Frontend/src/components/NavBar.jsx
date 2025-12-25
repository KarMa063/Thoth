import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export default function NavBar() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const nav = useNavigate();

  async function handleLogout() {
    await logout();
    nav("/login");
  }

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0,
      height: "64px",
      background: "var(--card-bg)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid var(--card-border)",
      zIndex: 100,
      display: "flex",
      alignItems: "center"
    }}>
      <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
        <Link to="/" style={{ fontSize: "1.5rem", fontWeight: "bold", textDecoration: "none", color: "var(--accent-color)" }}>
          Thoth
        </Link>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <button
            className="btn ghost"
            onClick={toggle}
            aria-label="Toggle theme"
            style={{
              padding: "8px",
              borderRadius: "50%",
              width: "40px",
              height: "40px",
              minWidth: "40px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.2rem",
              border: "1px solid var(--card-border)",
              color: "var(--accent-color)"
            }}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          <Link to="/home" className="btn ghost" style={{ padding: "8px 16px", color: "var(--accent-color)" }}>Home</Link>

          {user ? (
            <button onClick={handleLogout} className="btn ghost" style={{ padding: "8px 16px", color: "var(--accent-color)" }}>Logout</button>
          ) : (
            <Link to="/login" className="btn primary" style={{ padding: "8px 20px" }}>Login</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
