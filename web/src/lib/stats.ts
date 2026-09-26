// Public view counts (D25). GoatCounter counts page views without cookies or personal data, and can
// serve each page's count as JSON so visitors (and sponsors) see "조회 N" like dreamspon.com.
// Set PUBLIC_GOATCOUNTER_CODE (the <code> in <code>.goatcounter.com) at build time; unset = no counting.
export const GC_CODE: string = (import.meta.env.PUBLIC_GOATCOUNTER_CODE ?? "").trim();
export const GC_ORIGIN = GC_CODE ? `https://${GC_CODE}.goatcounter.com` : "";

/** Counts below this stay hidden: "조회 3" tells a new visitor nobody comes here. */
export const MIN_SHOWN = 50;

/** The path we count under. Same rule as the counting script: always a trailing slash, no query. */
export function countPath(pathname: string): string {
  const p = pathname.split(/[?#]/)[0];
  return p.endsWith("/") ? p : `${p}/`;
}
