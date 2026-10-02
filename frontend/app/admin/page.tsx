"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Archive, BarChart3, Building2, Camera, CheckCircle2, GraduationCap, HardDrive,
  LoaderCircle, LogOut, Pencil, Plus, Search, Sparkles, UserRound, Users, X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Tab = "resumo" | "profissionais" | "turmas" | "criancas";
type Summary = { school: { name: string; plan_name: string }; active_professionals: number; active_classes: number; active_students: number; photo_count: number; storage_bytes: number; missing_files: number };
type Professional = { id: number; name: string; email: string; role: "PROFESSOR" | "MARKETING"; is_active: boolean; class_ids: number[] };
type SchoolClass = { id: number; name: string; year: number; is_active: boolean; teacher_ids: number[] };
type Student = { id: number; name: string; class_id: number; marketing_allowed: boolean; status: "ATIVO" | "INATIVO" };
type ProfessionalForm = { id: number; name: string; email: string; role: "PROFESSOR" | "MARKETING"; password: string; class_ids: number[] };

const emptyProfessional: ProfessionalForm = { id: 0, name: "", email: "", role: "PROFESSOR", password: "", class_ids: [] };
const emptyClass = { id: 0, name: "", year: new Date().getFullYear(), teacher_ids: [] as number[] };
const emptyStudent = { id: 0, name: "", class_id: 0, marketing_allowed: false };

function bytesLabel(value: number) {
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function AdminPage() {
  const { user, token, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("resumo");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [professionalForm, setProfessionalForm] = useState(emptyProfessional);
  const [classForm, setClassForm] = useState(emptyClass);
  const [studentForm, setStudentForm] = useState(emptyStudent);

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }), [token]);
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const urls = ["/api/admin/summary", "/api/admin/users?include_inactive=true", "/api/classes/?include_inactive=true", "/api/students/?include_inactive=true"];
      const responses = await Promise.all(urls.map((path) => fetch(`${API_URL}${path}`, { headers })));
      if (responses.some((response) => !response.ok)) throw new Error("Não foi possível carregar o painel.");
      const [summaryData, userData, classData, studentData] = await Promise.all(responses.map((response) => response.json()));
      setSummary(summaryData); setProfessionals(userData); setClasses(classData); setStudents(studentData);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Erro ao carregar o painel."); }
    finally { setLoading(false); }
  }, [headers, token]);

  useEffect(() => {
    if (authLoading || !user) return;
    if (user.role !== "COORDENADOR") { router.replace(user.role === "MARKETING" ? "/marketing" : "/"); return; }
    // A carga começa somente depois que a sessão do navegador foi restaurada.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [authLoading, load, router, user]);

  async function mutate(path: string, method: string, body?: object) {
    setSaving(true); setError(""); setMessage("");
    try {
      const response = await fetch(`${API_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Não foi possível salvar.");
      setMessage("Alterações salvas com sucesso."); await load(); return true;
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Não foi possível salvar."); return false; }
    finally { setSaving(false); }
  }

  async function saveProfessional(event: React.FormEvent) {
    event.preventDefault();
    const body = { name: professionalForm.name, email: professionalForm.email, role: professionalForm.role, class_ids: professionalForm.role === "PROFESSOR" ? professionalForm.class_ids : [], ...(professionalForm.password ? { password: professionalForm.password } : {}) };
    if (!professionalForm.id && !professionalForm.password) { setError("Informe uma senha inicial com pelo menos 6 caracteres."); return; }
    const ok = await mutate(professionalForm.id ? `/api/admin/users/${professionalForm.id}` : "/api/admin/users", professionalForm.id ? "PUT" : "POST", body);
    if (ok) setProfessionalForm(emptyProfessional);
  }
  async function saveClass(event: React.FormEvent) {
    event.preventDefault();
    const ok = await mutate(classForm.id ? `/api/classes/${classForm.id}` : "/api/classes/", classForm.id ? "PUT" : "POST", { name: classForm.name, year: classForm.year, teacher_ids: classForm.teacher_ids });
    if (ok) setClassForm(emptyClass);
  }
  async function saveStudent(event: React.FormEvent) {
    event.preventDefault();
    const ok = await mutate(studentForm.id ? `/api/students/${studentForm.id}` : "/api/students/", studentForm.id ? "PUT" : "POST", { name: studentForm.name, class_id: studentForm.class_id, marketing_allowed: studentForm.marketing_allowed });
    if (ok) setStudentForm(emptyStudent);
  }

  if (authLoading || !user || user.role !== "COORDENADOR") return <main className="grid min-h-screen place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></main>;
  const activeClasses = classes.filter((item) => item.is_active);
  const teachers = professionals.filter((item) => item.role === "PROFESSOR" && item.is_active);
  const q = search.toLocaleLowerCase("pt-BR");
  const shownProfessionals = professionals.filter((item) => `${item.name} ${item.email}`.toLocaleLowerCase("pt-BR").includes(q));
  const shownStudents = students.filter((item) => item.name.toLocaleLowerCase("pt-BR").includes(q));

  return <div className="min-h-screen bg-slate-50 text-slate-900">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white"><Building2 /></span><div><p className="font-semibold">{user.school.name}</p><p className="text-xs text-slate-500">Painel da coordenação</p></div></div><div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-sm font-medium">{user.name}</p><p className="text-xs text-slate-500">Coordenador</p></div><button onClick={logout} className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100" title="Sair"><LogOut className="h-5 w-5" /></button></div></div></header>
    <div className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[220px_1fr]">
      <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-2 shadow-sm"><nav className="grid grid-cols-2 gap-1 sm:grid-cols-5 lg:grid-cols-1">{([
        ["resumo", BarChart3, "Visão geral"], ["profissionais", Users, "Profissionais"], ["turmas", GraduationCap, "Turmas"], ["criancas", UserRound, "Crianças"],
      ] as const).map(([key, Icon, label]) => <button key={key} onClick={() => { setTab(key); setSearch(""); }} className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium ${tab === key ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"}`}><Icon className="h-4 w-4" />{label}</button>)}<Link href="/admin/photos" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-50"><Camera className="h-4 w-4" />Fotos</Link></nav></aside>
      <main className="min-w-0">
        {error && <Notice tone="error" onClose={() => setError("")}>{error}</Notice>}{message && <Notice tone="success" onClose={() => setMessage("")}>{message}</Notice>}
        {loading ? <div className="grid min-h-96 place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></div> : <>
          {tab === "resumo" && summary && <Overview summary={summary} onUpgrade={() => setUpgradeOpen(true)} />}
          {tab === "profissionais" && <section><SectionTitle title="Profissionais" subtitle="Cadastre professores e pessoas da equipe de marketing." /><SearchBox value={search} onChange={setSearch} placeholder="Buscar por nome ou e-mail" /><form onSubmit={saveProfessional} className="mb-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><FormHeading editing={!!professionalForm.id} label="profissional" onCancel={() => setProfessionalForm(emptyProfessional)} /><input className="input" required placeholder="Nome completo" value={professionalForm.name} onChange={(e) => setProfessionalForm({ ...professionalForm, name: e.target.value })} /><input className="input" required type="email" placeholder="E-mail" value={professionalForm.email} onChange={(e) => setProfessionalForm({ ...professionalForm, email: e.target.value })} /><select className="input" value={professionalForm.role} onChange={(e) => setProfessionalForm({ ...professionalForm, role: e.target.value as "PROFESSOR" | "MARKETING", class_ids: [] })}><option value="PROFESSOR">Professor</option><option value="MARKETING">Marketing</option></select><input className="input" type="password" minLength={6} placeholder={professionalForm.id ? "Nova senha (opcional)" : "Senha inicial"} value={professionalForm.password} onChange={(e) => setProfessionalForm({ ...professionalForm, password: e.target.value })} />{professionalForm.role === "PROFESSOR" && <CheckList title="Turmas atribuídas" items={activeClasses.map((item) => ({ id: item.id, label: `${item.name} · ${item.year}` }))} selected={professionalForm.class_ids} onChange={(class_ids) => setProfessionalForm({ ...professionalForm, class_ids })} />}<SaveButton saving={saving} editing={!!professionalForm.id} /></form><DataList empty="Nenhum profissional encontrado.">{shownProfessionals.map((item) => <Row key={item.id} inactive={!item.is_active} title={item.name} subtitle={`${item.email} · ${item.role === "PROFESSOR" ? "Professor" : "Marketing"}`} onEdit={() => setProfessionalForm({ id: item.id, name: item.name, email: item.email, role: item.role, password: "", class_ids: item.class_ids })} onToggle={() => void mutate(`/api/admin/users/${item.id}`, item.is_active ? "DELETE" : "PUT", item.is_active ? undefined : { is_active: true })} active={item.is_active} />)}</DataList></section>}
          {tab === "turmas" && <section><SectionTitle title="Turmas" subtitle="Organize o ano letivo e os professores responsáveis." /><form onSubmit={saveClass} className="mb-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><FormHeading editing={!!classForm.id} label="turma" onCancel={() => setClassForm(emptyClass)} /><input className="input" required placeholder="Nome da turma" value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} /><input className="input" required type="number" min={2000} max={2200} value={classForm.year} onChange={(e) => setClassForm({ ...classForm, year: Number(e.target.value) })} /><CheckList title="Professores" items={teachers.map((item) => ({ id: item.id, label: item.name }))} selected={classForm.teacher_ids} onChange={(teacher_ids) => setClassForm({ ...classForm, teacher_ids })} /><SaveButton saving={saving} editing={!!classForm.id} /></form><DataList empty="Nenhuma turma cadastrada.">{classes.map((item) => <Row key={item.id} inactive={!item.is_active} title={item.name} subtitle={`${item.year} · ${item.teacher_ids.length} professor(es)`} onOpen={item.is_active ? () => router.push(`/class/${item.id}`) : undefined} onEdit={() => setClassForm({ id: item.id, name: item.name, year: item.year, teacher_ids: item.teacher_ids })} onToggle={() => void mutate(`/api/classes/${item.id}`, item.is_active ? "DELETE" : "PUT", item.is_active ? undefined : { is_active: true })} active={item.is_active} />)}</DataList></section>}
          {tab === "criancas" && <section><SectionTitle title="Crianças" subtitle="Cadastre, transfira de turma ou desative sem perder o histórico." /><SearchBox value={search} onChange={setSearch} placeholder="Buscar criança" /><form onSubmit={saveStudent} className="mb-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><FormHeading editing={!!studentForm.id} label="criança" onCancel={() => setStudentForm(emptyStudent)} /><input className="input" required placeholder="Nome completo" value={studentForm.name} onChange={(e) => setStudentForm({ ...studentForm, name: e.target.value })} /><select className="input" required value={studentForm.class_id || ""} onChange={(e) => setStudentForm({ ...studentForm, class_id: Number(e.target.value) })}><option value="">Selecione a turma</option>{activeClasses.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.year}</option>)}</select><label className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm"><input type="checkbox" checked={studentForm.marketing_allowed} onChange={(e) => setStudentForm({ ...studentForm, marketing_allowed: e.target.checked })} />Uso de imagem autorizado para marketing</label><SaveButton saving={saving} editing={!!studentForm.id} /></form><DataList empty="Nenhuma criança encontrada.">{shownStudents.map((item) => { const schoolClass = classes.find((value) => value.id === item.class_id); return <Row key={item.id} inactive={item.status === "INATIVO"} title={item.name} subtitle={`${schoolClass?.name ?? "Turma"} · Marketing ${item.marketing_allowed ? "autorizado" : "não autorizado"}`} onEdit={() => setStudentForm({ id: item.id, name: item.name, class_id: item.class_id, marketing_allowed: item.marketing_allowed })} onToggle={() => void mutate(`/api/students/${item.id}`, item.status === "ATIVO" ? "DELETE" : "PUT", item.status === "ATIVO" ? undefined : { is_active: true })} active={item.status === "ATIVO"} />; })}</DataList></section>}
        </>}
      </main>
    </div>
    {upgradeOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4" onMouseDown={() => setUpgradeOpen(false)}><div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}><div className="mb-4 flex items-start justify-between"><span className="grid h-11 w-11 place-items-center rounded-xl bg-violet-100 text-violet-700"><Sparkles /></span><button onClick={() => setUpgradeOpen(false)} className="rounded-lg p-2 hover:bg-slate-100"><X className="h-5 w-5" /></button></div><h2 className="text-xl font-semibold">Upgrades em breve</h2><p className="mt-2 text-sm leading-6 text-slate-600">Estamos preparando novos planos com mais recursos para a sua escola. Nesta versão, o uso continua sem bloqueio e nenhuma cobrança será realizada.</p><button onClick={() => setUpgradeOpen(false)} className="mt-5 w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white">Entendi</button></div></div>}
  </div>;
}

function Overview({ summary, onUpgrade }: { summary: Summary; onUpgrade: () => void }) {
  const cards = [[Users, "Profissionais", summary.active_professionals], [GraduationCap, "Turmas", summary.active_classes], [UserRound, "Crianças", summary.active_students], [Camera, "Fotos", summary.photo_count]] as const;
  return <section><SectionTitle title="Visão geral" subtitle={`Acompanhe as informações principais da ${summary.school.name}.`} /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([Icon, label, value]) => <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><Icon className="mb-4 h-5 w-5 text-blue-600" /><p className="text-3xl font-semibold">{value}</p><p className="mt-1 text-sm text-slate-500">{label} ativos</p></div>)}</div><div className="mt-5 grid gap-5 lg:grid-cols-2"><div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><HardDrive className="h-5 w-5" /></span><div><p className="font-semibold">Armazenamento</p><p className="text-sm text-slate-500">Espaço usado pelas fotos da escola</p></div></div><p className="mt-6 text-3xl font-semibold">{bytesLabel(summary.storage_bytes)}</p><p className="mt-1 text-xs text-slate-500">{summary.missing_files ? `${summary.missing_files} arquivo(s) não encontrado(s) foram ignorados.` : "Todos os arquivos registrados foram contabilizados."}</p></div><div className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-white p-5 shadow-sm"><p className="text-sm font-medium text-violet-700">Plano atual</p><p className="mt-2 text-2xl font-semibold">{summary.school.plan_name}</p><p className="mt-2 text-sm text-slate-600">Sua escola continua usando o sistema normalmente, sem limite de armazenamento nesta fase.</p><button onClick={onUpgrade} className="mt-5 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-800"><Sparkles className="mr-2 inline h-4 w-4" />Conhecer upgrades</button></div></div></section>;
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) { return <div className="mb-5"><h1 className="text-2xl font-semibold">{title}</h1><p className="mt-1 text-sm text-slate-600">{subtitle}</p></div>; }
function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="relative mb-4 block"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input w-full pl-9" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} /></label>; }
function FormHeading({ editing, label, onCancel }: { editing: boolean; label: string; onCancel: () => void }) { return <div className="flex items-center justify-between md:col-span-2"><h2 className="font-semibold">{editing ? `Editar ${label}` : `Novo ${label}`}</h2>{editing && <button type="button" onClick={onCancel} className="text-xs font-medium text-slate-500 hover:text-slate-900">Cancelar edição</button>}</div>; }
function SaveButton({ saving, editing }: { saving: boolean; editing: boolean }) { return <button disabled={saving} className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : editing ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}{editing ? "Salvar alterações" : "Cadastrar"}</button>; }
function CheckList({ title, items, selected, onChange }: { title: string; items: { id: number; label: string }[]; selected: number[]; onChange: (ids: number[]) => void }) { return <fieldset className="rounded-xl border border-slate-200 p-3 md:col-span-2"><legend className="px-1 text-xs font-medium text-slate-500">{title}</legend><div className="flex flex-wrap gap-3">{items.length ? items.map((item) => <label key={item.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(item.id)} onChange={() => onChange(selected.includes(item.id) ? selected.filter((id) => id !== item.id) : [...selected, item.id])} />{item.label}</label>) : <span className="text-sm text-slate-400">Nenhuma opção disponível.</span>}</div></fieldset>; }
function DataList({ empty, children }: { empty: string; children: React.ReactNode }) { return <div className="space-y-2">{Array.isArray(children) && children.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">{empty}</div> : children}</div>; }
function Row({ title, subtitle, inactive, active, onOpen, onEdit, onToggle }: { title: string; subtitle: string; inactive: boolean; active: boolean; onOpen?: () => void; onEdit: () => void; onToggle: () => void }) { return <div className={`flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center ${inactive ? "opacity-60" : ""}`}><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}>{active ? <CheckCircle2 className="h-5 w-5" /> : <Archive className="h-5 w-5" />}</span><div className="min-w-0 flex-1"><p className="font-medium">{title}</p><p className="truncate text-sm text-slate-500">{subtitle}</p></div><div className="flex gap-2">{onOpen && <button onClick={onOpen} className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700">Abrir fotos</button>}<button onClick={onEdit} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50"><Pencil className="mr-1 inline h-3.5 w-3.5" />Editar</button><button onClick={onToggle} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50">{active ? "Desativar" : "Reativar"}</button></div></div>; }
function Notice({ tone, onClose, children }: { tone: "error" | "success"; onClose: () => void; children: React.ReactNode }) { return <div className={`mb-4 flex items-center justify-between rounded-xl border p-4 text-sm ${tone === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-green-200 bg-green-50 text-green-800"}`}><span>{children}</span><button onClick={onClose}><X className="h-4 w-4" /></button></div>; }
