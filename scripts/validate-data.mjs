#!/usr/bin/env node
// Checks data/processed against data/schema and the rules in docs/architecture.md (section 1).
// Exit code 1 on any error; warnings are printed but do not fail.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const SCHEMA_DIR = join(ROOT, "data", "schema");
const DATA_DIR = join(ROOT, "data", "processed");
const STALE_DAYS = 90;
const BASE_REF = process.env.VALIDATE_BASE_REF || "origin/main";

const errors = [];
const warnings = [];
const err = (file, msg) => errors.push(`${file}: ${msg}`);
const warn = (file, msg) => warnings.push(`${file}: ${msg}`);

const ajv = new Ajv2020({ allErrors: true, strict: false });
for (const name of readdirSync(SCHEMA_DIR).filter((f) => f.endsWith(".schema.json"))) {
  ajv.addSchema(JSON.parse(readFileSync(join(SCHEMA_DIR, name), "utf8")));
}

function readJsonDir(sub) {
  const dir = join(DATA_DIR, sub);
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const path = join(dir, f);
      const rel = relative(ROOT, path).replaceAll("\\", "/");
      try {
        return { rel, name: f, data: JSON.parse(readFileSync(path, "utf8")) };
      } catch (e) {
        err(rel, `JSON parse error: ${e.message}`);
        return null;
      }
    })
    .filter(Boolean);
}

function validate(schemaId, item) {
  const fn = ajv.getSchema(schemaId);
  if (!fn(item.data)) {
    for (const e of fn.errors) err(item.rel, `schema ${e.instancePath || "/"} ${e.message}`);
    return false;
  }
  return true;
}

// 1. Schema, file name = id, unique ids
const fields = readJsonDir("fields");
const steps = readJsonDir("steps");
const helps = readJsonDir("helps");
const seen = new Map();
function registerId(id, rel) {
  if (seen.has(id)) err(rel, `duplicate id "${id}" (also in ${seen.get(id)})`);
  else seen.set(id, rel);
}
for (const [items, schema] of [[fields, "field.schema.json"], [steps, "step.schema.json"], [helps, "help.schema.json"]]) {
  for (const item of items) {
    if (!validate(schema, item)) continue;
    if (item.name !== `${item.data.id}.json`) err(item.rel, `file name must be "${item.data.id}.json"`);
    registerId(item.data.id, item.rel);
  }
}
for (const f of fields) for (const p of f.data.paths ?? []) registerId(p.id, `${f.rel} (path)`);

// Find-talk data (D27): one catalog of fields the talk can suggest, one quiz. Both optional.
function readSingle(name, schemaId) {
  const path = join(DATA_DIR, name);
  if (!existsSync(path)) return null;
  const item = { rel: `data/processed/${name}`, data: null };
  try { item.data = JSON.parse(readFileSync(path, "utf8")); } catch (e) { err(item.rel, `JSON parse error: ${e.message}`); return null; }
  return validate(schemaId, item) ? item : null;
}
const catalog = readSingle("catalog.json", "catalog.schema.json");
const quiz = readSingle("quiz.json", "quiz.schema.json");

const redirectsPath = join(DATA_DIR, "redirects.json");
let redirects = [];
if (existsSync(redirectsPath)) {
  const item = { rel: "data/processed/redirects.json", data: JSON.parse(readFileSync(redirectsPath, "utf8")) };
  if (validate("redirects.schema.json", item)) redirects = item.data;
}

// 2. Referential integrity
const stepIds = new Set(steps.map((s) => s.data.id));
const fieldIds = new Set(fields.map((f) => f.data.id));
for (const f of fields) {
  for (const p of f.data.paths ?? []) {
    for (const s of p.steps ?? []) {
      if (!stepIds.has(s.step)) err(f.rel, `path "${p.id}" uses unknown step "${s.step}"`);
    }
  }
  if (f.data.replaced_by && !fieldIds.has(f.data.replaced_by)) err(f.rel, `replaced_by "${f.data.replaced_by}" not found`);
}
for (const s of steps) {
  if (s.data.replaced_by && !stepIds.has(s.data.replaced_by)) err(s.rel, `replaced_by "${s.data.replaced_by}" not found`);
}
for (const h of helps) {
  for (const id of h.data.step_ids ?? []) if (!stepIds.has(id)) err(h.rel, `unknown step_id "${id}"`);
  for (const id of h.data.field_ids ?? []) if (!fieldIds.has(id)) err(h.rel, `unknown field_id "${id}"`);
}

// 2b. Catalog and quiz integrity
if (catalog) {
  const ids = new Set();
  for (const f of catalog.data.fields) {
    if (ids.has(f.id)) err(catalog.rel, `duplicate catalog id "${f.id}"`);
    ids.add(f.id);
    if (f.status === "ready" && !fieldIds.has(f.id)) err(catalog.rel, `"${f.id}" is ready but data/processed/fields/${f.id}.json does not exist`);
    if (f.status === "coming" && fieldIds.has(f.id)) warn(catalog.rel, `"${f.id}" has a roadmap; set status to ready`);
  }
  for (const id of fieldIds) if (!ids.has(id)) warn(catalog.rel, `field "${id}" is missing from the catalog`);
}
if (quiz) {
  const q = new Set();
  for (const question of quiz.data.questions) {
    if (q.has(question.id)) err(quiz.rel, `duplicate question id "${question.id}"`);
    q.add(question.id);
    const o = new Set();
    for (const opt of question.options) {
      if (o.has(opt.id)) err(quiz.rel, `${question.id}: duplicate option id "${opt.id}"`);
      o.add(opt.id);
    }
  }
  const covered = new Set(quiz.data.questions.flatMap((qq) => qq.options.flatMap((opt) => Object.keys(opt.score))));
  for (const h of ["R", "I", "A", "S", "E", "C"]) if (!covered.has(h)) err(quiz.rel, `no option scores Holland type ${h}`);
}

// 3. No id that exists on the base branch may disappear (retire instead)
function baseIds() {
  try {
    const out = execFileSync("git", ["ls-tree", "-r", "--name-only", BASE_REF, "data/processed"], {
      cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
    });
    const ids = new Set();
    for (const path of out.split("\n").filter((p) => /\/(fields|steps|helps)\/[^/]+\.json$/.test(p))) {
      const data = JSON.parse(execFileSync("git", ["show", `${BASE_REF}:${path}`], { cwd: ROOT, encoding: "utf8" }));
      ids.add(data.id);
      for (const p of data.paths ?? []) ids.add(p.id);
    }
    return ids;
  } catch {
    warn("git", `could not read ${BASE_REF}; skipped the removed-id check`);
    return null;
  }
}
const before = baseIds();
if (before) for (const id of before) if (!seen.has(id)) err("data/processed", `id "${id}" exists on ${BASE_REF} but was removed; set "retired": true instead`);

// 4-5. Dates and URLs
const today = new Date().toISOString().slice(0, 10);
const daysBetween = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
for (const h of helps) {
  const { checked_at, deadline, age_min, age_max } = h.data;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(checked_at ?? "")) continue;
  if (checked_at > today) err(h.rel, `checked_at ${checked_at} is in the future`);
  if (/^\d{4}-\d{2}-\d{2}$/.test(deadline ?? "") && deadline < checked_at) err(h.rel, `deadline ${deadline} is before checked_at`);
  if (/^\d{4}-\d{2}-\d{2}$/.test(deadline ?? "") && deadline < today && !h.data.retired) warn(h.rel, `deadline ${deadline} has passed; retire or update it`);
  if (daysBetween(checked_at, today) > STALE_DAYS) warn(h.rel, `checked ${daysBetween(checked_at, today)} days ago; re-check the source`);
  if (age_min != null && age_max != null && age_min > age_max) err(h.rel, `age_min > age_max`);
}

// 6. No personal data patterns in content
const PATTERNS = [
  [/\b01[016789]-?\d{3,4}-?\d{4}\b/, "phone number"],
  [/\b\d{6}-?[1-4]\d{6}\b/, "resident registration number"],
  [/[A-Za-z0-9._%+-]+@(?![A-Za-z0-9.-]*\.(go\.kr|or\.kr|ac\.kr|re\.kr)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}/, "personal email"],
];
for (const item of [...fields, ...steps, ...helps]) {
  const text = JSON.stringify(item.data);
  for (const [re, label] of PATTERNS) if (re.test(text)) err(item.rel, `looks like a ${label}; remove personal data`);
}

// 7. Redirect targets must point somewhere real
const knownPaths = new Set(["/", ...fields.flatMap((f) => [`/fields/${f.data.id}`, ...(f.data.paths ?? []).map((p) => `/fields/${f.data.id}/${p.id}`)])]);
for (const r of redirects) {
  if (r.to.startsWith("/fields/") && !knownPaths.has(r.to)) warn("data/processed/redirects.json", `redirect target ${r.to} is not a known page`);
}

const counts = `${fields.length} fields, ${steps.length} steps, ${helps.length} helps`;
for (const w of warnings) console.log(`warn  ${w}`);
for (const e of errors) console.log(`error ${e}`);
if (errors.length) {
  console.log(`\n[fail] ${errors.length} error(s), ${warnings.length} warning(s) · ${counts}`);
  process.exit(1);
}
console.log(`[pass] data is valid · ${counts}${warnings.length ? ` · ${warnings.length} warning(s)` : ""}`);
