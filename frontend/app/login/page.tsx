"use client";

import { FormEvent, useState } from "react";
import { GraduationCap, LoaderCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("marilia@school.com");
  const [password, setPassword] = useState("mypassword");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const body = new URLSearchParams({ username: email.trim(), password });
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Credenciais inválidas.");
      login(data.access_token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível entrar.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-5">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <span className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-blue-600 text-white"><GraduationCap /></span>
        <h1 className="text-center text-2xl font-semibold">Prisma Escolar</h1>
        <p className="mb-8 mt-2 text-center text-sm text-slate-600">Entre para revisar e publicar a rotina escolar.</p>
        {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <form onSubmit={submit} className="space-y-4">
          <div><label className="mb-1 block text-sm font-medium">E-mail institucional</label><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></div>
          <div><label className="mb-1 block text-sm font-medium">Senha</label><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /></div>
          <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-medium text-white hover:bg-blue-700 disabled:opacity-60">{loading && <LoaderCircle className="h-4 w-4 animate-spin" />} Entrar</button>
        </form>
        <p className="mt-5 text-center text-xs text-slate-500">Conta local preparada: marilia@school.com</p>
      </div>
    </main>
  );
}
