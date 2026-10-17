"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, GraduationCap, ImageIcon, LoaderCircle, LogOut, Search } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Photo = { id: number; media_url: string; title?: string; description?: string; uploader_name?: string; created_at: string };

export default function MarketingPage() {
  const { user, token, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (authLoading || !user || !token) return;
    if (user.role !== "MARKETING") { router.replace(user.role === "COORDENADOR" ? "/admin" : "/"); return; }
    fetch(`${API_URL}/api/photos/marketing`, { headers: { Authorization: `Bearer ${token}` } }).then(async (response) => {
      if (!response.ok) throw new Error("Não foi possível carregar as fotos aprovadas.");
      setPhotos(await response.json());
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Erro ao carregar fotos.")).finally(() => setLoading(false));
  }, [authLoading, router, token, user]);

  const shown = useMemo(() => {
    const q = search.toLocaleLowerCase("pt-BR");
    return photos.filter((photo) => `${photo.title ?? ""} ${photo.description ?? ""} ${photo.uploader_name ?? ""}`.toLocaleLowerCase("pt-BR").includes(q));
  }, [photos, search]);
  const mediaUrl = (photo: Photo) => photo.media_url.startsWith("http") ? photo.media_url : `${API_URL}${photo.media_url}`;

  if (authLoading || !user || user.role !== "MARKETING") return <main className="grid min-h-screen place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></main>;
  return <div className="min-h-screen bg-slate-50"><header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-violet-600 text-white"><GraduationCap /></span><div><p className="font-semibold">{user.school.name}</p><p className="text-xs text-slate-500">Biblioteca do marketing</p></div></div><div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-sm font-medium">{user.name}</p><p className="text-xs text-slate-500">Somente fotos aprovadas</p></div><button onClick={logout} className="rounded-lg border border-slate-300 p-2 text-slate-600"><LogOut className="h-5 w-5" /></button></div></div></header>
    <main className="mx-auto max-w-7xl px-5 py-8"><h1 className="text-2xl font-semibold">Fotos aprovadas</h1><p className="mt-1 text-sm text-slate-600">Conteúdo liberado pela coordenação para uso da sua escola.</p><label className="relative my-6 block max-w-xl"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input value={search} onChange={(event) => setSearch(event.target.value)} className="input w-full pl-9" placeholder="Buscar por título, descrição ou autor" /></label>
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {loading ? <div className="grid min-h-80 place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-violet-600" /></div> : shown.length === 0 ? <div className="grid min-h-72 place-items-center rounded-2xl border border-dashed border-slate-300 bg-white text-center text-sm text-slate-500"><div><ImageIcon className="mx-auto mb-3 h-9 w-9" />Nenhuma foto aprovada encontrada.</div></div> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{shown.map((photo) => <article key={photo.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="relative aspect-[4/3] bg-slate-100"><Image src={mediaUrl(photo)} alt={photo.title ?? "Foto aprovada"} fill unoptimized className="object-cover" /></div><div className="p-4"><p className="truncate font-medium">{photo.title ?? "Foto escolar"}</p><p className="mt-1 text-xs text-slate-500">{new Date(photo.created_at).toLocaleDateString("pt-BR")} · {photo.uploader_name ?? "Equipe escolar"}</p><a href={mediaUrl(photo)} download className="mt-4 block rounded-xl border border-slate-300 px-3 py-2 text-center text-sm font-medium hover:bg-slate-50"><Download className="mr-1.5 inline h-4 w-4" />Baixar imagem</a></div></article>)}</div>}
    </main></div>;
}
