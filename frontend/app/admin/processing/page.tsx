"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
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
  ChevronUp
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

interface StatusCounts {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  total: number;
}

export default function FaceProcessingAdminPage() {
  const { user, token, logout, loading: authLoading } = useAuth();

  const [counts, setCounts] = useState<StatusCounts>({
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    total: 0,
  });

  const [photos, setPhotos] = useState<ProcessingPhoto[]>([]);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedPhoto, setSelectedPhoto] = useState<ProcessingPhoto | null>(null);
  const [expandedErrors, setExpandedErrors] = useState<Record<number, boolean>>({});

  const loadData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      // 1. Carrega métricas da fila
      const statusRes = await fetch(`${API_URL}/api/system/processing-status`);
      if (statusRes.ok) {
        const countsData = await statusRes.json();
        setCounts(countsData);
      }

      // 2. Carrega lista detalhada de fotos
      const photosRes = await fetch(`${API_URL}/api/system/processing-photos?status_filter=${activeFilter}&limit=100`);
      if (photosRes.ok) {
        const photosData = await photosRes.json();
        setPhotos(photosData);
      }
    } catch (err) {
      console.error("Erro ao carregar dados do processamento:", err);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [activeFilter]);

  // Carga inicial e quando o filtro muda
  useEffect(() => {
    void loadData(true);
  }, [loadData]);

  // Auto-refresh a cada 4 segundos
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      void loadData(false);
    }, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadData]);

  // Ação: Disparar Processamento Imediato (Process Now)
  async function handleProcessNow() {
    setActionLoading("process");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/process-now?batch_size=50`, {
        method: "POST",
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
      const res = await fetch(`${API_URL}/api/system/reprocess-failed`, { method: "POST" });
      const data = await res.json();
      setActionMessage({ type: "success", text: data.message });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: "Erro ao re-enfileirar fotos com falha." });
    } finally {
      setActionLoading(null);
    }
  }

  // Ação: Reprocessar Todas
  async function handleReprocessAll() {
    if (!confirm("Tem certeza que deseja reprocessar todas as fotos do sistema?")) return;
    setActionLoading("reprocess_all");
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/api/system/reprocess-all`, { method: "POST" });
      const data = await res.json();
      setActionMessage({ type: "success", text: data.message });
      await loadData(false);
    } catch (err) {
      setActionMessage({ type: "error", text: "Erro ao re-enfileirar todas as fotos." });
    } finally {
      setActionLoading(null);
    }
  }

  function toggleErrorExpand(photoId: number) {
    setExpandedErrors(prev => ({ ...prev, [photoId]: !prev[photoId] }));
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3.5">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
            >
              <ArrowLeft className="h-4 w-4" />
              Voltar
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-400" />
                <h1 className="font-semibold text-white tracking-tight">Reconhecimento Facial & Fila de Processamento</h1>
              </div>
              <p className="text-xs text-slate-400">Monitoramento e controle de inferência (InsightFace + DBSCAN)</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                autoRefresh
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-slate-700 bg-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${autoRefresh ? "animate-spin" : ""}`} />
              {autoRefresh ? "Auto-refresh: Ativo" : "Auto-refresh: Pausado"}
            </button>

            {user && (
              <div className="hidden sm:flex items-center gap-2 border-l border-slate-800 pl-3">
                <span className="text-xs text-slate-400">{user.email}</span>
                <button
                  onClick={logout}
                  className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
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
                ? "border-emerald-500/30 bg-emerald-950/40 text-emerald-200"
                : actionMessage.type === "error"
                ? "border-rose-500/30 bg-rose-950/40 text-rose-200"
                : "border-blue-500/30 bg-blue-950/40 text-blue-200"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {actionMessage.type === "success" && <CheckCircle2 className="h-5 w-5 text-emerald-400" />}
              {actionMessage.type === "error" && <AlertTriangle className="h-5 w-5 text-rose-400" />}
              {actionMessage.type === "info" && <Sparkles className="h-5 w-5 text-blue-400" />}
              <span>{actionMessage.text}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-xs opacity-70 hover:opacity-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Métricas da Fila */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 mb-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-medium text-slate-400">Total de Fotos</p>
            <p className="mt-1.5 text-2xl font-bold text-white">{counts.total}</p>
          </div>

          <div className="rounded-xl border border-blue-900/40 bg-blue-950/20 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-blue-300">Pendentes</p>
              <Clock className="h-4 w-4 text-blue-400" />
            </div>
            <p className="mt-1.5 text-2xl font-bold text-blue-200">{counts.pending}</p>
          </div>

          <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-amber-300">Em Processamento</p>
              <Loader2 className="h-4 w-4 text-amber-400 animate-spin" />
            </div>
            <p className="mt-1.5 text-2xl font-bold text-amber-200">{counts.processing}</p>
          </div>

          <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-emerald-300">Concluídas</p>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="mt-1.5 text-2xl font-bold text-emerald-200">{counts.completed}</p>
          </div>

          <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-4 col-span-2 sm:col-span-1">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-rose-300">Falhas</p>
              <ShieldAlert className="h-4 w-4 text-rose-400" />
            </div>
            <p className="mt-1.5 text-2xl font-bold text-rose-200">{counts.failed}</p>
          </div>
        </div>

        {/* Barra de Ações Principais */}
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4 mb-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Botão de Disparo Manual de Processamento */}
            <button
              onClick={handleProcessNow}
              disabled={actionLoading !== null}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 transition cursor-pointer"
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
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-200 hover:bg-slate-700 active:scale-95 disabled:opacity-50 transition cursor-pointer"
            >
              {actionLoading === "ingest" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FolderInput className="h-4 w-4 text-indigo-400" />
              )}
              <span>Importar Pasta de Testes (test_images/)</span>
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {counts.failed > 0 && (
              <button
                onClick={handleReprocessFailed}
                disabled={actionLoading !== null}
                className="flex items-center gap-1.5 rounded-xl border border-rose-800/60 bg-rose-950/30 px-3 py-2 text-xs font-medium text-rose-300 hover:bg-rose-900/40 transition cursor-pointer"
              >
                <RotateCcwIcon className="h-3.5 w-3.5" />
                Reprocessar Falhas ({counts.failed})
              </button>
            )}

            <button
              onClick={handleReprocessAll}
              disabled={actionLoading !== null}
              className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition cursor-pointer"
            >
              Reprocessar Todas
            </button>

            <button
              onClick={() => loadData(true)}
              disabled={loading}
              className="rounded-xl border border-slate-700 bg-slate-800 p-2 text-slate-400 hover:text-white transition"
              title="Atualizar agora"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Abas de Filtros */}
        <div className="flex border-b border-slate-800 mb-6 gap-1 overflow-x-auto pb-1">
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
                  ? "border-indigo-500 text-indigo-400 bg-indigo-500/5 rounded-t-lg"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <span>{tab.label}</span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                activeFilter === tab.id
                  ? "bg-indigo-500/20 text-indigo-300"
                  : "bg-slate-800 text-slate-400"
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Lista / Grade de Fotos com Detalhes */}
        {loading && photos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mb-3" />
            <p className="text-sm">Carregando status das imagens...</p>
          </div>
        ) : photos.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-800 p-12 text-center">
            <FolderInput className="mx-auto h-12 w-12 text-slate-600 mb-3" />
            <h3 className="text-base font-medium text-slate-300">Nenhuma foto encontrada neste filtro</h3>
            <p className="mt-1 text-xs text-slate-500 max-w-md mx-auto">
              Coloque arquivos de imagem na pasta <code className="text-indigo-400 bg-indigo-950/50 px-1.5 py-0.5 rounded">backend/test_images/</code> e clique em &quot;Importar Pasta de Testes&quot; acima para iniciar!
            </p>
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
                  className={`flex flex-col rounded-2xl border bg-slate-900/60 p-4 transition shadow-sm hover:border-slate-700 ${
                    isFailed
                      ? "border-rose-900/50"
                      : isProcessing
                      ? "border-amber-800/50"
                      : isPending
                      ? "border-blue-900/50"
                      : "border-slate-800"
                  }`}
                >
                  {/* Cabeçalho do Card */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-slate-200" title={photo.file_path}>
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
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : isProcessing
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                          : isPending
                          ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
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
                    className="relative aspect-video w-full rounded-xl bg-slate-950 overflow-hidden cursor-pointer group border border-slate-800/80 mb-3"
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
                    <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                      <span className="font-medium flex items-center gap-1">
                        <Layers className="h-3.5 w-3.5 text-indigo-400" />
                        Rostos Detectados:
                      </span>
                      <span className="font-semibold text-slate-200">
                        {photo.detected_faces.length}
                      </span>
                    </div>

                    {isCompleted && photo.detected_faces.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {photo.detected_faces.map((face) => (
                          <div
                            key={face.id}
                            className="group relative flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950/80 p-1.5 pr-2.5 text-[11px]"
                          >
                            {face.face_crop_url ? (
                              <img
                                src={`${API_URL}${face.face_crop_url}`}
                                alt="Face crop"
                                className="h-8 w-8 rounded-md object-cover border border-slate-700"
                              />
                            ) : (
                              <div className="h-8 w-8 rounded-md bg-slate-800 flex items-center justify-center">
                                <User className="h-4 w-4 text-slate-500" />
                              </div>
                            )}
                            <div className="min-w-0">
                              <p className="truncate font-medium text-slate-300 max-w-[100px]">
                                {face.student_name ? face.student_name : face.cluster_name || "Pessoa"}
                              </p>
                              <p className="text-[9px] text-slate-500">
                                {face.student_name ? "Identificado" : "Não atribuído"}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : isCompleted && photo.detected_faces.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">Nenhum rosto identificado nesta imagem.</p>
                    ) : isPending ? (
                      <p className="text-xs text-blue-400/80 bg-blue-950/30 rounded-lg p-2 border border-blue-900/30">
                        Aguardando processamento na fila...
                      </p>
                    ) : isProcessing ? (
                      <p className="text-xs text-amber-400/80 bg-amber-950/30 rounded-lg p-2 border border-amber-900/30 flex items-center gap-1.5">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Executando InsightFace e gerando embeddings...
                      </p>
                    ) : null}
                  </div>

                  {/* Log de Erro se Falhou */}
                  {isFailed && photo.process_error && (
                    <div className="mt-3 rounded-xl border border-rose-900/60 bg-rose-950/30 p-2.5 text-xs text-rose-300">
                      <button
                        onClick={() => toggleErrorExpand(photo.id)}
                        className="flex w-full items-center justify-between font-medium text-rose-300"
                      >
                        <span className="flex items-center gap-1.5">
                          <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                          Ver erro do processamento (Tentativa #{photo.process_attempts})
                        </span>
                        {expandedErrors[photo.id] ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      </button>
                      {expandedErrors[photo.id] && (
                        <pre className="mt-2 max-h-40 overflow-y-auto rounded bg-black/50 p-2 font-mono text-[10px] text-rose-200 whitespace-pre-wrap">
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

        {/* Modal de Inspeção Detalhada */}
        {selectedPhoto && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
            <div className="relative max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
              <button
                onClick={() => setSelectedPhoto(null)}
                className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>

              <h2 className="text-lg font-bold text-white mb-1">Inspeção da Foto #{selectedPhoto.id}</h2>
              <p className="text-xs text-slate-400 mb-4">{selectedPhoto.file_path}</p>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="rounded-xl overflow-hidden bg-slate-950 border border-slate-800">
                  <img
                    src={`${API_URL}${selectedPhoto.image_url}`}
                    alt="Full Preview"
                    className="w-full h-auto object-contain max-h-[400px]"
                  />
                </div>

                <div className="flex flex-col gap-4">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs">
                    <p className="font-semibold text-slate-300 mb-2">Detalhes de Processamento</p>
                    <div className="space-y-1.5 text-slate-400">
                      <p><strong className="text-slate-300">Status:</strong> {selectedPhoto.process_status}</p>
                      <p><strong className="text-slate-300">Tentativas:</strong> {selectedPhoto.process_attempts}</p>
                      <p><strong className="text-slate-300">Data de Registro:</strong> {new Date(selectedPhoto.created_at).toLocaleString()}</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-300 mb-2">Faces Detectadas ({selectedPhoto.detected_faces.length})</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {selectedPhoto.detected_faces.map((face, index) => (
                        <div
                          key={face.id}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/80 p-2.5 text-xs"
                        >
                          <div className="flex items-center gap-3">
                            {face.face_crop_url && (
                              <img
                                src={`${API_URL}${face.face_crop_url}`}
                                alt="Crop"
                                className="h-10 w-10 rounded-lg object-cover border border-slate-700"
                              />
                            )}
                            <div>
                              <p className="font-semibold text-slate-200">Face #{index + 1}</p>
                              <p className="text-[11px] text-slate-400">
                                Cluster: <span className="text-indigo-400">{face.cluster_name || face.cluster_id?.slice(0, 8) || "N/A"}</span>
                              </p>
                            </div>
                          </div>

                          <div className="text-right">
                            <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-semibold ${
                              face.student_name
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : "bg-slate-800 text-slate-400"
                            }`}>
                              {face.student_name ? `Aluno: ${face.student_name}` : "Não atribuído"}
                            </span>
                            {face.detection_score && (
                              <p className="text-[10px] text-slate-500 mt-0.5">
                                Confiança: {(face.detection_score * 100).toFixed(1)}%
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
