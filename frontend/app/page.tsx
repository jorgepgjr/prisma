"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { CalendarDays, GraduationCap, LoaderCircle, LogOut, Sparkles, Users } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type SchoolClass = { id: number; name: string; year: number };

export default function DashboardPage() {
  const { user, token, logout, loading: authLoading } = useAuth();
  const router = useRouter();
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadClasses = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/classes/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Não foi possível carregar suas turmas.");
      setClasses(await response.json());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro ao carregar suas turmas.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (authLoading || !user) return;
    if (user.role === "COORDENADOR") { router.replace("/admin"); return; }
    if (user.role === "MARKETING") { router.replace("/marketing"); return; }
    // A carga começa somente depois que a sessão do navegador foi restaurada.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadClasses();
  }, [authLoading, loadClasses, router, user]);

  if (authLoading || !user || user.role !== "PROFESSOR") {
    return <main className="grid min-h-screen place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></main>;
  }

  return <div className="min-h-screen bg-slate-50">
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white"><GraduationCap /></span>
          <div><p className="font-semibold">{user.school.name}</p><p className="text-xs text-slate-500">Área do professor</p></div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/admin/processing" className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100">
            <Sparkles className="h-4 w-4" /><span>Fila facial</span>
          </Link>
          <div className="hidden text-right sm:block"><p className="text-sm font-medium">{user.name}</p><p className="text-xs text-slate-500">{user.email}</p></div>
          <button onClick={logout} className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100" title="Sair"><LogOut className="h-5 w-5" /></button>
        </div>
      </div>
    </header>
    <main className="mx-auto max-w-6xl px-5 py-8">
      <h1 className="text-2xl font-semibold">Minhas turmas</h1>
      <p className="mb-8 mt-1 text-sm text-slate-600">Escolha uma turma para organizar fotos e publicações.</p>
      {error && <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {loading ? (
        <div className="grid py-24 place-items-center"><LoaderCircle className="h-7 w-7 animate-spin text-blue-600" /></div>
      ) : classes.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-14 text-center text-sm text-slate-500">Você ainda não está vinculado a uma turma.</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {classes.map((item) => <Link key={item.id} href={`/class/${item.id}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md">
            <span className="mb-5 grid h-10 w-10 place-items-center rounded-lg bg-blue-50 text-blue-700"><Users className="h-5 w-5" /></span>
            <p className="font-semibold">{item.name}</p>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500"><CalendarDays className="h-4 w-4" />Ano letivo {item.year}</p>
          </Link>)}
        </div>
      )}
    </main>
  </div>;
}
