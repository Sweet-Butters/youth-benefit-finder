# 혜택 수집기

공식 출처에서 청소년 혜택(시험 일정, 장학금, 체험, 봉사)을 모아 `data/collected/`에 둔다.
사이트는 빌드할 때 `items.json`을 읽어 분야 페이지 혜택 칸에 **공식 자동** 표시로 띄운다 (열림·곧 열림만, `web/src/lib/collected.ts`). 파일이 없거나 비어도 빌드된다. 설계 이유는 `docs/collection-strategy.md`.

```bash
pip install -r requirements.txt
export DATA_GO_KR_KEY=...      # 공공데이터포털 일반 인증키 (없으면 키가 필요한 출처는 건너뜀)
export TYPESAFE_API_KEY=...    # Jev (없으면 규칙만으로 판단)
python -m crawler.main         # 전체
python -m crawler.main qnet    # 출처 하나만
```

## 흐름

1. 출처마다 `crawler/sources/<이름>.py`의 `fetch()`가 `Item` 목록을 돌려준다. 한 출처가 깨져도 나머지는 돈다.
2. `youth.py`: 14~24세가 신청할 수 있나 (규칙). 모르면 검토.
3. `attach.py` + `config/attach-rules.json`: 로드맵 어느 단계에 붙나 (규칙). 없으면 검토.
4. `jev.py`: Jev가 두 번째 의견. 규칙이 모를 때 0.85 이상이면 살리고, 느슨한 단어로만 붙었을 때 0.15 미만이면 뺀다. 학교 밖 청소년 가능 0.85 이상이면 `out_of_school_ok` 태그. 단계 답은 힌트(`jev.step`)로만 남긴다 (첫 실행에서 틀린 게 많았다).
5. `merge.py`: 이전 결과와 합치고, 출처끼리 중복을 묶고, 날짜로 상태(열림, 곧 열림, 마감)를 정한다.

## 결과 파일

| 파일 | 내용 | 커밋 |
|---|---|---|
| `items.json` | 청소년 가능 + 단계에 붙은 항목 | 예 |
| `review.json` | 사람이 볼 항목 (`review_reason`) | 아니오 (Actions 산출물) |
| `meta.json` | 출처별 가져온 수·오류·시간, Jev 통계 | 예 |
| `jev_cache.json`, `jev_runs.jsonl` | Jev 답 캐시, 실행별 비용 | 예 |

## 출처 추가

`sources/qnet.py`를 본보기로 `NAME`, `LABEL`, `NEEDS_KEY`, `fetch()`를 만들고 `sources/__init__.py`의 `ALL`에 넣는다.
키는 코드나 파일에 쓰지 않는다. `http.get(..., api_key=True)`가 환경 변수에서 붙이고, 오류 메시지에서는 지운다.
