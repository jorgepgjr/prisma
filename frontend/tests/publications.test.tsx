import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import PublicationActions from "../app/publications/PublicationActions";
import PublicationDrawer from "../app/publications/PublicationDrawer";
import PublicationImage from "../app/publications/PublicationImage";
import PublicationsWorkspace from "../app/publications/PublicationsWorkspace";
import { filterPublications, INITIAL_FILTERS, localDay, postImages, type Post } from "../app/publications/model";

const { replace, auth, query } = vi.hoisted(() => ({
  replace: vi.fn(), query: { current: new URLSearchParams() },
  auth: { user: { id: 1, name: "Professora de teste", role: "PROFESSOR", school: { name: "Escola de teste" } }, token: "test-token", loading: false },
}));
const router = { replace };
vi.mock("next/navigation", () => ({ useRouter: () => router, useSearchParams: () => query.current }));
vi.mock("../context/AuthContext", () => ({ useAuth: () => auth }));
vi.mock("next/link", () => ({ default: ({ children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a {...props}>{children}</a> }));
// eslint-disable-next-line @next/next/no-img-element -- Mock only: no src and no external image requests in DOM tests.
vi.mock("next/image", () => ({ default: ({ src, alt, className, onError }: { src: string; alt: string; className?: string; onError?: () => void }) => <img alt={alt} data-src={src} className={className} onError={onError} /> }));

const post: Post = {
  id: "p1", class_id: 1, created_by_user_id: 1, classroom_name: "Grupo 2", teacher_name: "Professora Ana",
  created_at: "2026-10-30T10:00:00", caption: "Sofia desenhando\nUma manhã com muitas cores.", image_url: "/photo-1.jpg", image_urls: ["/photo-1.jpg", "/photo-2.jpg"],
  photo_ids: [1, 2], student_ids: [1], child_names: ["Sofia"], can_manage: true,
};
const classes = [{ id: 1, name: "Grupo 2", year: 2026, is_active: true }];
const other = { ...post, id: "p2", caption: "Brincadeiras no jardim", can_manage: false, teacher_name: "Professor Bruno", created_at: "2026-10-22T10:00:00" };
function mockApi(posts = [post, other]) {
  const fetcher = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    void init;
    const url = String(input);
    const data = url.includes("/api/classes/") ? classes
      : url.includes("/api/photos/class/") ? [{ id: 1, media_url: "/photo-1.jpg", publication_count: 1 }, { id: 2, media_url: "/photo-2.jpg", publication_count: 1 }]
      : url.includes("/api/students/class/") ? [{ id: 1, name: "Sofia", child_id: "child-1" }]
      : url.endsWith("/api/posts/p1") ? post : url.endsWith("/api/posts/p2") ? other : posts;
    return { ok: true, json: async () => data } as Response;
  });
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); query.current = new URLSearchParams(); auth.user.role = "PROFESSOR"; });

describe("filters on real publication fields", () => {
  const now = new Date(2026, 9, 30, 15);
  it("searches caption, teacher, class and linked students without changing records", () => {
    for (const search of ["SOFIA", "manhã", "manha", "Grupo 2", "Professora Ana"]) {
      expect(filterPublications([post], { ...INITIAL_FILTERS, search }, now)).toEqual([post]);
    }
    expect(filterPublications([post], { ...INITIAL_FILTERS, search: "não existe" }, now)).toEqual([]);
  });
  it("sorts chronologically, without mutating the API array", () => {
    const input = [other, post];
    expect(filterPublications(input, INITIAL_FILTERS, now).map((p) => p.id)).toEqual(["p1", "p2"]);
    expect(filterPublications(input, { ...INITIAL_FILTERS, sort: "oldest" }, now).map((p) => p.id)).toEqual(["p2", "p1"]);
    expect(input.map((p) => p.id)).toEqual(["p2", "p1"]);
  });
  it("combines dates with search, using local calendar boundaries", () => {
    expect(localDay(new Date(2026, 9, 30, 0, 1))).toBe("2026-10-30");
    for (const date of ["today", "week"] as const) expect(filterPublications([post, other], { ...INITIAL_FILTERS, date }, now)).toEqual([post]);
    expect(filterPublications([post, other], { ...INITIAL_FILTERS, date: "month" }, now)).toHaveLength(2);
    expect(filterPublications([post, other], { ...INITIAL_FILTERS, date: "custom", from: "2026-10-30", to: "2026-10-30", search: "cores" }, now)).toEqual([post]);
    expect(filterPublications([post], { ...INITIAL_FILTERS, date: "custom", from: "2026-11-01", to: "2026-10-01" }, now)).toEqual([]);
  });
  it("preserves the cover fallback of legacy publications", () => {
    expect(postImages({ ...post, image_urls: [] })).toEqual([post.image_url]);
    expect(postImages({ ...post, image_urls: [], image_url: "" })).toEqual([]);
  });
});

describe("contextual actions", () => {
  it("supports keyboard navigation, Escape and focus restoration without opening the row", async () => {
    const user = userEvent.setup(), onRow = vi.fn(), onAction = vi.fn();
    render(<div onClick={onRow}><PublicationActions canManage onAction={onAction} /></div>);
    const trigger = screen.getByRole("button", { name: "Ações da publicação" });
    trigger.focus(); await user.keyboard("{ArrowDown}");
    expect(document.activeElement?.textContent).toBe("Ver detalhes");
    await user.keyboard("{ArrowDown}"); expect(document.activeElement?.textContent).toBe("Editar");
    await user.keyboard("{End}"); expect(document.activeElement?.textContent).toBe("Excluir");
    await user.keyboard("{Escape}"); expect(document.activeElement).toBe(trigger);
    await user.click(trigger); await user.click(screen.getByRole("menuitem", { name: "Editar" }));
    expect(onAction).toHaveBeenCalledWith("edit"); expect(onRow).not.toHaveBeenCalled();
  });
  it("offers only viewing when the server denies management", async () => {
    render(<PublicationActions canManage={false} onAction={vi.fn()} />);
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getAllByRole("menuitem").map((item) => item.textContent)).toEqual(["Ver detalhes"]);
  });
  it("closes on outside interaction", async () => {
    render(<><PublicationActions canManage onAction={vi.fn()} /><button>Fora</button></>);
    await userEvent.click(screen.getByRole("button", { name: "Ações da publicação" }));
    await userEvent.click(screen.getByRole("button", { name: "Fora" }));
    expect(screen.queryByRole("menu")).toBeNull();
  });
});

describe("publication drawer", () => {
  it("shows full caption and metadata, navigates images and enlarges without cropping", async () => {
    const user = userEvent.setup(), onClose = vi.fn();
    render(<PublicationDrawer post={post} loading={false} error="" onClose={onClose} onRetry={vi.fn()} onAction={vi.fn()} />);
    expect(screen.getByRole("region", { name: "Legenda completa" }).textContent).toBe(post.caption);
    expect(screen.getByRole("img", { name: "Foto 1 da publicação" }).className).toContain("object-contain");
    expect(screen.getByRole("button", { name: "Foto anterior" }).hasAttribute("disabled")).toBe(true);
    await user.click(screen.getByRole("button", { name: "Próxima foto" }));
    expect(screen.getByRole("status").textContent).toBe("2 de 2");
    await user.click(screen.getByRole("button", { name: "Ampliar fotografia" }));
    expect(screen.getAllByRole("dialog")).toHaveLength(2);
    expect(screen.getByRole("img", { name: "Foto ampliada 2" }).className).toContain("object-contain");
    await user.click(screen.getByRole("button", { name: "Fechar fotografia ampliada" }));
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Fechar publicação" })); expect(onClose).toHaveBeenCalledOnce();
  });
  it("exposes retry, loading, empty media and read-only states", () => {
    const retry = vi.fn();
    const props = { post: null, loading: true, error: "", onClose: vi.fn(), onRetry: retry, onAction: vi.fn() };
    const { rerender } = render(<PublicationDrawer {...props} />);
    expect(screen.getByRole("status", { name: "Carregando publicação" })).toBeTruthy();
    rerender(<PublicationDrawer {...props} loading={false} error="Falha de conexão" />);
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" })); expect(retry).toHaveBeenCalledOnce();
    rerender(<PublicationDrawer {...props} loading={false} post={{ ...other, image_url: "", image_urls: [] }} />);
    expect(screen.getByText("Nenhuma foto disponível")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Ações da publicação" })).toBeNull();
  });
  it("restores body scrolling and opener focus on close", () => {
    const opener = document.createElement("button"); document.body.appendChild(opener); opener.focus();
    document.body.style.overflow = "auto";
    const { unmount } = render(<PublicationDrawer post={post} loading={false} error="" onClose={vi.fn()} onRetry={vi.fn()} onAction={vi.fn()} />);
    expect(document.body.style.overflow).toBe("hidden"); unmount();
    expect(document.body.style.overflow).toBe("auto"); expect(document.activeElement).toBe(opener); opener.remove();
  });
  it("keeps an unavailable image visible and allows loading retry", () => {
    render(<div className="relative"><PublicationImage src="/missing.jpg" alt="Teste de falha" /></div>);
    fireEvent.error(screen.getByRole("img")); expect(screen.getByText("Foto indisponível")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Tentar carregar" })); expect(screen.getByRole("img")).toBeTruthy();
  });
});

describe("workspace integrated with existing API contracts", () => {
  it("preserves creation with real photo/student selections and the existing payload", async () => {
    const user = userEvent.setup(), fetcher = mockApi([]);
    render(<PublicationsWorkspace />); await screen.findByText("Ainda não há publicações");
    await user.click(screen.getByRole("button", { name: "Nova publicação" }));
    const dialog = screen.getByRole("dialog");
    await user.selectOptions(within(dialog).getByRole("combobox", { name: "Turma" }), "1");
    await within(dialog).findByRole("checkbox", { name: "Selecionar foto 1" });
    await user.type(within(dialog).getByRole("textbox", { name: "Legenda" }), "Uma atividade em família");
    await user.click(within(dialog).getByRole("checkbox", { name: "Selecionar foto 1" }));
    await user.click(within(dialog).getByRole("checkbox", { name: "Sofia" }));
    await user.click(within(dialog).getByRole("button", { name: "Publicar para as famílias" }));
    await screen.findByText("Publicação enviada às famílias.");
    const request = fetcher.mock.calls.find(([, init]) => init?.method === "POST");
    expect(request?.[0]).toContain("/api/posts/");
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ caption: "Uma atividade em família", photo_ids: [1], student_ids: [1] });
  });
  it("reuses edit without changing class, authorship or date", async () => {
    const user = userEvent.setup(), fetcher = mockApi([post]);
    render(<PublicationsWorkspace />); await screen.findByRole("button", { name: "Ver publicação: " + post.caption });
    await user.click(screen.getByRole("button", { name: /Ações da publicação: Sofia/ }));
    await user.click(screen.getByRole("menuitem", { name: "Editar" }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByRole("checkbox", { name: "Selecionar foto 1" });
    expect(within(dialog).getByRole("combobox", { name: "Turma" }).hasAttribute("disabled")).toBe(true);
    await user.clear(within(dialog).getByRole("textbox", { name: "Legenda" }));
    await user.type(within(dialog).getByRole("textbox", { name: "Legenda" }), "Legenda atualizada");
    await user.click(within(dialog).getByRole("button", { name: "Salvar alterações" }));
    await screen.findByText("Publicação atualizada para as famílias.");
    const request = fetcher.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(request?.[0]).toContain("/api/posts/p1");
    expect(JSON.parse(String(request?.[1]?.body))).toEqual({ caption: "Legenda atualizada", photo_ids: [1, 2], student_ids: [1] });
  });
  it("requires confirmation before deleting only the publication endpoint", async () => {
    const user = userEvent.setup(), fetcher = mockApi([post]);
    render(<PublicationsWorkspace />); await screen.findByRole("button", { name: "Ver publicação: " + post.caption });
    async function openDelete() {
      await user.click(screen.getByRole("button", { name: /Ações da publicação: Sofia/ }));
      await user.click(screen.getByRole("menuitem", { name: "Excluir" }));
      return await screen.findByRole("dialog");
    }
    let dialog = await openDelete();
    expect(dialog.textContent).toContain("As fotos continuarão na biblioteca da escola.");
    expect(fetcher.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    dialog = await openDelete();
    await user.click(within(dialog).getByRole("button", { name: "Excluir publicação" }));
    await screen.findByText("Publicação excluída. As fotos foram preservadas.");
    const requests = fetcher.mock.calls.filter(([, init]) => init?.method === "DELETE");
    expect(requests).toHaveLength(1); expect(requests[0][0]).toContain("/api/posts/p1");
  });
  it("keeps filters and sort after closing details, and opens the menu without fetching details", async () => {
    const user = userEvent.setup(), fetcher = mockApi();
    render(<PublicationsWorkspace />);
    await screen.findByRole("button", { name: "Ver publicação: " + post.caption });
    expect(fetcher.mock.calls[0][1]?.headers).toEqual({ Authorization: "Bearer test-token", "Content-Type": "application/json" });
    await user.type(screen.getByRole("searchbox"), "Sofia");
    await user.selectOptions(screen.getByRole("combobox", { name: "Ordenar publicações" }), "oldest");
    await user.click(screen.getByRole("button", { name: /Ações da publicação: Sofia/ }));
    expect(fetcher).toHaveBeenCalledTimes(2); expect(screen.queryByRole("dialog")).toBeNull();
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Ver publicação: " + post.caption }));
    await screen.findByRole("region", { name: "Legenda completa" });
    await user.click(screen.getByRole("button", { name: "Fechar publicação" }));
    expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe("Sofia");
    expect((screen.getByRole("combobox", { name: "Ordenar publicações" }) as HTMLSelectElement).value).toBe("oldest");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("loads only the authorized class through the existing class query", async () => {
    query.current = new URLSearchParams("class_id=1"); const fetcher = mockApi([post]);
    render(<PublicationsWorkspace />); await screen.findByRole("button", { name: "Ver publicação: " + post.caption });
    expect(String(fetcher.mock.calls[0][0])).toContain("/api/posts/?class_id=1");
    expect((screen.getByRole("combobox", { name: "Filtrar por turma" }) as HTMLSelectElement).value).toBe("1");
  });
  it("renders progressively and resets the batch on search", async () => {
    mockApi(Array.from({ length: 28 }, (_, i) => ({ ...post, id: "item" + i, caption: "Atividade " + i })));
    render(<PublicationsWorkspace />);
    await screen.findByRole("button", { name: "Carregar mais" });
    const list = screen.getByRole("region", { name: "Lista de publicações" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(25);
    await userEvent.click(screen.getByRole("button", { name: "Carregar mais" }));
    expect(within(list).getAllByRole("listitem")).toHaveLength(28);
    await userEvent.type(screen.getByRole("searchbox"), "não existe");
    expect(screen.getByText("Nenhuma publicação encontrada")).toBeTruthy();
  });
  it("reports initial failure and retries successfully", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Sem conexão")));
    render(<PublicationsWorkspace />); await screen.findByRole("alert");
    mockApi([]); await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await screen.findByText("Ainda não há publicações");
    expect(screen.getByRole("button", { name: "Nova publicação" }).hasAttribute("disabled")).toBe(false);
  });
  it("ignores late detail responses after the drawer is closed", async () => {
    const fetcher = mockApi();
    render(<PublicationsWorkspace />); await screen.findByRole("button", { name: "Ver publicação: " + post.caption });
    let resolve!: (value: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise<Response>((done) => { resolve = done; }));
    await userEvent.click(screen.getByRole("button", { name: "Ver publicação: " + post.caption }));
    await userEvent.click(screen.getByRole("button", { name: "Fechar publicação" }));
    await act(async () => resolve({ ok: true, json: async () => post } as Response));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("does not trust stale can_manage values when opening edit", async () => {
    const fetcher = mockApi([post]);
    render(<PublicationsWorkspace />); await screen.findByRole("button", { name: "Ver publicação: " + post.caption });
    fetcher.mockImplementationOnce(async () => ({ ok: true, json: async () => ({ ...post, can_manage: false }) }) as Response);
    await userEvent.click(screen.getByRole("button", { name: /Ações da publicação: Sofia/ }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Editar" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("permissão"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
