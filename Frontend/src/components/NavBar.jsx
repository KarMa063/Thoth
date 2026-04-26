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
    <nav className="nav-bar">
      <div className="nav-inner">
        <Link to="/" className="nav-brand">
          Thoth
        </Link>

        <div className="nav-actions">
          <button
            className="btn btn-icon ghost theme-toggle"
            onClick={toggle}
            aria-label="Toggle theme"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            type="button"
          >
            {theme === "dark" ? "L" : "D"}
          </button>

          {user && (
            <Link to="/home" className="btn ghost">
              Workspace
            </Link>
          )}

          {user ? (
            <button onClick={handleLogout} className="btn ghost" type="button">
              Sign Out
            </button>
          ) : (
            <Link to="/login" className="btn primary">
              Sign In
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
