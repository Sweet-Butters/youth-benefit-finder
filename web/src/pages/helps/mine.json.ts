// 내 조건 혜택 for the home page's find-talk as JSON (lib/payload.ts), fetched when the talk reaches its result.
import type { APIRoute } from "astro";
import { minePayload } from "../../lib/payload";

export const GET: APIRoute = () =>
  new Response(JSON.stringify(minePayload()), { headers: { "Content-Type": "application/json; charset=utf-8" } });
