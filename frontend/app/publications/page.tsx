"use client";

import { Suspense } from "react";
import { LoaderCircle } from "lucide-react";
import PublicationsWorkspace from "./PublicationsWorkspace";

export default function PublicationsPage() {
  return <Suspense fallback={<div role="status" aria-label="Carregando" className="grid min-h-64 place-items-center"><LoaderCircle className="h-7 w-7 animate-spin text-blue-600" /></div>}><PublicationsWorkspace /></Suspense>;
}
