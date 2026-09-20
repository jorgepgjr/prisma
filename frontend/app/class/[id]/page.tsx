"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft, CalendarDays, Check, CheckCircle2, FileImage, ImageIcon, Info,
  Layers3, LoaderCircle, Send, Tag as TagIcon, UserRoundCheck, X,
} from "lucide-react";
import { useAuth } from "../../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Tag = { id: number; name: string };
type Photo = {
  id: number; file_path: string; title?: string; description?: string;
  uploader_name?: string; created_at: string; student_ids: number[]; tags: Tag[];
};
type Student = { id: number; name: string; child_id?: string | null };
type FamilyChild = {
  id: string; name: string; classroom: string; parent_names: string[];
  parent_emails: string[]; linked_student_id?: number | null;
};
type ManagedPost = {
  id: string; image_url: string; image_urls: string[]; caption: string;
  teacher_name: string; child_names: string[]; created_at: string;
};
type ModalKind = "post" | "portfolio" | "family" | null;

function detailFrom(data: unknown, fallback: string) {
  if (typeof data === "object" && data && "detail" in data && typeof data.detail === "string") return data.detail;
  return fallback;
}

function photoUrl(photo: Photo) {
  return `${API_URL}/api/photos/file/${encodeURIComponent(photo.file_path)}`;
}

function signedUrl(value: string) {
  return value.startsWith("http") ? value : `${API_URL}${value}`;
}

function monthKey(date: string) {
  const value = new Date(date);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(date: string) {
  const label = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(new Date(date));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

export default function ClassPage() {
  const params = useParams<{ id: string }>();
  const classId = Number(params.id);
  const { token } = useAuth();
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [photos, setPhotos] = useState<Photo[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [posts, setPosts] = useState<ManagedPost[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [families, setFamilies] = useState<FamilyChild[]>([]);
  const [activePhotoId, setActivePhotoId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedStudents, setSelectedStudents] = useState<number[]>([]);
  const [selectionMode, setSelectionMode] = useState(false);
  const [groupByMonth, setGroupByMonth] = useState(true);
  const [studentFilter, setStudentFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [modal, setModal] = useState<ModalKind>(null);
  const [familyStudent, setFamilyStudent] = useState<Student | null>(null);
  const [familyChildId, setFamilyChildId] = useState("");
  const [caption, setCaption] = useState("");
  const [portfolioTitle, setPortfolioTitle] = useState("");
  const [portfolioDescription, setPortfolioDescription] = useState("");
  const [objectives, setObjectives] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    if (!token || !Number.isFinite(classId)) return;
    setLoading(true);
    setError("");
    try {
      const responses = await Promise.all([
        fetch(`${API_URL}/api/photos/class/${classId}`, { headers }),
        fetch(`${API_URL}/api/students/class/${classId}`, { headers }),
        fetch(`${API_URL}/api/posts/?class_id=${classId}`, { headers }),
        fetch(`${API_URL}/api/tags/`, { headers }),
        fetch(`${API_URL}/api/families/children`, { headers }),
      ]);
      if (responses.some((response) => !response.ok)) throw new Error("Não foi possível carregar os dados da turma.");
      const [photoData, studentData, postData, tagData, familyData] = await Promise.all(responses.map((response) => response.json()));
      setPhotos(photoData);
      setStudents(studentData);
      setPosts(postData);
      setTags(tagData);
      setFamilies(familyData);
      setActivePhotoId((current) => current ?? photoData[0]?.id ?? null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro ao carregar a turma.");
    } finally {
      setLoading(false);
    }
  }, [classId, headers, token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData();
  }, [loadData]);

  const filteredPhotos = useMemo(() => photos.filter((photo) => {
    const created = new Date(photo.created_at);
    if (studentFilter && !photo.student_ids.includes(Number(studentFilter))) return false;
    if (tagFilter && !photo.tags.some((tag) => tag.id === Number(tagFilter))) return false;
    if (dateFrom && created < new Date(`${dateFrom}T00:00:00`)) return false;
    if (dateTo && created > new Date(`${dateTo}T23:59:59`)) return false;
    return true;
  }), [dateFrom, dateTo, photos, studentFilter, tagFilter]);

  const groups = useMemo(() => {
    if (!groupByMonth) return [["Todas as fotos", filteredPhotos]] as [string, Photo[]][];
    const values = new Map<string, Photo[]>();
    filteredPhotos.forEach((photo) => {
      const key = monthKey(photo.created_at);
      values.set(key, [...(values.get(key) ?? []), photo]);
    });
    return [...values.entries()].map(([, items]) => [monthLabel(items[0].created_at), items] as [string, Photo[]]);
  }, [filteredPhotos, groupByMonth]);

  const activePhoto = photos.find((photo) => photo.id === activePhotoId) ?? null;
  const actionPhotoIds = selectedIds.length ? selectedIds : activePhoto ? [activePhoto.id] : [];

  function selectPhoto(photo: Photo) {
    setActivePhotoId(photo.id);
    if (selectionMode) {
      setSelectedIds((current) => current.includes(photo.id) ? current.filter((id) => id !== photo.id) : [...current, photo.id]);
    }
  }

  function toggleStudent(studentId: number) {
    setSelectedStudents((current) => current.includes(studentId) ? current.filter((id) => id !== studentId) : [...current, studentId]);
  }

  function openAction(kind: "post" | "portfolio") {
    if (!actionPhotoIds.length) {
      setError("Selecione ao menos uma foto.");
      return;
    }
    setError("");
    setSelectedStudents([]);
    setModal(kind);
  }

  async function savePost() {
    await save(`${API_URL}/api/posts/`, { photo_ids: actionPhotoIds, caption, student_ids: selectedStudents }, "Publicação enviada às famílias.");
  }

  async function savePortfolio() {
    await save(`${API_URL}/api/portfolio/`, {
      photo_ids: actionPhotoIds,
      student_ids: selectedStudents,
      title: portfolioTitle,
      description: portfolioDescription,
      pedagogical_objectives: objectives.split("\n").map((value) => value.trim()).filter(Boolean),
    }, "Portfólio criado para os alunos selecionados.");
  }

  async function save(url: string, body: object, success: string) {
    setSaving(true);
    setError("");
    try {
      const response = await fetch(url, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) throw new Error(detailFrom(data, "Não foi possível concluir a operação."));
      setMessage(success);
      setModal(null);
      setCaption(""); setPortfolioTitle(""); setPortfolioDescription(""); setObjectives("");
      setSelectedIds([]); setSelectionMode(false);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível concluir a operação.");
    } finally {
      setSaving(false);
    }
  }

  async function updateTag(tagId: number, remove: boolean) {
    if (!activePhoto) return;
    const response = await fetch(`${API_URL}/api/photos/${activePhoto.id}/tags/${tagId}`, { method: remove ? "DELETE" : "POST", headers });
    if (!response.ok) {
      const data = await response.json();
      setError(detailFrom(data, "Não foi possível atualizar a tag."));
      return;
    }
    await loadData();
  }

  function openFamily(student: Student) {
    setFamilyStudent(student);
    setFamilyChildId(student.child_id ?? "");
    setModal("family");
  }

  async function saveFamilyLink() {
    if (!familyStudent) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/families/students/${familyStudent.id}`, {
        method: "PUT", headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ child_id: familyChildId || null }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(detailFrom(data, "Não foi possível salvar o vínculo."));
      setMessage(`${familyStudent.name} foi vinculado ao perfil familiar.`);
      setModal(null);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível salvar o vínculo.");
    } finally {
      setSaving(false);
    }
  }

  async function createFamilyProfile(payload: { parent_name: string; parent_email: string; parent_phone: string; initial_password: string }) {
    if (!familyStudent) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/families/students/${familyStudent.id}`, {
        method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(detailFrom(data, "Não foi possível cadastrar a família."));
      setMessage(`Responsável cadastrado e vinculado a ${familyStudent.name}.`);
      setModal(null);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível cadastrar a família.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] items-center gap-4 px-5 py-4">
          <Link href="/" className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100"><ArrowLeft className="h-5 w-5" /></Link>
          <div><h1 className="font-semibold">Fotos e publicações</h1><p className="text-xs text-slate-500">Turma #{classId}</p></div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-5 py-6">
        {error && <div className="mb-4 flex items-start justify-between rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"><span>{error}</span><button onClick={() => setError("")}><X className="h-4 w-4" /></button></div>}
        {message && <div className="mb-4 flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"><CheckCircle2 className="h-5 w-5" />{message}</div>}

        {loading ? <div className="grid min-h-[480px] place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></div> : (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
            <section className="space-y-5">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div><h2 className="font-semibold">Biblioteca de fotos</h2><p className="text-sm text-slate-500">{filteredPhotos.length} de {photos.length} fotos</p></div>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => { setSelectionMode((value) => !value); setSelectedIds([]); }} className={`rounded-lg border px-3 py-2 text-sm font-medium ${selectionMode ? "border-blue-600 bg-blue-50 text-blue-700" : "border-slate-300 hover:bg-slate-50"}`}><Check className="mr-1.5 inline h-4 w-4" />{selectionMode ? "Cancelar seleção" : "Selecionar várias"}</button>
                    <button onClick={() => openAction("portfolio")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-50"><FileImage className="mr-1.5 inline h-4 w-4" />Portfólio</button>
                    <button onClick={() => openAction("post")} className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"><Send className="mr-1.5 inline h-4 w-4" />Publicar{actionPhotoIds.length > 1 ? ` (${actionPhotoIds.length})` : ""}</button>
                  </div>
                </div>

                <div className="mb-5 grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-2 lg:grid-cols-5">
                  <select value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="">Todos os alunos</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name}</option>)}</select>
                  <select value={tagFilter} onChange={(event) => setTagFilter(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><option value="">Todas as tags</option>{tags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}</select>
                  <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" aria-label="Data inicial" />
                  <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" aria-label="Data final" />
                  <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"><input type="checkbox" checked={groupByMonth} onChange={(event) => setGroupByMonth(event.target.checked)} /> Agrupar por mês</label>
                </div>

                {photos.length === 0 ? <EmptyPhotos /> : filteredPhotos.length === 0 ? <p className="py-16 text-center text-sm text-slate-500">Nenhuma foto corresponde aos filtros.</p> : groups.map(([label, items]) => (
                  <div key={label} className="mb-7 last:mb-0">
                    <div className="mb-3 flex items-center gap-2"><CalendarDays className="h-4 w-4 text-slate-400" /><h3 className="text-sm font-semibold">{label}</h3><span className="text-xs text-slate-400">{items.length}</span></div>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6">
                      {items.map((photo) => {
                        const selected = selectedIds.includes(photo.id);
                        return <button key={photo.id} onClick={() => selectPhoto(photo)} className={`group relative aspect-square overflow-hidden rounded-xl border-2 bg-slate-100 ${selected ? "border-blue-600 ring-2 ring-blue-100" : activePhotoId === photo.id ? "border-slate-500" : "border-transparent"}`}>
                          <Image src={photoUrl(photo)} alt={photo.title ?? "Foto escolar"} fill unoptimized className="object-cover transition group-hover:scale-[1.02]" />
                          {selectionMode && <span className={`absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-full border-2 ${selected ? "border-blue-600 bg-blue-600 text-white" : "border-white bg-black/25 text-transparent"}`}><Check className="h-3.5 w-3.5" /></span>}
                          <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent px-2 pb-2 pt-7 text-left text-[11px] text-white">{new Date(photo.created_at).toLocaleDateString("pt-BR")}</span>
                        </button>;
                      })}
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid gap-5 lg:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h2 className="mb-3 font-semibold">Vínculos familiares</h2>
                  <div className="space-y-2">{students.map((student) => <div key={student.id} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3"><div className={`grid h-9 w-9 place-items-center rounded-full ${student.child_id ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}><UserRoundCheck className="h-4 w-4" /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{student.name}</p><p className="truncate text-xs text-slate-500">{student.child_id ? `Perfil: ${student.child_id}` : "Sem responsável vinculado"}</p></div><button onClick={() => openFamily(student)} className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs font-medium hover:bg-slate-50">{student.child_id ? "Alterar" : "Vincular"}</button></div>)}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h2 className="mb-3 font-semibold">Publicações recentes</h2>
                  {posts.length === 0 ? <p className="text-sm text-slate-500">Nenhuma publicação criada.</p> : <div className="space-y-2">{posts.slice(0, 6).map((post) => <div key={post.id} className="flex gap-3 rounded-xl border border-slate-200 p-2.5"><div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg"><Image src={signedUrl(post.image_url)} alt="Publicação" fill unoptimized className="object-cover" />{post.image_urls?.length > 1 && <span className="absolute right-1 top-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-white"><Layers3 className="mr-0.5 inline h-3 w-3" />{post.image_urls.length}</span>}</div><div className="min-w-0"><p className="line-clamp-2 text-sm">{post.caption}</p><p className="mt-1 truncate text-xs text-slate-500">{post.child_names.join(", ")}</p></div></div>)}</div>}
                </div>
              </div>
            </section>

            <PhotoDetails photo={activePhoto} students={students} tags={tags} onTag={updateTag} />
          </div>
        )}
      </main>

      {(modal === "post" || modal === "portfolio") && <ActionModal kind={modal} photos={photos.filter((photo) => actionPhotoIds.includes(photo.id))} students={students} selectedStudents={selectedStudents} onToggleStudent={toggleStudent} caption={caption} setCaption={setCaption} portfolioTitle={portfolioTitle} setPortfolioTitle={setPortfolioTitle} portfolioDescription={portfolioDescription} setPortfolioDescription={setPortfolioDescription} objectives={objectives} setObjectives={setObjectives} saving={saving} onClose={() => setModal(null)} onSave={modal === "post" ? savePost : savePortfolio} />}
      {modal === "family" && familyStudent && <FamilyModal student={familyStudent} families={families} selected={familyChildId} setSelected={setFamilyChildId} saving={saving} onClose={() => setModal(null)} onSave={saveFamilyLink} onCreate={createFamilyProfile} />}
    </div>
  );
}

function PhotoDetails({ photo, students, tags, onTag }: { photo: Photo | null; students: Student[]; tags: Tag[]; onTag: (tagId: number, remove: boolean) => void }) {
  if (!photo) return <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm"><Info className="mb-2 h-5 w-5" />Selecione uma foto para ver os detalhes.</aside>;
  const names = students.filter((student) => photo.student_ids.includes(student.id)).map((student) => student.name);
  return <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-4 shadow-sm xl:sticky xl:top-5">
    <div className="mb-3 flex items-center gap-2"><Info className="h-5 w-5 text-blue-600" /><h2 className="font-semibold">Informações da foto</h2></div>
    <div className="relative mb-4 aspect-[4/3] overflow-hidden rounded-xl bg-slate-100"><Image src={photoUrl(photo)} alt={photo.title ?? "Foto"} fill unoptimized className="object-cover" /></div>
    <dl className="space-y-3 text-sm">
      <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Data</dt><dd>{new Date(photo.created_at).toLocaleString("pt-BR")}</dd></div>
      <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Enviada por</dt><dd>{photo.uploader_name ?? "Equipe escolar"}</dd></div>
      <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Alunos</dt><dd>{names.length ? names.join(", ") : "Ainda não identificados"}</dd></div>
      {photo.description && <div><dt className="text-xs font-medium uppercase tracking-wide text-slate-400">Descrição</dt><dd>{photo.description}</dd></div>}
    </dl>
    <div className="mt-5 border-t border-slate-200 pt-4"><p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Tags</p><div className="flex flex-wrap gap-2">{tags.map((tag) => { const active = photo.tags.some((item) => item.id === tag.id); return <button key={tag.id} onClick={() => void onTag(tag.id, active)} className={`rounded-full border px-2.5 py-1 text-xs ${active ? "border-blue-300 bg-blue-50 text-blue-700" : "border-slate-300 text-slate-500 hover:bg-slate-50"}`}><TagIcon className="mr-1 inline h-3 w-3" />{tag.name}{active && <X className="ml-1 inline h-3 w-3" />}</button>; })}</div></div>
  </aside>;
}

function ActionModal(props: {
  kind: "post" | "portfolio"; photos: Photo[]; students: Student[]; selectedStudents: number[];
  onToggleStudent: (id: number) => void; caption: string; setCaption: (value: string) => void;
  portfolioTitle: string; setPortfolioTitle: (value: string) => void;
  portfolioDescription: string; setPortfolioDescription: (value: string) => void;
  objectives: string; setObjectives: (value: string) => void; saving: boolean; onClose: () => void; onSave: () => void;
}) {
  const isPost = props.kind === "post";
  const valid = props.selectedStudents.length > 0 && (isPost ? props.caption.trim() : props.portfolioTitle.trim() && props.portfolioDescription.trim());
  return <Modal title={isPost ? "Criar publicação" : "Criar portfólio"} onClose={props.onClose}>
    <div className="mb-4 flex gap-2 overflow-x-auto pb-1">{props.photos.map((photo) => <div key={photo.id} className="relative h-20 w-20 shrink-0 overflow-hidden rounded-lg"><Image src={photoUrl(photo)} alt="Selecionada" fill unoptimized className="object-cover" /></div>)}</div>
    <p className="mb-4 text-xs text-slate-500">{props.photos.length > 1 ? `${props.photos.length} fotos — será exibido como carrossel.` : "1 foto selecionada."}</p>
    {isPost ? <Field label="Legenda"><textarea value={props.caption} onChange={(event) => props.setCaption(event.target.value)} rows={4} className="input w-full resize-none" placeholder="Conte o que aconteceu nesta atividade..." /></Field> : <><Field label="Título"><input value={props.portfolioTitle} onChange={(event) => props.setPortfolioTitle(event.target.value)} className="input w-full" placeholder="Ex.: Descobrindo as cores" /></Field><Field label="Descrição"><textarea value={props.portfolioDescription} onChange={(event) => props.setPortfolioDescription(event.target.value)} rows={3} className="input w-full resize-none" /></Field><Field label="Objetivos pedagógicos (um por linha)"><textarea value={props.objectives} onChange={(event) => props.setObjectives(event.target.value)} rows={3} className="input w-full resize-none" /></Field></>}
    <p className="mb-2 text-sm font-medium">Alunos</p>
    <div className="mb-5 max-h-48 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-2">{props.students.map((student) => <label key={student.id} className={`flex items-center gap-3 rounded-lg p-2 text-sm ${student.child_id ? "cursor-pointer hover:bg-slate-50" : "cursor-not-allowed bg-slate-50 text-slate-400"}`}><input type="checkbox" disabled={!student.child_id} checked={props.selectedStudents.includes(student.id)} onChange={() => props.onToggleStudent(student.id)} /><span className="flex-1">{student.name}</span>{!student.child_id && <span className="text-[10px]">sem vínculo familiar</span>}</label>)}</div>
    <button onClick={props.onSave} disabled={props.saving || !valid} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{props.saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : isPost ? <Send className="h-4 w-4" /> : <FileImage className="h-4 w-4" />}{isPost ? "Publicar para as famílias" : "Criar portfólio"}</button>
  </Modal>;
}

function FamilyModal({ student, families, selected, setSelected, saving, onClose, onSave, onCreate }: { student: Student; families: FamilyChild[]; selected: string; setSelected: (value: string) => void; saving: boolean; onClose: () => void; onSave: () => void; onCreate: (payload: { parent_name: string; parent_email: string; parent_phone: string; initial_password: string }) => Promise<void> }) {
  const available = families.filter((family) => !family.linked_student_id || family.linked_student_id === student.id);
  const family = families.find((item) => item.id === selected);
  const [parentName, setParentName] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [parentPhone, setParentPhone] = useState("");
  const [initialPassword, setInitialPassword] = useState("");
  const canCreate = parentName.trim().length >= 2 && parentEmail.includes("@") && initialPassword.length >= 6;
  return <Modal title={`Vincular ${student.name}`} onClose={onClose}>
    <p className="mb-4 text-sm text-slate-600">Escolha o perfil da criança que já pertence à conta de um responsável no TinhaKids.</p>
    <select value={selected} onChange={(event) => setSelected(event.target.value)} className="input mb-4 w-full"><option value="">Sem vínculo</option>{available.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.classroom}</option>)}</select>
    {family && <div className="mb-5 rounded-xl bg-slate-50 p-3 text-sm"><p className="font-medium">Responsáveis</p><p className="mt-1 text-slate-600">{family.parent_names.join(", ") || "Nome não informado"}</p><p className="text-xs text-slate-500">{family.parent_emails.join(", ")}</p></div>}
    <button onClick={onSave} disabled={saving || !selected} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white disabled:opacity-50">{saving && <LoaderCircle className="h-4 w-4 animate-spin" />}Usar perfil existente</button>
    {!student.child_id && <><div className="my-5 flex items-center gap-3 text-xs font-medium uppercase tracking-wide text-slate-400"><span className="h-px flex-1 bg-slate-200" />ou cadastre a família<span className="h-px flex-1 bg-slate-200" /></div>
      <div className="grid gap-3 sm:grid-cols-2"><input className="input" value={parentName} onChange={(event) => setParentName(event.target.value)} placeholder="Nome do responsável" /><input className="input" type="email" value={parentEmail} onChange={(event) => setParentEmail(event.target.value)} placeholder="E-mail" /><input className="input" value={parentPhone} onChange={(event) => setParentPhone(event.target.value)} placeholder="Telefone (opcional)" /><input className="input" type="password" value={initialPassword} onChange={(event) => setInitialPassword(event.target.value)} placeholder="Senha inicial (mín. 6)" /></div>
      <p className="my-3 text-xs text-slate-500">A conta fica ativa imediatamente e o responsável já pode entrar no TinhaKids com o e-mail e a senha inicial.</p>
      <button onClick={() => void onCreate({ parent_name: parentName, parent_email: parentEmail, parent_phone: parentPhone, initial_password: initialPassword })} disabled={saving || !canCreate} className="flex w-full items-center justify-center gap-2 rounded-xl border border-blue-300 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700 disabled:opacity-50">{saving && <LoaderCircle className="h-4 w-4 animate-spin" />}Cadastrar e vincular</button></>}
  </Modal>;
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4" onMouseDown={onClose}><div onMouseDown={(event) => event.stopPropagation()} className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl"><div className="mb-5 flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2><button onClick={onClose} className="rounded-lg p-2 hover:bg-slate-100"><X className="h-5 w-5" /></button></div>{children}</div></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="mb-4 block"><span className="mb-1.5 block text-sm font-medium">{label}</span>{children}</label>;
}

function EmptyPhotos() {
  return <div className="grid min-h-56 place-items-center rounded-xl border border-dashed border-slate-300 text-center text-sm text-slate-500"><div><ImageIcon className="mx-auto mb-2 h-8 w-8" />Aguardando o primeiro envio do Tinhaphone.</div></div>;
}
