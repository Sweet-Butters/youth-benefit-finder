import { defineConfig } from "astro/config";

// Content data lives outside web/ (../data/processed), shared with the validator and later the crawler.
export default defineConfig({
  site: "https://example.pages.dev", // TODO: 도메인이 정해지면 바꾼다 (docs/architecture.md 5절)
  vite: { server: { fs: { allow: [".."] } } },
});
