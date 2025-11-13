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
    <div className="nav">
      <div className="nav-inner container">
        <Link to="/" className="brand">Thoth</Link>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
          <button className="toggle" onClick={toggle} aria-label="Toggle theme">
            {theme === "dark" ? "Ìºô" : "‚òÄÔ∏è"}
          </button>
          <Link to="/home" className="btn ghost">Home</Link>
          {user ? (
            <button onClick={handleLogout} className="btn">Logout</button>
          ) : (
            <Link to="/login" className="btn primary">Login</Link>
          )}
        </div>
      </div>
    </div>
  );
}
