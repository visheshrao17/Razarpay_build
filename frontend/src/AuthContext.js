import React, { createContext, useContext, useEffect, useState } from "react";
import { auth } from "./api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anonymous

  useEffect(() => {
    auth.me().then((r) => setUser(r.data)).catch(() => setUser(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await auth.login(email, password);
    setUser(data);
    return data;
  };

  const logout = async () => {
    try { await auth.logout(); } catch (e) { /* ignore */ }
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
