// robots.txt under the base path. On jinro.mandeun.com (base "/") this is the real one crawlers read.
// Built under a sub-path (SITE_BASE) it is only a pointer for people and tools, because crawlers read
// robots.txt at the domain root; the sitemap then has to be submitted in Search Console by hand.
import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, "/");
  const sitemap = new URL(`${base}sitemap-index.xml`, site).href;
  return new Response(`User-agent: *\nAllow: /\n\nSitemap: ${sitemap}\n`, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
