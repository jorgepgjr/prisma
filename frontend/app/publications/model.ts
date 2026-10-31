export type SchoolClass = { id: number; name: string; year: number; is_active: boolean };
export type Post = {
  id: string; class_id: number | null; created_by_user_id: number | null; classroom_name: string;
  teacher_name: string; created_at: string; caption: string; image_url: string; image_urls: string[];
  photo_ids: number[]; student_ids: number[]; child_names: string[]; can_manage: boolean;
};
export type DateFilter = "all" | "today" | "week" | "month" | "custom";
export type PublicationFilters = { search: string; date: DateFilter; from: string; to: string; sort: "newest" | "oldest" };
export const INITIAL_FILTERS: PublicationFilters = { search: "", date: "all", from: "", to: "", sort: "newest" };
export const PAGE_SIZE = 25;
const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");

// Compare calendar days in the user's timezone, not UTC midnight.
export function localDay(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function filterPublications(posts: Post[], filters: PublicationFilters, now = new Date()): Post[] {
  const today = localDay(now);
  const week = new Date(now); week.setDate(week.getDate() - 6);
  const month = `${today.slice(0, 7)}-01`;
  const term = normalize(filters.search.trim());
  return posts.filter((post) => {
    if (term && !normalize([post.caption, post.classroom_name, post.teacher_name, ...post.child_names].join(" ")).includes(term)) return false;
    const date = new Date(post.created_at);
    if (filters.date === "all") return true;
    if (!Number.isFinite(date.getTime())) return false;
    const day = localDay(date);
    if (filters.date === "today") return day === today;
    if (filters.date === "week") return day >= localDay(week) && day <= today;
    if (filters.date === "month") return day >= month && day <= today;
    return (!filters.from || day >= filters.from) && (!filters.to || day <= filters.to);
  }).sort((a, b) => {
    const difference = (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0);
    return (filters.sort === "newest" ? difference : -difference) || a.id.localeCompare(b.id);
  });
}

export function postImages(post: Post): string[] {
  return post.image_urls?.length ? post.image_urls : post.image_url ? [post.image_url] : [];
}
export function formatDate(value: string, full = false): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Data não informada";
  return full ? date.toLocaleString("pt-BR", { dateStyle: "long", timeStyle: "short" }) : date.toLocaleDateString("pt-BR");
}
