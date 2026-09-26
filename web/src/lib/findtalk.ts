// Find-talk data (D27): the catalog of fields the talk can point to and the interest questions.
// Both files are optional so the site still builds before they exist; the home page then shows the static links only.
export type Holland = "R" | "I" | "A" | "S" | "E" | "C";
export const HOLLAND: Holland[] = ["R", "I", "A", "S", "E", "C"];

export interface CatalogField {
  id: string; title: string; holland: Holland[]; one_line: string; jobs?: string[]; try_first?: string;
  status: "ready" | "coming"; benefit_words?: string[];
}
export interface QuizOption { id: string; label: string; score: Partial<Record<Holland, number>> }
export interface QuizQuestion { id: string; text: string; hint?: string; multi?: boolean; options: QuizOption[] }
export interface Quiz { version: number; questions: QuizQuestion[] }

const one = <T>(mods: Record<string, unknown>): T | null => {
  const m = Object.values(mods)[0] as { default: T } | undefined;
  return m ? m.default : null;
};

export const catalog: CatalogField[] =
  one<{ fields: CatalogField[] }>(import.meta.glob("../../../data/processed/catalog.json", { eager: true }))?.fields ?? [];
export const quiz: Quiz | null = one<Quiz>(import.meta.glob("../../../data/processed/quiz.json", { eager: true }));

/** The highest total each type can reach (best option per question, best two on a multi question). */
export function maxByType(q: Quiz): Record<Holland, number> {
  const out = Object.fromEntries(HOLLAND.map((h) => [h, 0])) as Record<Holland, number>;
  for (const qq of q.questions)
    for (const h of HOLLAND) {
      const s = qq.options.map((o) => o.score[h] ?? 0).sort((a, b) => b - a);
      out[h] += qq.multi ? s[0] + (s[1] ?? 0) : s[0];
    }
  return out;
}
