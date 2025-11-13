import React, { createContext, useContext, useEffect, useState } from "react";
import { observeAuth, googleLogout } from "../firebase";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsub = observeAuth((fbUser) => {
      if (fbUser) {
        setUser({
          id: fbUser.uid,
          name: fbUser.displayName || fbUser.email,
          email: fbUser.email,
          photo: fbUser.photoURL || null,
          provider: fbUser.providerData?.[0]?.providerId || "password",
        });
      } else {
        setUser(null);
      }
      setLoading(false);
    });
    return () => unsub();
  }, []);

  async function logout() {
    await googleLogout(); // also works when provider is password; it signs out the session
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
