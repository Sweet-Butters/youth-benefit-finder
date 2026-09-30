# 인수인계: 다른 컴퓨터에서 이어 하기

> **마지막 갱신:** 2026-10-01 (Claude)
> 이 문서는 "어디서 무엇을 가져와야 하나"만 적는다. 지금 할 일과 상태는 `docs/progress.md`, 결정 이유는 `docs/decisions.md`가 정본이다.

## 1. 한눈에

- 저장소: https://github.com/Sweet-Butters/youth-benefit-finder (`main`이 정본, 작업은 브랜치 → PR)
- 사이트: https://sweet-butters.github.io/youth-benefit-finder/ (main 머지 시 자동 배포)
- 단계: 1단계 MVP. M1·M2 개발 끝, 사람 확인·학생 시험 남음. M3는 개인정보 상담 뒤.
- **프로젝트의 모든 내용은 GitHub에 있다.** 새 컴퓨터에서는 clone만 하면 문서·데이터·코드·현황판이 다 온다. 저장소 밖에 있는 것은 아래 4절뿐이다.

## 2. 새 컴퓨터 준비 (한 번)

필요한 것: Git, [GitHub CLI](https://cli.github.com/)(`gh`), Node.js 22 이상, Python 3.12 이상, Claude Code.

```bash
gh auth login                                   # Sweet-Butters 계정
gh repo clone Sweet-Butters/youth-benefit-finder
cd youth-benefit-finder
npm ci                                          # 데이터 검사 도구
(cd web && npm ci)                              # 사이트
pip install -r requirements.txt                 # 수집기 (수집을 직접 돌릴 때만)
python tests/verify.py                          # 전체 검사: 데이터 검사 + 사이트 빌드
```

`python tests/verify.py`가 통과하면 준비 끝이다. 사이트를 눈으로 보려면 `cd web && npm run dev` → http://localhost:4321.

## 3. Claude로 이어 하기

저장소 폴더에서 Claude Code를 열고 "프로젝트 불러와줘"라고 하면 된다. Claude는 `CLAUDE.md`의 **Start here** 순서(`docs/state/active-work.json` → `docs/progress.md` → `docs/decisions.md`)대로 읽고 현황을 보고한다.

- 한 번에 **코디네이터 세션은 하나만**. 두 컴퓨터에서 동시에 현황판을 고치면 서로 어긋난다. 옮기기 전에 옛 컴퓨터의 작업은 PR로 올리거나 머지해 둔다.
- 현황판과 git이 다르면 git이 맞다.
- `CLAUDE.md`가 말하는 `pr-loop`, `verify`, `verify-visual` 스킬은 **저장소에 없고 사용자 Claude 설정(`~/.claude/skills/`)에 있다**. 새 컴퓨터에 없으면 같은 일을 손으로 한다: PR은 `gh pr create`/`gh pr merge`, 검사는 `python tests/verify.py`, 그림은 크기·글자·여백을 수치로 확인.
- Claude의 대화 기록·메모리(`~/.claude/projects/`)는 컴퓨터마다 따로다. 필요한 것은 모두 저장소 문서에 적어 두었으므로 옮기지 않아도 된다.

## 4. 저장소 밖에 있는 것 (직접 챙길 것)

| 무엇 | 어디에 | 새 컴퓨터에서 |
|---|---|---|
| 공공데이터포털 키, Jev(TypeSafe) 키 | **GitHub Secrets**(`DATA_GO_KR_KEY`, `TYPESAFE_API_KEY`)에 등록돼 있음. 원래 컴퓨터의 `D:\orca\secrets\youth-benefit-finder\`에도 파일로 | 매일 수집은 GitHub Actions에서 돌므로 **옮기지 않아도 된다**. 수집기를 직접 돌릴 때만 `cp .env.example .env` 후 값을 채운다. 키를 채팅·커밋에 붙이지 않는다 |
| GoatCounter 조회수 | 계정 `sweetbutters`, 저장소 변수 `GOATCOUNTER_CODE` | 할 일 없음 |
| 커리어넷·온통청년·보조금24 API | 각 사이트 계정(사용자) | 승인 나면 키를 GitHub Secrets 또는 `.env`에 |
| Cloudflare(`jinro.mandeun.com`) | 팀원 계정 tree8727, PR #41 참고 | PR #41을 머지하려면 `CLOUDFLARE_API_TOKEN` Secret이 필요 |
| 1주차 미션 PPT, 한 장 요약, 꿈드림 멘토단 신청서 | 원래 컴퓨터의 Downloads 등 (저장소 밖, 팀원 이름이 있어 일부러 뺌) | 필요하면 USB·드라이브로 직접 옮긴다 |
| 크롤링 원문 `data/raw/`, 검토 목록 `review.json` | 커밋 안 함(저작권·크기) | 수집기를 돌리면 다시 생긴다. 검토 목록은 collect 워크플로의 Actions 산출물 |

## 5. 자동으로 도는 것

- **collect** (`.github/workflows/collect.yml`): 매일 06:00 KST 혜택 수집 → `data/processed/` 커밋 → 사이트 배포.
- **deploy**: main에 머지하면 사이트 배포.
- **check**: PR마다 전체 검사.
- **수집 경고**: 출처가 이틀 연속 실패하거나 절반 아래로 떨어지면 GitHub 이슈(라벨 `collect-alert`), 월요일엔 주간 요약 이슈.

## 6. 옮기는 시점에 열려 있던 것 (2026-10-01)

- **PR #41** 사이트를 `jinro.mandeun.com`으로 옮김(Cloudflare Workers, D29). 검사 통과, 머지 전 사람 할 일: `CLOUDFLARE_API_TOKEN` Secret 등록, GitHub Pages 끄기. D29는 이 PR이 머지돼야 `docs/decisions.md`에 들어간다.
- **이슈 #42** 수집기 주간 요약(2026-09-28). 보조금24(gov24)가 0개인 것은 키 승인 대기 때문(현황판 할 일 3번).
- 그 밖의 원격 브랜치는 모두 main에 머지됐다.
