"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, CalendarDays, Camera, Download, ImageIcon, LoaderCircle, LogOut, Search } from "lucide-react";
import { useAuth } from "../../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Photo = { id: number; media_url: string; title?: string; description?: string; uploader_name?: string; class_id?: number; class_name?: string; status: string; created_at: string };
type SchoolClass = { id: number; name: string; year: number; is_active: boolean };
const statusLabels: Record<string, string> = { PENDING_REVIEW: "Aguardando revisão", PRIVATE_SCHOOL_ONLY: "Somente escola", APPROVED_FOR_MARKETING: "Aprovada para marketing" };
const statusStyles: Record<string, string> = { PENDING_REVIEW: "bg-amber-100 text-amber-800", PRIVATE_SCHOOL_ONLY: "bg-slate-200 text-slate-700", APPROVED_FOR_MARKETING: "bg-green-100 text-green-800" };

export default function AdminPhotosPage() {
  const { user, token, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const [photoResponse, classResponse] = await Promise.all([
        fetch(`${API_URL}/api/photos/`, { headers }),
        fetch(`${API_URL}/api/classes/?include_inactive=true`, { headers }),
      ]);
      if (!photoResponse.ok || !classResponse.ok) throw new Error("Não foi possível carregar a biblioteca de fotos.");
      setPhotos(await photoResponse.json()); setClasses(await classResponse.json());
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Erro ao carregar fotos."); }
    finally { setLoading(false); }
  }, [headers, token]);

  useEffect(() => {
    if (authLoading || !user) return;
    if (user.role !== "COORDENADOR") { router.replace(user.role === "MARKETING" ? "/marketing" : "/"); return; }
    // A carga começa somente depois que a sessão do navegador foi restaurada.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [authLoading, load, router, user]);

  const filtered = useMemo(() => photos.filter((photo) => {
    const q = search.toLocaleLowerCase("pt-BR");
    if (classFilter && photo.class_id !== Number(classFilter)) return false;
    if (statusFilter && photo.status !== statusFilter) return false;
    return `${photo.title ?? ""} ${photo.description ?? ""} ${photo.uploader_name ?? ""} ${photo.class_name ?? ""}`.toLocaleLowerCase("pt-BR").includes(q);
  }), [classFilter, photos, search, statusFilter]);

  async function updateStatus(photoId: number, status: string) {
    const response = await fetch(`${API_URL}/api/photos/${photoId}/status`, { method: "PUT", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
    if (!response.ok) { setError("Não foi possível atualizar a liberação da foto."); return; }
    const updated = await response.json();
    setPhotos((current) => current.map((photo) => photo.id === photoId ? updated : photo));
  }
  const mediaUrl = (photo: Photo) => photo.media_url.startsWith("http") ? photo.media_url : `${API_URL}${photo.media_url}`;

  if (authLoading || !user || user.role !== "COORDENADOR") return <main className="grid min-h-screen place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></main>;
  return <div className="min-h-screen bg-slate-50 text-slate-900">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4"><div className="flex items-center gap-3"><Link href="/admin" className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100"><ArrowLeft className="h-5 w-5" /></Link><span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white"><Camera /></span><div><p className="font-semibold">Biblioteca de fotos</p><p className="text-xs text-slate-500">{user.school.name}</p></div></div><button onClick={logout} className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100" title="Sair"><LogOut className="h-5 w-5" /></button></div></header>
    <main className="mx-auto max-w-7xl px-5 py-8"><div className="mb-6"><h1 className="text-2xl font-semibold">Todas as fotos</h1><p className="mt-1 text-sm text-slate-600">Visualize e revise as fotos de todas as turmas da escola.</p></div>
      <div className="mb-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-[1fr_240px_240px]"><label className="relative"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input className="input w-full pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar foto, turma ou autor" /></label><select className="input" value={classFilter} onChange={(event) => setClassFilter(event.target.value)}><option value="">Todas as turmas</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.year}{item.is_active ? "" : " (inativa)"}</option>)}</select><select className="input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">Todas as situações</option><option value="PENDING_REVIEW">Aguardando revisão</option><option value="PRIVATE_SCHOOL_ONLY">Somente escola</option><option value="APPROVED_FOR_MARKETING">Aprovadas para marketing</option></select></div>
      <div className="mb-4 flex items-center gap-2 text-sm text-slate-500"><ImageIcon className="h-4 w-4" />{filtered.length} de {photos.length} fotos</div>
      {error && <div className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {loading ? <div className="grid min-h-96 place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></div> : filtered.length === 0 ? <div className="grid min-h-72 place-items-center rounded-2xl border border-dashed border-slate-300 bg-white text-center text-sm text-slate-500"><div><ImageIcon className="mx-auto mb-3 h-9 w-9" />Nenhuma foto encontrada.</div></div> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{filtered.map((photo) => <article key={photo.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="relative aspect-[4/3] bg-slate-100"><Image src={mediaUrl(photo)} alt={photo.title ?? "Foto escolar"} fill unoptimized className="object-cover" /><span className={`absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-medium ${statusStyles[photo.status]}`}>{statusLabels[photo.status]}</span></div><div className="p-4"><p className="truncate font-medium">{photo.title ?? "Foto escolar"}</p><p className="mt-1 text-sm text-slate-600">{photo.class_name ?? "Sem turma"}</p><p className="mt-1 flex items-center gap-1 text-xs text-slate-500"><CalendarDays className="h-3.5 w-3.5" />{new Date(photo.created_at).toLocaleDateString("pt-BR")} · {photo.uploader_name ?? "Equipe escolar"}</p><label className="mt-4 block text-xs font-medium text-slate-500">Liberação<select className="input mt-1 w-full" value={photo.status} onChange={(event) => void updateStatus(photo.id, event.target.value)}><option value="PENDING_REVIEW">Aguardando revisão</option><option value="PRIVATE_SCHOOL_ONLY">Somente escola</option><option value="APPROVED_FOR_MARKETING">Aprovada para marketing</option></select></label><div className="mt-3 grid grid-cols-2 gap-2">{photo.class_id ? <Link href={`/class/${photo.class_id}`} className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-center text-xs font-medium text-blue-700">Abrir turma</Link> : <span />}<a href={mediaUrl(photo)} download className="rounded-lg border border-slate-300 px-3 py-2 text-center text-xs font-medium hover:bg-slate-50"><Download className="mr-1 inline h-3.5 w-3.5" />Baixar</a></div></div></article>)}</div>}
    </main>
  </div>;
}
