// The public benefits board (/helps/, D26): every youth benefit the crawler collected, step or general,
// all at the "공식 자동" tier. Built from the same items.json as lib/collected.ts, with repeated rounds grouped:
// Q-Net by exam, 봉사·체험 by title + place/provider, so one entry keeps a list of its windows or sessions.
// Dates are judged in Korean time at build; the pages re-check them in the browser so a stale build never
// shows a passed deadline as open. 한국장학재단 장학금 stay after they close, as "지난 모집" (D28). Items the board cannot place (unknown source and type, no title or link)
// are skipped, never a build failure; only an id collision fails the build.
import { collected, boardId, boardKey, SOURCE_LABEL, type CollectedItem } from "./collected";
import { REGION_LABEL } from "./content";

export type KindKey = "scholarship" | "support" | "volunteer" | "activity" | "exam" | "contest";
export const KIND: Record<KindKey, string> = { scholarship: "장학금", support: "지원", volunteer: "봉사", activity: "체험", exam: "시험", contest: "공모전" };
export const KIND_ORDER: KindKey[] = ["scholarship", "support", "volunteer", "activity", "exam", "contest"];
export const KIND_COLOR: Record<KindKey, string> = {
  scholarship: "var(--line-1)", support: "var(--line-5)", volunteer: "var(--line-2)", activity: "var(--line-3)", exam: "var(--line-4)",
  contest: "var(--me)",
};
// 공모전 come from listing sites (crawler/sources/contest_*.py), not from an agency. Their terms forbid republishing,
// so an entry shows only title, host, period, target and category, and links to the site's own page.
export const CONTEST_SITE: Record<string, string> = {
  allcon: "올콘", allforyoung: "요즘것들", contestkorea: "콘테스트코리아", thinkgood: "씽굿", wevity: "위비티", linkareer: "링커리어",
};
const KIND_BY_SOURCE: Record<string, KindKey> = {
  kosaf: "scholarship", volunteer: "volunteer", vms1365: "volunteer", certi: "activity", qnet: "exam", bizinfo: "support", kstartup: "support",
};
// 한국장학재단 장학금 recur every year (D28): the board keeps every one, closed ones as "지난 모집" with their last dates.
const RECUR_SOURCES = new Set(["kosaf"]);
// Any other source (보조금24 and later ones) is placed by its item type; a type not listed here is skipped.
const KIND_BY_TYPE: Record<string, KindKey> = { scholarship: "scholarship", support: "support", contest: "contest" };
const kindOf = (it: CollectedItem): KindKey | undefined => KIND_BY_SOURCE[it.source] ?? KIND_BY_TYPE[it.type];

/** One application window. s..e is when to apply; ev is the activity or exam day, when known; k is 필기/실기. */
export interface BoardWindow { s: string; e: string; ev?: string; k?: string }
export interface BoardRow { label: string; value: string; list?: string[] }
/** always = 상시 (no deadline: apply any time, e.g. 보조금24 "상시신청"). */
/** closed = 지난 모집: a recurring 장학금 (D28) with no window ahead, shown with its last dates. */
export type BoardStatus = "open" | "upcoming" | "check" | "always" | "closed";
export const STATUS_LABEL: Record<BoardStatus, string> = { open: "접수 중", upcoming: "곧 열림", check: "일정 확인", always: "상시", closed: "지난 모집" };

export interface BoardEntry {
  id: string; source: string; sourceLabel: string; kind: KindKey; kindLabel: string;
  title: string; provider: string; summary: string; url: string; seen: string;
  regions: string[]; regionLabel: string; stepIds: string[]; scope: "step" | "general";
  /** Apply-based sources (장학금, 봉사, 시험): windows still open or ahead at build, soonest deadline first.
   *  A recurring 장학금 (recurs) also keeps its past windows, so a closed one still has its last dates. */
  windows: BoardWindow[];
  /** A 한국장학재단 장학금 (D28): kept after it closes and shown as "지난 모집" until it opens again. */
  recurs: boolean;
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
  /** Age range when known: the item's own age_min/age_max (체험), else 고등학생 15~19 / 대학생 18~29 for 장학금; null = unknown. */
  ageMin: number | null; ageMax: number | null;
  /** The crawler thinks 학교 밖 청소년 can apply (tag out_of_school_ok or open_to_all). A hint, not a filter. */
  oosOk: boolean;
  /** The item itself is for 학교 밖 청소년 (the words appear in the title or target). */
  forOutOfSchool: boolean;
  /** Catalog fields the crawler tagged it with ("field:<id>", e.g. 기능사 exams per field). */
  fieldIds: string[];
  /** Trust label on the detail page: "공식 자동" (agency data) or "모음 사이트 자동" (공모전). */
  tierLabel: string;
  /** Text of the button to the original page. */
  goLabel: string;
  /** 누가 받을 수 있나 (#1): the crawler's for:<key> tags, or when it has none, guessed from the target line (whoOf). */
  who: WhoKey[];
  /** Conditions it asks for (#1): the crawler's cond:<key> tags, or guessed from the 장학금 columns and the target line. */
  conds: CondKey[];
  /** First day the crawler saw it (first_seen), for 새로 올라온 순; the collection day when unknown. */
  firstSeen: string;
  /** 모음 사이트 that list the same 공모전 (#2): the kept one first, then also_in. url is "" when not known. */
  sites: { key: string; label: string; url: string }[];
  /** 장학금 학과 계열 from the target's "학과:" part: "any" (제한 없음·모든 계열·no 학과 part), "specific" (특정 학과
   *  with no group named), or the groups named (MAJOR_GROUPS). Other kinds are "any"; the list sends it for 장학금 only. */
  majors: Majors;
}

/** 누가 받을 수 있나 (#1). The crawler tags items for:<key>; all = 누구나 (no age or schooling limit). */
export type WhoKey = "middle" | "high" | "oos" | "univ" | "young" | "all";
export const WHO: Record<WhoKey, string> = { middle: "중학생", high: "고등학생", oos: "학교 밖", univ: "대학생", young: "청년", all: "누구나" };
export const WHO_ORDER: WhoKey[] = ["middle", "high", "oos", "univ", "young", "all"];
/** Conditions (cond:<key>). The /helps/ 조건 row hides ones that need income, grade or special; region is shown, not filtered. */
export type CondKey = "income" | "region" | "grade" | "special";
export const COND: Record<CondKey, string> = { income: "소득 기준", region: "거주 조건", grade: "성적 기준", special: "특정 자격" };
export const COND_ORDER: CondKey[] = ["income", "grade", "special", "region"];

// Fallbacks while items still lack for:/cond: tags: read the target line (and title) the way a person would.
// "청소년" alone covers 중·고등학생 and 학교 밖 청소년.
const WHO_TEXT: [WhoKey, RegExp][] = [
  ["middle", /중학생|중학교|중등|청소년/],
  ["high", /고등학생|고교|고등학교|특성화고|마이스터고|청소년/],
  ["oos", /학교\s*밖|학업\s*중단|검정고시|자퇴|청소년/],
  ["univ", /대학생|대학교|전문대|대학\s*(신입생|재학)/],
  ["young", /청년|일반인|직장인|성인|취업\s*준비|취준/],
];
const ALL_TEXT = /^(누구나|제한\s*없음|대상\s*제한\s*없음|전\s*국민)/;
/** A 장학금 column that states a real limit ("가점"·"우대" are bonuses, "기관에 확인 필요" says nothing). */
const realLimit = (v: unknown) => { const t = str(v); return !!t && !/^(가점|우대)|확인\s*필요|제한\s*없|해당\s*없|^-$/.test(t); };
const INCOME_TEXT = /저소득|기초\s*생활|차상위|중위\s*소득|소득\s*(분위|구간|인정|기준)|가정\s*형편|학자금\s*지원\s*구간/;
const GRADE_TEXT = /성적|평점|내신|등급\s*이내|백분위/;
const SPECIAL_TEXT = /장애|다문화|보훈|유공자|북한\s*이탈|새터민|한부모|조손|자립\s*준비|보호\s*종료|아동\s*양육|농어촌|다자녀|자녀|특정\s*(대학|학과|학교)|수급자/;
const tagged = (tags: Set<string>, prefix: string) => [...tags].filter((t) => typeof t === "string" && t.startsWith(prefix)).map((t) => t.slice(prefix.length));

/** for:<key> tags if the crawler gave any, else a guess from the target line, the title and the age range. */
export function whoOf(its: CollectedItem[], tags: Set<string>): WhoKey[] {
  const given = tagged(tags, "for:").filter((k): k is WhoKey => k in WHO);
  if (given.length) return WHO_ORDER.filter((k) => given.includes(k));
  const first = its[0];
  const target = str(first.target_text);
  const text = `${target} ${str(first.title)}`;
  const out = new Set<WhoKey>();
  if (ALL_TEXT.test(target) || (tags.has("open_to_all") && !/청소년|학생/.test(target))) out.add("all");
  for (const [k, re] of WHO_TEXT) if (re.test(text)) out.add(k);
  if (tags.has("out_of_school_ok")) out.add("oos");
  // Only ages to go on (체험): the school stages the age range covers.
  if (!out.size) {
    const lo = its.map((i) => i.age_min).find((n): n is number => typeof n === "number");
    const hi = its.map((i) => i.age_max).find((n): n is number => typeof n === "number");
    if (lo != null || hi != null) {
      const a = lo ?? 0, b = hi ?? 99;
      if (a <= 15 && b >= 13) out.add("middle");
      if (a <= 18 && b >= 16) out.add("high");
      if (b >= 19) out.add("young");
    }
  }
  return WHO_ORDER.filter((k) => out.has(k));
}

/** cond:<key> tags if the crawler gave any, else the 장학금 columns (income, grade, residence) and the target line. */
export function condsOf(its: CollectedItem[], tags: Set<string>, regions: string[]): CondKey[] {
  const given = tagged(tags, "cond:");
  if (given.length) return COND_ORDER.filter((k) => given.includes(k));
  const first = its[0];
  const x = extraOf(first);
  const text = `${str(first.target_text)} ${str(first.title)}`;
  const out = new Set<CondKey>();
  if (realLimit(x.income) || INCOME_TEXT.test(text)) out.add("income");
  if (realLimit(x.grade) || GRADE_TEXT.test(text)) out.add("grade");
  if (SPECIAL_TEXT.test(text)) out.add("special");
  if (realLimit(x.residence) || (regions.length > 0 && !regions.includes("all"))) out.add("region");
  return COND_ORDER.filter((k) => out.has(k));
}

// A 모음 사이트's page address from its id, learned from the items (every allcon url is ".../view/contest/<id>"),
// so an also_in key ("linkareer:306744") can link to that site's own page. A site whose urls do not follow
// one pattern gets no link, only its name.
let urlPatterns: Map<string, [string, string] | null> | null = null;
function siteUrl(source: string, id: string): string {
  if (!urlPatterns) {
    urlPatterns = new Map();
    for (const it of collected.items) {
      if (!it || typeof it.url !== "string" || typeof it.source_id !== "string" || !it.source_id) continue;
      const i = it.url.indexOf(it.source_id);
      const pat: [string, string] | null = i < 0 || it.url.indexOf(it.source_id, i + 1) >= 0 ? null : [it.url.slice(0, i), it.url.slice(i + it.source_id.length)];
      const had = urlPatterns.get(it.source);
      if (had === undefined) urlPatterns.set(it.source, pat);
      else if (had && (!pat || had[0] !== pat[0] || had[1] !== pat[1])) urlPatterns.set(it.source, null);
    }
  }
  const p = urlPatterns.get(source);
  return p && /^[\w.-]+$/.test(id) ? `${p[0]}${id}${p[1]}` : "";
}
const siteLabel = (s: string) => CONTEST_SITE[s] ?? SOURCE_LABEL[s] ?? s;
/** The kept item's site, then each also_in key ("site:id" or {source, source_id, url}), then any other name in sources. */
function sitesOf(its: CollectedItem[]): BoardEntry["sites"] {
  const first = its[0];
  const out = new Map<string, { key: string; label: string; url: string }>();
  out.set(first.source, { key: first.source, label: siteLabel(first.source), url: first.url });
  for (const it of its) {
    const also = (it as { also_in?: unknown }).also_in;
    for (const a of Array.isArray(also) ? also : []) {
      let src = "", id = "", u = "";
      if (typeof a === "string") { const at = a.indexOf(":"); src = at < 0 ? a : a.slice(0, at); id = at < 0 ? "" : a.slice(at + 1); }
      else if (a && typeof a === "object") {
        const o = a as Record<string, unknown>;
        src = str(o.source); id = str(o.source_id); u = /^https?:\/\//.test(str(o.url)) ? str(o.url) : "";
      }
      if (!src || out.has(src)) continue;
      out.set(src, { key: src, label: siteLabel(src), url: u || (id ? siteUrl(src, id) : "") });
    }
    const srcs = (it as { sources?: unknown }).sources;
    for (const s of Array.isArray(srcs) ? srcs : []) if (typeof s === "string" && s && !out.has(s)) out.set(s, { key: s, label: siteLabel(s), url: "" });
  }
  return [...out.values()];
}

/** The 학과 계열 names a 장학금 target uses, in the order the /helps/ filter lists them. */
export const MAJOR_GROUPS = ["공학", "예체능", "의약", "자연", "사회", "인문", "교육"] as const;
export type Majors = string[] | "any" | "specific";
/** "대학생 대상 · 학과: 공학계열, 특정 학과 · …" -> ["공학"]; "학과: 제한 없음" or no 학과 part -> "any". */
export function majorsOf(target: string): Majors {
  const m = /학과\s*[:：]\s*([^·]*)/.exec(target);
  const t = m ? m[1].trim() : "";
  if (!t || /제한\s*없음|모든\s*계열/.test(t)) return "any";
  const groups = MAJOR_GROUPS.filter((g) => t.includes(g));
  return groups.length ? groups : "specific";
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
  const today = todayKst();
  const ahead = e.windows.find((w) => w.e >= today);
  const past = !ahead && e.recurs ? lastWindow(e) : undefined;
  const next = ahead ?? past;
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
    row(past ? "지난 신청기간" : "신청기간", apply);
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
    row("활동 시간", all("hours").join(" / "));
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
  } else if (kind === "contest") {
    // Listing facts only (the sites' terms): no description, prize or poster.
    const hosts = Array.isArray(x.hosts) ? uniq((x.hosts as unknown[]).map(tidy).filter(Boolean)) : [];
    row("분야", tidy(x.category));
    row("주최", hosts.length ? hosts.join(" · ") : e.provider);
    // Some sites give only the deadline (a D-day): say "까지" rather than a one-day period.
    row("접수기간", next && !isIso(first.apply_start) ? `${ymd(next.e)}까지` : apply || "원문에서 확인");
    row("참가대상", e.target);
    row("지역", e.regionLabel);
    row("모음 사이트", e.sites.length > 1 ? e.sites.map((x) => x.label).join(" · ") : e.sourceLabel);
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
    const recurs = kind === "scholarship" && RECUR_SOURCES.has(it.source);
    if (it.status === "closed" && !recurs) continue;
    if (kind === "activity") {
      const next = [it.event_start, ...(Array.isArray(extraOf(it).sessions) ? (extraOf(it).sessions as unknown[]) : [])].filter(isIso).some((d) => d >= today);
      if (!next) continue;
    } else if (isIso(it.apply_end)) {
      if (it.apply_end < today && !recurs) continue;
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
    // A 공모전 the site marks 지역 제한 without naming the place (tag region_limited) has no region: it is listed
    // under 모든 지역 only, never as 전국.
    const limited = (i: CollectedItem) => !(Array.isArray(i.regions) && i.regions.length) && !!i.tags?.includes("region_limited");
    const regions = uniq(its.flatMap((i) => (Array.isArray(i.regions) && i.regions.length ? i.regions.map(String) : limited(i) ? [] : ["all"])));
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
    const tagSet = new Set(its.flatMap((i) => i.tags ?? []));
    const base: Omit<BoardEntry, "rows" | "ageMin" | "ageMax" | "oosOk" | "forOutOfSchool"> = {
      id, source: first.source, sourceLabel: SOURCE_LABEL[first.source] ?? CONTEST_SITE[first.source] ?? (str(extraOf(first).site) || str(first.provider) || first.source), kind, kindLabel: KIND[kind],
      title: kind === "exam" || its.length > 1 ? first.title.replace(ROUND, " ").replace(/\s+/g, " ").trim() : str(first.title),
      provider: kind === "volunteer" ? cleanPlace(str(first.provider)) : str(first.provider),
      // A grouped exam spans 필기 and 실기 rounds, so the first round's wording is made general.
      summary: kind === "contest" ? "" : kind === "exam" && its.length > 1 ? str(first.summary).replace(/\s*(필기|실기)\s+시험/, " 시험") : str(first.summary), url: first.url,
      seen: its.map((i) => i.last_seen ?? "").filter(isIso).sort().pop() ?? fallbackSeen,
      regions, regionLabel: regions.includes("all") ? "전국" : regions.length ? regions.map((r) => REGION_LABEL[r] ?? r).join(" · ") : "지역 제한",
      stepIds: uniq(its.flatMap((i) => (Array.isArray(i.step_ids) ? i.step_ids : []))),
      scope: its.some((i) => i.scope === "step" || i.step_ids?.length) ? "step" : "general",
      windows, recurs: kind === "scholarship" && RECUR_SOURCES.has(first.source), sessions, always, deadlineText: dText,
      cost: str(first.cost_text), target: str(first.target_text), extra, count: its.length,
      who: whoOf(its, tagSet), conds: condsOf(its, tagSet, regions),
      firstSeen: its.map((i) => (i as { first_seen?: unknown }).first_seen).filter(isIso).sort()[0] ?? fallbackSeen,
      sites: kind === "contest" ? sitesOf(its) : [],
    };
    // Age: the item's own limits win; a 장학금 without them gets the school level's usual ages (kosaf:hs / kosaf:univ).
    const mins = its.map((i) => i.age_min).filter((n): n is number => typeof n === "number");
    const maxs = its.map((i) => i.age_max).filter((n): n is number => typeof n === "number");
    const tags = new Set(its.flatMap((i) => i.tags ?? []));
    const level = tags.has("kosaf:hs") ? [15, 19] : tags.has("kosaf:univ") ? [18, 29] : null;
    const age = {
      ageMin: mins.length ? Math.min(...mins) : level ? level[0] : null,
      ageMax: maxs.length ? Math.max(...maxs) : level ? level[1] : null,
      oosOk: tags.has("out_of_school_ok") || tags.has("open_to_all"),
      forOutOfSchool: /학교\s*밖/.test(`${first.title} ${first.target_text ?? ""}`),
      fieldIds: [...tags].filter((t) => typeof t === "string" && t.startsWith("field:")).map((t) => t.slice(6)),
      tierLabel: kind === "contest" ? "모음 사이트 자동" : "공식 자동",
      goLabel: kind === "contest" ? "원문 보기 ↗" : "원문 공고 보기 ↗",
      majors: kind === "scholarship" ? majorsOf(str(first.target_text)) : ("any" as Majors),
    };
    return { ...base, ...age, rows: rowsFor(kind, its, { ...base, ...age }) };
  });
}

/** Sort key for 상시 entries: after every dated one, before anything with no date left. */
export const ALWAYS_SORT = "9998";

/** The latest window by start date (the one a 지난 모집 repeats), or undefined. */
export const lastWindow = (e: Pick<BoardEntry, "windows">): BoardWindow | undefined =>
  e.windows.reduce<BoardWindow | undefined>((a, w) => (!a || w.s > a.s || (w.s === a.s && w.e > a.e) ? w : a), undefined);

/**
 * 다음 예상 for anything whose windows are all past (a 지난 모집 장학금, D28): the last window's start date rolled
 * forward by whole years until it is today or later. date is that day; the page says only "YYYY년 M월쯤".
 * null when a window is still open or ahead, or there is no window at all.
 */
export function nextExpected(e: Pick<BoardEntry, "windows">, today: string): { year: number; month: number; date: string } | null {
  if (!e.windows.length || e.windows.some((w) => w.e >= today)) return null;
  const last = lastWindow(e)!;
  const rest = last.s.slice(4);
  let y = +last.s.slice(0, 4);
  while (`${y}${rest}` < today) y++;
  return { year: y, month: +rest.slice(1, 3), date: `${y}${rest}` };
}
/** A 장학금 for any of these 학과 계열 (a field's major_groups); "any" and "specific" never match. */
export const majorsMatch = (m: Majors, groups: readonly string[]) => Array.isArray(m) && m.some((g) => groups.includes(g));
export const nextLabel = (n: { year: number; month: number }) => `${n.year}년 ${n.month}월쯤`;

/**
 * 지난 모집 sort after every live entry ("9999-…" sorts after ALWAYS_SORT), by the next expected start date
 * (nextExpected), soonest first. The browser list (helps/index.astro) repeats this rule.
 */
export function closedSortKey(w: BoardWindow, today: string) {
  const rest = w.s.slice(4);
  let y = +w.s.slice(0, 4);
  while (`${y}${rest}` < today) y++;
  return `9999-${y}${rest}`;
}

/**
 * The month a 장학금 (or anything dated) opens in, for the 1년 장학금 달력 and the /helps/ month filter:
 * the current or next window's start, or 다음 예상 when every window is past; null for 상시 and 체험.
 */
export function openMonth(e: Pick<BoardEntry, "windows" | "sessions" | "always"> & { recurs?: boolean }, today: string) {
  const st = stateOn(e, today);
  if (st.status === "closed") return nextExpected(e, today);
  return st.window ? { year: +st.window.s.slice(0, 4), month: +st.window.s.slice(5, 7), date: st.window.s } : null;
}

/**
 * The recurrence lines for a 지난 모집 (D28): "보통 N월에 모집해요" from the last window's start month, and the
 * last two windows' dates labelled by year ("작년·올해 일정", "작년 일정", "올해 일정", or "지난 일정" when older).
 */
export function recurHint(e: Pick<BoardEntry, "windows">, today = todayKst()) {
  const last = lastWindow(e);
  if (!last) return null;
  const month = +last.s.slice(5, 7);
  const y = +today.slice(0, 4);
  const recent = [...e.windows].sort((a, b) => (a.s < b.s ? 1 : -1)).slice(0, 2).reverse();
  const years = new Set(recent.map((w) => +w.s.slice(0, 4)));
  const label = [...years].every((v) => v === y - 1 || v === y)
    ? years.has(y - 1) && years.has(y) ? "작년·올해 일정" : years.has(y) ? "올해 일정" : "작년 일정"
    : "지난 일정";
  return { month, when: `보통 ${month}월에 모집해요`, dates: `${label}: ${recent.map((w) => rangeLabel(w.s, w.e)).join(", ")}` };
}

/**
 * State on a given day: open (apply window has started), upcoming, check (체험: only a session day is known),
 * or always (상시: no deadline). live is false when nothing is left ahead.
 */
export function stateOn(e: Pick<BoardEntry, "windows" | "sessions" | "always"> & { recurs?: boolean }, today: string) {
  const w = e.windows.filter((x) => x.e >= today);
  const s = e.sessions.filter((d) => d >= today);
  if (w.length) {
    const open = w.find((x) => x.s <= today);
    const pick = open ?? w[0];
    return { status: (open ? "open" : "upcoming") as BoardStatus, window: pick, date: open ? pick.e : pick.s, sortKey: pick.e, live: true };
  }
  if (s.length) return { status: "check" as BoardStatus, window: undefined, date: s[0], sortKey: s[0], live: true };
  if (e.always) return { status: "always" as BoardStatus, window: undefined, date: "", sortKey: ALWAYS_SORT, live: true };
  const last = e.recurs ? lastWindow(e) : undefined;
  if (last) return { status: "closed" as BoardStatus, window: last, date: "", sortKey: closedSortKey(last, today), live: false };
  return { status: "check" as BoardStatus, window: undefined, date: "", sortKey: "9999", live: false };
}
export const daysBetween = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);

/**
 * 비슷한 혜택 for one entry: the same kind, never another region's item.
 * A 전국 entry gets other 전국 entries; a regional one gets its own region first, then 전국.
 * Within each group: open now first (closest deadline first, 상시 after dated), then upcoming, then the rest.
 */
// The live entries of each kind in similarTo's order, worked out once per list and day (thousands of detail pages).
const simCache = new WeakMap<BoardEntry[], { today: string; byKind: Map<KindKey, BoardEntry[]> }>();
function livePools(all: BoardEntry[], today: string) {
  const hit = simCache.get(all);
  if (hit && hit.today === today) return hit.byKind;
  const ranked = all.map((o) => ({ o, st: stateOn(o, today) })).filter((x) => x.st.live).map(({ o, st }) => ({
    o, key: st.sortKey, rank: st.status === "open" || st.status === "always" ? 0 : st.status === "upcoming" ? 1 : 2,
  }));
  ranked.sort((a, b) => a.rank - b.rank || (a.key < b.key ? -1 : a.key > b.key ? 1 : a.o.title.localeCompare(b.o.title, "ko")));
  const byKind = new Map<KindKey, BoardEntry[]>();
  for (const { o } of ranked) {
    const list = byKind.get(o.kind);
    if (list) list.push(o);
    else byKind.set(o.kind, [o]);
  }
  simCache.set(all, { today, byKind });
  return byKind;
}
export function similarTo(e: BoardEntry, all: BoardEntry[], today: string, n = 3): BoardEntry[] {
  const nationwide = (o: BoardEntry) => o.regions.includes("all");
  const sameRegion = (o: BoardEntry) => !nationwide(o) && o.regions.some((r) => e.regions.includes(r));
  const pool = (livePools(all, today).get(e.kind) ?? []).filter((o) => o.id !== e.id);
  const groups = nationwide(e) ? [pool.filter(nationwide)] : [pool.filter(sameRegion), pool.filter(nationwide)];
  return groups.flat().slice(0, n);
}

let cache: BoardEntry[] | null = null;
/** Every board entry, soonest deadline (or next 활동일) first, 상시 after the dated ones, then 지난 모집 장학금 (D28).
 *  Ids are unique; a collision fails the build. */
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

/**
 * 장학금 for a field (its catalog major_groups), for the field page and the /fields/ cards:
 * mine = 이 분야 학과 장학금 (a 학과 계열 in groups), any = 누구나 (no 학과 condition), each with how many are live today;
 * byMonth[m] (1~12) counts them by the month they open in (openMonth), and top = the two months where the most
 * 장학금 of all kinds of 학과 condition open, in calendar order.
 */
export function scholarshipsFor(groups: readonly string[], today = todayKst()) {
  const all = boardEntries().filter((e) => e.kind === "scholarship");
  const mine = all.filter((e) => majorsMatch(e.majors, groups));
  const any = all.filter((e) => e.majors === "any");
  const live = (xs: BoardEntry[]) => xs.filter((e) => stateOn(e, today).live).length;
  const byMonth = Array.from({ length: 13 }, () => ({ mine: 0, any: 0, all: 0 }));
  const mineIds = new Set(mine.map((e) => e.id));
  for (const e of all) {
    const m = openMonth(e, today)?.month;
    if (!m) continue;
    byMonth[m].all++;
    if (mineIds.has(e.id)) byMonth[m].mine++;
    else if (e.majors === "any") byMonth[m].any++;
  }
  const top = byMonth.map((c, m) => ({ m, n: c.all })).slice(1).sort((a, b) => b.n - a.n || a.m - b.m).slice(0, 2).filter((x) => x.n > 0)
    .map((x) => x.m).sort((a, b) => a - b);
  return { mine: mine.length, mineLive: live(mine), any: any.length, anyLive: live(any), byMonth, top };
}
