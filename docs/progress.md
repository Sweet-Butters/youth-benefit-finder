# youth-benefit-finder 현황판

> **마지막 갱신:** 2026-09-25 03:13 (Claude)
> 작업과 **같은 커밋**에서 이 파일을 고친다. 로그만 늘리지 말고 요약과 위 시각도 바꾼다.
> 모든 항목에는 시각과 누가 했는지를 적는다. 기계용 상태는 `docs/state/active-work.json`, 결정 이유는 `docs/decisions.md`.

## 요약

- **0단계: 문제 검증 준비 중.** 코드는 아직 없다. 기획 문서(README, 경쟁 분석, 검증 계획, 로드맵)만 있다.
- 기획 로드맵(`docs/roadmap.md`), 로드맵 그림 3장(`docs/images/*.svg`), 현황판을 `main`으로 보내는 **PR을 올렸다** (리뷰·머지 대기).
- 다음 큰 일정은 2026년 10월 꿈드림 AI 교육 봉사 시작과 당사자 인터뷰다.

## 진행 중

| 작업 | 누가 | 하는 일 | 상태 | 시작 |
|---|---|---|---|---|
| 로드맵·그림·현황판 PR | Claude | `Sweet-Butters/plan-youth-benefit-mermaid` → `main` | PR 리뷰·머지 대기 | 2026-09-25 |

## 사용자가 할 일

| # | 할 일 | 메모 |
|---|---|---|
| 1 | `docs/images/` 그림 3장 확인 | 팀원·센터 선생님용으로 괜찮은지 |
| 2 | 로드맵·현황판 PR 확인 후 머지 결정 | 브랜치 `Sweet-Butters/plan-youth-benefit-mermaid` → `main` |
| 3 | Orca → Settings → youth-benefit-finder → Setup script에 현황판 스크립트 넣기 | CLI로는 설정 불가. 명령: `& "$HOME\.claude\skills\project-board\bootstrap-board.ps1"` |
| 4 | 꿈드림 센터에 10월 봉사 일정 연락 | 검증 계획 방법 1 |

## 결정 대기

| 결정 | 아무 말 없으면 | 언제까지 |
|---|---|---|
| H1 판단 기준 수치 (예: 인터뷰 15명 중 8명 이상 "나중에 알고 놓쳤다") | 예시 수치를 그대로 쓴다 | 첫 인터뷰 전 (2026-10월 말) |
| README를 영어 기본 + `README.ko.md` 한글판으로 나눌지 (bilingual-repo 스킬) | 외부 공개·홍보 전까지 한국어만 유지 | 저장소를 외부에 알리기 전 |
| 서비스 이름 확정 | 가칭 `youth-benefit-finder` 유지 | MVP 공개 전 |
| 라이선스 | 정하지 않음 (모든 권리 저작자) | 외부 기여를 받기 전 |

---

## 로그 (최신이 위)

| 시각 | 종류 | 한 일 | 결과 |
|---|---|---|---|
| 2026-09-25 03:13 | pr | Claude: 로드맵·그림·현황판을 커밋하고 `main`으로 PR 생성 (사용자 요청) | PR 리뷰 대기 |
| 2026-09-25 03:06 | setup | Claude: 현황판(progress.md, active-work.json, CLAUDE.md, decisions.md) 생성, `.claude/handoff.md`를 .gitignore에 추가 | 스킬 세팅 완료 |
| 2026-09-25 03:02 | docs | Codex(gpt-5.6-luna): 로드맵 머메이드 3개를 SVG 그림으로 제작 | `docs/images/roadmap-{decisions,timeline,mvp-scope}.svg`, UTF-8·한글 확인 |
| 2026-09-25 | docs | Claude: 기획 로드맵 작성, README에서 링크 | `docs/roadmap.md` |
| 2026-09-25 | docs | 사용자: 멘토 매칭, 경쟁 분석, 검증 계획 추가 | 커밋 56b3942 |
| 2026-09-25 | setup | 사용자: 프로젝트 뼈대 생성 | 커밋 16a2ea4 |
