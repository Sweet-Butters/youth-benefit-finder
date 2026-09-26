// robots.txt under the base path. GitHub Pages serves this project at /youth-benefit-finder/, and crawlers only
// read robots.txt at the domain root, so on github.io this file is a pointer for people and tools; the sitemap
// itself has to be submitted in Search Console. On our own domain (base "/") it becomes the real one.
import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, "/");
  const sitemap = new URL(`${base}sitemap-index.xml`, site).href;
  return new Response(`User-agent: *\nAllow: /\n\nSitemap: ${sitemap}\n`, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
