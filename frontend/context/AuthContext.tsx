"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  role: "COORDENADOR" | "PROFESSOR" | "MARKETING";
  school_id: number;
  school: { id: number; name: string; plan_name: string; is_active: boolean };
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function loadProfile(token: string): Promise<UserProfile> {
  const response = await fetch(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("Sessão inválida.");
  return response.json();
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    // O estado inicial depende do armazenamento disponível apenas no navegador.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!savedToken) { setLoading(false); return; }
    loadProfile(savedToken).then((profile) => {
      setToken(savedToken); setUser(profile);
    }).catch(() => {
      localStorage.removeItem("token");
      document.cookie = "token=; path=/; max-age=0; SameSite=Lax";
      router.replace("/login");
    }).finally(() => setLoading(false));
  }, [router]);

  const login = async (newToken: string) => {
    const profile = await loadProfile(newToken);
    localStorage.setItem("token", newToken);
    document.cookie = `token=${newToken}; path=/; max-age=${30 * 60}; SameSite=Lax`;
    setToken(newToken); setUser(profile);
    router.push(profile.role === "COORDENADOR" ? "/admin" : profile.role === "MARKETING" ? "/marketing" : "/");
  };

  const logout = () => {
    localStorage.removeItem("token");
    document.cookie = "token=; path=/; max-age=0; SameSite=Lax";
    setToken(null); setUser(null); router.push("/login");
  };

  return <AuthContext.Provider value={{ user, token, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth deve ser utilizado dentro de AuthProvider");
  return context;
}
