// The /helps/ list as JSON (lib/payload.ts), fetched by helps/index.astro so the page itself stays small.
import type { APIRoute } from "astro";
import { listPayload } from "../../lib/payload";

export const GET: APIRoute = () =>
  new Response(JSON.stringify(listPayload()), { headers: { "Content-Type": "application/json; charset=utf-8" } });
