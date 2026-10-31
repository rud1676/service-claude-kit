---
name: knowledgebase-raw-scraping
description: >-
  지식 베이스의 `raw/` 를 **등록된 원천 전부**에서 한 번에 채우는 상위 적재 스킬. 원천별 적재 스킬
  (`knowledgebase-raw-scraping-github` · `knowledgebase-raw-scraping-youtube`)을 `Skill` 도구로 차례로 부르고,
  각 결과를 **적재 요약 한 장 + 합친 페이지 후보 목록**으로 묶어 보고한 뒤 멈춘다(페이지는 만들지 않는다).
  원천을 콕 집지 않은 수집 요청 — "raw 데이터 수집해줘", "raw 수집해줘", "지식베이스 자료 수집", "원본 전부 긁어와" —
  에 쓰고 `/knowledgebase-raw-scraping` 으로도 호출한다. 원천을 지정한 요청("깃허브 이슈 긁어와", "유튜브 자막 적재")은
  해당 원천 스킬로 바로 간다. **지식 베이스(`schema/rules.md`)가 먼저 있어야 한다** — 없으면 `knowledgebase-setup` 을 부른다.
---

# knowledgebase-raw-scraping — 원천 전부 적재 (상위)

"raw 수집해줘" 한마디로 **등록된 원천을 전부** 돌리는 오케스트레이터. 스스로 긁지 않는다 — 원천 스킬을 부르고, 결과를 합치고, 멈춘다.

> 원천 스킬은 **옮기기만**, 이 스킬은 **묶기만**, 판단은 **사람이 후보를 고를 때**. 페이지는 `knowledgebase-compile` 이 만든다.

## 이 스킬의 자리

```
/knowledgebase-raw-scraping   ← 이 스킬 ("raw 데이터 수집해줘")
   ├─ Skill▶ knowledgebase-raw-scraping-github    이슈·PR·커밋·릴리스 → raw/github/
   ├─ Skill▶ knowledgebase-raw-scraping-youtube   자막·설명란        → raw/youtube/
   └─ Skill▶ (예정) slack · figma · db · paste
        ↓ 합친 후보 보고 → 사용자가 고름
/knowledgebase-compile        고른 후보만 wiki/{영역}/ 페이지로
```

`knowledgebase-compile` 도 **0단계(원본 최신화)에서 이 스킬을 부른다.** 새 원문이 있다고 판단했을 때만이며, 그때 args 는 `상위 호출(knowledgebase-compile) · KB_ROOT=… · 대상=<새 글이 있는 원천만> · 보고=후보 목록만` 이다.

## 원천 레지스트리 — 무엇을 돌리나

**"등록된 원천" = `state/` 에 워터마크가 있는 원천**이다. 별도 설정 파일을 두지 않는다 — 워터마크가 곧 "지난번에 이 대상을 수집하기로 합의했다"는 기록이다.

| 원천 | 스킬 | 워터마크 | 대상(키) |
|---|---|---|---|
| GitHub | `knowledgebase-raw-scraping-github` | `state/github-watermark.json` | `owner/repo` |
| YouTube | `knowledgebase-raw-scraping-youtube` | `state/youtube-watermark.json` | 채널 URL |

원천 스킬이 새로 생기면 이 표에 한 줄 추가하고, 그 스킬의 워터마크 형식을 위 둘과 맞춘다(키 = 대상, 값에 `last_run`).

## 단계

### 0. 선행 확인 — 묻기 전에 내가 본다

```bash
ls <KB_ROOT>/schema/rules.md            # 없으면 knowledgebase-setup 먼저
cat <KB_ROOT>/state/*-watermark.json    # 등록된 원천·대상·지난 수집일
```

- 워터마크가 있는 원천은 **대상 확인 없이** 그 대상 그대로 돌린다. 시작 전에 계획을 한 줄로만 보여 준다:
  `GitHub 3 repo (지난 2026-10-16) · YouTube 1 채널 (지난 2026-10-16) — 순서대로 돌립니다`
- 워터마크가 **하나도 없으면** 어느 원천·대상으로 시작할지 한 번만 묻는다(첫 수집은 대상 합의가 필요하다).
- 사용자가 "유튜브는 빼고", "이 repo도 추가" 처럼 말하면 그대로 따른다. 새 대상은 원천 스킬이 적재하면서 워터마크에 남긴다.
- **compile 이 불렀을 때**(args 가 `상위 호출(knowledgebase-compile)` 로 시작): 계획 보고와 질문을 건너뛰고 args 의 `대상` 만 돌린다. compile 이 이미 dry-run 으로 새 글을 확인하고 사용자에게 보고했다. 2단계 보고는 사용자 안내 없이 **합친 후보 목록만** compile 에 돌려준다.

### 1. 원천 스킬을 차례로 부른다

`Skill` 도구로 레지스트리 순서대로 **하나씩** 부른다. 각 원천은 쓰는 폴더(`raw/<원천>/`)와 워터마크가 달라 서로 간섭하지 않지만, 보고를 합치려면 하나가 끝난 뒤 다음으로 간다.

넘기는 인자(args)는 이 형식으로 고정한다 — 원천 스킬이 "상위 호출"로 알아보고 대상 확인을 건너뛴다:

```
상위 호출(knowledgebase-raw-scraping) · KB_ROOT=<경로> · 대상=<워터마크의 키 목록> · 보고=후보 목록만
```

- **한 원천이 실패해도 멈추지 않는다.** 실패 사유(인증 만료·rate limit·yt-dlp 깨짐 등)를 기록하고 다음 원천으로 간다. 실패한 원천의 워터마크는 원천 스킬 규칙대로 **적재 성공분까지만** 전진한다.
- 원천 스킬의 선행 조건(예: `gh auth`, `yt-dlp`)이 없으면 그 원천만 **건너뛰고 설치·인증 안내**를 보고에 남긴다. 대신 설치하지 않는다.

### 2. 합친 보고 — 한 장으로

```
raw 수집 (2026-10-23)
  GitHub   ✅ 이슈 4 · PR 6 · 커밋 2 · 릴리스 0   (중복 1 건너뜀)   3 repo
  YouTube  ✅ 영상 2 (자동 자막 2)                                 @spobite
  Slack    —  등록 안 됨

지식 베이스 후보 (합침)
  [갱신] spec     wiki/product/s-0002-랭킹기준  ← GitHub 이슈 #127 · YouTube 10-20 영상 03:12  (두 원천)
  [새로] concept  "달러게임 점수 배분"           ← GitHub PR #214
  [새로] question "정산 단가 두 값 불일치"        ← PR #198 리뷰 vs 영상 10-18 설명란  (원천 간 충돌)
  [새로] event    "포스트시즌 특집"              ← YouTube 10-20 영상 · ASR — 숫자 확인 필요
```

합치는 규칙:

- **같은 페이지를 건드리는 후보는 한 줄로** 묶고 근거를 원천별로 나열한다. 두 원천이 같은 사실을 말하면 근거가 늘 뿐, 등급이 저절로 오르지 않는다.
- **원천끼리 다르게 말하면 고르지 않는다** — `question` 후보로 올린다(원천 스킬과 같은 규칙).
- 원천 스킬이 붙인 꼬리표(`confirm_pending`, `ASR — 숫자 확인 필요`)는 **지우지 않고 그대로 옮긴다.**
- 합친 후보가 20건을 넘으면 영역별로 묶고 상위 10건만 본문에, 전체는 `state/candidates-<YYYY-MM-DD>.md` 에 남긴다. 원천별 후보 파일(예: `state/github-candidates-*.md`)은 원천 스킬이 쓰던 대로 둔다.

### 3. 멈춘다

후보 중 사용자가 고른 것만 `knowledgebase-compile` 로 넘긴다. 이 스킬은 페이지를 만들지 않고, 커밋도 하지 않는다(사용자가 요청할 때만).

## 주의점

- **상위 스킬이 원천 스킬의 판정을 다시 하지 않는다.** 무엇을 긁고 뺄지(코드·조회수 제외 등), ASR 등급 상한은 원천 스킬이 정본이다. 여기서 바꾸고 싶으면 원천 스킬을 고친다.
- **원천을 지정한 요청은 이 스킬로 오지 않는다.** "깃허브만", "유튜브 자막만"은 원천 스킬로 바로 가는 게 맞다 — 상위를 거치면 묻지 않아도 될 계획 보고가 한 번 더 생긴다.
- 수집 주기를 자동으로 돌리지 않는다. 사람이 부를 때만 돈다(지식 베이스 운전 규칙 — 자동은 린트만).
