// Subway-map layout for one field (D22): paths = lines, steps = stations, a step on several paths = a transfer station.
// Shared by the full map (pages/fields/[field].astro) and the small previews (components/MiniMap.astro).
import type { Field, Path } from "./content";

export const PALETTE = ["var(--line-1)", "var(--line-2)", "var(--line-3)", "var(--line-4)", "#7b52ae", "#0a93ad", "#8a5a2b", "#5c6b00"];

export interface Line { id: string; title: string; summary: string; color: string; steps: string[] }
export interface Station { id: string; lines: number[]; notes: Record<number, string>; preds: Set<string> }
export interface LineSeg extends Line { lane: number; a: number; b: number }

export function livePaths<P extends Path>(field: Field & { paths: P[] }): P[] {
  return field.paths.filter((p) => !p.retired);
}

/**
 * Station order along the map: a station comes after every station before it on any line, the station right after the
 * last placed one wins when it can, otherwise the one on the lowest line. Every line is one lane from its first to its last station.
 */
export function layout(paths: Path[]) {
  const lines: Line[] = paths.map((p, i) => ({
    id: p.id, title: p.title, summary: p.summary, color: PALETTE[i % PALETTE.length], steps: p.steps.map((s) => s.step),
  }));

  const stations = new Map<string, Station>();
  paths.forEach((p, li) =>
    p.steps.forEach((ps, i) => {
      const st = stations.get(ps.step) ?? { id: ps.step, lines: [], notes: {}, preds: new Set<string>() };
      if (!st.lines.includes(li)) st.lines.push(li);
      if (ps.note) st.notes[li] = ps.note;
      if (i > 0) st.preds.add(p.steps[i - 1].step);
      stations.set(ps.step, st);
    }),
  );

  const order: string[] = [];
  const placed = new Set<string>();
  let last: string | null = null;
  const isNextOf = (prev: string, id: string) =>
    lines.some((l) => {
      const i = l.steps.indexOf(prev);
      return i >= 0 && l.steps[i + 1] === id;
    });
  while (order.length < stations.size) {
    const unplaced = [...stations.values()].filter((s) => !placed.has(s.id));
    let avail = unplaced.filter((s) => [...s.preds].every((p) => placed.has(p)));
    if (!avail.length) avail = unplaced;
    avail.sort((a, b) => Math.min(...a.lines) - Math.min(...b.lines));
    const prev = last;
    const pick = (prev && avail.find((s) => isNextOf(prev, s.id))) || avail[0];
    order.push(pick.id);
    placed.add(pick.id);
    last = pick.id;
  }
  const pos = new Map(order.map((id, i) => [id, i]));
  const lineSegs: LineSeg[] = lines.map((l, li) => ({ ...l, lane: li, a: pos.get(l.steps[0])!, b: pos.get(l.steps[l.steps.length - 1])! }));
  return { lines, stations, order, pos, lineSegs };
}
