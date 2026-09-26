import { defineConfig } from "astro/config";

const BASE = "/youth-benefit-finder";

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
  // 지금은 GitHub Pages(sweet-butters.github.io/youth-benefit-finder). 나중에 우리 도메인으로 옮기면
  // site를 그 도메인으로, base를 "/"로 바꾼다. 내부 링크는 src/lib/url.ts를 거치므로 따라온다 (docs/architecture.md 5절).
  site: "https://sweet-butters.github.io",
  base: BASE,
  markdown: { remarkPlugins: [remarkBaseLinks] },
  vite: { server: { fs: { allow: [".."] } } },
});
