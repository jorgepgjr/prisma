"use client";

import NextImage from "next/image";
import { ImageIcon } from "lucide-react";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const mediaUrl = (url: string) => !url ? "" : url.startsWith("http") ? url : `${API_URL}${url}`;

export default function PublicationImage({ src, alt, className = "object-cover" }: {
  src: string; alt: string; className?: string; fill?: boolean; unoptimized?: boolean;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return !src || failedUrl === src ? <div className="absolute inset-0 grid place-content-center gap-1 bg-slate-100 p-2 text-center text-xs text-slate-500">
    <ImageIcon aria-hidden="true" className="mx-auto h-5 w-5" />
    <span>Foto indisponível</span>
    {src && <button type="button" onClick={(event) => { event.stopPropagation(); setFailedUrl(null); }} className="min-h-8 underline underline-offset-2">Tentar carregar</button>}
  </div> : <NextImage src={mediaUrl(src)} alt={alt} fill unoptimized sizes="(max-width: 640px) 100vw, 560px" className={className} onError={() => setFailedUrl(src)} />;
}
