import { createContext, useContext, useEffect, useState } from "react";
import { endpoints } from "../services/api";

const AuthContext = createContext(null);

const TOKEN_KEY = "token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await endpoints.me();
      setUser(me);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const refreshMe = async () => {
    const me = await endpoints.me();
    setUser(me);
    return me;
  };

  useEffect(() => {
    loadMe();
  }, []);

  const login = async (email, password) => {
    const { access_token } = await endpoints.login({ email, password });
    localStorage.setItem(TOKEN_KEY, access_token);
    const me = await endpoints.me();
    setUser(me);
    return me;
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };

  const value = {
    user,
    loading,
    login,
    logout,
    refreshMe,
    isAuthenticated: !!user,
    isAdmin: user?.role === "ADMIN",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
