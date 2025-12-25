import React, { createContext, useContext, useEffect, useState } from "react";
import {
  observeAuth,
  googleLogin,
  githubLogin,
  emailSignIn,
  emailSignUp,
} from "../firebase";
import { auth } from "../firebase";
import { signOut } from "firebase/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // --- Listen for Firebase auth state changes ---
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

  // --- Provider login functions ---
  async function loginWithGoogle() {
    const u = await googleLogin();
    return u;
  }

  async function loginWithGithub() {
    const u = await githubLogin();
    return u;
  }

  async function loginWithEmail(email, password) {
    return await emailSignIn({ email, password });
  }

  async function signupWithEmail(name, email, password) {
    return await emailSignUp({ name, email, password });
  }

  // --- Logout ---
  async function logout() {
    await signOut(auth);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        loginWithGoogle,
        loginWithGithub,
        loginWithEmail,
        signupWithEmail,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
