"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { api, setAuthToken } from "@/lib/api";

interface User {
  username: string;
  role: string;
  level: string;
  completed: number;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string, role: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      setAuthToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const res = await api.auth.login({ username, password });
    setUser({ 
      username: res.username, 
      role: res.role, 
      level: res.level, 
      completed: res.completed 
    });
    setToken(res.access_token);
    setAuthToken(res.access_token);
    localStorage.setItem("user", JSON.stringify({
      username: res.username,
      role: res.role,
      level: res.level,
      completed: res.completed
    }));
    localStorage.setItem("access_token", res.access_token);
  };

  const signup = async (username: string, password: string, role: string) => {
    const res = await api.auth.signup({ username, password, role });
    // After signup, auto-login
    await login(username, password);
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch (e) {
      // Ignore logout errors
    }
    setUser(null);
    setToken(null);
    setAuthToken(null);
    localStorage.removeItem("user");
    localStorage.removeItem("access_token");
  };

  return (
    <AuthContext.Provider value={{ user, token, login, signup, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}