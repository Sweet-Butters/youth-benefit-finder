// Site base path (astro.config `base`). Every internal link goes through here so the site
// works at "/" on jinro.mandeun.com and under a sub-path when SITE_BASE is set (astro.config.mjs).
const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

/** Prefix a root-relative path ("/guide", "/fields/cooking#x") with the base path. */
export function url(path: string): string {
  if (!path.startsWith("/") || path.startsWith("//")) return path;
  return path === "/" ? `${BASE}/` : `${BASE}${path}`;
}

/** Strip the base from a pathname, e.g. for matching the current nav item. */
export function unbase(pathname: string): string {
  return BASE && pathname.startsWith(BASE) ? pathname.slice(BASE.length) || "/" : pathname;
}
