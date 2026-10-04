"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Archive, BarChart3, Building2, Camera, CheckCircle2, GraduationCap, HardDrive,
  LoaderCircle, LogOut, Pencil, Plus, Search, Sparkles, UserRound, Users, X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Tab = "resumo" | "profissionais" | "turmas" | "criancas" | "familiares";
type Summary = { school: { name: string; plan_name: string }; active_professionals: number; active_classes: number; active_students: number; photo_count: number; storage_bytes: number; missing_files: number };
type Professional = { id: number; name: string; email: string; role: "PROFESSOR" | "MARKETING"; is_active: boolean; class_ids: number[] };
type SchoolClass = { id: number; name: string; year: number; is_active: boolean; teacher_ids: number[] };
type Parent = { id: string; name: string; email: string; phone?: string | null; is_active: boolean; student_ids: number[] };
type Student = { parent_ids: string[]; id: number; name: string; class_id: number; marketing_allowed: boolean; status: "ATIVO" | "INATIVO" };
type ProfessionalForm = { id: number; name: string; email: string; role: "PROFESSOR" | "MARKETING"; password: string; class_ids: number[] };

const emptyProfessional: ProfessionalForm = { id: 0, name: "", email: "", role: "PROFESSOR", password: "", class_ids: [] };
const emptyClass = { id: 0, name: "", year: new Date().getFullYear(), teacher_ids: [] as number[] };
const emptyStudent = { id: 0, name: "", class_id: 0, marketing_allowed: false, parent_ids: [] as string[] };

const emptyParent = { id: "", name: "", email: "", phone: "", password: "", student_ids: [] as number[] };
type ParentFormData = typeof emptyParent;

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
  const [parents, setParents] = useState<Parent[]>([]);
  const [formOpen, setFormOpen] = useState<Tab | null>(null);
  const [classFilter, setClassFilter] = useState("");
  const [professionalClassFilter, setProfessionalClassFilter] = useState("");
  const [classListFilter, setClassListFilter] = useState("");
  const [showInactive, setShowInactive] = useState<Record<Tab, boolean>>({ resumo: false, profissionais: false, turmas: false, criancas: false, familiares: false });
  const [parentForm, setParentForm] = useState(emptyParent);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [professionalForm, setProfessionalForm] = useState(emptyProfessional);
  const [classForm, setClassForm] = useState(emptyClass);
  const [studentForm, setStudentForm] = useState(emptyStudent);

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }), [token]);
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const urls = ["/api/admin/summary", "/api/admin/users?include_inactive=true", "/api/classes/?include_inactive=true", "/api/students/?include_inactive=true", "/api/families/parents?include_inactive=true"];
      const responses = await Promise.all(urls.map((path) => fetch(`${API_URL}${path}`, { headers })));
      if (responses.some((response) => !response.ok)) throw new Error("Não foi possível carregar o painel.");
      const [summaryData, userData, classData, studentData, parentData] = await Promise.all(responses.map((response) => response.json()));
      setSummary(summaryData); setProfessionals(userData); setClasses(classData); setStudents(studentData); setParents(parentData);
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
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Confira os campos e tente novamente.");
      setMessage("Alterações salvas com sucesso."); await load(); return true;
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Não foi possível salvar."); return false; }
    finally { setSaving(false); }
  }

  async function saveProfessional(event: React.FormEvent) {
    event.preventDefault();
    const body = { name: professionalForm.name, email: professionalForm.email, role: professionalForm.role, class_ids: professionalForm.role === "PROFESSOR" ? professionalForm.class_ids : [], ...(professionalForm.password ? { password: professionalForm.password } : {}) };
    if (!professionalForm.id && !professionalForm.password) { setError("Informe uma senha inicial com pelo menos 6 caracteres."); return; }
    const ok = await mutate(professionalForm.id ? `/api/admin/users/${professionalForm.id}` : "/api/admin/users", professionalForm.id ? "PUT" : "POST", body);
    if (ok) { setProfessionalForm(emptyProfessional); setFormOpen(null); setMessage(professionalForm.id ? "Profissional atualizado com sucesso." : "Profissional cadastrado com sucesso."); }
  }
  async function saveClass(event: React.FormEvent) {
    event.preventDefault();
    const ok = await mutate(classForm.id ? `/api/classes/${classForm.id}` : "/api/classes/", classForm.id ? "PUT" : "POST", { name: classForm.name, year: classForm.year, teacher_ids: classForm.teacher_ids });
    if (ok) { setClassForm(emptyClass); setFormOpen(null); setMessage(classForm.id ? "Turma atualizada com sucesso." : "Turma cadastrada com sucesso."); }
  }
  async function saveStudent(event: React.FormEvent) {
    event.preventDefault();
    const ok = await mutate(studentForm.id ? `/api/students/${studentForm.id}` : "/api/students/", studentForm.id ? "PUT" : "POST", { name: studentForm.name, class_id: studentForm.class_id, marketing_allowed: studentForm.marketing_allowed, parent_ids: studentForm.parent_ids });
    if (ok) { setStudentForm(emptyStudent); setFormOpen(null); setMessage(studentForm.id ? "Aluno atualizado com sucesso." : "Aluno cadastrado com sucesso."); }
  }

  async function saveParent(event: React.FormEvent) {
    event.preventDefault();
    const body = { name: parentForm.name, email: parentForm.email, phone: parentForm.phone || null, student_ids: parentForm.student_ids, ...(parentForm.password ? { password: parentForm.password } : {}) };
    const ok = await mutate(parentForm.id ? `/api/families/parents/${parentForm.id}` : "/api/families/parents", parentForm.id ? "PUT" : "POST", body);
    if (ok) { setParentForm(emptyParent); setFormOpen(null); setMessage(parentForm.id ? "Familiar atualizado com sucesso." : "Familiar cadastrado com sucesso."); }
  }

  if (authLoading || !user || user.role !== "COORDENADOR") return <main className="grid min-h-screen place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></main>;
  const activeClasses = classes.filter((item) => item.is_active);
  const teachers = professionals.filter((item) => item.role === "PROFESSOR" && item.is_active);
  const q = search.toLocaleLowerCase("pt-BR");
  const shownProfessionals = professionals.filter((item) => (showInactive.profissionais || item.is_active) && `${item.name} ${item.email}`.toLocaleLowerCase("pt-BR").includes(q) && (!professionalClassFilter || (professionalClassFilter === "none" ? item.class_ids.length === 0 : item.class_ids.includes(Number(professionalClassFilter)))));
  const shownClasses = classes.filter((item) => (showInactive.turmas || item.is_active) && `${item.name} ${item.year}`.toLocaleLowerCase("pt-BR").includes(q) && (!classListFilter || (classListFilter === "none" ? !item.teacher_ids.some((id) => teachers.some((teacher) => teacher.id === id)) : item.id === Number(classListFilter))));
  const shownParents = parents.filter((item) => (showInactive.familiares || item.is_active) && `${item.name} ${item.email} ${item.phone ?? ""}`.toLocaleLowerCase("pt-BR").includes(q));
  const shownStudents = students.filter((item) => (showInactive.criancas || item.status === "ATIVO") && item.name.toLocaleLowerCase("pt-BR").includes(q) && (!classFilter || item.class_id === Number(classFilter)));

  return <div className="min-h-screen bg-slate-50 text-slate-900">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white"><Building2 /></span><div><p className="font-semibold">{user.school.name}</p><p className="text-xs text-slate-500">Painel da coordenação</p></div></div><div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-sm font-medium">{user.name}</p><p className="text-xs text-slate-500">Coordenador</p></div><button onClick={logout} className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-100" title="Sair"><LogOut className="h-5 w-5" /></button></div></div></header>
    <div className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[220px_1fr]">
      <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-2 shadow-sm"><nav className="grid grid-cols-2 gap-1 sm:grid-cols-5 lg:grid-cols-1">{([
        ["resumo", BarChart3, "Visão geral"], ["profissionais", Users, "Profissionais"], ["turmas", GraduationCap, "Turmas"], ["criancas", UserRound, "Alunos"], ["familiares", Users, "Familiares"],
      ] as const).map(([key, Icon, label]) => <button key={key} onClick={() => { setTab(key); setSearch(""); }} className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium ${tab === key ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"}`}><Icon className="h-4 w-4" />{label}</button>)}<Link href="/admin/photos" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-50"><Camera className="h-4 w-4" />Fotos</Link><Link href="/admin/processing" className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-50"><Sparkles className="h-4 w-4" />Fila facial</Link></nav></aside>
      <main className="min-w-0">
        {error && <Notice tone="error" onClose={() => setError("")}>{error}</Notice>}{message && <Notice tone="success" onClose={() => setMessage("")}>{message}</Notice>}
        {loading ? <div className="grid min-h-96 place-items-center"><LoaderCircle className="h-8 w-8 animate-spin text-blue-600" /></div> : <>
          {tab === "resumo" && summary && <Overview summary={summary} onUpgrade={() => setUpgradeOpen(true)} />}
          {tab === "profissionais" && <section><SectionTitle title="Profissionais" subtitle="Cadastre professores e pessoas da equipe de marketing." /><div className="mb-4 grid gap-3 md:grid-cols-3"><SearchBox value={search} onChange={setSearch} placeholder="Buscar por nome" /><ClassFilter classes={classes} value={professionalClassFilter} onChange={setProfessionalClassFilter} label="Filtrar profissionais por turma" unassignedLabel="Sem turma" /><InactiveButton visible={showInactive.profissionais} onToggle={() => setShowInactive({ ...showInactive, profissionais: !showInactive.profissionais })} /></div><button onClick={() => { setProfessionalForm(emptyProfessional); setError(""); setFormOpen("profissionais"); }} className="mb-5 flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white"><Plus className="h-4 w-4" />Cadastrar</button><DataList empty="Nenhum profissional encontrado.">{shownProfessionals.map((item) => <Row key={item.id} inactive={!item.is_active} title={item.name} subtitle={`${item.email} · ${item.role === "PROFESSOR" ? "Professor" : "Marketing"}`} onEdit={() => { setProfessionalForm({ id: item.id, name: item.name, email: item.email, role: item.role, password: "", class_ids: item.class_ids }); setError(""); setFormOpen("profissionais"); }} onToggle={() => void mutate(`/api/admin/users/${item.id}`, item.is_active ? "DELETE" : "PUT", item.is_active ? undefined : { is_active: true })} active={item.is_active} />)}</DataList></section>}
          {tab === "turmas" && <section><SectionTitle title="Turmas" subtitle="Organize o ano letivo e os professores responsáveis." /><div className="mb-4 grid gap-3 md:grid-cols-3"><SearchBox value={search} onChange={setSearch} placeholder="Buscar por nome" /><ClassFilter classes={classes} value={classListFilter} onChange={setClassListFilter} label="Filtrar turmas" unassignedLabel="Sem professores" /><InactiveButton visible={showInactive.turmas} onToggle={() => setShowInactive({ ...showInactive, turmas: !showInactive.turmas })} /></div><button onClick={() => { setClassForm(emptyClass); setError(""); setFormOpen("turmas"); }} className="mb-5 flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white"><Plus className="h-4 w-4" />Cadastrar</button><DataList empty="Nenhuma turma cadastrada.">{shownClasses.map((item) => <Row key={item.id} inactive={!item.is_active} title={item.name} subtitle={`${item.year} · ${item.teacher_ids.length} professor(es)`} onOpen={item.is_active ? () => router.push(`/class/${item.id}`) : undefined} onEdit={() => { setClassForm({ id: item.id, name: item.name, year: item.year, teacher_ids: item.teacher_ids }); setError(""); setFormOpen("turmas"); }} onToggle={() => void mutate(`/api/classes/${item.id}`, item.is_active ? "DELETE" : "PUT", item.is_active ? undefined : { is_active: true })} active={item.is_active} />)}</DataList></section>}
          {tab === "criancas" && <section><SectionTitle title="Alunos" subtitle="Cadastre, transfira de turma ou desative sem perder o histórico." /><div className="mb-4 grid gap-3 md:grid-cols-3"><SearchBox value={search} onChange={setSearch} placeholder="Buscar por nome" /><ClassFilter classes={classes} value={classFilter} onChange={setClassFilter} label="Filtrar alunos por turma"  /><InactiveButton visible={showInactive.criancas} onToggle={() => setShowInactive({ ...showInactive, criancas: !showInactive.criancas })} /></div><button onClick={() => { setStudentForm(emptyStudent); setError(""); setFormOpen("criancas"); }} className="mb-5 flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white"><Plus className="h-4 w-4" />Cadastrar</button><DataList empty="Nenhum aluno encontrado.">{shownStudents.map((item) => { const schoolClass = classes.find((value) => value.id === item.class_id); return <Row key={item.id} inactive={item.status === "INATIVO"} title={item.name} subtitle={`${schoolClass?.name ?? "Turma"} · Marketing ${item.marketing_allowed ? "autorizado" : "não autorizado"}`} onOpen={() => router.push(`/admin/photos?student_id=${item.id}`)} openLabel="Ver fotos" onEdit={() => { setStudentForm({ id: item.id, name: item.name, class_id: item.class_id, marketing_allowed: item.marketing_allowed, parent_ids: item.parent_ids ?? [] }); setError(""); setFormOpen("criancas"); }} onToggle={() => void mutate(`/api/students/${item.id}`, item.status === "ATIVO" ? "DELETE" : "PUT", item.status === "ATIVO" ? undefined : { is_active: true })} active={item.status === "ATIVO"} />; })}</DataList></section>}
          {tab === "familiares" && <section>
            <SectionTitle title="Familiares" subtitle="Cadastre responsáveis e vincule os alunos da escola." />
            <div className="mb-4 grid gap-3 sm:grid-cols-2"><SearchBox value={search} onChange={setSearch} placeholder="Buscar familiar por nome, e-mail ou telefone" /><InactiveButton visible={showInactive.familiares} onToggle={() => setShowInactive({ ...showInactive, familiares: !showInactive.familiares })} /></div>
            <button onClick={() => { setParentForm(emptyParent); setError(""); setFormOpen("familiares"); }} className="mb-5 flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white"><Plus className="h-4 w-4" />Cadastrar</button>
            <DataList empty="Nenhum familiar encontrado.">{shownParents.map((item) => <Row key={item.id} inactive={!item.is_active} active={item.is_active} title={item.name} subtitle={`${item.email} · ${students.filter((student) => item.student_ids.includes(student.id)).map((student) => student.name).join(", ") || "Sem aluno vinculado"}`} onEdit={() => { setParentForm({ id: item.id, name: item.name, email: item.email, phone: item.phone ?? "", password: "", student_ids: item.student_ids }); setError(""); setFormOpen("familiares"); }} onToggle={() => void mutate(`/api/families/parents/${item.id}`, item.is_active ? "DELETE" : "PUT", item.is_active ? undefined : { is_active: true })} />)}</DataList>
          </section>}
        </>}
      </main>
    </div>
    {formOpen && <RegistrationModal title={formOpen === "profissionais" ? (professionalForm.id ? "Editar profissional" : "Cadastrar profissional") : formOpen === "turmas" ? (classForm.id ? "Editar turma" : "Cadastrar turma") : formOpen === "familiares" ? (parentForm.id ? "Editar familiar" : "Cadastrar familiar") : (studentForm.id ? "Editar aluno" : "Cadastrar aluno")} saving={saving} onClose={() => { if (!saving) { setFormOpen(null); setError(""); } }}>{error && <Notice tone="error" onClose={() => setError("")}>{error}</Notice>}{formOpen === "profissionais" && <form onSubmit={saveProfessional} className="mb-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><input className="input" required placeholder="Nome completo" value={professionalForm.name} onChange={(e) => setProfessionalForm({ ...professionalForm, name: e.target.value })} /><input className="input" required type="email" placeholder="E-mail" value={professionalForm.email} onChange={(e) => setProfessionalForm({ ...professionalForm, email: e.target.value })} /><select aria-label="Perfil do profissional" className="input" value={professionalForm.role} onChange={(e) => setProfessionalForm({ ...professionalForm, role: e.target.value as "PROFESSOR" | "MARKETING", class_ids: [] })}><option value="PROFESSOR">Professor</option><option value="MARKETING">Marketing</option></select><input className="input" type="password" required={!professionalForm.id} minLength={6} placeholder={professionalForm.id ? "Nova senha (opcional)" : "Senha inicial"} value={professionalForm.password} onChange={(e) => setProfessionalForm({ ...professionalForm, password: e.target.value })} />{professionalForm.role === "PROFESSOR" && <CheckList title="Turmas atribuídas" items={activeClasses.map((item) => ({ id: item.id, label: `${item.name} · ${item.year}` }))} selected={professionalForm.class_ids} onChange={(class_ids) => setProfessionalForm({ ...professionalForm, class_ids })} />}<SaveButton saving={saving} editing={!!professionalForm.id} /></form>}{formOpen === "turmas" && <form onSubmit={saveClass} className="mb-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><input className="input" required placeholder="Nome da turma" value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} /><input aria-label="Ano letivo" className="input" required type="number" min={2000} max={2200} value={classForm.year} onChange={(e) => setClassForm({ ...classForm, year: Number(e.target.value) })} /><CheckList title="Professores" items={teachers.map((item) => ({ id: item.id, label: item.name }))} selected={classForm.teacher_ids} onChange={(teacher_ids) => setClassForm({ ...classForm, teacher_ids })} /><SaveButton saving={saving} editing={!!classForm.id} /></form>}{formOpen === "criancas" && <form onSubmit={saveStudent} className="mb-5 grid gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-2"><input className="input" required placeholder="Nome completo" value={studentForm.name} onChange={(e) => setStudentForm({ ...studentForm, name: e.target.value })} /><select aria-label="Turma do aluno" className="input" required value={studentForm.class_id || ""} onChange={(e) => setStudentForm({ ...studentForm, class_id: Number(e.target.value) })}><option value="">Selecione a turma</option>{activeClasses.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.year}</option>)}</select><label className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-sm"><input type="checkbox" checked={studentForm.marketing_allowed} onChange={(e) => setStudentForm({ ...studentForm, marketing_allowed: e.target.checked })} />Uso de imagem autorizado para marketing</label><ParentChoices parents={parents.filter((item) => item.is_active || studentForm.parent_ids.includes(item.id))} selected={studentForm.parent_ids} onChange={(parent_ids) => setStudentForm({ ...studentForm, parent_ids })} /><SaveButton saving={saving} editing={!!studentForm.id} /></form>}{formOpen === "familiares" && <ParentForm form={parentForm} onChange={setParentForm} students={students} classes={classes} saving={saving} onSubmit={saveParent} />}</RegistrationModal>}
    {upgradeOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4" onMouseDown={() => setUpgradeOpen(false)}><div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl" onMouseDown={(e) => e.stopPropagation()}><div className="mb-4 flex items-start justify-between"><span className="grid h-11 w-11 place-items-center rounded-xl bg-violet-100 text-violet-700"><Sparkles /></span><button onClick={() => setUpgradeOpen(false)} className="rounded-lg p-2 hover:bg-slate-100"><X className="h-5 w-5" /></button></div><h2 className="text-xl font-semibold">Upgrades em breve</h2><p className="mt-2 text-sm leading-6 text-slate-600">Estamos preparando novos planos com mais recursos para a sua escola. Nesta versão, o uso continua sem bloqueio e nenhuma cobrança será realizada.</p><button onClick={() => setUpgradeOpen(false)} className="mt-5 w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white">Entendi</button></div></div>}
  </div>;
}

function Overview({ summary, onUpgrade }: { summary: Summary; onUpgrade: () => void }) {
  const cards = [[Users, "Profissionais", summary.active_professionals], [GraduationCap, "Turmas", summary.active_classes], [UserRound, "Alunos", summary.active_students], [Camera, "Fotos", summary.photo_count]] as const;
  return <section><SectionTitle title="Visão geral" subtitle={`Acompanhe as informações principais da ${summary.school.name}.`} /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([Icon, label, value]) => <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><Icon className="mb-4 h-5 w-5 text-blue-600" /><p className="text-3xl font-semibold">{value}</p><p className="mt-1 text-sm text-slate-500">{label} ativos</p></div>)}</div><div className="mt-5 grid gap-5 lg:grid-cols-2"><div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><HardDrive className="h-5 w-5" /></span><div><p className="font-semibold">Armazenamento</p><p className="text-sm text-slate-500">Espaço usado pelas fotos da escola</p></div></div><p className="mt-6 text-3xl font-semibold">{bytesLabel(summary.storage_bytes)}</p><p className="mt-1 text-xs text-slate-500">{summary.missing_files ? `${summary.missing_files} arquivo(s) não encontrado(s) foram ignorados.` : "Todos os arquivos registrados foram contabilizados."}</p></div><div className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-white p-5 shadow-sm"><p className="text-sm font-medium text-violet-700">Plano atual</p><p className="mt-2 text-2xl font-semibold">{summary.school.plan_name}</p><p className="mt-2 text-sm text-slate-600">Sua escola continua usando o sistema normalmente, sem limite de armazenamento nesta fase.</p><button onClick={onUpgrade} className="mt-5 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-800"><Sparkles className="mr-2 inline h-4 w-4" />Conhecer upgrades</button></div></div></section>;
}

function RegistrationModal({ title, saving, onClose, children }: { title: string; saving: boolean; onClose: () => void; children: React.ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { element?.close(); document.body.style.overflow = previousOverflow; };
  }, []);
  return <dialog ref={dialog} aria-labelledby="registration-title" onCancel={(event) => { event.preventDefault(); if (!saving) onClose(); }} className="fixed inset-0 m-auto max-h-[90vh] w-[calc(100%_-_2rem)] max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl backdrop:bg-slate-950/45"><div className="mb-5 flex items-center justify-between"><h2 id="registration-title" className="text-lg font-semibold">{title}</h2><button type="button" disabled={saving} onClick={onClose} aria-label="Fechar formulário" className="rounded-lg p-2 hover:bg-slate-100 disabled:opacity-50"><X className="h-5 w-5" /></button></div>{children}</dialog>;
}

function ParentChoices({ parents, selected, onChange }: { parents: Parent[]; selected: string[]; onChange: (ids: string[]) => void }) {
  return <fieldset className="rounded-xl border border-slate-200 p-3 md:col-span-2"><legend className="px-1 text-sm font-medium">Pais ou mães (opcional)</legend><p className="mb-3 text-xs text-slate-500">Selecione um ou mais responsáveis da escola ou deixe sem vínculo.</p><div className="max-h-48 space-y-2 overflow-y-auto">{parents.length ? parents.map((parent) => <label key={parent.id} className="flex items-start gap-2 text-sm"><input type="checkbox" checked={selected.includes(parent.id)} onChange={() => onChange(selected.includes(parent.id) ? selected.filter((id) => id !== parent.id) : [...selected, parent.id])} /><span>{parent.name}<span className="block text-xs text-slate-500">{parent.email}</span></span></label>) : <p className="text-sm text-slate-500">Nenhum responsável cadastrado nesta escola. Você pode cadastrar e vincular a família depois, na aba Familiares.</p>}</div></fieldset>;
}

function ParentForm({ form, onChange, students, classes, saving, onSubmit }: { form: ParentFormData; onChange: (form: ParentFormData) => void; students: Student[]; classes: SchoolClass[]; saving: boolean; onSubmit: (event: React.FormEvent) => void }) {
  return <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-2">
    <input aria-label="Nome do familiar" className="input" required minLength={2} placeholder="Nome completo" value={form.name} onChange={(e) => onChange({ ...form, name: e.target.value })} />
    <input aria-label="E-mail do familiar" className="input" required type="email" placeholder="E-mail" value={form.email} onChange={(e) => onChange({ ...form, email: e.target.value })} />
    <input aria-label="Telefone do familiar" className="input" type="tel" placeholder="Telefone (opcional)" value={form.phone} onChange={(e) => onChange({ ...form, phone: e.target.value })} />
    <input aria-label="Senha do familiar" className="input" required={!form.id} type="password" minLength={6} placeholder={form.id ? "Nova senha (opcional)" : "Senha inicial"} value={form.password} onChange={(e) => onChange({ ...form, password: e.target.value })} />
    <CheckList title="Alunos vinculados (opcional)" items={students.filter((item) => item.status === "ATIVO" || form.student_ids.includes(item.id)).map((item) => ({ id: item.id, label: `${item.name} · ${classes.find((schoolClass) => schoolClass.id === item.class_id)?.name ?? "Turma"}${item.status === "INATIVO" ? " (desativado)" : ""}` }))} selected={form.student_ids} onChange={(student_ids) => onChange({ ...form, student_ids })} />
    <SaveButton saving={saving} editing={!!form.id} />
  </form>;
}

function InactiveButton({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  return <button type="button" aria-pressed={visible} onClick={onToggle} className="mb-4 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50">{visible ? "Ocultar desativados" : "Mostrar desativados"}</button>;
}

function ClassFilter({ classes, value, onChange, label, unassignedLabel }: { classes: SchoolClass[]; value: string; onChange: (value: string) => void; label: string; unassignedLabel?: string }) {
  return <select aria-label={label} className="input mb-4" value={value} onChange={(event) => onChange(event.target.value)}><option value="">Todas as turmas</option>{unassignedLabel && <option value="none">{unassignedLabel}</option>}{classes.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.year}{item.is_active ? "" : " (desativada)"}</option>)}</select>;
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) { return <div className="mb-5"><h1 className="text-2xl font-semibold">{title}</h1><p className="mt-1 text-sm text-slate-600">{subtitle}</p></div>; }
function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="relative mb-4 block"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input className="input w-full pl-9" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} /></label>; }
function SaveButton({ saving, editing }: { saving: boolean; editing: boolean }) { return <button disabled={saving} className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : editing ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}{editing ? "Salvar alterações" : "Cadastrar"}</button>; }
function CheckList({ title, items, selected, onChange }: { title: string; items: { id: number; label: string }[]; selected: number[]; onChange: (ids: number[]) => void }) { return <fieldset className="rounded-xl border border-slate-200 p-3 md:col-span-2"><legend className="px-1 text-xs font-medium text-slate-500">{title}</legend><div className="flex flex-wrap gap-3">{items.length ? items.map((item) => <label key={item.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(item.id)} onChange={() => onChange(selected.includes(item.id) ? selected.filter((id) => id !== item.id) : [...selected, item.id])} />{item.label}</label>) : <span className="text-sm text-slate-400">Nenhuma opção disponível.</span>}</div></fieldset>; }
function DataList({ empty, children }: { empty: string; children: React.ReactNode }) { return <div className="space-y-2">{Array.isArray(children) && children.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">{empty}</div> : children}</div>; }
function Row({ title, subtitle, inactive, active, onOpen, openLabel = "Abrir fotos", onEdit, onToggle }: { title: string; subtitle: string; inactive: boolean; active: boolean; onOpen?: () => void; openLabel?: string; onEdit: () => void; onToggle: () => void }) { return <div className={`flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center ${inactive ? "opacity-60" : ""}`}><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${active ? "bg-green-50 text-green-700" : "bg-slate-100 text-slate-500"}`}>{active ? <CheckCircle2 className="h-5 w-5" /> : <Archive className="h-5 w-5" />}</span><div className="min-w-0 flex-1"><p className="font-medium">{title}</p><p className="truncate text-sm text-slate-500">{subtitle}</p></div><div className="flex gap-2">{onOpen && <button onClick={onOpen} className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700">{openLabel}</button>}<button onClick={onEdit} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50"><Pencil className="mr-1 inline h-3.5 w-3.5" />Editar</button><button onClick={onToggle} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50">{active ? "Desativar" : "Reativar"}</button></div></div>; }
function Notice({ tone, onClose, children }: { tone: "error" | "success"; onClose: () => void; children: React.ReactNode }) { return <div role={tone === "error" ? "alert" : "status"} className={`mb-4 flex items-center justify-between rounded-xl border p-4 text-sm ${tone === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-green-200 bg-green-50 text-green-800"}`}><span>{children}</span><button onClick={onClose}><X className="h-4 w-4" /></button></div>; }
