import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Guide articles (situation and career guides). Facts must carry sources; drafts are not built.
const guide = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/guide" }),
  schema: z.object({
    title: z.string().max(60),
    description: z.string().max(160),
    updated: z.coerce.date(),
    field: z.string().regex(/^[a-z0-9][a-z0-9-]{1,39}$/).optional(),
    sources: z.array(z.object({ title: z.string(), url: z.string().url().startsWith("https://"), checked_at: z.string() })).default([]),
    draft: z.boolean().default(true),
  }),
});

export const collections = { guide };
