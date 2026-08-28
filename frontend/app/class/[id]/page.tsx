"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../context/AuthContext";
import { 
  ArrowLeft, 
  Search, 
  Filter, 
  Calendar,
  SlidersHorizontal,
  Image as ImageIcon,
  CheckCircle,
  AlertCircle,
  Lock,
  Loader2,
  Users,
  X,
  Tag,
  Check,
  AlertTriangle,
  Download,
  FolderOpen
} from "lucide-react";

interface PhotoData {
  id: number;
  file_id: string;
  title: string;
  uploaded_by_user_id: number;
  class_id: number;
  status: string;
  created_at: string;
  student_ids: number[];
}

interface ClassData {
  id: number;
  name: string;
  year: number;
  created_at: string;
}

interface StudentData {
  id: number;
  name: string;
  class_id: number;
  marketing_allowed: boolean;
  status: string;
}

export default function ClassPhotosPage() {
  const params = useParams();
  const classId = params.id as string;
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [currentClass, setCurrentClass] = useState<ClassData | null>(null);
  const [photos, setPhotos] = useState<PhotoData[]>([]);
  const [students, setStudents] = useState<StudentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtros e Ordenação
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("NEWEST"); // NEWEST or OLDEST

  // Navegação Lateral / Abas
  const [activeTab, setActiveTab] = useState<"TODOS" | "ACTIVITIES" | "STUDENTS" | "PORTFOLIO">("TODOS");
  const [selectedFilterStudentIds, setSelectedFilterStudentIds] = useState<number[]>([]);
  const [studentSearchTerm, setStudentSearchTerm] = useState("");

  // Detalhe e Marcação
  const [selectedPhoto, setSelectedPhoto] = useState<PhotoData | null>(null);
  const [taggingLoadingId, setTaggingLoadingId] = useState<number | null>(null);
  const [statusUpdating, setStatusUpdating] = useState(false);
  
  // Transição de scroll / aviso de mês ativo
  const [activeMonth, setActiveMonth] = useState<string | null>(null);

  const fetchClassData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Busca todas as turmas para extrair a turma atual
      const classRes = await fetch("http://localhost:8000/api/classes/", {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!classRes.ok) throw new Error("Não foi possível buscar os dados da turma.");
      const classesData: ClassData[] = await classRes.json();
      const match = classesData.find(c => c.id === Number(classId));
      if (!match) throw new Error("Turma não encontrada.");
      setCurrentClass(match);

      // 2. Busca as fotos da turma
      const photosRes = await fetch(`http://localhost:8000/api/photos/class/${classId}`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!photosRes.ok) throw new Error("Falha ao carregar as fotos.");
      const photosData = await photosRes.json();
      setPhotos(photosData);

      // 3. Busca os alunos da turma
      const studentsRes = await fetch(`http://localhost:8000/api/students/class/${classId}`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (studentsRes.ok) {
        const studentsData = await studentsRes.json();
        setStudents(studentsData);
      }
    } catch (err: any) {
      setError(err.message || "Erro ao carregar dados.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && token && user) {
      fetchClassData();
    }
  }, [authLoading, token, user, classId]);

  // Observer para monitoramento de transição de scroll de meses
  useEffect(() => {
    if (photos.length === 0 || activeTab === "STUDENTS") {
      setActiveMonth(null);
      return;
    }
    
    const observerOptions = {
      root: null,
      rootMargin: "-80px 0px -70% 0px",
      threshold: 0
    };

    const handleIntersection = (entries: IntersectionObserverEntry[]) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const month = entry.target.getAttribute("data-month");
          if (month) {
            setActiveMonth(month);
          }
        }
      });
    };

    const observer = new IntersectionObserver(handleIntersection, observerOptions);
    const targets = document.querySelectorAll("[data-month]");
    targets.forEach(target => observer.observe(target));

    return () => {
      targets.forEach(target => observer.unobserve(target));
      observer.disconnect();
    };
  }, [photos, activeTab, selectedFilterStudentIds, searchTerm, statusFilter, sortBy]);

  // Selecionar aluno a partir do card para adicionar filtro
  const handleSelectStudentCard = (student: StudentData) => {
    setSelectedFilterStudentIds(prev => {
      if (prev.includes(student.id)) return prev;
      return [...prev, student.id];
    });
    setActiveTab("TODOS");
  };

  // Salvar marcação de alunos
  const handleToggleTagStudent = async (studentId: number) => {
    if (!selectedPhoto) return;
    setTaggingLoadingId(studentId);

    const isCurrentlyTagged = selectedPhoto.student_ids?.includes(studentId);
    let updatedStudentIds = [...(selectedPhoto.student_ids || [])];
    
    if (isCurrentlyTagged) {
      updatedStudentIds = updatedStudentIds.filter(id => id !== studentId);
    } else {
      updatedStudentIds.push(studentId);
    }

    try {
      const res = await fetch(`http://localhost:8000/api/photos/${selectedPhoto.id}/tag-students`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ student_ids: updatedStudentIds })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Erro ao salvar marcação de aluno.");
      }

      // Atualiza o state local para a foto no modal
      const updatedPhoto = { ...selectedPhoto, student_ids: updatedStudentIds };
      setSelectedPhoto(updatedPhoto);

      // Atualiza na lista de fotos principal
      setPhotos(prevPhotos => 
        prevPhotos.map(p => p.id === selectedPhoto.id ? updatedPhoto : p)
      );

    } catch (err: any) {
      alert(err.message || "Erro ao marcar aluno.");
    } finally {
      setTaggingLoadingId(null);
    }
  };

  // Atualizar status da foto
  const handleUpdateStatus = async (newStatus: string) => {
    if (!selectedPhoto) return;
    setStatusUpdating(true);

    try {
      const res = await fetch(`http://localhost:8000/api/photos/${selectedPhoto.id}/status`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ status: newStatus })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Erro ao atualizar status da foto.");
      }

      const updatedPhotoData = await res.json();
      
      // Atualiza o state local da foto no modal
      const updatedPhoto = { 
        ...selectedPhoto, 
        status: updatedPhotoData.status,
        student_ids: updatedPhotoData.student_ids || selectedPhoto.student_ids
      };
      setSelectedPhoto(updatedPhoto);

      // Atualiza na lista de fotos principal
      setPhotos(prevPhotos => 
        prevPhotos.map(p => p.id === selectedPhoto.id ? updatedPhoto : p)
      );

    } catch (err: any) {
      alert(err.message || "Erro ao atualizar status.");
    } finally {
      setStatusUpdating(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !currentClass) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-2xl mb-4 max-w-md text-center">
          <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
          <p className="font-semibold">Erro ao carregar informações</p>
          <p className="text-xs mt-1 text-slate-400">{error || "Turma não encontrada."}</p>
        </div>
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-850 rounded-xl transition-colors cursor-pointer text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Voltar ao Painel
        </button>
      </div>
    );
  }

  // --- LOGICA DE FILTRO E ORDENACAO ---
  let filteredPhotos = [...photos];

  // Filtro de acordo com a aba e aluno selecionado
  if (activeTab === "PORTFOLIO") {
    filteredPhotos = filteredPhotos.filter(p => p.status === "APPROVED_FOR_MARKETING");
  }

  // Filtrar por alunos selecionados (tags de multi-select)
  if (selectedFilterStudentIds.length > 0) {
    filteredPhotos = filteredPhotos.filter(p => 
      p.student_ids?.some(id => selectedFilterStudentIds.includes(id))
    );
  }

  // Filtro por termo de busca
  if (searchTerm) {
    filteredPhotos = filteredPhotos.filter(p => 
      p.title?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }

  // Filtro por status da foto
  if (statusFilter !== "ALL") {
    filteredPhotos = filteredPhotos.filter(p => p.status === statusFilter);
  }

  // Ordenação das fotos
  filteredPhotos.sort((a, b) => {
    const dateA = new Date(a.created_at).getTime();
    const dateB = new Date(b.created_at).getTime();
    return sortBy === "NEWEST" ? dateB - dateA : dateA - dateB;
  });

  // --- AGRUPAMENTO POR MESES ---
  const monthNames = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  const getMonthYearKey = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${monthNames[date.getMonth()]} ${date.getFullYear()}`;
  };

  // Agrupa preservando a ordenação definida acima
  const groupedPhotos: { [key: string]: PhotoData[] } = {};
  filteredPhotos.forEach(photo => {
    const key = getMonthYearKey(photo.created_at);
    if (!groupedPhotos[key]) {
      groupedPhotos[key] = [];
    }
    groupedPhotos[key].push(photo);
  });

  // Chaves dos meses agrupados
  const monthKeys = Object.keys(groupedPhotos);

  // Alunos filtrados por busca
  const filteredStudents = students.filter(s => 
    s.name.toLowerCase().includes(studentSearchTerm.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED_FOR_MARKETING":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-500/10 text-emerald-450 border border-emerald-500/20">
            <CheckCircle className="w-3 h-3 text-emerald-400" /> Marketing
          </span>
        );
      case "PRIVATE_SCHOOL_ONLY":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Lock className="w-3 h-3 text-sky-400" /> Privado
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertCircle className="w-3 h-3 text-amber-400" /> Pendente
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* Menu Lateral Esquerdo */}
      <aside className="w-full md:w-64 md:h-screen md:sticky md:top-0 bg-slate-900/20 border-b md:border-b-0 md:border-r border-slate-900/80 backdrop-blur-xl p-5 flex flex-col justify-between shrink-0 z-40">
        <div>
          {/* Voltar ao Painel */}
          <button
            onClick={() => router.push("/")}
            className="group flex items-center gap-2 text-xs text-slate-500 hover:text-slate-200 transition-colors mb-6 cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            Voltar ao Painel
          </button>
          
          {/* Infos da Turma */}
          <div className="mb-8">
            <h2 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent truncate" title={currentClass.name}>
              {currentClass.name}
            </h2>
            <p className="text-xs text-slate-550 mt-1">Ano Letivo {currentClass.year}</p>
          </div>

          {/* Opções de Navegação */}
          <nav className="space-y-1.5">
            <button
              onClick={() => {
                setActiveTab("TODOS");
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                activeTab === "TODOS"
                  ? "bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 shadow-[0_0_15px_-3px_rgba(79,70,229,0.1)]"
                  : "text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 border border-transparent"
              }`}
            >
              <ImageIcon className="w-4 h-4" />
              Todos
            </button>
            <button
              onClick={() => {
                setActiveTab("ACTIVITIES");
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                activeTab === "ACTIVITIES"
                  ? "bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 shadow-[0_0_15px_-3px_rgba(79,70,229,0.1)]"
                  : "text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 border border-transparent"
              }`}
            >
              <Calendar className="w-4 h-4" />
              Atividades
            </button>
            <button
              onClick={() => {
                setActiveTab("PORTFOLIO");
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                activeTab === "PORTFOLIO"
                  ? "bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 shadow-[0_0_15px_-3px_rgba(79,70,229,0.1)]"
                  : "text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 border border-transparent"
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              Portfólio
            </button>
            <button
              onClick={() => {
                setActiveTab("STUDENTS");
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                activeTab === "STUDENTS"
                  ? "bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 shadow-[0_0_15px_-3px_rgba(79,70,229,0.1)]"
                  : "text-slate-400 hover:bg-slate-900/50 hover:text-slate-200 border border-transparent"
              }`}
            >
              <Users className="w-4 h-4" />
              Alunos
            </button>
          </nav>
        </div>

        {/* Footer do Menu */}
        <div className="mt-8 pt-4 border-t border-slate-900/60 hidden md:block">
          <p className="text-xs font-semibold text-slate-400 truncate">{user?.email}</p>
          <p className="text-[9px] text-slate-500 font-medium uppercase mt-0.5 tracking-wider">{user?.role}</p>
        </div>
      </aside>

      {/* Conteúdo Principal */}
      <div className="flex-1 flex flex-col min-h-screen relative">
        
        {/* Aviso flutuante discreto de transição de mês */}
        {activeMonth && activeTab !== "STUDENTS" && (
          <div className="fixed top-6 left-1/2 -translate-x-1/2 md:left-[calc(50%+128px)] z-30 bg-slate-900/90 border border-indigo-500/30 text-indigo-400 text-[10px] font-bold tracking-wider uppercase px-4 py-1.5 rounded-full shadow-[0_4px_20px_rgba(0,0,0,0.5)] backdrop-blur-md transition-all duration-300 animate-fade-in flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" />
            <span>{activeMonth}</span>
          </div>
        )}

        {/* Topbar com filtros rápidos */}
        <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-30 px-6 py-4 flex flex-col gap-3">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 w-full">
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent flex items-center gap-2">
                {activeTab === "TODOS" && "Todas as Fotos"}
                {activeTab === "ACTIVITIES" && "Atividades da Turma"}
                {activeTab === "PORTFOLIO" && "Portfólio da Turma"}
                {activeTab === "STUDENTS" && "Alunos Matriculados"}
              </h1>
              <p className="text-xs text-slate-550 font-medium mt-0.5">
                {currentClass.name} • {filteredPhotos.length} fotos encontradas
              </p>
            </div>

            {/* Filtros Rápidos de Fotos */}
            {activeTab !== "STUDENTS" && (
              <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                {/* Busca */}
                <div className="relative w-full sm:w-auto">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-550" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Buscar foto..."
                    className="w-full sm:w-48 pl-9 pr-4 py-1.5 bg-slate-900/40 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors text-xs"
                  />
                </div>

                {/* Filtro por Aluno (Dropdown) */}
                <div className="flex items-center gap-1.5 bg-slate-900/40 border border-slate-800 rounded-xl px-2.5 py-1.5 w-full sm:w-auto justify-between sm:justify-start">
                  <span className="text-slate-500 text-xs flex items-center gap-1">
                    <Users className="w-3.5 h-3.5 text-slate-500" />
                    Filtrar Aluno:
                  </span>
                  <select
                    value=""
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === "ALL") {
                        setSelectedFilterStudentIds([]);
                      } else {
                        const numVal = Number(val);
                        if (numVal && !selectedFilterStudentIds.includes(numVal)) {
                          setSelectedFilterStudentIds(prev => [...prev, numVal]);
                        }
                      }
                      e.target.value = ""; // Reset
                    }}
                    className="bg-transparent border-none text-xs text-slate-300 focus:outline-none cursor-pointer pr-1 max-w-[120px]"
                  >
                    <option value="" disabled>Selecionar...</option>
                    <option value="ALL">Todos</option>
                    {students
                      .filter(s => !selectedFilterStudentIds.includes(s.id))
                      .map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))
                    }
                  </select>
                </div>

                {/* Filtro por Status */}
                <div className="flex items-center gap-1.5 bg-slate-900/40 border border-slate-800 rounded-xl px-2.5 py-1.5 w-full sm:w-auto justify-between sm:justify-start">
                  <span className="text-slate-500 text-xs flex items-center gap-1">
                    <Filter className="w-3.5 h-3.5" />
                    Status:
                  </span>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-transparent border-none text-xs text-slate-300 focus:outline-none cursor-pointer pr-1"
                  >
                    <option value="ALL">Todos</option>
                    <option value="PENDING_REVIEW">Pendente de Revisão</option>
                    <option value="APPROVED_FOR_MARKETING">Aprovado Marketing</option>
                    <option value="PRIVATE_SCHOOL_ONLY">Privado Escola</option>
                  </select>
                </div>

                {/* Ordenação */}
                <div className="flex items-center gap-1.5 bg-slate-900/40 border border-slate-800 rounded-xl px-2.5 py-1.5 w-full sm:w-auto justify-between sm:justify-start">
                  <span className="text-slate-500 text-xs flex items-center gap-1">
                    <SlidersHorizontal className="w-3.5 h-3.5" />
                    Ordem:
                  </span>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="bg-transparent border-none text-xs text-slate-300 focus:outline-none cursor-pointer pr-1"
                  >
                    <option value="NEWEST">Mais Recentes</option>
                    <option value="OLDEST">Mais Antigas</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Render das tags dos alunos filtrados */}
          {activeTab !== "STUDENTS" && selectedFilterStudentIds.length > 0 && (
            <div className="flex flex-wrap gap-1.5 items-center pt-2.5 border-t border-slate-900/60 w-full animate-fade-in">
              <span className="text-[10px] font-bold text-slate-550 uppercase tracking-wider flex items-center gap-1">
                <Tag className="w-3 h-3 text-indigo-400" />
                Filtrando por:
              </span>
              {selectedFilterStudentIds.map(sid => {
                const student = students.find(s => s.id === sid);
                if (!student) return null;
                return (
                  <button
                    key={sid}
                    onClick={() => setSelectedFilterStudentIds(prev => prev.filter(id => id !== sid))}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-rose-500/10 hover:text-rose-450 hover:border-rose-500/20 transition-all cursor-pointer"
                  >
                    <span>{student.name}</span>
                    <X className="w-2.5 h-2.5 ml-1 shrink-0 text-indigo-500" />
                  </button>
                );
              })}
              <button
                onClick={() => setSelectedFilterStudentIds([])}
                className="text-[10px] text-slate-550 hover:text-slate-300 underline cursor-pointer ml-2"
              >
                Limpar filtros
              </button>
            </div>
          )}
        </header>

        {/* Corpo de Fotos/Alunos */}
        <main className="flex-1 px-6 py-6 overflow-y-auto">
          {activeTab === "STUDENTS" ? (
            /* Renderiza Grid de Alunos */
            <div className="space-y-6">
              {/* Filtro de busca de alunos */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/10 border border-slate-900/50 rounded-2xl p-4">
                <div className="relative max-w-xs w-full">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={studentSearchTerm}
                    onChange={(e) => setStudentSearchTerm(e.target.value)}
                    placeholder="Filtrar aluno pelo nome..."
                    className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-850 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors text-xs"
                  />
                </div>
                <div className="text-xs text-slate-500">
                  Total matriculados: <span className="font-semibold text-slate-300">{students.length}</span>
                </div>
              </div>

              {filteredStudents.length === 0 ? (
                <div className="p-12 border border-slate-900 border-dashed rounded-2xl text-center">
                  <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <h3 className="text-sm font-semibold text-slate-400">Nenhum aluno encontrado</h3>
                  <p className="text-xs text-slate-600 mt-1">Refine seu termo de pesquisa.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {filteredStudents.map((student) => {
                    const taggedCount = photos.filter(p => p.student_ids?.includes(student.id)).length;
                    
                    return (
                      <div
                        key={student.id}
                        onClick={() => handleSelectStudentCard(student)}
                        className="group bg-slate-900/30 border border-slate-900 hover:border-indigo-500/20 hover:bg-slate-900/55 rounded-2xl p-4 flex items-center justify-between gap-4 cursor-pointer transition-all hover:shadow-[0_4px_25px_rgba(79,70,229,0.08)]"
                      >
                        <div className="flex items-center gap-3">
                          {/* Avatar com Gradiente */}
                          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-550/20 to-violet-550/20 border border-indigo-550/30 flex items-center justify-center font-bold text-indigo-400 text-sm group-hover:scale-105 transition-transform shrink-0">
                            {student.name.substring(0, 2).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <h4 className="font-semibold text-sm text-slate-200 group-hover:text-indigo-400 transition-colors truncate">
                              {student.name}
                            </h4>
                            <p className="text-[10px] text-slate-500 mt-0.5">
                              {taggedCount} {taggedCount === 1 ? 'foto marcada' : 'fotos marcadas'}
                            </p>
                          </div>
                        </div>

                        <div className="flex flex-col items-end justify-center shrink-0">
                          <span className={`w-2 h-2 rounded-full ${student.status === "ATIVO" ? "bg-emerald-550 animate-pulse" : "bg-slate-655"}`} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* Renderiza Fotos Agrupadas por Mês */
            <div>
              {photos.length === 0 ? (
                <div className="p-12 border border-slate-900 border-dashed rounded-2xl text-center">
                  <div className="inline-flex items-center justify-center p-3 bg-indigo-650/10 border border-indigo-650/20 text-indigo-400 rounded-xl mb-3">
                    <ImageIcon className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-300">Nenhuma foto encontrada</h3>
                  <p className="text-xs text-slate-550 mt-1">Esta turma ainda não possui fotos vinculadas.</p>
                </div>
              ) : filteredPhotos.length === 0 ? (
                <div className="p-12 border border-slate-900 border-dashed rounded-2xl text-center">
                  <h3 className="text-sm font-semibold text-slate-350">Nenhuma foto</h3>
                  <p className="text-xs text-slate-550 mt-1">Nenhuma imagem corresponde aos filtros aplicados.</p>
                </div>
              ) : (
                <div className="space-y-12">
                  {monthKeys.map((monthKey) => (
                    <section key={monthKey} data-month={monthKey} className="space-y-4">
                      {/* Cabeçalho de Mês Sticky - Glassmorphism */}
                      <div className="sticky top-0 bg-slate-950/90 border-b border-slate-900/50 backdrop-blur-md z-20 py-2.5 flex items-center gap-2 text-indigo-400 font-semibold text-xs tracking-widest uppercase">
                        <Calendar className="w-4 h-4 text-indigo-500" />
                        {monthKey}
                      </div>

                      {/* Grid de Imagens */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                        {groupedPhotos[monthKey].map((photo) => (
                          <div 
                            key={photo.id}
                            onClick={() => setSelectedPhoto(photo)}
                            className="group bg-slate-900/20 border border-slate-900 hover:border-slate-800 rounded-2xl overflow-hidden shadow-lg transition-all flex flex-col cursor-pointer hover:-translate-y-0.5 hover:shadow-[0_8px_30px_rgba(0,0,0,0.4)]"
                          >
                            {/* Visualização de Imagem */}
                            <div className="relative aspect-video bg-slate-950 overflow-hidden flex items-center justify-center">
                              <img
                                src={`http://localhost:8000/api/photos/file/${photo.file_path}`}
                                alt="Foto escolar"
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                loading="lazy"
                              />
                              
                              <div className="absolute top-3 left-3 z-10">
                                {getStatusBadge(photo.status)}
                              </div>
                            </div>

                            {/* Alunos marcados na foto (em vez do título) */}
                            <div className="p-3 bg-slate-900/40 flex-1 flex flex-col justify-end">
                              {photo.student_ids && photo.student_ids.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {photo.student_ids.map(sid => {
                                    const student = students.find(s => s.id === sid);
                                    if (!student) return null;
                                    return (
                                      <span key={sid} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[9px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 max-w-full truncate" title={student.name}>
                                        <Tag className="w-2.5 h-2.5 text-indigo-500 mr-0.5 shrink-0" />
                                        <span className="truncate">{student.name}</span>
                                      </span>
                                    );
                                  })}
                                </div>
                              ) : (
                                <span className="text-[10px] text-slate-600 italic">Sem alunos marcados</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Modal / Lightbox de Detalhes da Imagem */}
      {selectedPhoto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md animate-fade-in">
          <div className="bg-slate-900 border border-slate-850 rounded-3xl overflow-hidden max-w-5xl w-full h-[85vh] flex flex-col md:flex-row shadow-2xl relative">
            
            {/* Fechar */}
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute top-4 right-4 z-50 p-2 bg-slate-950/80 border border-slate-800 hover:bg-slate-800 hover:text-slate-50 text-slate-400 rounded-full transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Painel da Esquerda (Imagem Grande) */}
            <div className="flex-1 bg-slate-950 relative flex items-center justify-center overflow-hidden border-b md:border-b-0 md:border-r border-slate-850">
              <img
                src={`http://localhost:8000/api/photos/file/${selectedPhoto.file_path}`}
                alt={selectedPhoto.title || "Foto escolar"}
                className="max-w-full max-h-full object-contain"
              />
              
              {/* Botão de Download */}
              <a
                href={`http://localhost:8000/api/photos/file/${selectedPhoto.file_path}`}
                target="_blank"
                rel="noreferrer"
                download={selectedPhoto.file_path}
                className="absolute bottom-4 left-4 p-2.5 bg-slate-950/80 hover:bg-indigo-600 border border-slate-800 text-slate-200 hover:text-white rounded-xl transition-all cursor-pointer flex items-center gap-1.5 text-xs font-semibold shadow-lg"
              >
                <Download className="w-4 h-4" />
                <span>Baixar Imagem</span>
              </a>
            </div>

            {/* Painel da Direita (Infos, Tags de Alunos, Ações de Status) */}
            <div className="w-full md:w-96 p-6 flex flex-col h-full overflow-y-auto bg-slate-900/90">
              <div className="mb-6">
                <span className="mb-2 block">{getStatusBadge(selectedPhoto.status)}</span>
                <h3 className="text-base font-bold text-slate-100 leading-snug">
                  {selectedPhoto.title || "Foto Escolar"}
                </h3>
                <p className="text-[10px] text-slate-500 mt-1">
                  Arquivo: <span className="font-mono text-[9px] text-indigo-400">{selectedPhoto.file_id}</span>
                </p>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  Registrado em: {new Date(selectedPhoto.created_at).toLocaleDateString("pt-BR", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit"
                  })}
                </p>
              </div>

              {/* Seção de Marcação de Alunos (Tags) */}
              <div className="flex-1 flex flex-col min-h-0 border-t border-slate-850 pt-4">
                <h4 className="text-xs font-bold text-indigo-400 tracking-wider uppercase flex items-center gap-1.5 mb-3">
                  <Tag className="w-3.5 h-3.5 text-indigo-500" />
                  Alunos Marcados nesta Foto
                </h4>
                
                {/* Lista rolável de alunos da turma */}
                <div className="flex-1 overflow-y-auto pr-1 space-y-1.5">
                  {students.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">Carregando lista de alunos...</p>
                  ) : (
                    students.map((student) => {
                      const isTagged = selectedPhoto.student_ids?.includes(student.id);
                      const isLoading = taggingLoadingId === student.id;

                      return (
                        <button
                          key={student.id}
                          disabled={user?.role === "MARKETING"}
                          onClick={() => handleToggleTagStudent(student.id)}
                          className={`w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between border cursor-pointer transition-all ${
                            isTagged
                              ? "bg-indigo-600/10 border-indigo-500/30 text-indigo-350 font-medium"
                              : "bg-slate-950/20 border-slate-900 text-slate-400 hover:bg-slate-800/30"
                          } ${user?.role === "MARKETING" ? "pointer-events-none" : ""}`}
                        >
                          <div className="flex items-center gap-2">
                            <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${
                              isTagged ? "bg-indigo-500 border-indigo-450 text-white" : "border-slate-800 bg-slate-950"
                            }`}>
                              {isTagged && <Check className="w-2.5 h-2.5" />}
                            </div>
                            <span className="truncate max-w-[150px]">{student.name}</span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {isLoading && (
                              <Loader2 className="w-3 animate-spin text-indigo-500" />
                            )}
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Ações Administrativas de Status (Apenas ADMIN, DIRETOR, COORDENADOR) */}
              {["ADMIN", "DIRETOR", "COORDENADOR"].includes(user?.role || "") && (
                <div className="mt-4 pt-4 border-t border-slate-850 shrink-0 space-y-2">
                  <p className="text-[9px] font-bold text-slate-500 tracking-wider uppercase">
                    Gerenciamento (Direção / Coordenação)
                  </p>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      disabled={statusUpdating}
                      onClick={() => handleUpdateStatus("APPROVED_FOR_MARKETING")}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold cursor-pointer transition-all flex items-center justify-center gap-1.5 border ${
                        selectedPhoto.status === "APPROVED_FOR_MARKETING"
                          ? "bg-emerald-600 border-emerald-500 text-white shadow-[0_0_15px_-3px_rgba(16,185,129,0.25)]"
                          : "bg-slate-950 border-slate-900 text-emerald-450 hover:bg-emerald-500/10"
                      }`}
                      title="Aprovar para Marketing"
                    >
                      {statusUpdating ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          Liberar Mkt
                        </>
                      )}
                    </button>

                    <button
                      disabled={statusUpdating}
                      onClick={() => handleUpdateStatus("PRIVATE_SCHOOL_ONLY")}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold cursor-pointer transition-all flex items-center justify-center gap-1.5 border ${
                        selectedPhoto.status === "PRIVATE_SCHOOL_ONLY"
                          ? "bg-sky-600 border-sky-500 text-white shadow-[0_0_15px_-3px_rgba(14,165,233,0.25)]"
                          : "bg-slate-950 border-slate-900 text-sky-400 hover:bg-sky-500/10"
                      }`}
                    >
                      {statusUpdating ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <>
                          <Lock className="w-3.5 h-3.5" />
                          Privado
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
