import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { AUTH_API_URL } from "../lib/constants";

const TOKEN_KEY = "sentinel_token";

export type AuthUser = {
  id: string;
  username: string;
  email: string;
  role: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuthProvider(): AuthContextValue {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setUser(token ? _parseUser(token) : null);
  }, [token]);

  const _save = useCallback((data: {
    access_token: string; user_id: string;
    username: string; email: string; role: string;
  }) => {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    setUser({ id: data.user_id, username: data.username, email: data.email, role: data.role });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${AUTH_API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Login failed");
      _save(await res.json());
    } finally {
      setIsLoading(false);
    }
  }, [_save]);

  const register = useCallback(async (username: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${AUTH_API_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Registration failed");
      _save(await res.json());
    } finally {
      setIsLoading(false);
    }
  }, [_save]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return { user, token, isLoading, login, register, logout };
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function _parseUser(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return { id: payload.sub, username: payload.username ?? "", email: "", role: payload.role };
  } catch {
    return null;
  }
}
