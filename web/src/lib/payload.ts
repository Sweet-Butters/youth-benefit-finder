// The benefits board as small JSON files for the browser, written at build by src/pages/helps/board.json.ts
// and mine.json.ts. With thousands of entries (D28 keeps every 한국장학재단 장학금) an inline copy made
// /helps/ and the home page over 2 MB each, so the pages keep only the first rows and fetch these.
// Short keys, the kind as an index into KIND_ORDER, no detail rows; "all" regions and empty lists are left out.
import { boardEntries, stateOn, todayKst, KIND_ORDER, type BoardEntry } from "./board";

const clip = (t: string, max: number) => (t.length > max ? t.slice(0, max) : t);
const regionsOf = (e: BoardEntry) => (e.regions.length === 1 && e.regions[0] === "all" ? {} : { r: e.regions });

/**
 * /helps/ list: i id, k kind index, t title, p provider, r regions (none = 전국), w [start, end] windows
 * (a 지난 모집 keeps only its last round), s session days, a 상시, c recurring 장학금,
 * q extra search text besides the title and provider (the start of the target line; left out when dozens of
 * entries share it, such as 1365's fixed "청소년 가능" line, since it tells them apart from nothing),
 * m 장학금 학과 계열 (장학금 only): "*" anyone, "?" 특정 학과 with no group named, else the groups.
 */
export function listPayload() {
  const today = todayKst();
  const qOf = (e: BoardEntry) => clip(e.target, 40).toLowerCase();
  const seen = new Map<string, number>();
  for (const e of boardEntries()) seen.set(qOf(e), (seen.get(qOf(e)) ?? 0) + 1);
  return boardEntries().map((e) => {
    const st = stateOn(e, today);
    const w = st.status === "closed" ? [[st.window!.s, st.window!.e]] : e.windows.filter((x) => x.e >= today).map((x) => [x.s, x.e]);
    const q = (seen.get(qOf(e)) ?? 0) < 30 ? qOf(e) : "";
    return {
      i: e.id, k: KIND_ORDER.indexOf(e.kind), t: e.title, p: e.provider, ...regionsOf(e),
      ...(w.length ? { w } : {}), ...(e.sessions.length ? { s: e.sessions } : {}), ...(e.always ? { a: 1 } : {}), ...(e.recurs ? { c: 1 } : {}),
      ...(q ? { q } : {}),
      ...(e.kind === "scholarship" ? { m: e.majors === "any" ? "*" : e.majors === "specific" ? "?" : e.majors } : {}),
    };
  });
}

/**
 * 내 조건 혜택 on the home page: live entries with a date ahead or 상시 (no 체험-only sessions, no 지난 모집).
 * lo/hi age range, ok 학교 밖 가능, oos 학교 밖 전용, stu needs a student, fi catalog fields,
 * q the start of the summary; the page adds the title, and matches both against a field's benefit words.
 */
export function minePayload() {
  const today = todayKst();
  return boardEntries().filter((e) => { const s = stateOn(e, today); return s.live && s.status !== "check"; }).map((e) => ({
    i: e.id, k: KIND_ORDER.indexOf(e.kind), t: e.title, p: e.provider, ...regionsOf(e),
    ...(e.windows.length ? { w: e.windows.filter((x) => x.e >= today).map((x) => [x.s, x.e]) } : {}), ...(e.always ? { a: 1 } : {}),
    ...(e.ageMin != null ? { lo: e.ageMin } : {}), ...(e.ageMax != null ? { hi: e.ageMax } : {}),
    ...(e.oosOk ? { ok: 1 } : {}), ...(e.forOutOfSchool ? { oos: 1 } : {}),
    // 고등학생·대학생 대상 장학금 ask for a student; a 학교 밖 reader does not see them unless the source says otherwise.
    ...(e.kind === "scholarship" && /^(고등학생|대학생)\s*대상/.test(e.target) && !e.oosOk ? { stu: 1 } : {}),
    ...(e.summary ? { q: clip(e.summary, 60).toLowerCase() } : {}),
    ...(e.fieldIds.length ? { fi: e.fieldIds } : {}),
  }));
}
