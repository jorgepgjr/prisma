"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CalendarDays, GraduationCap, LoaderCircle, LogOut, Plus, Users } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SchoolClass = { id: number; name: string; year: number };

function messageFrom(error: unknown) {
  return error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
}

export default function DashboardPage() {
  const { user, token, logout, loading: authLoading } = useAuth();
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [creating, setCreating] = useState(false);

  const loadClasses = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/classes/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Não foi possível carregar as turmas.");
      setClasses(await response.json());
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    // A carga é disparada quando o token restaurado pelo provedor fica disponível.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!authLoading && token) void loadClasses();
  }, [authLoading, token, loadClasses]);

  async function createClass(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !name.trim()) return;
    setCreating(true);
    try {
      const response = await fetch(`${API_URL}/api/classes/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), year }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Não foi possível criar a turma.");
      setName("");
      await loadClasses();
    } catch (requestError) {
      setError(messageFrom(requestError));
    } finally {
      setCreating(false);
    }
  }

  if (authLoading || !user) {
    return <main className="grid min-h-screen place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></main>;
  }

  const canCreate = ["ADMIN", "DIRETOR", "COORDENADOR"].includes(user.role);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-blue-600 text-white"><GraduationCap /></span>
            <div><p className="font-semibold">Prisma Escolar</p><p className="text-xs text-slate-500">Publicações para as famílias</p></div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block"><p className="text-sm font-medium">{user.email}</p><p className="text-xs text-slate-500">{user.role}</p></div>
            <button onClick={logout} className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100" title="Sair"><LogOut className="h-5 w-5" /></button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight">Turmas</h1>
          <p className="mt-1 text-sm text-slate-600">Escolha uma turma para revisar as fotos recebidas e publicar no TinhaKids.</p>
        </div>

        {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        <div className={canCreate ? "grid gap-6 lg:grid-cols-[280px_1fr]" : ""}>
          {canCreate && (
            <form onSubmit={createClass} className="h-fit rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2 font-medium"><Plus className="h-5 w-5 text-blue-600" /> Nova turma</div>
              <label className="mb-1 block text-sm font-medium">Nome</label>
              <input value={name} onChange={(event) => setName(event.target.value)} required className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" placeholder="Ex.: Grupo 2" />
              <label className="mb-1 block text-sm font-medium">Ano letivo</label>
              <input type="number" value={year} onChange={(event) => setYear(Number(event.target.value))} required className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
              <button disabled={creating} className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">{creating && <LoaderCircle className="h-4 w-4 animate-spin" />} Criar turma</button>
            </form>
          )}

          <section>
            {loading ? (
              <div className="grid place-items-center rounded-xl border border-slate-200 bg-white py-20"><LoaderCircle className="h-7 w-7 animate-spin text-blue-600" /></div>
            ) : classes.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-500">Nenhuma turma disponível.</div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {classes.map((schoolClass) => (
                  <Link key={schoolClass.id} href={`/class/${schoolClass.id}`} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md">
                    <span className="mb-5 grid h-10 w-10 place-items-center rounded-lg bg-blue-50 text-blue-700"><Users className="h-5 w-5" /></span>
                    <p className="font-semibold">{schoolClass.name}</p>
                    <p className="mt-1 flex items-center gap-1.5 text-sm text-slate-500"><CalendarDays className="h-4 w-4" /> Ano letivo {schoolClass.year}</p>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
