"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { api, setAuthToken, ApiError } from "@/lib/api";

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
  /** Re-read /auth/me and replace the cached profile (e.g. after onboarding). */
  refreshUser: () => Promise<void>;
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

    if (!storedToken || !storedUser) {
      setLoading(false);
      return;
    }

    // A stored token is only a claim, not proof that it is still valid — it may
    // have expired, or the session may have been revoked, since it was issued.
    // Confirm it with the server before treating the visitor as signed in, so a
    // dead token fails here instead of half-working until some unrelated
    // request comes back 401.
    //
    // A transport failure (backend asleep, laptop offline) is NOT evidence that
    // the token is bad, so the cached session is kept in that case rather than
    // signing the learner out for an outage outside their control.
    let cancelled = false;

    (async () => {
      try {
        const me = await api.auth.me();
        if (cancelled) return;
        const fresh: User = {
          username: me.username,
          role: me.role,
          level: me.level,
          completed: me.completed,
        };
        setToken(storedToken);
        setAuthToken(storedToken);
        setUser(fresh);
        // Re-sync the cached copy: role/level/completed can change server-side
        // while the browser still holds the values from the original login.
        localStorage.setItem("user", JSON.stringify(fresh));
      } catch (err) {
        if (cancelled) return;
        const status = (err as ApiError)?.status;
        if (status === 401 || status === 403) {
          // The server explicitly rejected the token. apiRequest has already
          // cleared the stored keys on a 401, so just drop the session here.
          setToken(null);
          setAuthToken(null);
          setUser(null);
        } else {
          // Could not reach the server — fall back to what we already had.
          try {
            setToken(storedToken);
            setAuthToken(storedToken);
            setUser(JSON.parse(storedUser));
          } catch {
            setToken(null);
            setAuthToken(null);
            setUser(null);
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
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

  const refreshUser = async () => {
    // Re-read the profile from the server instead of trusting whatever was
    // cached at login. Used after onboarding so the UI never keeps showing the
    // profile from before the learner answered.
    const me = await api.auth.me();
    const fresh: User = {
      username: me.username,
      role: me.role,
      level: me.level,
      completed: me.completed,
    };
    setUser(fresh);
    localStorage.setItem("user", JSON.stringify(fresh));
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
    <AuthContext.Provider value={{ user, token, login, signup, refreshUser, logout, loading }}>
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