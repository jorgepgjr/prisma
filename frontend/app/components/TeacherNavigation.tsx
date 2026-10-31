import Link from "next/link";
import { Images, UsersRound } from "lucide-react";

export default function TeacherNavigation({ current }: { current: "classes" | "publications" }) {
  const links = [
    { href: "/", label: "Minhas turmas", id: "classes", Icon: UsersRound },
    { href: "/publications", label: "Publicações", id: "publications", Icon: Images },
  ];
  return <nav aria-label="Navegação do professor" className="border-b border-slate-200 bg-white">
    <div className="mx-auto flex max-w-6xl gap-6 px-5">
      {links.map(({ href, label, id, Icon }) => <Link key={id} href={href} aria-current={current === id ? "page" : undefined}
        className={`relative flex min-h-12 items-center gap-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-blue-600 ${current === id ? "text-blue-700 after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:rounded-full after:bg-blue-600" : "text-slate-600 hover:text-slate-900"}`}>
        <Icon className="h-4 w-4" aria-hidden="true" />{label}
      </Link>)}
    </div>
  </nav>;
}
