import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// 주소는 환경변수로 고른다 (docs/architecture.md 1절). 기본값이 우리 도메인이다.
// 옛 GitHub Pages 주소로 빌드하려면: SITE_URL=https://sweet-butters.github.io SITE_BASE=/youth-benefit-finder
const SITE = process.env.SITE_URL ?? "https://jinro.mandeun.com";
const BASE = (process.env.SITE_BASE ?? "/").replace(/\/+$/, ""); // 도메인 루트면 ""

// Markdown links like [x](/fields/cooking) are root-relative; prefix them with the base.
function remarkBaseLinks() {
  const walk = (node) => {
    if ((node.type === "link" || node.type === "image") && typeof node.url === "string"
        && node.url.startsWith("/") && !node.url.startsWith("//") && !node.url.startsWith(BASE + "/")) {
      node.url = BASE + node.url;
    }
    node.children?.forEach(walk);
  };
  return (tree) => walk(tree);
}

// Content data lives outside web/ (../data/processed), shared with the validator and later the crawler.
export default defineConfig({
  // jinro.mandeun.com (Cloudflare Workers, web/wrangler.jsonc, .github/workflows/deploy.yml).
  // 내부 링크는 src/lib/url.ts를 거치므로 base를 따라온다 (docs/architecture.md 5절).
  site: SITE,
  base: BASE || "/",
  markdown: { remarkPlugins: [remarkBaseLinks] },
  // Every stylesheet as a cached file, never inlined: thousands of /helps/ detail pages share them (D28).
  build: { inlineStylesheets: "never" },
  // sitemap-index.xml + sitemap-0.xml under the base, every built page except design concepts and 404.
  // Drafts are never built, so they never get listed. robots.txt (src/pages/robots.txt.ts) points here.
  integrations: [sitemap({ filter: (page) => !/\/(concepts\/|404\/?$)/.test(new URL(page).pathname) })],
  vite: { server: { fs: { allow: [".."] } } },
});
