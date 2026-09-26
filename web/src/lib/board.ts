// The public benefits board (/helps/, D26): every youth benefit the crawler collected, step or general,
// all at the "공식 자동" tier. Built from the same items.json as lib/collected.ts, with repeated rounds grouped:
// Q-Net by exam, 봉사·체험 by title + provider, so one entry keeps a list of its windows or sessions.
// Dates are judged in Korean time at build; the pages re-check them in the browser so a stale build never
// shows a passed deadline as open.
import { collected, boardId, boardKey, SOURCE_LABEL, type CollectedItem } from "./collected";
import { REGION_LABEL } from "./content";

export type KindKey = "scholarship" | "volunteer" | "activity" | "exam";
export const KIND: Record<KindKey, string> = { scholarship: "장학금", volunteer: "봉사", activity: "체험", exam: "시험" };
export const KIND_ORDER: KindKey[] = ["scholarship", "volunteer", "activity", "exam"];
const KIND_OF: Record<string, KindKey> = { kosaf: "scholarship", volunteer: "volunteer", certi: "activity", qnet: "exam" };

/** One application window. s..e is when to apply; ev is the activity or exam day, when known; k is 필기/실기. */
export interface BoardWindow { s: string; e: string; ev?: string; k?: string }
export interface BoardRow { label: string; value: string; list?: string[] }
export type BoardStatus = "open" | "upcoming" | "check";
export const STATUS_LABEL: Record<BoardStatus, string> = { open: "접수 중", upcoming: "곧 열림", check: "일정 확인" };

export interface BoardEntry {
  id: string; source: string; sourceLabel: string; kind: KindKey; kindLabel: string;
  title: string; provider: string; summary: string; url: string; seen: string;
  regions: string[]; regionLabel: string; stepIds: string[]; scope: "step" | "general";
  /** Apply-based sources (장학금, 봉사, 시험): windows still open or ahead at build, soonest deadline first. */
  windows: BoardWindow[];
  /** 체험 (certi) has no apply dates, only session days (event dates) still ahead at build. */
  sessions: string[];
  cost: string; target: string;
  /** The Dreamspon-style info table for the detail page, empty rows already dropped. */
  rows: BoardRow[];
  /** The raw 한국장학재단 columns (grade, income, residence, ...), for anyone who needs them as they came. */
  extra: Record<string, string>;
  /** How many crawled items this entry groups. */
  count: number;
}

const ISO = /^\d{4}-\d{2}-\d{2}$/;
const isIso = (s: unknown): s is string => typeof s === "string" && ISO.test(s);
/** Today in Korea (UTC+9), as YYYY-MM-DD. */
export const todayKst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const md = (d: string) => `${+d.slice(5, 7)}월 ${+d.slice(8, 10)}일`;
const ymd = (d: string) => `${d.slice(0, 4)}년 ${+d.slice(5, 7)}월 ${+d.slice(8, 10)}일`;
export const rangeLabel = (s: string, e: string) => (s === e ? ymd(s) : s.slice(0, 4) === e.slice(0, 4) ? `${ymd(s)} ~ ${md(e)}` : `${ymd(s)} ~ ${ymd(e)}`);
export const shortRange = (s: string, e: string) => (s === e ? md(s) : `${md(s)}~${md(e)}`);
export { md, ymd };

// "한식조리기능사 2026년 16회 실기 원서접수" -> "한식조리기능사 원서접수", kind "실기" (same rule as collected.ts).
const ROUND = /\s*\d{4}년\s*\d+회\s*(필기|실기)?\s*/;
const str = (v: unknown) => (v == null ? "" : String(v).replace(/\s+/g, " ").trim());
/** "기관확인필요" and friends read better as a sentence; "해당없음" and blanks are dropped. */
const tidy = (v: unknown) => {
  const s = str(v);
  if (!s || s === "해당없음" || s === "-") return "";
  return s.replace(/^기관\s*확인\s*필요$/, "기관에 확인 필요").replace(/^대학\s*확인\s*필요$/, "대학에 확인 필요");
};
/** Split "A / B / C※ note" into items for a list. */
const splitList = (s: string) => s.split(/\s+\/\s+|※/).map((x) => x.trim()).filter(Boolean);
// 봉사 providers are really the activity place, sometimes with a "집결 장소 :" prefix.
const cleanPlace = (s: string) => s.replace(/^집결\s*장소\s*[:：]\s*/, "").trim();
const uniq = <T>(xs: T[]) => [...new Set(xs)];

function rowsFor(kind: KindKey, its: CollectedItem[], e: Omit<BoardEntry, "rows">): BoardRow[] {
  const first = its[0];
  const x = (first.extra ?? {}) as Record<string, unknown>;
  const all = (k: string) => uniq(its.map((i) => tidy((i.extra as Record<string, unknown> | undefined)?.[k])).filter(Boolean));
  const next = e.windows[0];
  const apply = next ? rangeLabel(next.s, next.e) : "";
  const rows: (BoardRow | null)[] = [];
  const row = (label: string, value: string, list?: string[]) => rows.push(value || list?.length ? { label, value, list } : null);
  if (kind === "scholarship") {
    row("장학종류", [tidy(x.aid_kind), tidy(x.provider_kind) && `${tidy(x.provider_kind)} 운영`].filter(Boolean).join(" · "));
    row("선발대상", e.target);
    row("장학혜택", e.cost);
    row("신청기간", apply);
    row("지역", e.regionLabel);
    row("거주 조건", tidy(x.residence));
    row("성적 기준", tidy(x.grade));
    row("소득 기준", tidy(x.income));
    row("선발인원", tidy(x.quota));
    row("선발방법", tidy(x.selection));
    row("추천", tidy(x.recommendation));
    const docs = tidy(x.documents);
    row("제출서류", "", docs ? splitList(docs) : []);
    const rest = tidy(x.restrictions);
    row("제한 사항", "", rest ? splitList(rest) : []);
    row("운영기관", e.provider);
  } else if (kind === "volunteer") {
    row("봉사 분야", uniq([tidy(x.vlntwkDtlTypeNm), tidy(x.vlntwkDtlCnNm)].filter(Boolean)).join(" · "));
    row("모집대상", e.target);
    const hours = all("certHr").map((h) => `${h}시간`).join(" / ");
    row("봉사시간", hours && `${hours} 인정`);
    row("모집인원", all("rcrtNope").map((n) => `${n}명`).join(" / ") + (its.length > 1 && all("rcrtNope").length ? " (회차마다)" : ""));
    row("신청기간", apply);
    row("활동일", next?.ev ? ymd(next.ev) + (e.windows.length > 1 ? ` 외 ${e.windows.length - 1}회` : "") : "");
    row("지역", [e.regionLabel, tidy(x.actvSggNm)].filter(Boolean).join(" "));
    row("활동 장소", uniq(its.map((i) => cleanPlace(i.provider))).join(" / "));
    row("활동 내용", tidy(x.mainCn));
    if (tidy(x.actcn) !== tidy(x.mainCn)) row("세부 일정", tidy(x.actcn));
    row("비용", e.cost);
  } else if (kind === "activity") {
    const age = first.age_min != null && first.age_max != null ? `${first.age_min}~${first.age_max}살`
      : first.age_min != null ? `${first.age_min}살부터` : first.age_max != null ? `${first.age_max}살까지` : "";
    row("활동 종류", "국가 인증 청소년 수련활동");
    row("참가대상", e.target);
    row("나이", age);
    row("참가비", e.cost);
    row("다음 활동일", e.sessions[0] ? ymd(e.sessions[0]) + (e.sessions.length > 1 ? ` 외 ${e.sessions.length - 1}회` : "") : "");
    row("신청 마감", "활동일 전에 운영 기관에서 확인");
    row("지역", e.regionLabel);
    row("운영기관", e.provider);
    row("인증번호", tidy(x.certNo));
    row("인증일", isIso(x.registered) ? ymd(x.registered) : "");
  } else {
    const open = its.some((i) => i.tags?.includes("open_to_all"));
    row("시험", e.title.replace(/\s*원서접수$/, ""));
    row("시행", tidy(x.description).replace(/\s*\(\d{4}년도 제\d+회\)$/, ""));
    row("다음 접수", next ? apply + (next.k ? ` · ${next.k}` : "") : "");
    row("시험일", next?.ev ? ymd(next.ev) : "");
    row("응시 자격", open ? "나이·학력 제한 없음" : "");
    row("지역", e.regionLabel);
    row("시행기관", e.provider);
  }
  return rows.filter((r): r is BoardRow => !!r);
}

function build(): BoardEntry[] {
  const today = todayKst();
  const fallbackSeen = collected.updatedAt.slice(0, 10);
  const byKey = new Map<string, CollectedItem[]>();
  const keyOf = new Map<string, string>();
  for (const it of collected.items) {
    if (!it || !it.url || !it.title || !KIND_OF[it.source]) continue;
    if (it.status === "closed") continue;
    if (it.source === "certi") {
      const next = [it.event_start, ...(((it.extra?.sessions as unknown[]) ?? []))].filter(isIso).some((d) => d >= today);
      if (!next) continue;
    } else if (!(it.status === "open" || it.status === "upcoming") || !isIso(it.apply_end) || it.apply_end < today) continue;
    const id = boardId(it);
    const key = `${it.source}|${boardKey(it)}`;
    if ((keyOf.get(id) ?? key) !== key) throw new Error(`board id collision: ${id} for "${keyOf.get(id)}" and "${key}"`);
    keyOf.set(id, key);
    byKey.set(id, [...(byKey.get(id) ?? []), it]);
  }
  return [...byKey.entries()].map(([id, its]) => {
    const first = its[0];
    const kind = KIND_OF[first.source];
    const regions = uniq(its.flatMap((i) => (i.regions?.length ? i.regions : ["all"])));
    const windows: BoardWindow[] = kind === "activity" ? [] : its
      .map((i) => ({
        s: isIso(i.apply_start) ? i.apply_start : i.apply_end!, e: i.apply_end!,
        ...(isIso(i.event_start) ? { ev: i.event_start } : {}),
        ...(ROUND.exec(i.title)?.[1] ? { k: ROUND.exec(i.title)![1] } : {}),
      }))
      .sort((a, b) => (a.e < b.e ? -1 : a.e > b.e ? 1 : (a.ev ?? "") < (b.ev ?? "") ? -1 : 1));
    const sessions = kind !== "activity" ? [] : uniq(its.flatMap((i) => [i.event_start, ...((i.extra?.sessions as unknown[]) ?? [])]).filter(isIso))
      .filter((d) => d >= today).sort();
    const extra = kind === "scholarship"
      ? Object.fromEntries(Object.entries(first.extra ?? {}).map(([k, v]) => [k, str(v)]).filter(([, v]) => v))
      : {};
    const base: Omit<BoardEntry, "rows"> = {
      id, source: first.source, sourceLabel: SOURCE_LABEL[first.source] ?? first.provider, kind, kindLabel: KIND[kind],
      title: kind === "exam" || its.length > 1 ? first.title.replace(ROUND, " ").replace(/\s+/g, " ").trim() : str(first.title),
      provider: kind === "volunteer" ? cleanPlace(str(first.provider)) : str(first.provider),
      // A grouped exam spans 필기 and 실기 rounds, so the first round's wording is made general.
      summary: kind === "exam" && its.length > 1 ? str(first.summary).replace(/\s*(필기|실기)\s+시험/, " 시험") : str(first.summary), url: first.url,
      seen: its.map((i) => i.last_seen ?? "").filter(isIso).sort().pop() ?? fallbackSeen,
      regions, regionLabel: regions.includes("all") ? "전국" : regions.map((r) => REGION_LABEL[r] ?? r).join(" · "),
      stepIds: uniq(its.flatMap((i) => i.step_ids ?? [])),
      scope: its.some((i) => i.scope === "step" || i.step_ids?.length) ? "step" : "general",
      windows, sessions, cost: str(first.cost_text), target: str(first.target_text), extra, count: its.length,
    };
    return { ...base, rows: rowsFor(kind, its, base) };
  });
}

/** State on a given day: open (apply window has started), upcoming, or check (체험: only a session day is known). */
export function stateOn(e: Pick<BoardEntry, "windows" | "sessions">, today: string) {
  const w = e.windows.filter((x) => x.e >= today);
  const s = e.sessions.filter((d) => d >= today);
  if (w.length) {
    const open = w.find((x) => x.s <= today);
    const pick = open ?? w[0];
    return { status: (open ? "open" : "upcoming") as BoardStatus, window: pick, date: open ? pick.e : pick.s, sortKey: pick.e, live: true };
  }
  if (s.length) return { status: "check" as BoardStatus, window: undefined, date: s[0], sortKey: s[0], live: true };
  return { status: "check" as BoardStatus, window: undefined, date: "", sortKey: "9999", live: false };
}
export const daysBetween = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);

let cache: BoardEntry[] | null = null;
/** Every board entry, soonest deadline (or next 활동일) first. Ids are unique; a collision fails the build. */
export function boardEntries(): BoardEntry[] {
  if (cache) return cache;
  const today = todayKst();
  const list = build().sort((a, b) => {
    const x = stateOn(a, today).sortKey, y = stateOn(b, today).sortKey;
    return x < y ? -1 : x > y ? 1 : a.title.localeCompare(b.title, "ko");
  });
  cache = list;
  return list;
}
