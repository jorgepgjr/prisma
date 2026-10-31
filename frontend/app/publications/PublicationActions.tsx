"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Eye, MoreVertical, Pencil, Trash2 } from "lucide-react";

export type PublicationAction = "view" | "edit" | "delete";

export default function PublicationActions({ canManage, onAction, showView = true, label = "Ações da publicação" }: {
  canManage: boolean; onAction: (action: PublicationAction) => void; showView?: boolean; label?: string;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const id = useId();
  function close(restore = true) { setOpen(false); if (restore) trigger.current?.focus({ preventScroll: true }); }
  useEffect(() => {
    if (!open) return;
    menu.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    function outside(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    function focusOutside(event: FocusEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", focusOutside);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("focusin", focusOutside); };
  }, [open]);
  if (!canManage && !showView) return null;
  const actions = [...(showView ? [{ id: "view" as const, label: "Ver detalhes", Icon: Eye }] : []),
    ...(canManage ? [{ id: "edit" as const, label: "Editar", Icon: Pencil }, { id: "delete" as const, label: "Excluir", Icon: Trash2 }] : [])];
  return <div ref={root} className="relative shrink-0 self-start" onClick={(event) => event.stopPropagation()}>
    <button ref={trigger} type="button" aria-label={label} aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => setOpen(!open)} onKeyDown={(event) => { if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); setOpen(true); } }}
      className={`grid h-10 w-10 place-items-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-blue-600 ${open ? "bg-slate-100 text-slate-900" : ""}`}>
      <MoreVertical aria-hidden="true" className="h-5 w-5" strokeWidth={1.5} />
    </button>
    {open && <div id={id} ref={menu} role="menu" aria-label="Ações" className="absolute right-0 top-11 z-30 w-44 rounded-xl border border-slate-200 bg-white p-1 shadow-lg shadow-slate-900/10"
      onKeyDown={(event) => {
        const items = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? []);
        const index = items.indexOf(document.activeElement as HTMLButtonElement);
        if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
        else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (index + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
          items[next]?.focus();
        }
      }}>
      {actions.map(({ id: action, label: text, Icon }) => <button type="button" role="menuitem" tabIndex={-1} key={action}
        onClick={() => { close(); onAction(action); }} className={`flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm outline-none hover:bg-slate-50 focus:bg-slate-100 ${action === "delete" ? "text-red-700" : "text-slate-700"}`}>
        <Icon aria-hidden="true" className="h-4 w-4" strokeWidth={1.5} />{text}
      </button>)}
    </div>}
  </div>;
}
