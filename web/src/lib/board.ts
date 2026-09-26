// The public benefits board (/helps/, D26): every youth benefit the crawler collected, step or general,
// all at the "공식 자동" tier. Built from the same items.json as lib/collected.ts, with repeated rounds grouped:
// Q-Net by exam, 봉사·체험 by title + place/provider, so one entry keeps a list of its windows or sessions.
// Dates are judged in Korean time at build; the pages re-check them in the browser so a stale build never
// shows a passed deadline as open. Items the board cannot place (unknown source and type, no title or link)
// are skipped, never a build failure; only an id collision fails the build.
import { collected, boardId, boardKey, SOURCE_LABEL, type CollectedItem } from "./collected";
import { REGION_LABEL } from "./content";

export type KindKey = "scholarship" | "support" | "volunteer" | "activity" | "exam";
export const KIND: Record<KindKey, string> = { scholarship: "장학금", support: "지원", volunteer: "봉사", activity: "체험", exam: "시험" };
export const KIND_ORDER: KindKey[] = ["scholarship", "support", "volunteer", "activity", "exam"];
export const KIND_COLOR: Record<KindKey, string> = {
  scholarship: "var(--line-1)", support: "var(--line-5)", volunteer: "var(--line-2)", activity: "var(--line-3)", exam: "var(--line-4)",
};
const KIND_BY_SOURCE: Record<string, KindKey> = { kosaf: "scholarship", volunteer: "volunteer", certi: "activity", qnet: "exam" };
// Any other source (보조금24 and later ones) is placed by its item type; a type not listed here is skipped.
const KIND_BY_TYPE: Record<string, KindKey> = { scholarship: "scholarship", support: "support" };
const kindOf = (it: CollectedItem): KindKey | undefined => KIND_BY_SOURCE[it.source] ?? KIND_BY_TYPE[it.type];

/** One application window. s..e is when to apply; ev is the activity or exam day, when known; k is 필기/실기. */
export interface BoardWindow { s: string; e: string; ev?: string; k?: string }
export interface BoardRow { label: string; value: string; list?: string[] }
/** always = 상시 (no deadline: apply any time, e.g. 보조금24 "상시신청"). */
export type BoardStatus = "open" | "upcoming" | "check" | "always";
export const STATUS_LABEL: Record<BoardStatus, string> = { open: "접수 중", upcoming: "곧 열림", check: "일정 확인", always: "상시" };

export interface BoardEntry {
  id: string; source: string; sourceLabel: string; kind: KindKey; kindLabel: string;
  title: string; provider: string; summary: string; url: string; seen: string;
  regions: string[]; regionLabel: string; stepIds: string[]; scope: "step" | "general";
  /** Apply-based sources (장학금, 봉사, 시험): windows still open or ahead at build, soonest deadline first. */
  windows: BoardWindow[];
  /** 체험 (certi) has no apply dates, only session days (event dates) still ahead at build. */
  sessions: string[];
  /** No dated window: the source says it takes applications any time ("상시"). */
  always: boolean;
  /** The source's own deadline wording when it has no date ("상시신청"), else "". */
  deadlineText: string;
  cost: string; target: string;
  /** The Dreamspon-style info table for the detail page, empty rows already dropped. */
  rows: BoardRow[];
  /** The raw 장학금 columns (grade, income, residence, ...), for anyone who needs them as they came. */
  extra: Record<string, string>;
  /** How many crawled items this entry groups. */
  count: number;
}

const ISO = /^\d{4}-\d{2}-\d{2}$/;
const isIso = (s: unknown): s is string => typeof s === "string" && ISO.test(s);
const ALWAYS = /상시/;
/** Today in Korea (UTC+9), as YYYY-MM-DD. */
export const todayKst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const md = (d: string) => `${+d.slice(5, 7)}월 ${+d.slice(8, 10)}일`;
const ymd = (d: string) => `${d.slice(0, 4)}년 ${+d.slice(5, 7)}월 ${+d.slice(8, 10)}일`;
export const rangeLabel = (s: string, e: string) => (s === e ? ymd(s) : s.slice(0, 4) === e.slice(0, 4) ? `${ymd(s)} ~ ${md(e)}` : `${ymd(s)} ~ ${ymd(e)}`);
export const shortRange = (s: string, e: string) => (s === e ? md(s) : `${md(s)}~${md(e)}`);
export { md, ymd };

// "한식조리기능사 2026년 16회 실기 원서접수" -> "한식조리기능사 원서접수", kind "실기" (same rule as collected.ts).
const ROUND = /\s*\d{4}년\s*\d+회\s*(필기|실기)?\s*/;
const str = (v: unknown) => (v == null || typeof v === "object" ? "" : String(v).replace(/\s+/g, " ").trim());
/** "기관확인필요" and friends read better as a sentence; "해당없음" and blanks are dropped. */
const tidy = (v: unknown) => {
  const s = str(v);
  if (!s || s === "해당없음" || s === "-") return "";
  return s.replace(/^기관\s*확인\s*필요$/, "기관에 확인 필요").replace(/^대학\s*확인\s*필요$/, "대학에 확인 필요");
};
/** Split "A / B / C※ note" into items for a list. */
const splitList = (s: string) => s.split(/\s+\/\s+|※/).map((x) => x.trim()).filter(Boolean);
// Old 봉사 items carried the place as provider, sometimes with a "집결 장소 :" prefix; kept only as a fallback.
const cleanPlace = (s: string) => s.replace(/^집결\s*장소\s*[:：]\s*/, "").trim();
const uniq = <T>(xs: T[]) => [...new Set(xs)];
const extraOf = (i: CollectedItem): Record<string, unknown> =>
  i.extra && typeof i.extra === "object" && !Array.isArray(i.extra) ? (i.extra as Record<string, unknown>) : {};
const deadlineText = (i: CollectedItem) => str((i as { deadline_text?: unknown }).deadline_text);
/** 봉사 place: extra.place from the crawler, else the raw actvPlcCn, else the old provider-as-place. */
const placeOf = (i: CollectedItem) => {
  const x = extraOf(i);
  return cleanPlace(tidy(x.place) || tidy(x.actvPlcCn) || str(i.provider));
};
// How to apply, where, and whom to ask, under whichever key the source uses (보조금24 Korean keys, certi English).
const APPLY_KEYS = ["how_to_apply", "신청방법", "apply_method"];
const OFFICE_KEYS = ["접수기관", "office", "reception"];
const CONTACT_KEYS = ["contact", "전화문의", "문의처", "phone"];

function rowsFor(kind: KindKey, its: CollectedItem[], e: Omit<BoardEntry, "rows">): BoardRow[] {
  const first = its[0];
  const x = extraOf(first);
  const pick = (keys: string[]) => keys.map((k) => tidy(x[k])).find(Boolean) ?? "";
  const all = (k: string) => uniq(its.map((i) => tidy(extraOf(i)[k])).filter(Boolean));
  const next = e.windows[0];
  const apply = next ? rangeLabel(next.s, next.e) : e.always ? e.deadlineText || "상시 신청" : e.deadlineText;
  const rows: (BoardRow | null)[] = [];
  const row = (label: string, value: string, list?: string[]) => rows.push(value || list?.length ? { label, value, list } : null);
  const howRows = () => {
    row("신청방법", pick(APPLY_KEYS));
    row("접수기관", pick(OFFICE_KEYS));
    row("문의", pick(CONTACT_KEYS));
  };
  if (kind === "scholarship" || kind === "support") {
    if (kind === "scholarship") row("장학종류", [tidy(x.aid_kind), tidy(x.provider_kind) && `${tidy(x.provider_kind)} 운영`].filter(Boolean).join(" · "));
    else row("지원 분야", tidy(x["서비스분야"]) || (first.tags ?? []).filter((t) => typeof t === "string" && /[가-힣]/.test(t) && !t.includes(":")).slice(0, 3).join(" · "));
    row(kind === "scholarship" ? "선발대상" : "지원대상", e.target);
    row(kind === "scholarship" ? "장학혜택" : "지원내용", e.cost);
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
    howRows();
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
    const places = uniq(its.map(placeOf).filter(Boolean));
    row("활동 장소", places.join(" / "));
    row("활동 내용", tidy(x.mainCn));
    if (tidy(x.actcn) !== tidy(x.mainCn)) row("세부 일정", tidy(x.actcn));
    row("비용", e.cost);
    howRows();
    // Once provider is the real organisation it differs from the place and gets its own row.
    if (e.provider && !places.includes(e.provider)) row("운영기관", e.provider);
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
    row("활동 장소", tidy(x.place));
    howRows();
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
    howRows();
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
    if (!it || typeof it !== "object" || typeof it.source !== "string" || !it.url || !it.title) continue;
    const kind = kindOf(it);
    if (!kind) continue;
    if (it.status === "closed") continue;
    if (kind === "activity") {
      const next = [it.event_start, ...(Array.isArray(extraOf(it).sessions) ? (extraOf(it).sessions as unknown[]) : [])].filter(isIso).some((d) => d >= today);
      if (!next) continue;
    } else if (isIso(it.apply_end)) {
      if (it.apply_end < today) continue;
    } else if (!ALWAYS.test(deadlineText(it))) continue; // no date and not 상시: nothing to show a reader
    const id = boardId(it);
    const key = `${it.source}|${boardKey(it)}`;
    if ((keyOf.get(id) ?? key) !== key) throw new Error(`board id collision: ${id} for "${keyOf.get(id)}" and "${key}"`);
    keyOf.set(id, key);
    byKey.set(id, [...(byKey.get(id) ?? []), it]);
  }
  return [...byKey.entries()].map(([id, its]) => {
    const first = its[0];
    const kind = kindOf(first)!;
    const regions = uniq(its.flatMap((i) => (Array.isArray(i.regions) && i.regions.length ? i.regions.map(String) : ["all"])));
    const windows: BoardWindow[] = kind === "activity" ? [] : its
      .filter((i) => isIso(i.apply_end))
      .map((i) => ({
        s: isIso(i.apply_start) ? i.apply_start : i.apply_end!, e: i.apply_end!,
        ...(isIso(i.event_start) ? { ev: i.event_start } : {}),
        ...(ROUND.exec(i.title)?.[1] ? { k: ROUND.exec(i.title)![1] } : {}),
      }))
      .sort((a, b) => (a.e < b.e ? -1 : a.e > b.e ? 1 : (a.ev ?? "") < (b.ev ?? "") ? -1 : 1));
    const sessions = kind !== "activity" ? [] : uniq(its.flatMap((i) => [i.event_start, ...(Array.isArray(extraOf(i).sessions) ? (extraOf(i).sessions as unknown[]) : [])]).filter(isIso))
      .filter((d) => d >= today).sort();
    const dText = uniq(its.map(deadlineText).filter(Boolean))[0] ?? "";
    const always = kind !== "activity" && its.some((i) => !isIso(i.apply_end) && ALWAYS.test(deadlineText(i)));
    const extra = kind === "scholarship" || kind === "support"
      ? Object.fromEntries(Object.entries(extraOf(first)).map(([k, v]) => [k, str(v)]).filter(([, v]) => v))
      : {};
    const base: Omit<BoardEntry, "rows"> = {
      id, source: first.source, sourceLabel: SOURCE_LABEL[first.source] ?? (str(first.provider) || first.source), kind, kindLabel: KIND[kind],
      title: kind === "exam" || its.length > 1 ? first.title.replace(ROUND, " ").replace(/\s+/g, " ").trim() : str(first.title),
      provider: kind === "volunteer" ? cleanPlace(str(first.provider)) : str(first.provider),
      // A grouped exam spans 필기 and 실기 rounds, so the first round's wording is made general.
      summary: kind === "exam" && its.length > 1 ? str(first.summary).replace(/\s*(필기|실기)\s+시험/, " 시험") : str(first.summary), url: first.url,
      seen: its.map((i) => i.last_seen ?? "").filter(isIso).sort().pop() ?? fallbackSeen,
      regions, regionLabel: regions.includes("all") ? "전국" : regions.map((r) => REGION_LABEL[r] ?? r).join(" · "),
      stepIds: uniq(its.flatMap((i) => (Array.isArray(i.step_ids) ? i.step_ids : []))),
      scope: its.some((i) => i.scope === "step" || i.step_ids?.length) ? "step" : "general",
      windows, sessions, always, deadlineText: dText,
      cost: str(first.cost_text), target: str(first.target_text), extra, count: its.length,
    };
    return { ...base, rows: rowsFor(kind, its, base) };
  });
}

/** Sort key for 상시 entries: after every dated one, before anything with no date left. */
export const ALWAYS_SORT = "9998";

/**
 * State on a given day: open (apply window has started), upcoming, check (체험: only a session day is known),
 * or always (상시: no deadline). live is false when nothing is left ahead.
 */
export function stateOn(e: Pick<BoardEntry, "windows" | "sessions" | "always">, today: string) {
  const w = e.windows.filter((x) => x.e >= today);
  const s = e.sessions.filter((d) => d >= today);
  if (w.length) {
    const open = w.find((x) => x.s <= today);
    const pick = open ?? w[0];
    return { status: (open ? "open" : "upcoming") as BoardStatus, window: pick, date: open ? pick.e : pick.s, sortKey: pick.e, live: true };
  }
  if (s.length) return { status: "check" as BoardStatus, window: undefined, date: s[0], sortKey: s[0], live: true };
  if (e.always) return { status: "always" as BoardStatus, window: undefined, date: "", sortKey: ALWAYS_SORT, live: true };
  return { status: "check" as BoardStatus, window: undefined, date: "", sortKey: "9999", live: false };
}
export const daysBetween = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);

/**
 * 비슷한 혜택 for one entry: the same kind, never another region's item.
 * A 전국 entry gets other 전국 entries; a regional one gets its own region first, then 전국.
 * Within each group: open now first (closest deadline first, 상시 after dated), then upcoming, then the rest.
 */
export function similarTo(e: BoardEntry, all: BoardEntry[], today: string, n = 3): BoardEntry[] {
  const nationwide = (o: BoardEntry) => o.regions.includes("all");
  const sameRegion = (o: BoardEntry) => !nationwide(o) && o.regions.some((r) => e.regions.includes(r));
  const rank = (o: BoardEntry) => {
    const st = stateOn(o, today);
    return st.status === "open" || st.status === "always" ? 0 : st.status === "upcoming" ? 1 : 2;
  };
  const order = (a: BoardEntry, b: BoardEntry) => {
    const d = rank(a) - rank(b);
    if (d) return d;
    const x = stateOn(a, today).sortKey, y = stateOn(b, today).sortKey;
    return x < y ? -1 : x > y ? 1 : a.title.localeCompare(b.title, "ko");
  };
  const pool = all.filter((o) => o.id !== e.id && o.kind === e.kind && stateOn(o, today).live);
  const groups = nationwide(e) ? [pool.filter(nationwide)] : [pool.filter(sameRegion), pool.filter(nationwide)];
  return groups.flatMap((g) => g.sort(order)).slice(0, n);
}

let cache: BoardEntry[] | null = null;
/** Every board entry, soonest deadline (or next 활동일) first, 상시 after the dated ones. Ids are unique; a collision fails the build. */
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
