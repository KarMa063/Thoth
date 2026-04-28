import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PrivateRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <span className="text-muted">Loading...</span>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" replace />;
}
