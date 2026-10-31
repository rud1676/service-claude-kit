---
name: knowledgebase-raw-scraping-github
description: >-
  GitHub에서 **사람이 쓴 글**(이슈 본문·코멘트, PR 설명·리뷰, 본문 있는 커밋 메시지, 릴리스 노트)을 긁어
  지식 베이스의 `raw/github/` 에 **추가만** 하는 적재 스킬. 원천 id·URL·수집일·본문 해시를 `.meta.json` 에 남기고,
  워터마크로 증분 수집해 두 번 돌려도 같은 결과를 만든다. 적재 후 **어느 페이지를 새로 만들/갱신해야 하는지 후보만 보고**하며
  페이지를 자동 생성하지 않는다. "깃허브에서 raw 긁어와", "이슈·PR 지식베이스에 적재해줘", "github 원본 수집" 같은 요청에 쓰고
  `/knowledgebase-raw-scraping-github` 으로도 호출한다. **지식 베이스(`schema/rules.md`)가 이미 있어야 동작한다** —
  없으면 `knowledgebase-setup` 을 먼저 부른다. 원천을 집지 않은 "raw 데이터 수집해줘"는 상위 `knowledgebase-raw-scraping` 이 이 스킬을 부른다.
---

# knowledgebase-raw-scraping-github — GitHub 원본 적재

지식 베이스의 **바닥(`raw/`)을 채우는 원자 스킬**. 판단하지 않고 **옮기기만** 한다.

> 페이지의 모든 문장이 `raw/`를 가리킨다. 그래서 이 스킬의 유일한 책임은 **"원문을 그대로, 추가만, 재현 가능하게"** 다.

## 이 스킬의 자리

```
/knowledgebase-raw-scraping  (상위 — "raw 데이터 수집해줘")
   ├─ Skill▶ knowledgebase-raw-scraping-github   ← 이 스킬 (GitHub)
   ├─ Skill▶ knowledgebase-raw-scraping-youtube  자막·설명란
   └─ Skill▶ (예정) slack · figma · db · paste
```

**혼자도, 상위 아래서도 쓴다.** "깃허브만" 같은 원천 지정 요청은 이 스킬로 바로 오고, 원천을 안 집은 "raw 수집"은 상위 `knowledgebase-raw-scraping` 이 이 스킬을 부른다. 상태 파일·메타 형식·보고 형식은 원천 이름만 바뀌면 그대로 재사용되도록 맞춰 둔다(§상태와 메타).

## 긁는 것 / 안 긁는 것

**판정 기준은 하나다**: 코드를 다시 읽으면 확인되는 것인가?

| | 긁나 | 왜 |
|---|---|---|
| 이슈 본문·코멘트 | ✅ | 사람이 쓴 글. 코드엔 없다 |
| PR 설명·리뷰 코멘트 | ✅ | "왜 이렇게 했나"가 여기 산다 |
| **본문 있는** 커밋 메시지 | ✅ (기본) | 본문을 쓴 커밋은 누군가 *왜*를 설명한 것 |
| 릴리스 노트 | ✅ | 변경의 의미를 사람이 정리한 글 |
| 한 줄 커밋 (`fix: typo`) | ❌ | 지식이 없다. 노이즈만 늘린다 |
| 머지 커밋 · 봇 커밋 | ❌ | 기계가 만든 글 |
| **소스 코드** | ❌ | 언제든 다시 읽으면 확인된다 → 워크스페이스 `context/`·코드위키의 일 |
| repo의 `*.md` 문서 | ❌ (기본), opt-in | 코드와 함께 버전 관리되니 다시 읽으면 된다. **삭제·대체될 예정인 기획 md만** 사람이 지정해 긁는다 |

> **코드를 긁지 않는 이유**를 꼭 이해할 것: `raw/`는 "그 시점의 사진"이고 페이지는 거기에 출처를 건다. 코드는 매주 바뀌므로, 코드를 `raw/`에 넣으면 **출처 표기가 다음 주에 전부 거짓**이 된다. 코드에 박힌 정책값(계산식·상수·임계값)이 필요하면 `raw/`에 복사하는 대신 `concept`/`spec` 페이지에서 **파일:줄로 인용**하고, 그 값이 *왜 그 값인지*의 근거만 `raw/`(사람이 쓴 글)에서 찾는다.

## 단계

### 0. 선행 확인

```bash
gh auth status                      # 인증
ls <KB_ROOT>/schema/rules.md        # 지식 베이스가 있나 (없으면 knowledgebase-setup 먼저)
cat <KB_ROOT>/state/github-watermark.json 2>/dev/null   # 지난 수집 지점
```

대상 repo 목록을 사용자에게 확인한다. 워크스페이스라면 `repository/*` 의 각 repo `origin` 에서 뽑아 제안한다.

**상위 호출일 때**(args 가 `상위 호출(knowledgebase-raw-scraping)` 로 시작): 대상 확인과 dry-run 승인을 건너뛰고(상위가 계획을 이미 보여 줬다) args 의 `대상` 을 그대로 쓴다. 보고는 §2 형식의 **적재 요약 + 후보 목록만** 돌려준다 — 합치기와 사용자 안내는 상위가 한다.

### 1. 적재 — 스크립트가 한다

스킬 경로를 `$SKILL`(= 이 파일이 있는 디렉토리. 프로젝트 설치 시 `<워크스페이스>/.claude/skills/knowledgebase-raw-scraping-github`, 전역 설치 시 `~/.claude/skills/knowledgebase-raw-scraping-github`)이라 부른다.

```bash
python3 $SKILL/scripts/scrape_github.py \
  --kb <KB_ROOT> \
  --repo owner/name [--repo owner/other] \
  [--kinds issues,pulls,commits,releases] \
  [--since 2026-01-01] [--limit 200] [--dry-run]
```

- **추가만**: 이미 있는 파일을 덮지 않는다. 이슈·PR에 새 코멘트가 붙으면 그 파일 **끝에 `## 수집 YYYY-MM-DD` 절로 새 것만 덧붙인다.** 기존 본문은 한 글자도 바뀌지 않으므로 `[src:n]` 인용이 계속 참이다.
- **증분**: `state/github-watermark.json` 의 repo별 `updated_at` 이후만 가져온다. 두 번 돌려도 결과가 같다.
- **중복 차단**: 본문 sha256 을 `.meta.json` 에 남기고, 같은 해시는 적재하지 않고 **건너뛴 사실을 보고한다**(조용한 성공 금지).
- **개인정보**: 이메일은 적재 단계에서 마스킹한다(`--no-mask` 로 끔). 페이지 단계에서 지우면 이미 늦다.
- `--dry-run` 으로 **무엇이 들어올지 먼저 보여주고** 사용자 승인 후 실제 적재한다.

### 2. 보고 — 판단은 여기서, 자동 생성은 안 한다

적재된 글을 읽고 **후보만** 보고한다. 페이지를 만들지 않는다.

```
적재: 이슈 12 · PR 8 · 커밋 5 · 릴리스 2   (중복 3건 건너뜀)

지식 베이스 후보
  [새로] concept  "달러게임 점수 배분"      ← PR #214 설명에 계산 근거
  [갱신] spec     product/s-0002-랭킹기준   ← 이슈 #127 에서 기준이 바뀜 (현재 내용과 충돌)
  [새로] decision "포스트시즌 제외"          ← 이슈 #131 코멘트. 확정 근거는 없음 → confirm_pending
  [새로] question "정산 단가 두 값 불일치"    ← PR #198 리뷰 vs 이슈 #150 가 다름
```

- **충돌을 발견하면 고르지 않는다.** 둘 다 적고 등급을 낮춘 `question` 후보로 올린다.
- 확정 근거(결정권자 확인 원문·승인)가 없으면 **확정 상태로 올리지 않는다**. `confirm_pending: true` 후보로 보고한다.
- 후보가 20건을 넘으면 영역별로 묶고 **상위 10건만** 본문에 적는다. 나머지는 목록 파일로 남긴다.

### 3. 컴파일은 별도

후보 중 사용자가 고른 것만 페이지로 만든다. 이 스킬은 거기까지 가지 않는다 — **적재와 컴파일을 섞으면, 잘못 읽은 원문이 그대로 페이지가 된다.**

## 상태와 메타 (다른 원천 스킬과 공유할 형식)

```
<KB_ROOT>/
├── raw/github/
│   ├── issues/<repo>-<번호>.md        + .meta.json
│   ├── pulls/<repo>-<번호>.md         + .meta.json
│   ├── commits/<repo>-<YYYY-MM>.md    + .meta.json   (월 단위로 덧붙임)
│   └── releases/<repo>-<태그>.md      + .meta.json
└── state/github-watermark.json
```

`.meta.json` 공통 칸 — **원천이 바뀌어도 이 칸은 같다**:

```json
{
  "source": "github",
  "source_id": "owner/name#127",
  "url": "https://github.com/owner/name/issues/127",
  "retrieved": "2026-10-16T14:30:00+09:00",
  "body_sha256": "…",
  "masked": ["email"],
  "appended": ["2026-10-16", "2026-10-20"]
}
```

`state/` 는 기계가 쓰는 칸이다. 린트는 `wiki/` 아래만 읽으므로 따로 제외할 필요가 없다.

## 주의점

- **`raw/`를 고치거나 지우지 않는다.** 잘못 적재했으면 지우는 대신 파일 안에 `> [적재 오류] …` 주석을 달고, 그 파일을 가리키는 페이지의 등급을 낮춘다.
- **GitHub 날짜는 UTC다.** 파일명·`retrieved` 는 현지 시각으로 변환해 적는다. 안 하면 새벽 수집이 전날로 찍힌다.
- **비공개 repo·조직 권한**: `gh` 토큰 범위를 먼저 확인한다. 못 읽은 repo를 조용히 건너뛰지 말고 **보고**한다.
- **rate limit**: `--limit` 기본 200. 초과하면 워터마크를 **적재 성공분까지만** 전진시켜, 다음 실행이 이어 받게 한다.
- 이 스킬은 **PR·이슈를 만들거나 코멘트를 달지 않는다.** 읽기 전용이다(쓰기 권한이 섞인 토큰이면 경고한다).
