"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../context/AuthContext";
import { 
  LogOut, 
  Users, 
  FolderPlus, 
  GraduationCap, 
  Image as ImageIcon,
  ShieldCheck, 
  Plus, 
  Calendar,
  Sparkles,
  Loader2
} from "lucide-react";

interface ClassData {
  id: number;
  name: string;
  year: number;
  created_at: string;
}

export default function DashboardPage() {
  const { user, token, logout, loading: authLoading } = useAuth();
  const [classes, setClasses] = useState<ClassData[]>([]);
  const [loadingClasses, setLoadingClasses] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados do formulário de criação de turma (Apenas ADMIN/DIRETOR/COORDENADOR)
  const [className, setClassName] = useState("");
  const [classYear, setClassYear] = useState(new Date().getFullYear());
  const [isCreatingClass, setIsCreatingClass] = useState(false);
  const [createSuccess, setCreateSuccess] = useState(false);

  useEffect(() => {
    if (!authLoading && token && user) {
      fetchClasses();
    }
  }, [authLoading, token, user]);

  const fetchClasses = async () => {
    setLoadingClasses(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/classes/", {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (res.status === 403) {
        // Para Marketing, classes podem retornar 403 dependendo da implementação, tratamos com elegância
        setClasses([]);
        setLoadingClasses(false);
        return;
      }
      if (!res.ok) throw new Error("Falha ao carregar as turmas.");
      const data = await res.json();
      setClasses(data);
    } catch (err: any) {
      setError(err.message || "Erro de conexão.");
    } finally {
      setLoadingClasses(false);
    }
  };

  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!className) return;
    setIsCreatingClass(true);
    setCreateSuccess(false);

    try {
      const res = await fetch("http://localhost:8000/api/classes/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name: className, year: classYear })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Erro ao criar turma.");
      }

      setClassName("");
      setCreateSuccess(true);
      fetchClasses(); // Atualiza a lista
      setTimeout(() => setCreateSuccess(false), 3000);
    } catch (err: any) {
      alert(err.message || "Não foi possível criar a turma.");
    } finally {
      setIsCreatingClass(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  // Se não houver usuário logado (gerenciado pelo Middleware, mas previne quebra de render)
  if (!user) return null;

  const isAdminOrDirector = ["ADMIN", "DIRETOR", "COORDENADOR"].includes(user.role);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="border-b border-slate-900 bg-slate-900/50 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 rounded-xl">
              <GraduationCap className="w-6 h-6" />
            </div>
            <div>
              <span className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                Vault Web Portal
              </span>
              <span className="text-xs text-slate-500 block">Galeria Escolar</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-sm font-medium text-slate-200">{user.email}</span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                <ShieldCheck className="w-3.5 h-3.5" />
                {user.role}
              </span>
            </div>
            
            <button
              onClick={logout}
              className="p-2 hover:bg-slate-800/80 text-slate-400 hover:text-rose-400 rounded-xl transition-colors cursor-pointer border border-slate-800/50"
              title="Sair da conta"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* Left Column (Forms for Directors/Coordinators) */}
        {isAdminOrDirector && (
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-4 text-slate-200">
                <FolderPlus className="w-5 h-5 text-indigo-400" />
                <h2 className="font-semibold text-sm uppercase tracking-wider">Nova Turma</h2>
              </div>

              <form onSubmit={handleCreateClass} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Nome da Turma</label>
                  <input
                    type="text"
                    required
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                    placeholder="Ex: Maternal A, 1º Ano B"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Ano Letivo</label>
                  <input
                    type="number"
                    required
                    value={classYear}
                    onChange={(e) => setClassYear(parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors text-sm"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isCreatingClass}
                  className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-600/50 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2 text-xs font-semibold cursor-pointer"
                >
                  {isCreatingClass ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4" />
                  )}
                  Criar Turma
                </button>
              </form>

              {createSuccess && (
                <div className="mt-3 text-xs text-center text-emerald-400 font-medium">
                  Turma criada com sucesso!
                </div>
              )}
            </div>
          </div>
        )}

        {/* Right Column (Classes list / Dashboard view) */}
        <div className={isAdminOrDirector ? "lg:col-span-3 space-y-6" : "lg:col-span-4 space-y-6"}>
          
          {/* Welcome Banner */}
          <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950/40 p-6">
            <div className="absolute top-0 right-0 p-6 text-indigo-500/10 pointer-events-none">
              <Sparkles className="w-32 h-32" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-100">
              Bem-vindo ao Portal, {user.role === "PROFESSOR" ? "Professor" : "Administrador"}!
            </h1>
            <p className="text-sm text-slate-400 mt-2 max-w-xl">
              {user.role === "PROFESSOR"
                ? "Gerencie as fotos e marque os alunos das turmas que estão sob a sua responsabilidade."
                : user.role === "MARKETING"
                ? "Navegue e faça o download de fotos escolares aprovadas para divulgação."
                : "Painel de administração. Gerencie as turmas escolares, alunos e controle a aprovação de fotos."}
            </p>
          </div>

          {/* Classes Section */}
          <div>
            <h2 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              {user.role === "MARKETING" ? "Galeria do Marketing" : "Turmas Disponíveis"}
            </h2>

            {loadingClasses ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-32 bg-slate-900/50 border border-slate-900 rounded-2xl animate-pulse"></div>
                ))}
              </div>
            ) : error ? (
              <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl text-center text-slate-400 text-sm">
                Não foi possível carregar as turmas: {error}
              </div>
            ) : user.role === "MARKETING" ? (
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 text-center">
                <div className="inline-flex items-center justify-center p-3 bg-violet-600/10 border border-violet-500/20 text-violet-400 rounded-xl mb-3">
                  <ImageIcon className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-semibold text-slate-300">Biblioteca de Imagens do Marketing</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  Acesse a galeria das turmas para baixar imagens aprovadas.
                </p>
              </div>
            ) : classes.length === 0 ? (
              <div className="p-8 bg-slate-900/30 border border-slate-900 border-dashed rounded-2xl text-center text-slate-500 text-sm">
                Nenhuma turma cadastrada no sistema.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {classes.map((cls) => (
                  <Link href={`/class/${cls.id}`} key={cls.id} className="block no-underline">
                    <div 
                      className="group bg-slate-900/50 hover:bg-slate-900 border border-slate-850 hover:border-indigo-500/40 rounded-2xl p-5 transition-all cursor-pointer relative overflow-hidden"
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div className="p-2.5 bg-indigo-600/10 group-hover:bg-indigo-600/20 border border-indigo-500/20 group-hover:border-indigo-500/30 text-indigo-400 rounded-xl transition-all">
                          <GraduationCap className="w-5 h-5" />
                        </div>
                        <span className="flex items-center gap-1 text-xs text-slate-500 font-medium">
                          <Calendar className="w-3.5 h-3.5" />
                          {cls.year}
                        </span>
                      </div>

                      <h3 className="font-semibold text-slate-200 group-hover:text-slate-50 transition-colors text-base">
                        {cls.name}
                      </h3>
                      
                      <p className="text-xs text-slate-500 mt-1.5">
                        Visualizar fotos e alunos da turma
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

        </div>

      </main>
    </div>
  );
}
