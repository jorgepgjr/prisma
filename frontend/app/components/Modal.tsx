"use client";

import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";

export default function Modal({ title, onClose, children, busy = false }: {
  title: string; onClose: () => void; children: React.ReactNode; busy?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const heading = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    return () => { document.body.style.overflow = overflow; previous?.focus(); };
  }, []);
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4" onMouseDown={() => { if (!busy) onClose(); }}>
    <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={heading} tabIndex={-1}
      onMouseDown={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !busy) { event.stopPropagation(); onClose(); }
        if (event.key !== "Tab") return;
        const elements = ref.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]');
        if (!elements?.length) { event.preventDefault(); return; }
        const first = elements[0], last = elements[elements.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || document.activeElement === ref.current)) { event.preventDefault(); first.focus(); }
      }} className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl outline-none sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-4"><h2 id={heading} className="text-lg font-semibold text-slate-900">{title}</h2><button type="button" onClick={onClose} disabled={busy} aria-label="Fechar" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-40"><X className="h-5 w-5" /></button></div>
      {children}
    </div>
  </div>;
}
