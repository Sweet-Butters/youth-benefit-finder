// Reads the crawler's output (../data/collected/items.json) at build time, for the "공식 자동" tier:
// collected from an official source, not yet checked by a person. A missing, empty or broken file means no items.
// Repeated rounds of one exam (Q-Net) become one entry with a list of windows so the panel is not flooded.

export interface CollectedItem {
  source: string; source_id: string; type: string; title: string; provider: string; url: string; summary?: string;
  apply_start?: string | null; apply_end?: string | null; regions?: string[]; tags?: string[]; cost_text?: string;
  target_text?: string; step_ids?: string[]; last_seen?: string; status?: string;
}
export interface AutoWindow { s: string; e: string; k: string }
export interface AutoGroup {
  id: string; source: string; sourceLabel: string; type: string; title: string; provider: string; url: string;
  summary: string; regions: string[]; stepIds: string[]; costText: string; seen: string;
  /** "out_of_school" only when the item itself is for 학교 밖 청소년; otherwise "any". */
  audience: "any" | "out_of_school";
  /** The crawler thinks 학교 밖 청소년 can apply (tag out_of_school_ok or open_to_all). A hint, not a filter. */
  outOfSchoolOk: boolean;
  /** Open or upcoming application windows, soonest first. */
  windows: AutoWindow[];
}

const SOURCE_LABEL: Record<string, string> = { qnet: "큐넷", kosaf: "한국장학재단", certi: "청소년활동정보서비스", vms: "1365 자원봉사" };
const ISO = /^\d{4}-\d{2}-\d{2}$/;

function load(): { updatedAt: string; items: CollectedItem[] } {
  const raw = Object.values(import.meta.glob("../../../data/collected/items.json", { eager: true, query: "?raw", import: "default" }))[0];
  if (typeof raw !== "string" || !raw.trim()) return { updatedAt: "", items: [] };
  try {
    const d = JSON.parse(raw);
    const items = Array.isArray(d) ? d : Array.isArray(d?.items) ? d.items : [];
    return { updatedAt: typeof d?.updatedAt === "string" ? d.updatedAt : "", items };
  } catch {
    return { updatedAt: "", items: [] };
  }
}
const data = load();

// "한식조리기능사 2026년 16회 실기 원서접수" -> name "한식조리기능사 원서접수", kind "실기".
const ROUND = /\s*\d{4}년\s*\d+회\s*(필기|실기)?\s*/;
const groupKey = (it: CollectedItem) => {
  const exam = it.source === "qnet" && it.tags?.find((t) => t.startsWith("qnet:"));
  return exam ? `auto-${exam.replace(":", "-")}` : `auto-${it.source}-${it.source_id}`;
};

export function autoGroups(): AutoGroup[] {
  const live = data.items.filter(
    (it) => it && it.url && it.title && (it.status === "open" || it.status === "upcoming") && ISO.test(it.apply_end ?? ""),
  );
  const byKey = new Map<string, CollectedItem[]>();
  for (const it of live) byKey.set(groupKey(it), [...(byKey.get(groupKey(it)) ?? []), it]);
  const fallbackSeen = data.updatedAt.slice(0, 10);
  return [...byKey.entries()].map(([id, its]) => {
    const first = its[0];
    const grouped = its.length > 1;
    const text = `${first.title} ${first.target_text ?? ""}`;
    const tags = new Set(its.flatMap((i) => i.tags ?? []));
    const windows = its
      .map((i) => ({ s: ISO.test(i.apply_start ?? "") ? i.apply_start! : i.apply_end!, e: i.apply_end!, k: ROUND.exec(i.title)?.[1] ?? "" }))
      .sort((a, b) => (a.s < b.s ? -1 : a.s > b.s ? 1 : a.e < b.e ? -1 : 1));
    return {
      id,
      source: first.source,
      sourceLabel: SOURCE_LABEL[first.source] ?? first.provider,
      type: first.type,
      title: grouped || first.source === "qnet" ? first.title.replace(ROUND, " ").replace(/\s+/g, " ").trim() : first.title,
      provider: first.provider,
      url: first.url,
      summary: grouped ? "" : first.summary ?? "",
      regions: first.regions?.length ? first.regions : ["all"],
      stepIds: [...new Set(its.flatMap((i) => i.step_ids ?? []))],
      costText: grouped ? "" : first.cost_text ?? "",
      seen: its.map((i) => i.last_seen ?? "").filter((s) => ISO.test(s)).sort().pop() ?? fallbackSeen,
      audience: first.type === "scholarship" && /학교\s*밖/.test(text) ? "out_of_school" : "any",
      outOfSchoolOk: tags.has("out_of_school_ok") || tags.has("open_to_all"),
      windows,
    };
  });
}
