# MVP 아키텍처: 나중에 바꾸기 어려운 것만

> 작성일: 2026-09-25 (Claude Fable 5.1 작성, Claude Opus 5.5 검토). `docs/mvp.md`(MVP 설계)와 `docs/decisions.md` D1~D15를 따른다. 작성 중에 정해진 D16~D19와의 차이는 맨 아래 **검토 메모**에 있다.
> 이 문서는 **바꾸는 비용이 큰 결정**만 다룬다. 화면 구성, 컴포넌트 이름, 색 같은 것은 만들면서 정한다.
> 확실한 것과 가정을 나눠 적었다. 가정은 "(가정)"으로 표시했다.

## 0. 전제

| 항목 | 내용 | 비고 |
|---|---|---|
| 웹 | Astro 정적 사이트. React 아일랜드는 **퀴즈와 로드맵 도구, 내 페이지**에만 쓴다 | 콘텐츠 페이지는 JS 없이 나가야 검색과 저사양 폰에 좋다 |
| 콘텐츠 데이터 | `data/processed/`의 JSON. PR로 고치고 자동 검사를 거친다 | 저장소는 공개다 |
| 사용자 데이터 | Supabase (Auth, Postgres, Storage). 무료 티어 | 저장소에 절대 두지 않는다 (`CLAUDE.md`) |
| 호스팅 | Cloudflare Pages 또는 Vercel 무료 티어. 정적 파일만 올린다 | 서버 코드 없음 |
| 호스팅 (지금) | **GitHub Pages** `https://sweet-butters.github.io/youth-benefit-finder/` (`base: /youth-benefit-finder`, `.github/workflows/deploy.yml`). 이 컴퓨터에 Cloudflare 로그인이 없어서 먼저 이걸로 공개했다. GitHub Pages는 301 리다이렉트 파일을 못 쓰므로 `redirects.json`이 생기기 전이나 도메인을 정할 때 다시 본다 | 내부 링크는 `web/src/lib/url.ts`를 거쳐 base를 따른다 |
| 방문 통계 | 쿠키 없고 개인을 못 알아보는 도구 (예: Cloudflare Web Analytics, Umami) | 3절 참고 |
| 팀 | 학생 3명, 파트타임. React 경험은 한 명이 조금 | 그래서 **서버를 만들지 않는다** |

- 위 기술 선택은 `decisions.md`에 아직 없다. **D20으로 기록하기를 제안한다.** README의 "기술 스택 (예정)" 표도 그때 고친다.
- 커스텀 백엔드 서버, 마이크로서비스, 별도 DB 서버는 만들지 않는다. 비밀 키가 필요한 일(v1의 AI 호출, 통계 집계)은 Supabase Edge Function이나 GitHub Actions에서 한다.

## 1. 데이터가 어디에 사는가

### 결정: 콘텐츠는 git, 사용자 데이터는 Supabase. 둘은 **문자열 ID**로만 연결한다

| | 콘텐츠 (지도, 지원 정보, 퀴즈) | 사용자 데이터 |
|---|---|---|
| 어디 | `data/processed/*.json`, 공개 저장소 | Supabase Postgres, Storage |
| 누가 고치나 | 팀이 PR로. 사실 확인 담당(C)이 리뷰 | 학생 본인만 (RLS) |
| 개인정보 | **없어야 한다** (검사로 막는다) | 있다. 최소 수집 |
| 키 | `field_id`, `path_id`, `step_id`, `help_id` | 위 ID를 **문자열 그대로** 저장 |

- 사용자 테이블은 콘텐츠 ID를 **외래 키 없이** 문자열로 담는다. 콘텐츠가 DB에 없으니 외래 키를 걸 수 없고, 걸 필요도 없다.
- 그래서 **ID는 한 번 공개하면 절대 바꾸지 않는다.** 제목, 설명, 순서는 마음껏 고쳐도 학생의 기록(D15)은 살아남는다. 항목을 없앨 때는 지우지 않고 `retired: true`와 `replaced_by`를 적는다. 사이트는 `retired` 항목을 새로 추천하지 않지만, 이미 기록한 학생에게는 계속 보여 준다.
- 검토한 대안: **(a) 콘텐츠도 Supabase에** → 비개발자가 고치기 어렵고, 리뷰·되돌리기가 git보다 나쁘다. 공개 리뷰가 안 된다. **(b) 사용자 데이터를 로컬 저장소(브라우저)에만** → 기기 바꾸면 사라지고, 합친 통계(D10)와 나의 기록(D15)을 못 만든다. 다만 **가입하지 않은 사용자의 도구 답변은 브라우저 `localStorage`에만** 둔다 (mvp.md "가입하지 않으면 저장하지 않는다").

### JSON 데이터 모델

단계(step)는 길(path)에 속하지 않고 **전체에서 공유하는 카탈로그**다. 검정고시는 요리사 길에도, 개발자 길에도 나온다. 학생이 "해냈어요"를 한 번 누르면 모든 길에서 완료로 보인다.

```
data/processed/
  fields/<field_id>.json      분야 1개 + 그 분야의 길(paths) 목록
  steps/<step_id>.json        단계 1개 (공유 카탈로그)
  helps/<help_id>.json        지원·장학금·무료 강의·대회·체험 1개
  quiz/questions.json         퀴즈 10문항, 보기별 홀랜드 가중치
  quiz/scoring.json           홀랜드 점수 → 분야 3개 매핑
  redirects.json              바뀐 URL → 새 URL (5절)
data/schema/*.schema.json     위 파일들의 JSON Schema
```

ID 규칙: `^[a-z0-9][a-z0-9-]{1,39}$`. 영문 소문자와 숫자, 하이픈만. 예: `cooking`, `ged-high`, `cooking-college`, `help-2026-kfoods-contest`. 한글 ID는 URL과 코드에서 인코딩 문제가 생겨 쓰지 않는다.

| 파일 | 필수 필드 | 선택 필드 |
|---|---|---|
| `fields/*.json` | `id`, `title`, `summary`, `holland` (RIASEC 중 1~2개), `paths[]` | `retired`, `replaced_by` |
| `paths[]` (field 안) | `id`, `title`, `summary`, `steps[]` = `[{ "step": "<step_id>", "note": "..." }]` | `pros[]`, `cons[]`, `retired` |
| `steps/*.json` | `id`, `title`, `summary`, `kind` (`exam`, `license`, `training`, `school`, `experience`, `job`, `other`) | `official_url`, `typical_duration`, `retired`, `replaced_by` |
| `helps/*.json` | `id`, `type` (`support`, `scholarship`, `course`, `contest`, `experience`), `title`, `provider`, `url`, `summary` (200자 이내, **원문 복사 금지**), `checked_at` (YYYY-MM-DD), `deadline` (날짜 또는 `"rolling"` 또는 `null`), `regions[]` (`"all"` 또는 시·도 코드), `step_ids[]` 또는 `field_ids[]` 중 하나 이상, `sponsored` (기본 `false`) | `age_min`, `age_max`, `cost` (`free`, `paid`, `partly`), `retired` |
| `quiz/questions.json` | `id` (`q01`~`q10`), `text`, `options[]` = `{ "id": "a", "text", "weights": {"R":0,"I":1,...} }` | — |

- `sponsored`는 지금은 전부 `false`다. 나중에 기관 홍보 게재(business-model.md 4번)가 생겨도 **추천 계산에서는 빼고 "후원" 표시로만** 쓴다. 필드를 지금 만들어 두는 이유는, 나중에 추가하면 "추천이 돈에 영향받는가"를 코드로 증명하기 어려워지기 때문이다.
- 검사 스크립트(`scripts/validate-data.mjs`)가 PR마다 확인하는 것:
  1. JSON Schema 통과, 필수 필드 있음, ID 형식 맞음, ID 중복 없음
  2. 참조 무결성: `step_ids`, `field_ids`, `replaced_by`, `paths[].steps[].step`가 실제로 존재
  3. **`main`과 비교해 사라진 ID가 없음** (지우지 말고 `retired`로)
  4. `url`은 `https://`, `deadline >= checked_at`, `checked_at`이 미래가 아님
  5. `checked_at`이 90일 넘게 오래됐으면 **경고** (실패 아님, 팀이 확인 주기를 정한다)
  6. 개인정보 패턴 없음: 전화번호, 이메일(공식 기관 도메인 제외), 주민번호 형식
  7. 사라진 URL 슬러그가 `redirects.json`에 있음 (5절)

## 2. 사용자 데이터 모델

### 결정: 테이블 5개, D11·D13·D15에 필요한 열을 **처음부터** 둔다

모든 표는 Supabase Postgres `public` 스키마. 스키마와 RLS는 `supabase/migrations/*.sql`에 코드로 둔다. Supabase가 관리하는 `auth.users`는 우리가 열을 추가하지 않는다.

| 표 | 열 | 메모 |
|---|---|---|
| `profiles` (auth.users와 1:1) | `user_id uuid PK → auth.users ON DELETE CASCADE`, `track text` (`student` / `adult`, 가입 뒤 변경 불가), `nickname text` (2~12자), `age_band text` (`14-16`, `17-19`, `20-24`; 어른 트랙용 `25+`는 v1), `region text` (시·도 코드 17개 + `none`), `interests text[]` (field_id), `notify boolean` 기본 false, `adult_role text` NULL (`parent` / `teacher` / `mentor`, v1), `verified_at timestamptz` NULL (멘토 신원 확인, v1), `created_at`, `updated_at` | D11의 "모으는 것" 그대로. `adult_role`, `verified_at`는 v0에서 비워 둔다 (D13) |
| `saved_roadmaps` | `id uuid PK`, `user_id`, `field_id text`, `path_id text` NULL, `answers jsonb` (5개 답, **보기 코드만**, 자유 입력 없음), `created_at` | "결과 저장하기" |
| `quiz_results` | `id uuid PK`, `user_id`, `top_fields text[]` (3개), `scores jsonb` (RIASEC 6개 숫자), `created_at` | 가입자만. 비가입자 결과는 서버에 안 남는다 |
| `step_records` (나의 기록, D15) | `id uuid PK`, `user_id`, `step_id text`, `path_id text` NULL, `done_at date`, `note text` (200자 이내), `visibility text` 기본 `private` (`private` / `link` / `public`), `verification text` 기본 `self` (`self` / `proof` / `issuer`), `verified_by text` NULL, `verified_at` NULL, `created_at`, `updated_at`, UNIQUE (`user_id`, `step_id`) | v0에는 표만 만들고 화면은 v1. `visibility`는 v0·v1 모두 `private`만 허용 (DB CHECK로 막고, 공유가 열릴 때 CHECK만 푼다) |
| `proofs` | `id uuid PK`, `record_id → step_records ON DELETE CASCADE`, `user_id`, `storage_path text`, `mime text`, `bytes int`, `issuer text` NULL, `created_at` | 파일 자체는 Storage (4절) |
| `stats_weekly` | `week date`, `metric text`, `dims jsonb`, `value int`, PK (`week`, `metric`, `dims`) | **개인 열이 없다.** 3절 |

- **저장하지 않는 것**: 실명, 학교 이름, 전화번호, 상세 주소, 생년월일(나이대만), 성별, IP(우리 표에는 없음). 자유 입력 칸은 `nickname`과 `note` 둘뿐이고, 둘 다 전화번호·URL·이메일 패턴을 클라이언트와 DB CHECK에서 막는다.
- **로그인 식별자**: 이메일 매직 링크 또는 카카오 로그인. 어느 쪽이든 Supabase `auth.users`에 이메일이 남는다. D11의 목록에는 없으므로 **개인정보처리방침에 "로그인용 이메일"을 추가**해야 한다. → 열린 질문
- **나이 확인**: 가입 때 나이대를 고르고 "만 14세 이상입니다"에 체크한다. 14세 미만을 고르면 계정을 만들지 않고 아무것도 저장하지 않는다. 25세 이상은 v0에서 가입할 수 없다("어른 트랙은 준비 중"). 자기 신고만으로 충분한지는 **법률 확인 항목**이다.
- 검토한 대안: **(a) 테이블 하나에 `jsonb`로 전부** → 마이그레이션은 없지만 RLS·통계·검증이 어렵고, 지울 때 뭐가 들었는지 모른다. **(b) D15 표를 v1에 만들기** → 표 추가 자체는 싸지만, `step_id`를 문자열로 두는 결정과 공유·확인 열의 자리를 지금 정해 두지 않으면 v1에서 다시 논의하게 된다.

### RLS를 말로 풀면

1. 모든 표는 RLS를 켠다. **로그인 안 한 사람은 어떤 표도 못 읽는다.**
2. 로그인한 사람은 `user_id = auth.uid()`인 행만 읽고, 쓰고, 고치고, 지운다. 남의 행은 존재 여부도 알 수 없다.
3. `profiles.track`과 `user_id`는 트리거로 변경을 막는다. 학생이 어른 트랙으로, 어른이 학생 트랙으로 옮겨 갈 수 없다 (D13).
4. `stats_weekly`는 서비스 롤(GitHub Actions)만 쓰고, 읽기는 팀이 정한다(공개 리포트라면 anon 읽기 허용).
5. `anon key`는 브라우저에 노출되는 것이 정상이고, **보호는 RLS가 한다.** `service_role key`는 GitHub Secrets에만 두고 `web/`에서는 절대 쓰지 않는다.
6. 어른 트랙(v1)이 생겨도 규칙 2 덕분에 어른이 학생 데이터를 읽는 경로는 없다. 나중에 "링크로 공유"가 열리면 그때 **별도 뷰나 Edge Function**으로만 연다. RLS를 느슨하게 풀지 않는다.

## 3. 개인정보와 삭제

### 결정: 기본 비공개, 탈퇴는 한 번의 요청으로 전부 즉시 삭제, 통계는 개인 행이 없는 표에서만

- **기본 비공개**: `step_records.visibility`는 `private`가 기본이고 v0·v1에서는 유일한 값이다. 사진은 항상 서명 URL로만 본다 (4절).
- **탈퇴(계정 삭제)**: 내 설정 페이지의 "탈퇴" 버튼 → ① 클라이언트가 Storage의 `proofs/<user_id>/` 아래 파일을 모두 지운다(본인 권한으로 가능) → ② `rpc('delete_my_account')` 호출. 이 함수는 `security definer`로 `auth.users`에서 본인 행을 지우고, `ON DELETE CASCADE`로 `profiles`, `saved_roadmaps`, `quiz_results`, `step_records`, `proofs`가 함께 사라진다. 같은 요청 안에서 끝나므로 "즉시"다.
  - 안전장치: 매일 밤 GitHub Actions가 서비스 롤로 **주인 없는 Storage 파일**(DB에 `user_id`가 없는 경로)을 지운다. ①이 중간에 실패해도 하루 안에 정리된다.
  - Supabase의 백업 보관 기간(무료 티어에 일일 백업이 있는지, 며칠인지)은 **확인 후 처리방침에 적는다**. (가정: 짧다) 여기서 "즉시 삭제"는 운영 DB 기준이다.
- **기록 하나 삭제**: `step_records` 행을 지우면 `proofs` 행은 CASCADE로, 파일은 클라이언트가 먼저 지운다. 실패분은 위 야간 정리가 잡는다.
- **방문 통계가 모아도 되는 것**: 페이지 경로, 유입 경로(referrer), 국가, 기기 종류, 그리고 개인과 연결되지 않은 이벤트 5개: `quiz_completed {top_field}`, `roadmap_viewed {field_id}`, `share_clicked {kind}`, `experience_link_clicked {help_id}`, `signup_completed {age_band}`. **모으면 안 되는 것**: `user_id`, 닉네임, 이메일, 퀴즈 답안 개인별, 자유 입력 문구, 세션 녹화, 개인을 가리키는 UTM 값. 쿠키와 브라우저 지문(fingerprint)을 쓰지 않는 도구만 고른다. (가정) Cloudflare Web Analytics는 무료·쿠키 없음이라 첫 후보다. 로그인 뒤 페이지(`/me/*`)에는 통계 스크립트를 넣지 않는다.
- **합친 통계(D10) 만드는 법**: 매주 GitHub Actions가 서비스 롤로 SQL을 돌려 `stats_weekly`에 **개수만** 쓴다. 예: `metric = 'saved_roadmap_by_field', dims = {"field":"cooking","region":"seoul","age_band":"17-19"}, value = 12`. 규칙: ① 개수가 **k 미만인 칸은 쓰지 않는다** (k는 팀이 정한다, 예: 5). 지역 × 나이대 × 분야를 다 쪼개면 초기에는 한 명이 드러난다. ② 개인 행을 Supabase 밖으로 내보내는 작업은 없다. 리포트는 `stats_weekly`만 읽어 만든다. ③ 탈퇴해도 지난 주의 개수는 남는다. 개인 행이 아니므로 문제없다고 보지만 처리방침에 적는다.
- 검토한 대안: **삭제를 30일 유예** → 실수로 탈퇴한 학생을 구할 수 있지만 mvp.md의 "탈퇴하면 바로 삭제"와 어긋나고, 유예 중 데이터 관리가 늘어난다. 원하면 탈퇴 전 "내 기록 내려받기(JSON)"를 v1에 넣는 쪽이 낫다.

### 법률·처리방침 확인이 필요한 항목 (여기서 결론 내리지 않는다)

| 항목 | 왜 |
|---|---|
| 개인정보처리방침 필수 기재 사항과 동의 화면 문구 | 가입을 열기 전 (`active-work.json`의 `privacy-policy`) |
| 만 14세 이상 **자기 신고**로 충분한지 | 14세 미만은 보호자 동의가 필요하다는 것만 확실 (D11) |
| 로그인용 이메일·카카오 계정 식별자의 수집 항목 표기 | D11 목록에 없음 |
| Supabase 리전과 국외 이전 고지 | 서울 리전을 고른다 (가정: 무료 티어에서 선택 가능). 방문 통계 업체의 처리 위치도 같이 확인 |
| 백업 보관 기간 표기 | 위 |
| "확인됨" 표시, 추천서 | 이미 `pending_decisions`의 `verified-label-legal` |
| 사진에 찍힌 제3자, 기관 로고 | 나의 기록 v1을 열기 전 안내 문구 |

## 4. 사진·증빙 저장

### 결정: Supabase Storage 비공개 버킷 하나, 경로 첫 폴더가 `user_id`, 서명 URL로만 본다

- 버킷: `proofs` (public = false). 경로: `proofs/<user_id>/<record_id>/<uuid>.<ext>`.
- Storage 정책: `storage.objects`에서 **경로의 첫 폴더가 `auth.uid()`와 같을 때만** 올리기·읽기·지우기 허용. 그 외 전부 거부. 공개 URL은 만들지 않는다.
- 보기: 본인이 `createSignedUrl(path, 600)`로 **10분짜리 서명 URL**을 만들어 본다. 공유 기능이 열리기 전까지 다른 사람이 볼 방법이 없다.
- 제한 (버킷 설정 + 클라이언트 둘 다): 파일 하나 **최대 2 MB**, 기록 하나에 **최대 3개**, 종류는 `image/jpeg`, `image/png`, `image/webp`, `application/pdf`만. (가정) 무료 티어 저장 용량이 1 GB 수준이라, 사진을 줄이지 않으면 수백 장에서 끝난다. 숫자는 가입 전 다시 확인한다.
- **EXIF·위치 정보 제거**: 이미지는 올리기 전에 브라우저에서 `canvas`로 다시 그려 긴 변 1,600px 이하 WebP로 저장한다. 다시 그리면 EXIF(촬영 위치, 기기, 시각)가 **전부 사라진다.** 스크립트는 `web/src/lib/image.ts` 한 파일. PDF는 메타데이터를 브라우저에서 지우기 어려우므로 그대로 두되, 올리기 전 "PDF에는 이름이 들어 있을 수 있어요"라고 알린다.
- 삭제: 기록 삭제·탈퇴 흐름은 3절. 파일 이름에 원래 파일명을 쓰지 않는다(파일명에 이름이 들어 있는 경우가 많다).
- 검토한 대안: **(a) 서버(Edge Function)에서 리사이즈·EXIF 제거** → 더 확실하지만 코드와 콜드 스타트, 함수 실행 한도가 늘어난다. 클라이언트 처리로 시작하고, 우회 업로드가 확인되면 서버 검사를 덧붙인다. **(b) 외부 이미지 서비스(Cloudinary 등)** → 미성년자 사진을 제3자에 보내는 항목이 하나 더 생긴다. 안 한다. **(c) 공개 버킷 + 추측하기 어려운 파일명** → "비공개"가 아니다. 안 한다.

## 5. URL 구조

### 결정: 영문 소문자 슬러그, ID를 그대로 URL에 쓰고, 바꿀 때는 301 리다이렉트 파일로

| 무엇 | URL | 색인 |
|---|---|---|
| 홈 | `/` | O |
| 상황별·직업별 글 | `/guide/<slug>` (예: `/guide/after-dropout-options`) | O |
| 사람 이야기 | `/stories/<slug>` | O |
| 고민 Q&A 공개본 (사이트 게시판이 생기면) | `/qna/<slug>` | O |
| 분야 지도 | `/fields/<field_id>` | O |
| 길 (마일스톤 + 단계별 도움) | `/fields/<field_id>/<path_id>` | O |
| 지원·대회·체험 목록 | `/helps` (분야·유형 필터는 쿼리스트링) | O |
| 로드맵 도구 | `/roadmap` (질문 5개) → 결과는 `/fields/<field_id>/<path_id>?s=…&a=…&r=…&t=…` | 결과는 canonical을 길 페이지로 |
| 관심 찾기 퀴즈 | `/quiz` → 결과 `/quiz/result/<f1>-<f2>-<f3>` (예: `/quiz/result/cooking-design-care`) | 결과는 `noindex`, canonical `/quiz` |
| 계정 | `/login`, `/signup`, `/me`, `/me/records` (v1), `/me/settings` (탈퇴) | 전부 `noindex` |
| 어른 트랙 (v1) | `/adults/…` 아래로 분리 | — |
| 정책 | `/legal/privacy`, `/legal/terms` | O |

- 퀴즈·로드맵 결과가 **URL만으로 다시 그려지므로** 가입하지 않아도 공유가 되고, 서버에 아무것도 남지 않는다. 결과 이미지는 클라이언트에서 만든다.
- 슬러그 규칙은 ID 규칙과 같다(1절). 날짜, 번호, 한글을 URL에 넣지 않는다. 한글 URL은 카카오톡·인스타에 붙이면 퍼센트 인코딩으로 깨져 보인다.
- **이름 바꾸기**: 제목은 언제든 바꾼다. 슬러그·ID는 바꾸지 않는 것이 원칙이고, 꼭 바꿔야 하면 `data/processed/redirects.json`에 `{"from": "/guide/old", "to": "/guide/new"}`를 추가한다. 빌드가 이 파일로 호스팅용 리다이렉트 파일(Cloudflare/Netlify는 `_redirects`, Vercel은 `vercel.json`)을 만들고 301을 낸다. 검사 스크립트가 "사라진 슬러그는 반드시 redirects에 있음"을 확인한다.
- `sitemap.xml`, `robots.txt`, canonical, Open Graph는 Astro 통합으로 자동 생성한다. 서치 콘솔·네이버 서치어드바이저 등록은 도메인이 정해진 뒤 한다.
- 검토한 대안: **(a) `/posts/<slug>` 하나로 통일** → 단순하지만 글 종류별 검색 노출 분석이 어렵다. **(b) `/steps/<step_id>`, `/helps/<help_id>` 개별 페이지** → 얇은 페이지가 수십 개 생겨 검색 품질에 안 좋고 오래된 정보가 남는다. 항목이 100개를 넘으면 다시 본다.
- **도메인**: 서비스 이름이 미정이라(`pending_decisions.service-name`) 처음엔 `*.pages.dev`로 시작할 수 있지만, **검색과 공유 링크는 도메인이 바뀌면 다 잃는다.** 콘텐츠를 외부에 알리기 전에 도메인을 정하는 것이 가장 싼 길이다. → 열린 질문

## 6. 저장소 구조와 PR 검사

```
youth-benefit-finder/
├── web/                          Astro 앱
│   ├── src/pages/                URL과 1:1 (5절)
│   ├── src/content/              글(Markdown): guide/, stories/, qna/ — Astro content collections
│   ├── src/components/           Astro 컴포넌트 (JS 없음)
│   ├── src/islands/              React: Quiz.tsx, RoadmapTool.tsx, Me.tsx
│   ├── src/lib/                  supabase.ts, image.ts, content.ts (data/processed 읽기)
│   └── public/
├── data/
│   ├── schema/                   *.schema.json
│   ├── processed/                fields/ steps/ helps/ quiz/ redirects.json
│   └── raw/                      (gitignore, 크롤러가 생기기 전까지 비어 있음)
├── supabase/
│   ├── migrations/               0001_init.sql (표 + RLS + 트리거 + delete_my_account)
│   └── functions/                v0에는 없음 (v1 AI 호출용 자리)
├── scripts/
│   ├── validate-data.mjs         1절의 검사. 의존성은 ajv 하나
│   └── build-redirects.mjs       redirects.json → _redirects / vercel.json
├── tests/verify.py               validate-data + astro build를 한 번에 (verify 스킬용, CLAUDE.md)
├── crawler/                      비워 둔다 (D5)
└── .github/workflows/
    ├── check.yml                 PR마다: validate-data → astro check → astro build
    ├── storage-sweep.yml         매일: 주인 없는 Storage 파일 삭제 (service role)
    └── stats-weekly.yml          매주: stats_weekly 집계 (service role)
```

- 글(Markdown)은 `web/src/content/`에, 구조화된 지도 데이터는 `data/processed/`에 둔다. 글은 사이트의 일부이고, 지도 데이터는 나중에 크롤러·AI·다른 앱도 읽는 **공유 자산**이기 때문이다. Astro는 빌드 때 `../data/processed`를 import한다.
- `check.yml`은 브랜치 보호에서 **필수 검사**로 건다. `data/processed/**`는 `CODEOWNERS`로 사실 확인 담당(C)의 리뷰를 요구한다.
- 환경 변수: `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY`(공개돼도 되는 값), `SUPABASE_SERVICE_ROLE_KEY`(GitHub Secrets에만). `.env.example`은 코드가 생길 때 고친다. 수집기는 `DATA_GO_KR_KEY`와 `TYPESAFE_API_KEY`(Jev)를 GitHub Secrets에서 읽는다. `LLM_API_KEY`는 v1 전까지 쓰지 않는다.
- 검토한 대안: **모노레포 도구(turborepo, pnpm workspace)** → 패키지가 `web/` 하나뿐이라 필요 없다. 패키지가 둘이 되면 그때.

## 7. 일부러 미루는 것

| 미루는 것 | 다시 꺼내는 계기 | 지금 해 두는 최소한 |
|---|---|---|
| 퀴즈·로드맵의 AI 보조 (v1) | 3개월 점검 뒤 + 팀이 비용 상한을 정한 뒤 (mvp.md) | API 키는 브라우저에 두지 않는다. `supabase/functions/`에서 호출하도록 자리만 |
| 어른 트랙 (v1, D13) | 멘토 소규모 시험 시작(모인 사람 1,000명) | `profiles.track`, `adult_role`, `verified_at` 열, `/adults/` URL 예약 |
| 나의 기록 화면 (v1, D15) | 가입 뒤. H2 검증 지표 | 표와 Storage 정책, 삭제 흐름은 v0에 만든다 |
| 기록 공유(`link`/`public`), 이력서 PDF, 확인 표시 | 협력 기관 + 법률 확인 | `visibility`, `verification` 열. CHECK로 `private`/`self`만 허용 |
| 또래 댓글 (D12) | 사람이 모인 뒤, 안전장치 설계 문서가 먼저 | 없음. 신고·사전 확인 표는 그때 설계 |
| 지원 정보 크롤러 자동화 (D5) | 손으로 유지하는 항목이 팀 시간을 넘길 때, 또는 `checked_at` 경고가 계속 쌓일 때 | `helps/*.json` 스키마를 크롤러 출력 형식으로 그대로 쓴다 |
| 알림 (관심 분야 지원·대회) | 가입자가 생기고 채널(이메일/카카오)을 정한 뒤 | `profiles.notify`, `interests` |
| 기관 홍보 게재 (business-model 4번) | 구독자가 모인 뒤 | `helps.sponsored` 플래그. 추천 계산에서 제외 |
| 항목별 페이지(`/helps/<id>`), 사이트 내 검색 | 항목 100개 이상 | 없음 |
| 사이트 Q&A 게시판 | 인스타·카톡 반응을 본 뒤 (D12) | `/qna/<slug>` URL 예약 |
| 영어판·다국어 | 없음 | 없음 |

## 재검토 제안

- **D11 수집 항목에 로그인 식별자(이메일 또는 카카오 계정)가 빠져 있다.** 로그인이 있는 한 피할 수 없다. 결정을 바꾸자는 것이 아니라, D11을 보완하는 항목(예: D21 "로그인 식별자는 이메일 하나, 처리방침에 명시")을 추가하고 처리방침에 넣자는 제안이다.
- **시·도 단위 지역(D11)은 초기에는 식별 위험이 있다.** 사용자가 적을 때 지역 × 나이대 × 분야를 쪼개면 한 명이 보인다. 수집은 그대로 하되, 통계에서는 k 미만 칸을 숨기는 규칙(3절)을 D10의 실행 규칙으로 기록하기를 제안한다.

## 열린 질문

1. 로그인 방식: 이메일 매직 링크만? 카카오 로그인도? (학생에게는 카카오가 쉽지만 카카오 계정 정보를 받게 된다)
2. 통계 억제 기준 k (예: 5)와 `checked_at` 경고 기준(예: 90일)
3. 사진 한도: 2 MB × 기록당 3개로 시작해도 되는가. 무료 티어 용량을 확인한 뒤 확정
4. 도메인을 언제 사는가. 서비스 이름이 먼저다
5. 방문 통계 도구 확정 (Cloudflare Web Analytics vs 자체 호스팅 Umami)
6. 호스팅: Cloudflare Pages와 Vercel 중 하나. 리다이렉트 파일 형식만 다르다
7. Supabase 리전(서울)과 프로젝트 소유 계정(개인 계정이 아니라 팀 공용 계정으로)
8. 알림 채널: 이메일인가, 카카오 채널인가, 아니면 v0에서는 채널 친구 추가로 대신하는가
9. 25세 이상이 v0에 가입하려 할 때의 안내 문구와 어른 트랙 대기 명단을 받을지 여부
10. 위 기술 선택(0절)을 D20으로 기록할지

## 검토 메모: D16~D19 반영 (2026-09-25)

이 문서를 쓰는 동안 D16~D19가 정해졌다. 설계를 바꾸기 전에 팀이 확인할 차이:

1. **트랙 이름을 역할로 나눈다 (D19).** 지금 `track`은 `student`(14~24세) / `adult`(부모·선생님·멘토)다. D19는 20대 이상 **본인 진로를 찾는 성인**도 받는데, 이들은 `adult`(돕는 사람)와 다르다. 코드가 생기기 전에 `track`을 **`learner`(본인 진로 탐색) / `supporter`(부모·선생님·멘토)**로 바꾸고, 나이는 `age_band`로만 구분하기를 제안한다. v0에서는 `learner` + `14-16`·`17-19`·`20-24`만 허용하고, 25세 이상 `learner`는 D19 때 CHECK만 푼다. `adult_role`은 `supporter_role`로 바꾼다.
2. **탐색 기능의 자리 (D16).** 스와이프 결과와 주 1회 미션을 둘 곳이 없다. 제안: 미션은 `steps/*.json`의 `kind`에 **`mission`**을 추가해 같은 카탈로그로 두고, 해낸 미션은 `step_records`에 그대로 쌓는다. 스와이프는 가입하지 않으면 `localStorage`, 가입하면 `preferences` 표(`user_id`, `item_id`, `choice` = `like`/`skip`, `created_at`)에 둔다. 스와이프 카드 데이터는 `data/processed/cards/*.json`.
3. **반자동 기록 (D18).** "신청했어요?"를 며칠 뒤 물으려면, 가입한 학생이 누른 지원 링크를 기억해야 한다. 지금은 익명 통계 이벤트뿐이다. 제안: `help_clicks` 표(`user_id`, `help_id`, `clicked_at`, `followed_up_at`)를 두고, **기록을 켠 학생만** 쌓는다(기본 꺼짐). 탈퇴 시 CASCADE로 함께 지운다.
4. **지원 추천 자동 갱신 (D17).** `helps/*.json` 스키마를 크롤러 출력 형식으로 쓰는 7절의 방향은 맞다. 공모전 레이더(Searcher)의 수집기를 재사용할 때 그쪽 항목 형식과 이 스키마를 맞추는 변환 스크립트가 필요하다. 자동화 시점에 한다.
5. **취업 연계 (D18).** 법 확인 전까지는 스키마에 넣지 않는다. 협력 기관 훈련·인턴 프로그램은 지금 `helps.type`의 `course`·`experience`로 담을 수 있다. 필요하면 그때 `program`을 추가한다.
