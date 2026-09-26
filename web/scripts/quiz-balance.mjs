// Quick balance check for data/processed/quiz.json (D27): the highest total each Holland type can reach
// (one answer per question, or the best two on a "multi" question) and how many questions can score it.
// Run from web/:  node scripts/quiz-balance.mjs   Exit 1 when the largest max is more than 20% above the smallest.
import { readFileSync } from "node:fs";
const quiz = JSON.parse(readFileSync(new URL("../../data/processed/quiz.json", import.meta.url), "utf8"));
const H = ["R", "I", "A", "S", "E", "C"];
const max = Object.fromEntries(H.map((h) => [h, 0]));
const reach = Object.fromEntries(H.map((h) => [h, 0]));
for (const q of quiz.questions) {
  for (const h of H) {
    const s = q.options.map((o) => o.score[h] ?? 0).sort((a, b) => b - a);
    const best = q.multi ? s[0] + s[1] : s[0];
    max[h] += best;
    if (best > 0) reach[h]++;
  }
}
const lo = Math.min(...Object.values(max)), hi = Math.max(...Object.values(max));
console.log(`questions ${quiz.questions.length}, version ${quiz.version}`);
for (const h of H) console.log(`${h}  max ${String(max[h]).padStart(2)}  questions ${reach[h]}`);
console.log(`spread ${lo}..${hi} (${Math.round(((hi - lo) / lo) * 100)}%)`);
process.exit(hi > lo * 1.2 ? 1 : 0);
