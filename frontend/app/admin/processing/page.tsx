"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  FolderInput,
  Layers,
  Loader2,
  LogOut,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  User,
  XCircle,
  AlertTriangle,
  Eye,
  X,
  ChevronDown,
  ChevronUp,
  Filter,
  Users,
  Check,
  Link2,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Search
} from "lucide-react";
import { useAuth } from "../../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DetectedFace {
  id: string;
  bounding_box: number[];
  face_crop_url?: string | null;
  detection_score?: number | null;
  cluster_id?: string | null;
  cluster_name?: string | null;
  student_id?: number | null;
  student_name?: string | null;
}

interface ProcessingPhoto {
  id: number;
  file_path: string;
  image_url: string;
  class_id?: number | null;
  class_name?: string | null;
  process_status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;
  process_attempts: number;
  process_error?: string | null;
  created_at: string;
  detected_faces: DetectedFace[];
}

interface FaceCluster {
  id: string;
  student_id?: number | null;
  student_name?: string | null;
  student_class_name?: string | null;
  name?: string | null;
  face_count: number;
  photo_count: number;
  sample_face_crops: string[];
  created_at: string;
}

interface FaceMatchSuggestion {
  id: string;
  source_cluster_id: string;
  source_cluster_name?: string | null;
  source_student_id?: number | null;
  source_student_name?: string | null;
  source_face_id: string;
  source_face_crop_url?: string | null;
  source_photo_id: number;
  source_photo_url?: string | null;
  source_bounding_box?: number[] | null;

  target_cluster_id: string;
  target_cluster_name?: string | null;
  target_student_id?: number | null;
  target_student_name?: string | null;
  target_face_id: string;
  target_face_crop_url?: string | null;
  target_photo_id: number;
  target_photo_url?: string | null;
  target_bounding_box?: number[] | null;

  distance: number;
  similarity_percent: number;
}

interface StatusCounts {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total: number;
}

export default function FaceProcessingAdminPage() {
  const { user, token, logout } = useAuth();

  const [counts, setCounts] = useState<StatusCounts>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    total: 0,
  });

  type TabType = "dashboard" | "match" | "rostos";
  const [activeTab, setActiveTab] = useState<TabType>("dashboard");
  const [detectedFaces, setDetectedFaces] = useState<DetectedFace[]>([]);
  const [faceSearchTerm, setFaceSearchTerm] = useState("");
  const [faceFilterLinked, setFaceFilterLinked] = useState<"ALL" | "LINKED" | "UNLINKED">("ALL");

  const [photos, setPhotos] = useState<ProcessingPhoto[]>([]);
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [suggestions, setSuggestions] = useState<FaceMatchSuggestion[]>([]);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<string[]>([]);
  const [suggestionIndex, setSuggestionIndex] = useState(0);
  const [mergingSuggestionId, setMergingSuggestionId] = useState<string | null>(null);
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedPhoto, setSelectedPhoto] = useState<ProcessingPhoto | null>(null);
  const [expandedErrors, setExpandedErrors] = useState<Record<number, boolean>>({});

  const loadData = useCallback(async (showLoading = false, signal?: AbortSignal) => {
    if (!token || user?.role !== "COORDENADOR" || signal?.aborted) return;
    if (showLoading) setLoading(true);
    try {
      const options = { headers: { Authorization: `Bearer ${token}` }, signal };
      // 1. Carrega métricas da fila
      const statusRes = await fetch(`${API_URL}/api/system/processing-status`, options);
      if (!statusRes.ok) throw new Error("Não foi possível carregar a fila. Verifique sua sessão.");
      const countsData = await statusRes.json();

      // 2. Carrega lista de clusters (Pessoas)
      const clustersRes = await fetch(`${API_URL}/api/faces/clusters?status=all`, options);
      if (!clustersRes.ok) throw new Error("Não foi possível carregar os grupos.");
      const clustersData = await clustersRes.json();

      // 3. Carrega sugestões de matches entre rostos parecidos
      const suggestionsRes = await fetch(`${API_URL}/api/faces/match-suggestions?limit=20`, options);
      const suggestionsData = suggestionsRes.ok ? await suggestionsRes.json() : [];

      // 4. Carrega todos os rostos detectados
      const facesRes = await fetch(`${API_URL}/api/faces/detected?limit=300`, options);
      const facesData = facesRes.ok ? await facesRes.json() : [];

      // 5. Carrega lista detalhada de fotos (com filtro por status e/ou por cluster_id)
      let url = `${API_URL}/api/system/processing-photos?status_filter=${activeFilter}&limit=100`;
      if (selectedClusterId) {
        url += `&cluster_id=${encodeURIComponent(selectedClusterId)}`;
      }

      const photosRes = await fetch(url, options);
      if (!photosRes.ok) throw new Error("Não foi possível carregar as fotos.");
      const photosData = await photosRes.json();
      if (signal?.aborted) return;
      setCounts(countsData);
      setClusters(clustersData);
      setSuggestions(suggestionsData);
      setDetectedFaces(facesData);
      setPhotos(photosData);
    } catch (err) {
      if (signal?.aborted) return;
      setPhotos([]);
      setClusters([]);
      setSuggestions([]);
      setDetectedFaces([]);
      setSelectedPhoto(null);
      setCounts({ pending: 0, processing: 0, completed: 0, failed: 0, total: 0 });
      setActionMessage({ type: "error", text: err instanceof Error ? err.message : "Não foi possível atualizar a fila." });
    } finally {
      if (showLoading && !signal?.aborted) setLoading(false);
    }
  }, [activeFilter, selectedClusterId, token, user?.role]);

  // Carga inicial e quando os filtros mudam
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => { void loadData(true, controller.signal); }, 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [loadData]);

  // Auto-refresh a cada 4 segundos
  useEffect(() => {
    if (!autoRefresh) return;
    const controller = new AbortController();
    const interval = setInterval(() => {
      void loadData(false, controller.signal);
    }, 4000);
    return () => { clearInterval(interval); controller.abort(); };
  }, [autoRefresh, loadData]);

  // Ação: Disparar Processamento Imediato (Process Now)
  async function handleProcessNow() {
    setActionLoading("process");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/process-now?batch_size=50`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Falha ao iniciar processamento.");
      setActionMessage({ type: "success", text: data.message || "Lote processado com sucesso!" });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: err instanceof Error ? err.message : "Erro ao processar." });
    } finally {
      setActionLoading(null);
    }
  }

  // Ação: Ingestão da pasta test_images
  async function handleIngestTestFolder() {
    setActionLoading("ingest");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/ingest-test-folder`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Falha ao importar pasta de teste.");
      setActionMessage({ type: data.imported_count > 0 ? "success" : "info", text: data.message });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: err instanceof Error ? err.message : "Erro ao importar." });
    } finally {
      setActionLoading(null);
    }
  }

  // Ação: Reprocessar Falhas
  async function handleReprocessFailed() {
    setActionLoading("reprocess_failed");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/reprocess-failed`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Falha ao re-enfileirar fotos.");
      setActionMessage({ type: "success", text: data.message });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: err instanceof Error ? err.message : "Erro ao re-enfileirar fotos com falha." });
    } finally {
      setActionLoading(null);
    }
  }

  // Ação: Reprocessar Todas
  async function handleReprocessAll() {
    if (!confirm("Tem certeza que deseja reprocessar todas as fotos da sua escola?")) return;
    setActionLoading("reprocess_all");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/reprocess-all`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Falha ao re-enfileirar fotos.");
      setActionMessage({ type: "success", text: data.message });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: err instanceof Error ? err.message : "Erro ao re-enfileirar todas as fotos." });
    } finally {
      setActionLoading(null);
    }
  }

  // Ação: Reagrupar Todas as Faces via DBSCAN
  async function handleReclusterAll() {
    setActionLoading("recluster");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/recluster-all`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Falha ao reagrupar rostos.");
      setActionMessage({ type: "success", text: data.message });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: err instanceof Error ? err.message : "Erro ao reagrupar faces." });
    } finally {
      setActionLoading(null);
    }
  }

  // Ação: Confirmar Associação de Rostos Parecidos (Merge)
  async function handleConfirmMatch(suggestion: FaceMatchSuggestion) {
    setMergingSuggestionId(suggestion.id);
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/faces/clusters/merge`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_cluster_id: suggestion.source_cluster_id,
          target_cluster_id: suggestion.target_cluster_id,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail ?? "Falha ao associar rostos.");

      const person1 = suggestion.source_student_name || suggestion.source_cluster_name || "Rosto A";
      const person2 = suggestion.target_student_name || suggestion.target_cluster_name || "Rosto B";
      setActionMessage({
        type: "success",
        text: `Rostos associados com sucesso! ${person1} foi associado a ${person2}.`,
      });
      setSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
      await loadData(false);
    } catch (err) {
      setActionMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Erro ao associar rostos.",
      });
    } finally {
      setMergingSuggestionId(null);
    }
  }

  function handleDismissSuggestion(suggestionId: string) {
    setDismissedSuggestions((prev) => [...prev, suggestionId]);
  }

  function handleSkipSuggestion() {
    if (visibleSuggestions.length > 1) {
      setSuggestionIndex((prev) => (prev + 1) % visibleSuggestions.length);
    }
  }

  function handlePrevSuggestion() {
    if (visibleSuggestions.length > 1) {
      setSuggestionIndex((prev) => (prev - 1 + visibleSuggestions.length) % visibleSuggestions.length);
    }
  }

  function toggleErrorExpand(photoId: number) {
    setExpandedErrors(prev => ({ ...prev, [photoId]: !prev[photoId] }));
  }

  const activeCluster = clusters.find(c => c.id === selectedClusterId);
  const visibleSuggestions = suggestions.filter((s) => !dismissedSuggestions.includes(s.id));
  const safeIndex = visibleSuggestions.length > 0 ? suggestionIndex % visibleSuggestions.length : 0;
  const currentSuggestion = visibleSuggestions[safeIndex] ?? null;

  const filteredDetectedFaces = detectedFaces.filter((face) => {
    const name = face.student_name || face.cluster_name || "";
    const matchesSearch =
      faceSearchTerm.trim() === "" || name.toLowerCase().includes(faceSearchTerm.toLowerCase());
    const matchesFilter =
      faceFilterLinked === "ALL" ||
      (faceFilterLinked === "LINKED" && face.student_name) ||
      (faceFilterLinked === "UNLINKED" && !face.student_name);
    return matchesSearch && matchesFilter;
  });

  const linkedFacesCount = detectedFaces.filter((f) => f.student_name).length;
  const unlinkedFacesCount = detectedFaces.filter((f) => !f.student_name).length;

  if (!token || user?.role !== "COORDENADOR") {
    return <main className="p-8"><p>Esta área é exclusiva da coordenação.</p><Link href="/">Voltar ao início</Link></main>;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3.5">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition"
            >
              <ArrowLeft className="h-4 w-4" />
              Voltar
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-blue-600" />
                <h1 className="font-semibold text-slate-900 tracking-tight">Reconhecimento Facial & Fila de Processamento</h1>
              </div>
              <p className="text-xs text-slate-500">Monitoramento e agrupamento inteligente de fotos escolares</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
                autoRefresh
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 bg-slate-100 text-slate-500 hover:text-slate-800"
              }`}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${autoRefresh ? "animate-spin" : ""}`} />
              {autoRefresh ? "Auto-refresh: Ativo" : "Auto-refresh: Pausado"}
            </button>

            {user && (
              <div className="hidden sm:flex items-center gap-2 border-l border-slate-200 pl-3">
                <span className="text-xs text-slate-500">{user.email}</span>
                <button
                  onClick={logout}
                  className="rounded-lg border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
                  title="Sair"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-6">
        {/* Banner de Feedback de Ações */}
        {actionMessage && (
          <div
            className={`mb-6 flex items-center justify-between rounded-xl border p-4 text-sm ${
              actionMessage.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : actionMessage.type === "error"
                ? "border-rose-200 bg-rose-50 text-rose-800"
                : "border-blue-200 bg-blue-50 text-blue-800"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {actionMessage.type === "success" && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
              {actionMessage.type === "error" && <AlertTriangle className="h-5 w-5 text-rose-600" />}
              {actionMessage.type === "info" && <Sparkles className="h-5 w-5 text-blue-600" />}
              <span>{actionMessage.text}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-xs opacity-70 hover:opacity-100 cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Abas Principais de Navegação */}
        <div className="mb-6 flex border-b border-slate-200">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition cursor-pointer ${
              activeTab === "dashboard"
                ? "border-blue-600 text-blue-600 bg-blue-50/50 rounded-t-xl"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <LayoutDashboard className="h-4 w-4" />
            <span>Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab("match")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition cursor-pointer ${
              activeTab === "match"
                ? "border-blue-600 text-blue-600 bg-blue-50/50 rounded-t-xl"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <Sparkles className="h-4 w-4" />
            <span>Match</span>
            {visibleSuggestions.length > 0 && (
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-700">
                {visibleSuggestions.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("rostos")}
            className={`flex items-center gap-2 border-b-2 px-5 py-3 text-sm font-semibold transition cursor-pointer ${
              activeTab === "rostos"
                ? "border-blue-600 text-blue-600 bg-blue-50/50 rounded-t-xl"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            <Users className="h-4 w-4" />
            <span>Rostos</span>
            {detectedFaces.length > 0 && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {detectedFaces.length}
              </span>
            )}
          </button>
        </div>

        {/* ABA: DASHBOARD */}
        {activeTab === "dashboard" && (
          <div>
            {/* Métricas da Fila */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 mb-6">
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-medium text-slate-500">Total de Fotos</p>
                <p className="mt-1.5 text-2xl font-bold text-slate-900">{counts.total}</p>
              </div>

              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-blue-700">Pendentes</p>
                  <Clock className="h-4 w-4 text-blue-600" />
                </div>
                <p className="mt-1.5 text-2xl font-bold text-blue-800">{counts.pending}</p>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-amber-700">Em Processamento</p>
                  <Loader2 className="h-4 w-4 text-amber-600 animate-spin" />
                </div>
                <p className="mt-1.5 text-2xl font-bold text-amber-800">{counts.processing}</p>
              </div>

              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-emerald-700">Concluídas</p>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                </div>
                <p className="mt-1.5 text-2xl font-bold text-emerald-800">{counts.completed}</p>
              </div>

              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 col-span-2 sm:col-span-1">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-rose-700">Falhas</p>
                  <ShieldAlert className="h-4 w-4 text-rose-600" />
                </div>
                <p className="mt-1.5 text-2xl font-bold text-rose-800">{counts.failed}</p>
              </div>
            </div>

            {/* Barra de Ações Principais */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white/90 p-4 mb-6 shadow-sm">
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Botão de Disparo Manual de Processamento */}
                <button
                  onClick={handleProcessNow}
                  disabled={actionLoading !== null}
                  className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 hover:bg-blue-700 active:scale-95 disabled:opacity-50 transition cursor-pointer"
                >
                  {actionLoading === "process" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4 fill-white" />
                  )}
                  <span>Iniciar Processamento Agora</span>
                </button>

                {/* Botão de Ingestão da Pasta de Testes */}
                <button
                  onClick={handleIngestTestFolder}
                  disabled={actionLoading !== null}
                  className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-100 px-4 py-2.5 text-sm font-medium text-slate-800 hover:bg-slate-200 active:scale-95 disabled:opacity-50 transition cursor-pointer"
                >
                  {actionLoading === "ingest" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FolderInput className="h-4 w-4 text-blue-600" />
                  )}
                  <span>Importar Pasta de Testes</span>
                </button>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {counts.failed > 0 && (
                  <button
                    onClick={handleReprocessFailed}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 hover:bg-rose-100 transition cursor-pointer"
                  >
                    <RotateCcwIcon className="h-3.5 w-3.5" />
                    Reprocessar Falhas ({counts.failed})
                  </button>
                )}

                <button
                  onClick={handleReclusterAll}
                  disabled={actionLoading !== null}
                  className="flex items-center gap-1.5 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-100 transition cursor-pointer"
                  title="Executa DBSCAN novamente em todas as faces para reagrupar pessoas"
                >
                  {actionLoading === "recluster" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Layers className="h-3.5 w-3.5 text-blue-600" />
                  )}
                  Reagrupar Rostos (DBSCAN)
                </button>

                <button
                  onClick={handleReprocessAll}
                  disabled={actionLoading !== null}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-100 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-800 transition cursor-pointer"
                >
                  Reprocessar Todas
                </button>

                <button
                  onClick={() => loadData(true)}
                  disabled={loading}
                  className="rounded-xl border border-slate-200 bg-slate-100 p-2 text-slate-500 hover:text-slate-900 transition cursor-pointer"
                  title="Atualizar agora"
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                </button>
              </div>
            </div>

            {/* SEÇÃO: FILTRO POR PESSOA / CLUSTER */}
            {clusters.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 mb-6 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-blue-600" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      Pessoas Agrupadas ({clusters.length})
                    </h3>
                    <span className="text-[11px] text-slate-500">
                      — Clique em uma pessoa para ver todas as suas fotos
                    </span>
                  </div>

                  {selectedClusterId && (
                    <button
                      onClick={() => setSelectedClusterId(null)}
                      className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 transition cursor-pointer"
                    >
                      <X className="h-3.5 w-3.5" />
                      Ver Todas as Fotos (Limpar Filtro)
                    </button>
                  )}
                </div>

                {/* Carrossel / Faixa de Pessoas */}
                <div className="flex gap-2.5 overflow-x-auto pb-2 scrollbar-thin">
                  {/* Opção "Todos" */}
                  <button
                    onClick={() => setSelectedClusterId(null)}
                    className={`flex shrink-0 items-center gap-2.5 rounded-xl border p-2 text-left transition cursor-pointer ${
                      selectedClusterId === null
                        ? "border-blue-500 bg-blue-50 text-blue-900 ring-2 ring-blue-500/30"
                        : "border-slate-200 bg-slate-50/60 text-slate-500 hover:border-slate-300 hover:text-slate-800"
                    }`}
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                      <Users className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="pr-2">
                      <p className="text-xs font-semibold text-slate-900">Todas as Fotos</p>
                      <p className="text-[10px] text-slate-500">{counts.total} foto(s)</p>
                    </div>
                  </button>

                  {/* Lista de Clusters de Pessoas */}
                  {clusters.map((c, index) => {
                    const isSelected = selectedClusterId === c.id;
                    const sampleCrop = c.sample_face_crops?.[0];

                    return (
                      <button
                        key={c.id}
                        onClick={() => setSelectedClusterId(isSelected ? null : c.id)}
                        className={`flex shrink-0 items-center gap-2.5 rounded-xl border p-2 text-left transition cursor-pointer ${
                          isSelected
                            ? "border-blue-500 bg-blue-50 text-blue-900 ring-2 ring-blue-500/40 shadow-sm"
                            : "border-slate-200 bg-slate-50/80 text-slate-500 hover:border-slate-300 hover:text-slate-800"
                        }`}
                      >
                        {sampleCrop ? (
                          <img
                            src={`${API_URL}${sampleCrop}`}
                            alt={c.name || "Face"}
                            className="h-10 w-10 shrink-0 rounded-lg object-cover border border-slate-200"
                          />
                        ) : (
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                            <User className="h-5 w-5 text-slate-500" />
                          </div>
                        )}
                        <div className="min-w-0 pr-2">
                          <p className="truncate text-xs font-bold text-slate-900 max-w-[120px]">
                            {c.student_name || c.name || `Pessoa #${index + 1}`}
                          </p>
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                            <span className="font-semibold text-blue-700">{c.photo_count} foto{c.photo_count !== 1 ? "s" : ""}</span>
                            <span>•</span>
                            <span>{c.face_count} face{c.face_count !== 1 ? "s" : ""}</span>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Indicador de Filtro de Pessoa Ativo */}
            {activeCluster && (
              <div className="mb-4 flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-xs text-blue-900">
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-blue-600" />
                  <span>
                    Exibindo apenas fotos com <strong>{activeCluster.student_name || activeCluster.name || "esta Pessoa"}</strong> ({photos.length} fotos encontradas)
                  </span>
                </div>
                <button
                  onClick={() => setSelectedClusterId(null)}
                  className="flex items-center gap-1 rounded-lg bg-blue-100 px-2.5 py-1 text-[11px] font-semibold text-blue-800 hover:bg-blue-200 transition cursor-pointer"
                >
                  <X className="h-3.5 w-3.5" />
                  Remover Filtro
                </button>
              </div>
            )}

            {/* Abas de Filtros por Status */}
            <div className="flex border-b border-slate-200 mb-6 gap-1 overflow-x-auto pb-1">
              {[
                { id: "ALL", label: "Todas as Fotos", count: counts.total },
                { id: "PENDING", label: "Pendentes", count: counts.pending },
                { id: "PROCESSING", label: "Processando", count: counts.processing },
                { id: "COMPLETED", label: "Concluídas", count: counts.completed },
                { id: "FAILED", label: "Falhas", count: counts.failed },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveFilter(tab.id)}
                  className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                    activeFilter === tab.id
                      ? "border-blue-600 text-blue-600 bg-blue-50/50 rounded-t-lg font-semibold"
                      : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-200"
                  }`}
                >
                  <span>{tab.label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    activeFilter === tab.id
                      ? "bg-blue-100 text-blue-700"
                      : "bg-slate-100 text-slate-500"
                  }`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Lista / Grade de Fotos com Detalhes */}
            {loading && photos.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-500">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 mb-3" />
                <p className="text-sm">Carregando fotos...</p>
              </div>
            ) : photos.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-12 text-center bg-white">
                <FolderInput className="mx-auto h-12 w-12 text-slate-400 mb-3" />
                <h3 className="text-base font-medium text-slate-700">
                  {selectedClusterId ? "Nenhuma foto encontrada para esta pessoa neste filtro de status" : "Nenhuma foto encontrada neste filtro"}
                </h3>
                {selectedClusterId ? (
                  <button
                    onClick={() => setSelectedClusterId(null)}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition cursor-pointer"
                  >
                    Ver Todas as Fotos
                  </button>
                ) : (
                  <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
                    Coloque arquivos de imagem na pasta <code className="text-blue-600 bg-slate-100 px-1.5 py-0.5 rounded">backend/test_images/</code> e clique em &quot;Importar Pasta de Testes&quot; acima para iniciar!
                  </p>
                )}
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {photos.map((photo) => {
                  const isFailed = photo.process_status === "FAILED";
                  const isProcessing = photo.process_status === "PROCESSING";
                  const isPending = photo.process_status === "PENDING";
                  const isCompleted = photo.process_status === "COMPLETED";

                  return (
                    <div
                      key={photo.id}
                      className={`flex flex-col rounded-2xl border bg-white p-4 transition shadow-sm hover:border-slate-300 ${
                        isFailed
                          ? "border-rose-300"
                          : isProcessing
                          ? "border-amber-300"
                          : isPending
                          ? "border-blue-300"
                          : "border-slate-200"
                      }`}
                    >
                      {/* Cabeçalho do Card */}
                      <div className="flex items-start justify-between gap-2 mb-3">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-slate-800" title={photo.file_path}>
                            {photo.file_path}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            {photo.class_name ? `Turma: ${photo.class_name}` : "Geral"} • #{photo.id}
                          </p>
                        </div>

                        {/* Status Badge */}
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${
                            isCompleted
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : isProcessing
                              ? "bg-amber-50 text-amber-700 border border-amber-200 animate-pulse"
                              : isPending
                              ? "bg-blue-50 text-blue-700 border border-blue-200"
                              : "bg-rose-50 text-rose-700 border border-rose-200"
                          }`}
                        >
                          {isCompleted && <CheckCircle2 className="h-3 w-3" />}
                          {isProcessing && <Loader2 className="h-3 w-3 animate-spin" />}
                          {isPending && <Clock className="h-3 w-3" />}
                          {isFailed && <XCircle className="h-3 w-3" />}
                          {photo.process_status}
                        </span>
                      </div>

                      {/* Thumbnail da Foto Principal */}
                      <div
                        onClick={() => setSelectedPhoto(photo)}
                        className="relative aspect-video w-full rounded-xl bg-slate-50 overflow-hidden cursor-pointer group border border-slate-200/80 mb-3"
                      >
                        <img
                          src={`${API_URL}${photo.image_url}`}
                          alt={photo.file_path}
                          className="h-full w-full object-cover group-hover:scale-105 transition duration-300"
                          loading="lazy"
                        />
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-1.5 text-xs text-white font-medium">
                          <Eye className="h-4 w-4" />
                          Inspecionar
                        </div>
                      </div>

                      {/* Rostos Detectados */}
                      <div className="flex-1">
                        <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
                          <span className="font-medium flex items-center gap-1">
                            <Layers className="h-3.5 w-3.5 text-blue-600" />
                            Rostos Detectados:
                          </span>
                          <span className="font-semibold text-slate-800">
                            {photo.detected_faces.length}
                          </span>
                        </div>

                        {isCompleted && photo.detected_faces.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {photo.detected_faces.map((face) => {
                              const isThisClusterActive = selectedClusterId && face.cluster_id === selectedClusterId;

                              return (
                                <button
                                  key={face.id}
                                  onClick={() => face.cluster_id && setSelectedClusterId(face.cluster_id)}
                                  className={`group relative flex items-center gap-1.5 rounded-lg border p-1.5 pr-2.5 text-[11px] text-left transition cursor-pointer ${
                                    isThisClusterActive
                                      ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                                      : "border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white"
                                  }`}
                                  title={face.cluster_id ? "Clique para filtrar todas as fotos desta pessoa" : undefined}
                                >
                                  {face.face_crop_url ? (
                                    <img
                                      src={`${API_URL}${face.face_crop_url}`}
                                      alt="Face crop"
                                      className="h-8 w-8 rounded-md object-cover border border-slate-200"
                                    />
                                  ) : (
                                    <div className="h-8 w-8 rounded-md bg-slate-100 flex items-center justify-center">
                                      <User className="h-4 w-4 text-slate-500" />
                                    </div>
                                  )}
                                  <div className="min-w-0">
                                    <p className="truncate font-semibold text-slate-800 max-w-[100px]">
                                      {face.student_name ? face.student_name : face.cluster_name || "Pessoa"}
                                    </p>
                                    <p className="text-[9px] text-blue-600 group-hover:underline">
                                      {face.cluster_id ? "Ver fotos →" : "Sem grupo"}
                                    </p>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        ) : isCompleted && photo.detected_faces.length === 0 ? (
                          <p className="text-xs text-slate-500 italic">Nenhum rosto identificado nesta imagem.</p>
                        ) : isPending ? (
                          <p className="text-xs text-blue-700 bg-blue-50 rounded-lg p-2 border border-blue-200">
                            Aguardando processamento na fila...
                          </p>
                        ) : isProcessing ? (
                          <p className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2 border border-amber-200 flex items-center gap-1.5">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Executando InsightFace e gerando embeddings...
                          </p>
                        ) : null}
                      </div>

                      {/* Log de Erro se Falhou */}
                      {isFailed && photo.process_error && (
                        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-700">
                          <button
                            onClick={() => toggleErrorExpand(photo.id)}
                            className="flex w-full items-center justify-between font-medium text-rose-700 cursor-pointer"
                          >
                            <span className="flex items-center gap-1.5">
                              <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
                              Ver erro do processamento (Tentativa #{photo.process_attempts})
                            </span>
                            {expandedErrors[photo.id] ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                          </button>
                          {expandedErrors[photo.id] && (
                            <pre className="mt-2 max-h-40 overflow-y-auto rounded bg-white p-2 font-mono text-[10px] text-rose-800 whitespace-pre-wrap border border-rose-200">
                              {photo.process_error}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ABA: MATCH (ESTILO GOOGLE FOTOS / TINDER) */}
        {activeTab === "match" && (
          <div>
            {currentSuggestion ? (
              <div className="relative mb-8 overflow-hidden rounded-3xl border border-blue-200 bg-white p-5 sm:p-7 shadow-xl shadow-blue-500/5">
                {/* Faixa Superior: Título, Contador e Navegação */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                          É a mesma pessoa?
                        </h3>
                        <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 border border-blue-200/60">
                          Sugestão {safeIndex + 1} de {visibleSuggestions.length}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Identificamos estes dois rostos com alta semelhança. Confirme para associá-los ou descarte se forem pessoas diferentes.
                      </p>
                    </div>
                  </div>

                  {/* Badges e Navegação rápida */}
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 border border-emerald-200 shadow-sm">
                      <Link2 className="h-3.5 w-3.5" />
                      <span>{currentSuggestion.similarity_percent}% de similaridade</span>
                    </div>

                    {visibleSuggestions.length > 1 && (
                      <div className="flex items-center gap-1 border-l border-slate-200 pl-3">
                        <button
                          onClick={handlePrevSuggestion}
                          className="rounded-xl border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition cursor-pointer"
                          title="Sugestão anterior"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>
                        <button
                          onClick={handleSkipSuggestion}
                          className="rounded-xl border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition cursor-pointer"
                          title="Próxima sugestão"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Comparação Lado a Lado: Duas fotos grandes com Bounding Box */}
                <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-5 items-stretch">
                  <MatchPhotoCard
                    key={`source_${currentSuggestion.id}`}
                    photoUrl={currentSuggestion.source_photo_url}
                    cropUrl={currentSuggestion.source_face_crop_url}
                    boundingBox={currentSuggestion.source_bounding_box}
                    title={
                      currentSuggestion.source_student_name ||
                      currentSuggestion.source_cluster_name ||
                      `Pessoa / Grupo #${currentSuggestion.source_cluster_id}`
                    }
                    subtitle={`${
                      currentSuggestion.source_student_name
                        ? "Aluno já vinculado"
                        : `Grupo #${currentSuggestion.source_cluster_id}`
                    } • Foto #${currentSuggestion.source_photo_id}`}
                  />

                  <MatchPhotoCard
                    key={`target_${currentSuggestion.id}`}
                    photoUrl={currentSuggestion.target_photo_url}
                    cropUrl={currentSuggestion.target_face_crop_url}
                    boundingBox={currentSuggestion.target_bounding_box}
                    title={
                      currentSuggestion.target_student_name ||
                      currentSuggestion.target_cluster_name ||
                      `Pessoa / Grupo #${currentSuggestion.target_cluster_id}`
                    }
                    subtitle={`${
                      currentSuggestion.target_student_name
                        ? "Aluno já vinculado"
                        : `Grupo #${currentSuggestion.target_cluster_id}`
                    } • Foto #${currentSuggestion.target_photo_id}`}
                  />
                </div>

                {/* Ações Centrais Estilo Tinder / Google Fotos */}
                <div className="mt-7 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
                  {/* Botão Ignorar / Pessoas Diferentes */}
                  <button
                    onClick={() => handleDismissSuggestion(currentSuggestion.id)}
                    disabled={mergingSuggestionId !== null}
                    className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-2xl border-2 border-rose-200 bg-rose-50/80 px-7 py-3 text-sm font-bold text-rose-700 shadow-sm transition hover:bg-rose-100 hover:border-rose-300 active:scale-95 disabled:opacity-50 cursor-pointer"
                  >
                    <X className="h-5 w-5 stroke-[2.5]" />
                    <span>Pessoas Diferentes</span>
                  </button>

                  {/* Botão Pular / Próxima */}
                  {visibleSuggestions.length > 1 && (
                    <button
                      onClick={handleSkipSuggestion}
                      disabled={mergingSuggestionId !== null}
                      className="w-full sm:w-auto flex items-center justify-center gap-1.5 rounded-2xl border border-slate-200 bg-slate-100 px-5 py-3 text-xs font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition active:scale-95 disabled:opacity-50 cursor-pointer"
                      title="Pular esta sugestão por enquanto"
                    >
                      <span>Pular</span>
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  )}

                  {/* Botão Confirmar / Mesma Pessoa */}
                  <button
                    onClick={() => handleConfirmMatch(currentSuggestion)}
                    disabled={mergingSuggestionId !== null}
                    className="w-full sm:w-auto flex items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/25 transition hover:from-blue-700 hover:to-indigo-700 active:scale-95 disabled:opacity-50 cursor-pointer"
                  >
                    {mergingSuggestionId === currentSuggestion.id ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Check className="h-5 w-5 stroke-[2.5]" />
                    )}
                    <span>
                      {mergingSuggestionId === currentSuggestion.id
                        ? "Associando..."
                        : "Sim, é a mesma pessoa"}
                    </span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-12 text-center shadow-sm">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 mb-4">
                  <Sparkles className="h-7 w-7" />
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  Nenhuma sugestão de match pendente
                </h3>
                <p className="mt-1.5 text-xs text-slate-500 max-w-md mx-auto">
                  Não há pares de rostos com alta similaridade aguardando confirmação no momento. Quando o algoritmo encontrar fotos parecidas entre pessoas diferentes, elas aparecerão aqui para sua confirmação.
                </p>
                <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                  <button
                    onClick={handleReclusterAll}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition cursor-pointer"
                  >
                    {actionLoading === "recluster" ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Layers className="h-4 w-4" />
                    )}
                    <span>Reagrupar Rostos (DBSCAN)</span>
                  </button>
                  <button
                    onClick={() => loadData(true)}
                    disabled={loading}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs font-medium text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                  >
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    <span>Atualizar Dados</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ABA: ROSTOS (TODOS OS ROSTOS DETECTADOS) */}
        {activeTab === "rostos" && (
          <div>
            {/* Barra de Filtro e Busca de Rostos */}
            <div className="mb-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  value={faceSearchTerm}
                  onChange={(e) => setFaceSearchTerm(e.target.value)}
                  placeholder="Buscar por nome do aluno ou grupo..."
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-9 py-2 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none"
                />
                {faceSearchTerm && (
                  <button
                    onClick={() => setFaceSearchTerm("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setFaceFilterLinked("ALL")}
                  className={`rounded-xl px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
                    faceFilterLinked === "ALL"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  Todos ({detectedFaces.length})
                </button>
                <button
                  onClick={() => setFaceFilterLinked("LINKED")}
                  className={`rounded-xl px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
                    faceFilterLinked === "LINKED"
                      ? "bg-emerald-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  Alunos vinculados ({linkedFacesCount})
                </button>
                <button
                  onClick={() => setFaceFilterLinked("UNLINKED")}
                  className={`rounded-xl px-3 py-1.5 text-xs font-medium transition cursor-pointer ${
                    faceFilterLinked === "UNLINKED"
                      ? "bg-slate-700 text-white shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  Não vinculados ({unlinkedFacesCount})
                </button>
              </div>
            </div>

            {/* Grid com Todos os Rostos Detectados */}
            {filteredDetectedFaces.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-12 text-center">
                <User className="mx-auto h-12 w-12 text-slate-400 mb-3" />
                <h3 className="text-base font-bold text-slate-900">
                  Nenhum rosto encontrado
                </h3>
                <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
                  {faceSearchTerm || faceFilterLinked !== "ALL"
                    ? "Nenhum rosto corresponde aos filtros de busca aplicados."
                    : "Processe imagens na aba Dashboard para detectar novos rostos."}
                </p>
                {(faceSearchTerm || faceFilterLinked !== "ALL") && (
                  <button
                    onClick={() => {
                      setFaceSearchTerm("");
                      setFaceFilterLinked("ALL");
                    }}
                    className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition cursor-pointer"
                  >
                    Limpar Filtros
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                {filteredDetectedFaces.map((face) => {
                  const displayName =
                    face.student_name || face.cluster_name || `Pessoa #${face.cluster_id?.slice(0, 6) || "Sem grupo"}`;

                  return (
                    <div
                      key={face.id}
                      className="group flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm hover:border-blue-400 hover:shadow-md transition"
                    >
                      {/* Imagem do Rosto Grande */}
                      <div className="relative aspect-square w-full overflow-hidden bg-slate-100">
                        {face.face_crop_url ? (
                          <img
                            src={`${API_URL}${face.face_crop_url}`}
                            alt={displayName}
                            className="h-full w-full object-cover group-hover:scale-105 transition duration-300"
                            loading="lazy"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-slate-400">
                            <User className="h-12 w-12" />
                          </div>
                        )}

                        {face.detection_score && (
                          <span className="absolute top-2 right-2 rounded-md bg-black/60 backdrop-blur-sm px-1.5 py-0.5 text-[10px] font-semibold text-white">
                            {(face.detection_score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>

                      {/* Nome da Pessoa e Informações Embaixo */}
                      <div className="flex flex-1 flex-col justify-between p-3">
                        <div className="text-center">
                          <h4 className="font-bold text-xs sm:text-sm text-slate-900 truncate" title={displayName}>
                            {displayName}
                          </h4>
                          <div className="mt-1 flex items-center justify-center">
                            {face.student_name ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                                <Check className="h-2.5 w-2.5 stroke-[3]" />
                                Aluno
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                                {face.cluster_name || `Grupo #${face.cluster_id?.slice(0, 6) || "Sem grupo"}`}
                              </span>
                            )}
                          </div>
                        </div>

                        {face.cluster_id && (
                          <button
                            onClick={() => {
                              setSelectedClusterId(face.cluster_id!);
                              setActiveTab("dashboard");
                            }}
                            className="mt-3 w-full rounded-xl border border-blue-200 bg-blue-50 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 transition cursor-pointer"
                          >
                            Ver fotos
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Modal de Inspeção Detalhada */}
        {selectedPhoto && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
            <div className="relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
              <button
                onClick={() => setSelectedPhoto(null)}
                className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>

              <h2 className="text-lg font-bold text-slate-900 mb-1">Inspeção da Foto #{selectedPhoto.id}</h2>
              <p className="text-xs text-slate-500 mb-4">{selectedPhoto.file_path}</p>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="rounded-xl overflow-hidden bg-slate-50 border border-slate-200">
                  <img
                    src={`${API_URL}${selectedPhoto.image_url}`}
                    alt="Full Preview"
                    className="w-full h-auto object-contain max-h-[400px]"
                  />
                </div>

                <div className="flex flex-col gap-4">
                  <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-xs">
                    <p className="font-semibold text-slate-600 mb-2">Detalhes de Processamento</p>
                    <div className="space-y-1.5 text-slate-500">
                      <p><strong className="text-slate-600">Status:</strong> {selectedPhoto.process_status}</p>
                      <p><strong className="text-slate-600">Tentativas:</strong> {selectedPhoto.process_attempts}</p>
                      <p><strong className="text-slate-600">Data de Registro:</strong> {new Date(selectedPhoto.created_at).toLocaleString()}</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-600 mb-2">Faces Detectadas ({selectedPhoto.detected_faces.length})</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {selectedPhoto.detected_faces.map((face, index) => (
                        <div
                          key={face.id}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/80 p-2.5 text-xs"
                        >
                          <div className="flex items-center gap-3">
                            {face.face_crop_url && (
                              <img
                                src={`${API_URL}${face.face_crop_url}`}
                                alt="Crop"
                                className="h-10 w-10 rounded-lg object-cover border border-slate-200"
                              />
                            )}
                            <div>
                              <p className="font-semibold text-slate-800">Face #{index + 1}</p>
                              <p className="text-[11px] text-slate-500">
                                Cluster: <span className="text-blue-600">{face.cluster_name || face.cluster_id?.slice(0, 8) || "N/A"}</span>
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {face.cluster_id && (
                              <button
                                onClick={() => {
                                  setSelectedClusterId(face.cluster_id!);
                                  setSelectedPhoto(null);
                                }}
                                className="rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-[11px] font-medium text-blue-700 hover:bg-blue-700/20 transition cursor-pointer"
                              >
                                Ver todas as fotos
                              </button>
                            )}
                            {face.detection_score && (
                              <p className="text-[10px] text-slate-500">
                                {(face.detection_score * 100).toFixed(0)}%
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function MatchPhotoCard({
  photoUrl,
  cropUrl,
  boundingBox,
  title,
  subtitle,
}: {
  photoUrl?: string | null;
  cropUrl?: string | null;
  boundingBox?: number[] | null;
  title: string;
  subtitle: string;
}) {
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    if (naturalWidth > 0 && naturalHeight > 0) {
      setNaturalSize({ width: naturalWidth, height: naturalHeight });
    }
  };

  let bboxStyle: React.CSSProperties | null = null;
  if (boundingBox && boundingBox.length >= 4 && naturalSize && naturalSize.width > 0) {
    const [x1, y1, x2, y2] = boundingBox;
    const left = `${(x1 / naturalSize.width) * 100}%`;
    const top = `${(y1 / naturalSize.height) * 100}%`;
    const width = `${((x2 - x1) / naturalSize.width) * 100}%`;
    const height = `${((y2 - y1) / naturalSize.height) * 100}%`;
    bboxStyle = { left, top, width, height };
  }

  return (
    <div className="flex flex-col rounded-2xl border border-slate-200 bg-slate-900 overflow-hidden shadow-sm relative group">
      <div className="relative h-72 sm:h-96 w-full bg-slate-950 flex items-center justify-center overflow-hidden">
        {photoUrl ? (
          <div className="relative inline-block max-h-full max-w-full">
            <img
              src={`${API_URL}${photoUrl}`}
              alt={title}
              onLoad={handleImageLoad}
              className="max-h-72 sm:max-h-96 max-w-full w-auto h-auto object-contain block mx-auto"
            />
            {bboxStyle && (
              <div
                style={bboxStyle}
                className="absolute border-2 sm:border-[3px] border-emerald-400 bg-emerald-400/20 shadow-[0_0_15px_rgba(52,211,153,0.7)] rounded-md pointer-events-none transition-all"
              />
            )}
          </div>
        ) : cropUrl ? (
          <img
            src={`${API_URL}${cropUrl}`}
            alt={title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-600">
            <User className="h-16 w-16 mb-2" />
            <span className="text-xs">Foto indisponível</span>
          </div>
        )}

        {/* Recorte do rosto em destaque (Overlay flutuante na foto) */}
        {cropUrl && (
          <div className="absolute top-3 left-3 flex items-center gap-2.5 rounded-2xl bg-black/75 backdrop-blur-md p-2 pr-3.5 border border-white/20 text-white shadow-xl z-10">
            <img
              src={`${API_URL}${cropUrl}`}
              alt={title}
              className="h-12 w-12 sm:h-14 sm:w-14 rounded-xl object-cover border-2 border-white shadow-md ring-1 ring-black/50"
            />
            <div className="flex flex-col text-left">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-300">
                Rosto Detectado
              </span>
              <span className="text-xs font-semibold text-white truncate max-w-[130px] sm:max-w-[150px]">
                {title}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Rodapé da Foto */}
      <div className="bg-white p-3.5 border-t border-slate-200 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-xs font-bold text-slate-900 truncate">{title}</p>
          <p className="text-[11px] text-slate-500">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}

function RotateCcwIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  );
}
