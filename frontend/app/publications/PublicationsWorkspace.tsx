"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, GraduationCap, Images, Layers3, LoaderCircle, Plus, Search, UsersRound, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import Modal from "../components/Modal";
import TeacherNavigation from "../components/TeacherNavigation";
import PublicationActions, { type PublicationAction } from "./PublicationActions";
import PublicationDrawer from "./PublicationDrawer";
import PublicationEditor from "./PublicationEditor";
import PublicationImage from "./PublicationImage";
import { filterPublications, formatDate, INITIAL_FILTERS, PAGE_SIZE, postImages, type Post, type PublicationFilters, type SchoolClass } from "./model";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const failure = (error: unknown) => error instanceof Error ? error.message : "Não foi possível concluir. Tente novamente.";
async function responseData(response: Response) {
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Não foi possível carregar as publicações.");
  return data;
}

export default function PublicationsWorkspace() {
  const { user, token, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const classFilter = params.get("class_id") ?? "";
  const headers = useMemo(() => ({ Authorization: "Bearer " + token, "Content-Type": "application/json" }), [token]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [filters, setFilters] = useState<PublicationFilters>(INITIAL_FILTERS);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<"create" | "edit" | "delete" | null>(null);
  const [target, setTarget] = useState<Post | null>(null);
  const [selected, setSelected] = useState<Post | null>(null);
  const [detail, setDetail] = useState<Post | null>(null);
  const [detailError, setDetailError] = useState("");
  const [saving, setSaving] = useState(false);
  const [opening, setOpening] = useState(false);
  const operation = useRef<AbortController | null>(null);
  const listOperation = useRef<AbortController | null>(null);
  const load = useCallback(async (signal: AbortSignal) => {
    setLoading(true); setError("");
    try {
      const [postData, classData] = await Promise.all([
        fetch(API_URL + "/api/posts/" + (classFilter ? "?class_id=" + encodeURIComponent(classFilter) : ""), { headers, signal }).then(responseData),
        fetch(API_URL + "/api/classes/" + (user?.role === "COORDENADOR" ? "?include_inactive=true" : ""), { headers, signal }).then(responseData),
      ]);
      if (!signal.aborted) { setPosts(postData); setClasses(classData); }
    } catch (reason) { if (!signal.aborted) { setPosts([]); setError(failure(reason)); } }
    finally { if (!signal.aborted) setLoading(false); }
  }, [classFilter, headers, user]);
  useEffect(() => {
    if (authLoading || !user || !token) return;
    if (user.role === "MARKETING") { router.replace("/marketing"); return; }
    const controller = new AbortController(); listOperation.current = controller;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => { controller.abort(); listOperation.current?.abort(); operation.current?.abort(); };
  }, [authLoading, load, router, token, user]);

  function refresh() {
    listOperation.current?.abort();
    const controller = new AbortController(); listOperation.current = controller;
    void load(controller.signal);
  }
  function closeDetails() {
    operation.current?.abort(); setSelected(null); setDetail(null); setDetailError(""); setOpening(false);
  }
  async function open(post: Post, action: PublicationAction) {
    operation.current?.abort();
    const controller = new AbortController(); operation.current = controller;
    setOpening(true); setError(""); setMessage(""); setDetailError("");
    if (action === "view") { setSelected(post); setDetail(null); }
    try {
      const result: Post = await fetch(API_URL + "/api/posts/" + post.id, { headers, signal: controller.signal }).then(responseData);
      if (controller.signal.aborted) return;
      if (action === "view") setDetail(result);
      else if (result.can_manage) { setTarget(result); setMode(action); }
      else throw new Error("Você não tem permissão para alterar esta publicação.");
    } catch (reason) {
      if (!controller.signal.aborted) { if (action === "view" || selected) setDetailError(failure(reason)); else setError(failure(reason)); }
    } finally { if (!controller.signal.aborted) setOpening(false); }
  }
  function done(text: string) {
    setSaving(false); setMode(null); setTarget(null); setSelected(null); setDetail(null); setMessage(text); refresh();
  }
  async function remove() {
    if (!target?.can_manage || saving) return;
    const controller = new AbortController(); operation.current = controller;
    setSaving(true); setError("");
    try {
      const response = await fetch(API_URL + "/api/posts/" + target.id, { method: "DELETE", headers, signal: controller.signal });
      if (!response.ok) await responseData(response);
      if (!controller.signal.aborted) done("Publicação excluída. As fotos foram preservadas.");
    } catch (reason) { if (!controller.signal.aborted) setError(failure(reason)); }
    finally { if (!controller.signal.aborted) setSaving(false); }
  }
  function create() { setTarget(null); setMode("create"); setError(""); setMessage(""); }
  function updateFilters(change: Partial<PublicationFilters>) { setFilters((current) => ({ ...current, ...change })); setLimit(PAGE_SIZE); }
  function clearFilters() { setFilters(INITIAL_FILTERS); setLimit(PAGE_SIZE); router.replace("/publications", { scroll: false }); }
  const filtered = useMemo(() => filterPublications(posts, filters), [posts, filters]);
  const hasFilters = !!classFilter || !!filters.search.trim() || filters.date !== "all";
  const invalidRange = filters.date === "custom" && !!filters.from && !!filters.to && filters.from > filters.to;
  const canCreate = classes.some((item) => item.is_active);
  const listFailed = !!error && !posts.length;
  if (authLoading || !user || user.role === "MARKETING") return <div role="status" aria-label="Carregando" className="grid min-h-64 place-items-center"><LoaderCircle className="h-7 w-7 animate-spin text-blue-600" /></div>;
  return <div className="min-h-screen bg-[#f5f7fb] text-slate-900">
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          {user.role === "COORDENADOR" && <Link aria-label="Voltar ao painel" href="/admin" className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600"><ArrowLeft className="h-5 w-5" /></Link>}
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-blue-600 text-white"><GraduationCap className="h-5 w-5" /></span>
          <div className="min-w-0"><p className="truncate font-semibold">{user.school.name}</p><p className="text-xs text-slate-600">{user.role === "PROFESSOR" ? "Área do professor" : "Painel da coordenação"}</p></div>
        </div>
        <span className="max-w-32 truncate text-xs text-slate-600 sm:max-w-64 sm:text-sm" title={user.name}>{user.name}</span>
      </div>
    </header>
    {user.role === "PROFESSOR" && <TeacherNavigation current="publications" />}
    <main className="mx-auto max-w-6xl px-4 pb-16 pt-8 sm:px-5 sm:pt-10">

      {message && <p role="status" className="mb-5 flex items-center gap-2 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-800"><CheckCircle2 className="h-5 w-5 shrink-0" />{message}</p>}
      {error && !mode && <div role="alert" className="mb-5 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">{error}<button onClick={refresh} className="ml-3 min-h-9 font-medium underline underline-offset-2">Tentar novamente</button></div>}

      <section aria-label="Filtros das publicações">
        <div className="grid min-w-0 grid-cols-2 gap-3 lg:grid-cols-[minmax(0,1fr)_200px_180px_172px_auto]">
          <label className="relative col-span-2 min-w-0 lg:col-span-1">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-500"
              strokeWidth={1.5}
            />
            <input
              aria-label="Buscar publicação"
              type="search"
              className="input min-h-11 w-full text-sm"
              style={{ paddingLeft: "2.25rem" }}
              placeholder="Buscar publicação..."
              value={filters.search}
              onChange={(event) => updateFilters({ search: event.target.value })}
            />
          </label>

          <select
            aria-label="Filtrar por turma"
            className="input min-h-11 w-full min-w-0 text-sm"
            value={classFilter}
            onChange={(event) => {
              setLimit(PAGE_SIZE);
              closeDetails();
              router.replace(
                event.target.value
                  ? "/publications?class_id=" + event.target.value
                  : "/publications",
                { scroll: false }
              );
            }}
          >
            <option value="">Todas as turmas</option>
            {classes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.year}
                {item.is_active ? "" : " (inativa)"}
              </option>
            ))}
          </select>

          <select
            aria-label="Filtrar por data"
            className="input min-h-11 w-full min-w-0 text-sm"
            value={filters.date}
            onChange={(event) =>
              updateFilters({
                date: event.target.value as PublicationFilters["date"],
              })
            }
          >
            <option value="all">Todas as datas</option>
            <option value="today">Hoje</option>
            <option value="week">Últimos 7 dias</option>
            <option value="month">Este mês</option>
            <option value="custom">Período personalizado</option>
          </select>

          <select
            aria-label="Ordenar publicações"
            className="input min-h-11 w-full min-w-0 text-sm"
            value={filters.sort}
            onChange={(event) =>
              updateFilters({
                sort: event.target.value as PublicationFilters["sort"],
              })
            }
          >
            <option value="newest">Mais recentes</option>
            <option value="oldest">Mais antigas</option>
          </select>

          <button
            disabled={loading || opening || !canCreate}
            onClick={create}
            className="col-span-2 inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-not-allowed disabled:opacity-50 lg:col-span-1"
          >
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            Nova publicação
          </button>
        </div>
        {filters.date === "custom" && <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="min-w-0 flex-1 text-xs text-slate-600 sm:max-w-48">De<input type="date" aria-label="Data inicial" value={filters.from} onChange={(event) => updateFilters({ from: event.target.value })} className="input mt-1 min-h-11 w-full min-w-0 text-sm" /></label>
          <label className="min-w-0 flex-1 text-xs text-slate-600 sm:max-w-48">Até<input type="date" aria-label="Data final" min={filters.from || undefined} value={filters.to} onChange={(event) => updateFilters({ to: event.target.value })} className="input mt-1 min-h-11 w-full min-w-0 text-sm" /></label>
          {invalidRange && <p role="alert" className="w-full text-sm text-red-700">A data final deve ser igual ou posterior à inicial.</p>}
        </div>}
        <div className="flex min-h-12 items-center justify-between gap-3 py-3">
          <p aria-live="polite" className="text-xs text-slate-500">{loading ? "Carregando publicações..." : listFailed ? "Não foi possível carregar a lista" : filtered.length + (filtered.length === 1 ? " publicação encontrada" : " publicações encontradas")}</p>
          {hasFilters && <button onClick={clearFilters} className="inline-flex min-h-8 items-center gap-1.5 rounded text-xs font-medium text-slate-600 hover:text-blue-700 focus-visible:outline-2 focus-visible:outline-blue-600"><X className="h-3.5 w-3.5" />Limpar filtros</button>}
        </div>
      </section>

      <section aria-label="Lista de publicações" aria-busy={loading} className="rounded-xl border border-slate-200 bg-white">
        {loading ? <div role="status" aria-label="Carregando publicações" className="divide-y divide-slate-100">{[0, 1, 2].map((item) => <div key={item} className="flex h-[136px] animate-pulse items-center gap-4 px-4 motion-reduce:animate-none"><div className="h-[88px] w-[88px] shrink-0 rounded-lg bg-slate-100" /><div className="flex-1 space-y-3"><div className="h-3 w-24 rounded bg-slate-100" /><div className="h-4 w-2/3 rounded bg-slate-100" /><div className="h-3 w-1/2 rounded bg-slate-100" /></div></div>)}</div> : listFailed ? <div className="px-5 py-12 text-center text-sm text-slate-500">Suas publicações aparecerão aqui após tentar novamente.</div> : !filtered.length ? <div className="px-6 py-14 text-center"><Images aria-hidden="true" className="mx-auto h-7 w-7 text-slate-400" strokeWidth={1.5} /><h2 className="mt-4 text-base font-medium">{hasFilters ? "Nenhuma publicação encontrada" : "Ainda não há publicações"}</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">{hasFilters ? "Ajuste a busca ou os filtros para encontrar outros momentos." : canCreate ? "Compartilhe as fotos de uma atividade com as famílias dos seus alunos." : "Quando houver uma turma disponível, você poderá compartilhar momentos com as famílias."}</p>{hasFilters ? <button onClick={clearFilters} className="mt-4 min-h-10 text-sm font-medium text-blue-700 underline underline-offset-4">Limpar filtros</button> : canCreate && <button onClick={create} className="mt-4 min-h-10 text-sm font-medium text-blue-700 underline underline-offset-4">Criar primeira publicação</button>}</div> : <ul className="divide-y divide-slate-100">{filtered.slice(0, limit).map((post) => <li key={post.id} className={"relative flex h-[136px] items-center gap-3 px-3 transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-slate-50 sm:gap-4 sm:px-4 " + (selected?.id === post.id ? "bg-blue-50 ring-1 ring-inset ring-blue-200" : "")}>
          <button type="button" aria-label={"Ver publicação: " + post.caption} aria-haspopup="dialog" aria-expanded={selected?.id === post.id} onClick={() => void open(post, "view")} className="absolute inset-0 z-0 cursor-pointer rounded-lg focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-blue-600" />
          <div className="pointer-events-none relative h-20 w-20 shrink-0 overflow-hidden rounded-lg bg-slate-100 sm:h-[88px] sm:w-[88px]"><PublicationImage src={post.image_url} alt="Capa da publicação" />{postImages(post).length > 1 && <span className="absolute bottom-1.5 right-1.5 inline-flex items-center gap-1 rounded bg-slate-950/75 px-1.5 py-0.5 text-[11px] font-medium text-white"><Layers3 className="h-3 w-3" />{postImages(post).length}</span>}</div>
          <div className="pointer-events-none relative min-w-0 flex-1">
            <div className="mb-1 flex min-w-0 items-center gap-2 text-[11px] text-slate-500"><span className="max-w-full truncate rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-600 sm:max-w-48">{post.classroom_name}</span><time className="hidden shrink-0 sm:block" dateTime={post.created_at}>{formatDate(post.created_at)}</time></div>
            <p className="line-clamp-2 min-h-10 whitespace-pre-wrap break-words text-sm font-medium leading-5 text-slate-900">{post.caption}</p>
            <p className="mt-1 truncate text-xs leading-4 text-slate-500"><span className="sm:hidden">{formatDate(post.created_at)} · </span>{post.teacher_name}</p>
            <p className="mt-1 flex min-w-0 items-center gap-1.5 text-xs leading-4 text-slate-500"><UsersRound aria-hidden="true" className="h-3 w-3 shrink-0" /><span className="truncate">{post.child_names.join(", ") || "Sem alunos vinculados"}</span></p>
          </div>
          <div className="relative z-10 pt-3"><PublicationActions canManage={post.can_manage} label={"Ações da publicação: " + post.caption.slice(0, 60)} onAction={(action) => void open(post, action)} /></div>
        </li>)}</ul>}
        {!loading && filtered.length > limit && <div className="border-t border-slate-200 px-4 py-4 text-center"><p className="mb-2 text-xs text-slate-500">{Math.min(limit, filtered.length)} de {filtered.length} publicações</p><button type="button" onClick={() => setLimit((value) => value + PAGE_SIZE)} className="min-h-11 rounded-lg border border-slate-300 px-4 text-sm font-medium text-slate-700 hover:bg-slate-50">Carregar mais</button></div>}
      </section>
      {opening && !selected && <p role="status" className="mt-3 flex items-center gap-2 text-sm text-slate-600"><LoaderCircle className="h-4 w-4 animate-spin" />Abrindo publicação...</p>}
      {selected && !mode && <PublicationDrawer post={detail} loading={opening} error={detailError} onClose={closeDetails} onRetry={() => void open(selected, "view")} onAction={(action) => void open(detail ?? selected, action)} />}
      {(mode === "create" || mode === "edit") && <PublicationEditor key={target?.id ?? "new"} post={target} classes={classes} initialClass={classFilter} headers={headers} onClose={() => setMode(null)} onDone={done} />}
      {mode === "delete" && target && <Modal title="Excluir publicação?" busy={saving} onClose={() => setMode(null)}><p className="mb-5 text-sm leading-6 text-slate-600">Esta publicação será removida do aplicativo das famílias. As fotos continuarão na biblioteca da escola.</p>{error && <p role="alert" className="mb-4 text-sm text-red-700">{error}</p>}<div className="flex justify-end gap-3"><button disabled={saving} onClick={() => setMode(null)} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm">Cancelar</button><button disabled={saving} onClick={() => void remove()} className="flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50">{saving && <LoaderCircle className="h-4 w-4 animate-spin" />}Excluir publicação</button></div></Modal>}
    </main>
  </div>;
}
