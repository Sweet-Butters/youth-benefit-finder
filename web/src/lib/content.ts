// Reads the shared content data in ../data/processed at build time.
export type HelpType = "support" | "scholarship" | "course" | "contest" | "experience" | "resource";
export interface Step { id: string; title: string; summary: string; kind: string; official_url?: string; retired?: boolean }
export interface PathStep { step: string; note?: string }
export interface Path { id: string; title: string; summary: string; steps: PathStep[]; pros?: string[]; cons?: string[]; retired?: boolean }
export interface Field { id: string; title: string; summary: string; holland: string[]; paths: Path[]; retired?: boolean }
export interface Help {
  id: string; type: HelpType; title: string; provider: string; url: string; summary: string;
  checked_at: string; deadline: string | null; regions: string[]; step_ids?: string[]; field_ids?: string[];
  sponsored: boolean; age_min?: number; age_max?: number; cost?: string; retired?: boolean;
}

const values = <T>(mods: Record<string, unknown>) => Object.values(mods).map((m) => (m as { default: T }).default);

export const fields = values<Field>(import.meta.glob("../../../data/processed/fields/*.json", { eager: true }));
export const steps = new Map(values<Step>(import.meta.glob("../../../data/processed/steps/*.json", { eager: true })).map((s) => [s.id, s]));
export const helps = values<Help>(import.meta.glob("../../../data/processed/helps/*.json", { eager: true })).filter((h) => !h.retired);

export const helpsForStep = (stepId: string) => helps.filter((h) => h.step_ids?.includes(stepId));
export const helpsForField = (fieldId: string) => helps.filter((h) => h.field_ids?.includes(fieldId));

export const REGION_LABEL: Record<string, string> = {
  all: "전국", seoul: "서울", busan: "부산", daegu: "대구", incheon: "인천", gwangju: "광주", daejeon: "대전", ulsan: "울산", sejong: "세종",
  gyeonggi: "경기", gangwon: "강원", chungbuk: "충북", chungnam: "충남", jeonbuk: "전북", jeonnam: "전남", gyeongbuk: "경북", gyeongnam: "경남", jeju: "제주",
};
export const COST_LABEL: Record<string, string> = { free: "무료", paid: "유료", partly: "일부 지원" };

export const KIND_LABEL: Record<string, string> = {
  exam: "시험", license: "자격증", training: "훈련", school: "학교", experience: "체험", job: "일", mission: "미션", other: "기타",
};
export const HELP_LABEL: Record<HelpType, string> = {
  support: "지원", scholarship: "장학금", course: "강좌·훈련", contest: "대회", experience: "체험", resource: "자료",
};
