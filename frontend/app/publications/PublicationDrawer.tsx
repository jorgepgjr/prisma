"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Expand, ImageIcon, LoaderCircle, X } from "lucide-react";
import PublicationActions, { type PublicationAction } from "./PublicationActions";
import PublicationImage from "./PublicationImage";
import { formatDate, postImages, type Post } from "./model";
import styles from "./publications.module.css";

function Dialog({ children, titleId, onClose, viewer = false }: { children: ReactNode; titleId: string; onClose: () => void; viewer?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog?.showModal();
    return () => { dialog?.close(); document.body.style.overflow = overflow; opener?.focus({ preventScroll: true }); };
  }, []);
  return <dialog ref={ref} aria-labelledby={titleId} aria-modal="true" className={`${styles.drawer} ${viewer ? styles.viewer : ""}`}
    onCancel={(event) => { event.preventDefault(); onClose(); }} onClick={(event) => {
      if (event.target === event.currentTarget && event.clientX < event.currentTarget.getBoundingClientRect().left) onClose();
    }}>{children}</dialog>;
}

function Carousel({ post }: { post: Post }) {
  const urls = postImages(post);
  const [index, setIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const titleId = useId();
  const photo = urls[index];
  const navigation = <div className="flex items-center justify-between gap-3 py-3">
    <button type="button" aria-label="Foto anterior" disabled={index === 0} onClick={() => setIndex(index - 1)} className="grid h-10 w-10 place-items-center rounded-lg border border-current/15 disabled:opacity-30"><ChevronLeft className="h-5 w-5" /></button>
    <span role="status" className="text-sm tabular-nums">{index + 1} de {urls.length}</span>
    <button type="button" aria-label="Próxima foto" disabled={index >= urls.length - 1} onClick={() => setIndex(index + 1)} className="grid h-10 w-10 place-items-center rounded-lg border border-current/15 disabled:opacity-30"><ChevronRight className="h-5 w-5" /></button>
  </div>;
  if (!urls.length) return <div className="grid aspect-[4/3] place-content-center gap-2 rounded-xl bg-slate-100 text-center text-sm text-slate-500"><ImageIcon className="mx-auto h-6 w-6" />Nenhuma foto disponível</div>;
  return <section aria-label="Fotografias da publicação">
    <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-slate-100">
      <PublicationImage key={photo} src={photo} alt={`Foto ${index + 1} da publicação`} className="object-contain" />
      <button type="button" onClick={() => setExpanded(true)} aria-label="Ampliar fotografia" className="absolute bottom-3 right-3 grid h-10 w-10 place-items-center rounded-lg bg-white/95 text-slate-700 shadow-sm hover:bg-white focus-visible:outline-2 focus-visible:outline-blue-600"><Expand className="h-4 w-4" /></button>
    </div>
    {navigation}
    {expanded && <Dialog titleId={titleId} onClose={() => setExpanded(false)} viewer>
      <header className="flex shrink-0 items-center justify-between gap-4 p-4"><h3 id={titleId} className="text-sm">Fotografias da publicação</h3><button type="button" aria-label="Fechar fotografia ampliada" onClick={() => setExpanded(false)} className="grid h-11 w-11 place-items-center rounded-lg hover:bg-white/10"><X className="h-5 w-5" /></button></header>
      <div className="relative min-h-0 flex-1"><PublicationImage key={photo} src={photo} alt={`Foto ampliada ${index + 1}`} className="object-contain" /></div>
      <div className="mx-auto w-full max-w-lg px-5 pb-[max(16px,env(safe-area-inset-bottom))]">{navigation}</div>
    </Dialog>}
  </section>;
}

export default function PublicationDrawer({ post, loading, error, onClose, onRetry, onAction }: {
  post: Post | null; loading: boolean; error: string; onClose: () => void; onRetry: () => void; onAction: (action: PublicationAction) => void;
}) {
  const heading = useId();
  return <Dialog titleId={heading} onClose={onClose}>
    <header className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-5 py-4 sm:px-6">
      <div className="min-w-0"><h2 id={heading} className="text-lg font-semibold">Publicação</h2><p className="mt-1 truncate text-sm text-slate-600">{post?.classroom_name ?? "Detalhes do momento compartilhado"}</p>{post && <p className="mt-1 text-xs text-slate-500">{formatDate(post.created_at, true)}</p>}</div>
      <div className="flex shrink-0 gap-1">{post && <PublicationActions canManage={post.can_manage} showView={false} onAction={onAction} />}<button type="button" onClick={onClose} aria-label="Fechar publicação" className="grid h-10 w-10 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-blue-600"><X className="h-5 w-5" /></button></div>
    </header>
    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 sm:px-6">
      {loading ? <div role="status" aria-label="Carregando publicação" className="grid min-h-64 place-items-center"><LoaderCircle className="h-6 w-6 animate-spin text-blue-600" /></div> : error ? <div role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-800"><p>{error}</p><button type="button" onClick={onRetry} className="mt-3 min-h-10 font-medium underline underline-offset-4">Tentar novamente</button></div> : post && <>
        <Carousel key={post.id} post={post} />
        <section aria-label="Legenda completa" className="border-t border-slate-200 py-6"><p className="whitespace-pre-wrap break-words text-[15px] leading-7 text-slate-900">{post.caption}</p></section>
        <section aria-label="Informações da publicação" className="border-t border-slate-200 pt-5"><h3 className="mb-4 text-sm font-medium">Informações</h3>
          <dl className="grid grid-cols-[88px_minmax(0,1fr)] gap-x-4 gap-y-4 text-sm leading-6">
            <dt className="text-slate-500">Turma</dt><dd className="break-words">{post.classroom_name}</dd>
            <dt className="text-slate-500">Publicada em</dt><dd>{formatDate(post.created_at, true)}</dd>
            <dt className="text-slate-500">Professor</dt><dd className="break-words">{post.teacher_name}</dd>
            <dt className="text-slate-500">Alunos</dt><dd className="break-words">{post.child_names.join(", ") || "Sem alunos vinculados"}</dd>
          </dl>
        </section>
      </>}
    </div>
  </Dialog>;
}
