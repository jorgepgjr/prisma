"use client";
import { useEffect, useRef, useState } from "react";
import { Eye, LoaderCircle, Send } from "lucide-react";
import Modal from "../components/Modal";
import Image, { mediaUrl } from "./PublicationImage";
import type { Post, SchoolClass } from "./model";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Photo = { id: number; media_url: string; publication_count: number; title?: string };
type Student = { id: number; name: string; child_id: string | null };
const failure = (error: unknown) => error instanceof Error ? error.message : "Não foi possível concluir. Tente novamente.";
async function responseData(response: Response) {
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Confira os campos e tente novamente.");
  return data;
}


function Loading() { return <div className="grid min-h-64 place-items-center" role="status" aria-label="Carregando"><LoaderCircle className="h-7 w-7 animate-spin text-blue-600" /></div>; }
export default function PublicationEditor({ post, classes, initialClass, headers, onClose, onDone }: {
  post: Post | null; classes: SchoolClass[]; initialClass: string; headers: Record<string, string>;
  onClose: () => void; onDone: (message: string) => void;
}) {
  const [classId, setClassId] = useState(post?.class_id?.toString() ?? (classes.some((item) => item.is_active && String(item.id) === initialClass) ? initialClass : ""));
  const [caption, setCaption] = useState(post?.caption ?? "");
  const [photoIds, setPhotoIds] = useState<number[]>(post?.photo_ids ?? []);
  const [studentIds, setStudentIds] = useState<number[]>(post?.student_ids ?? []);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const operation = useRef<AbortController | null>(null);
  const submitting = useRef(false);
  useEffect(() => {
    if (!classId) return;
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError("");
      try {
        const [photoData, studentData] = await Promise.all([
          fetch(`${API_URL}/api/photos/class/${classId}`, { headers, signal: controller.signal }).then(responseData),
          fetch(`${API_URL}/api/students/class/${classId}`, { headers, signal: controller.signal }).then(responseData),
        ]);
        if (!controller.signal.aborted) { setPhotos(photoData); setStudents(studentData); }
      } catch (reason) { if (!controller.signal.aborted) { setPhotos([]); setStudents([]); setError(failure(reason)); } }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [classId, headers, retry]);
  useEffect(() => () => operation.current?.abort(), []);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setSaving(true); setError("");
    const controller = new AbortController(); operation.current = controller;
    try {
      await fetch(`${API_URL}/api/posts/${post ? post.id : ""}`, { method: post ? "PUT" : "POST", headers,
        signal: controller.signal, body: JSON.stringify({ caption, photo_ids: photoIds, student_ids: studentIds }) }).then(responseData);
      if (!controller.signal.aborted) onDone(post ? "Publicação atualizada para as famílias." : "Publicação enviada às famílias.");
    } catch (reason) { if (!controller.signal.aborted) setError(failure(reason)); }
    finally { submitting.current = false; if (!controller.signal.aborted) setSaving(false); }
  }
  const valid = classId && caption.trim() && photoIds.length && studentIds.length && !loading &&
    photoIds.every((id) => photos.some((photo) => photo.id === id)) &&
    studentIds.every((id) => students.some((student) => student.id === id && student.child_id));
  const mismatch = !loading && (photoIds.some((id) => !photos.some((photo) => photo.id === id)) || studentIds.some((id) => !students.some((student) => student.id === id && student.child_id)));
  return <Modal title={post ? "Editar publicação" : "Nova publicação"} busy={saving} onClose={onClose}><form onSubmit={(event) => void save(event)} className="space-y-5">
    <p className="-mt-2 text-sm leading-6 text-slate-600">Escolha as fotos e os alunos que poderão ver este momento no aplicativo.</p>
    <label className="block text-sm font-medium">Turma<select required disabled={saving || !!post?.class_id} className="input mt-1 w-full disabled:bg-slate-100" value={classId} onChange={(event) => { setClassId(event.target.value); setPhotos([]); setStudents([]); setPhotoIds([]); setStudentIds([]); }}><option value="">Selecione uma turma</option>{classes.filter((item) => item.is_active || item.id === post?.class_id).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.year}</option>)}</select></label>
    {post && !post.class_id && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Publicação antiga sem turma identificada. Selecione a turma para regularizar seus vínculos.</p>}
    <label className="block text-sm font-medium">Legenda<textarea required disabled={saving} value={caption} onChange={(event) => setCaption(event.target.value)} rows={3} placeholder="Conte o que aconteceu nesta atividade..." className="input mt-1 w-full resize-y" /></label>
    {error && <div role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}{!photos.length && classId && <button type="button" onClick={() => setRetry((value) => value + 1)} className="ml-2 underline">Tentar carregar novamente</button>}</div>}
    {loading ? <Loading /> : classId && <>
      {mismatch && <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Há fotos ou alunos indisponíveis nesta turma. Revise a seleção para salvar.<button type="button" disabled={saving} className="mt-2 block font-semibold underline" onClick={() => { setPhotoIds(photoIds.filter((id) => photos.some((photo) => photo.id === id))); setStudentIds(studentIds.filter((id) => students.some((student) => student.id === id && student.child_id))); }}>Remover indisponíveis da seleção</button></div>}
      <fieldset disabled={saving}><legend className="mb-2 text-sm font-medium">Fotos · {photoIds.length} selecionadas</legend><p className="mb-3 text-xs text-slate-500">A primeira foto selecionada será a capa. Use o ícone de ampliar para conferir cada imagem.</p>{!photos.length ? <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Nenhuma foto nesta turma. Envie fotos pelo aplicativo antes de publicar.</p> : <div className="grid max-h-72 grid-cols-3 gap-2 overflow-y-auto">{photos.map((photo) => <div key={photo.id} className={`relative overflow-hidden rounded-xl border-2 ${photoIds.includes(photo.id) ? "border-blue-600" : "border-slate-100"}`}><label className="relative block aspect-square cursor-pointer"><Image src={mediaUrl(photo.media_url)} alt={photo.title ?? `Foto ${photo.id}`} fill unoptimized className="object-cover" /><input aria-label={`Selecionar foto ${photo.id}`} type="checkbox" checked={photoIds.includes(photo.id)} onChange={() => setPhotoIds((ids) => ids.includes(photo.id) ? ids.filter((id) => id !== photo.id) : [...ids, photo.id])} className="absolute left-2 top-2 h-5 w-5 accent-blue-600" />{photoIds[0] === photo.id && <span className="absolute bottom-1 left-1 rounded bg-blue-600 px-1.5 text-[10px] text-white">Capa</span>}</label><a href={mediaUrl(photo.media_url)} target="_blank" rel="noopener noreferrer" aria-label={`Ampliar foto ${photo.id}`} className="absolute right-1 top-1 rounded bg-white/95 p-1 text-slate-700"><Eye className="h-4 w-4" /></a>{photo.publication_count > 0 && <span className="block px-1 py-1 text-center text-[10px] text-blue-700">Em publicação</span>}</div>)}</div>}</fieldset>
      <fieldset disabled={saving}><legend className="mb-2 text-sm font-medium">Alunos destinatários · {studentIds.length}</legend><div className="max-h-48 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-2">{!students.length && <p className="p-3 text-sm text-slate-500">Nenhum aluno ativo nesta turma.</p>}{students.map((student) => <label key={student.id} className={`flex items-center gap-3 rounded-lg p-2 text-sm ${student.child_id ? "cursor-pointer hover:bg-slate-50" : "text-slate-400"}`}><input type="checkbox" disabled={!student.child_id} checked={studentIds.includes(student.id)} onChange={() => setStudentIds((ids) => ids.includes(student.id) ? ids.filter((id) => id !== student.id) : [...ids, student.id])} /><span>{student.name}{!student.child_id && <small className="ml-2">Sem perfil familiar — procure a coordenação</small>}</span></label>)}</div></fieldset>
    </>}
    <p className="text-xs leading-5 text-slate-500">{post ? "As alterações serão exibidas às famílias dos alunos selecionados na próxima atualização do aplicativo." : "A publicação ficará disponível diretamente para as famílias dos alunos selecionados."}</p>
    <div className="flex justify-end gap-3"><button type="button" disabled={saving} onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm">Cancelar</button><button disabled={saving || !valid} className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}{post ? "Salvar alterações" : "Publicar para as famílias"}</button></div>
  </form></Modal>;
}
