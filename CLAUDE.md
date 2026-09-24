# youth-benefit-finder

진로 목표에 맞춰 청소년이 받을 수 있는 공공·민간 혜택을 찾아주고, 도와줄 사람과 연결하는 서비스. 자세한 내용은 `README.md`.

## Start here

1. Read `docs/state/active-work.json` - the machine-readable state.
2. Read `docs/progress.md` - the board people read.
3. Read the newest entries of `docs/decisions.md`.
4. Then report where things stand before proposing work.

## Rules

- **Keep the board true.** Update `docs/progress.md` and `docs/state/active-work.json`
  in the **same commit** as the work, including the summary and the timestamp.
- **Decisions go in `docs/decisions.md`**, never rewritten; the board says only what is true now.
- **Branch and PR.** Work on a branch off `main` and merge by PR (the `pr-loop` skill). Never
  commit straight to `main`.
- **Ask only for these**: publishing outside this repo, spending money, changing a decision
  that was already settled, and anything only the user can judge. Otherwise pick the
  sensible default, do it, and write down what you picked.
- **One coordinator session at a time.** Two sessions editing the board contradict each other.
- **No secrets in the repo.** Keys live in `.env` and GitHub Secrets.
- If the board and git disagree, git wins - say so.

## Project-specific rules

- **미성년자 개인정보는 저장소에 두지 않는다.** `data/users/`, DB 파일은 커밋 금지. 인터뷰 기록은 익명화해서만 `docs/`에 둔다.
- **크롤링 원문(`data/raw/`)은 커밋하지 않는다.** 정리된 정보와 원문 링크만 `data/processed/`에 둔다.
- 문서는 한국어로 쓴다. 영어 기본 + 한글판 분리는 `docs/decisions.md`와 현황판의 결정 대기 항목을 따른다.
- 아직 코드와 자동 검사가 없다. `verify` 스킬은 "검사 없음"으로 보고하고, 코드가 생기면 `tests/verify.py`를 만든다.
- 그림·PDF·포스터를 만들거나 고치면 `verify-visual` 방식으로 크기·글자·여백을 수치로 확인한다.
