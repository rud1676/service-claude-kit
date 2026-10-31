# service-claude-kit

[![GitHub](https://img.shields.io/badge/GitHub-rud1676%2Fservice--claude--kit-black?logo=github)](https://github.com/rud1676/service-claude-kit)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-workspace-D97757)](https://claude.com/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

**풀스택·인프라 등 서비스 개발을 위한 Claude Code 스킬 셋팅.**
목표: 운영 중인(또는 곧 운영할) 코드에 AI를 들이되, 개발자가 **통제권과 이해**를 놓지 않게 한다 — 변경은 격리해 검증하고, 결정은 기록하고, 요구사항은 코드 근거로 판별한다.

> 그린필드 MVP 스타터팩이 아니다([not-agent/starter-skills](https://skills.sh/not-agent/starter-skills) 참고). **살아있는 서비스 코드에 AI를 안전하게 들이는 쪽**에 집중한다.

## 기본 전제 (Defaults)

- **개발자를 루프에.** 자동화의 목적은 "AI가 알아서 다 하기"가 아니라 "개발자가 촘촘히 인지한 상태를 유지하기"다. 사람이 게이트에서 고를 것을 고르고, 코드 검토는 PR에서 사람이 한다.
- **멀티레포 워크스페이스.** 실제 코드는 `repository/` 아래 각 독립 git repo에 두고, 워크스페이스 자체는 git이 아니다. (front·server·admin 등이 한 워크스페이스에 모이는 실무 구조를 가정)
- **실행축 스킬은 "고쳐 쓰는 참고 구현".** 아래 worktree·jiraticket·figma-depth-find는 실무에서 검증된 절차지만, DDNS·포트·Jira cloudId 같은 구체값은 환경마다 다르다. 정신(격리→검증→게이트→PR 등)은 보편이고, 구체값은 각 파일의 `프로젝트 커스터마이징` 주석대로 자기 환경에 맞게 채운다.

## 빠른 시작 (Quickstart)

```bash
./scripts/install.sh myproject
```

설치 중 두 가지를 묻는다:

1. **프로젝트 관리 툴** — `Jira`(jiraticket 스킬 포함) / `GitHub Projects`(gh-project 스킬 포함, 무료·gh CLI) / `없음`
2. **작업 환경** — `원격 서버`(접속 링크를 내부/외부 2가지로 안내) / `로컬`(localhost만)
   - 외부 링크를 쓰려면 공유기 설정 페이지 등에서 **NAT(포트포워딩)로 해당 포트를 서버에 연결**해 둬야 한다.

답에 따라:
- Jira를 고르면 `jiraticket`만, GitHub Projects를 고르면 `gh-project`만 남긴다(둘 중 하나). `없음`이면 둘 다 설치하지 않는다.
- 로컬을 고르면 `worktree` 스킬에서 원격 접속(내부/외부 DDNS) 안내를 제거한다.
- 고른 값은 `CLAUDE.md`의 `service-kit:config` 블록에 기록돼, 다음 세션의 에이전트가 읽는다.

비대화(CI/스크립트) 환경에서는 질문을 건너뛰고 기본값(`jira` + `remote`)으로 설치한다. 환경변수로 지정할 수도 있다:

```bash
SCK_PMTOOL=jira|ghproject|none  SCK_ENV=remote|local  ./scripts/install.sh myproject
./scripts/install.sh myproject --force   # 이미 있는 .claude/ 파일까지 덮어씀
```

설치 후, 각 스킬 파일의 `프로젝트 커스터마이징` 주석(cloudId·프로젝트키·DDNS·포트 등 **인스턴스 비밀값**)을 채운다. 이 값들은 설치가 대신 주입하지 않는다 — 한 번 직접 채우는 편이 안전하다. 훅은 `python3`가 있어야 동작한다.

### 다른 채널 — skills.sh (개별 스킬만)

스킬 정본이 최상위 `skills/`에 있어, [skills.sh](https://skills.sh)/[`vercel-labs/skills`](https://github.com/vercel-labs/skills) CLI로 **개별 스킬만** 가져갈 수도 있다:

```bash
npx skills add rud1676/service-claude-kit
```

단, 이 채널은 **`SKILL.md`만** 설치한다 — `install.sh`가 하는 **훅 배선·`CLAUDE.md` 규칙 주입·워크스페이스 폴더(context/decision-log/repository) 스캐폴딩은 하지 않는다.** 그리고 `worktree`·`jiraticket`·`figma-depth-find`는 이 워크스페이스 구조와 `CLAUDE.md` 규칙에 엮여 있어, 낱개로 설치하면 반쪽만 동작한다. **풀 킷 경험은 `install.sh`가 정본**이고, skills.sh는 "스킬만 떼어 보고 싶을 때"의 보조 채널로 둔다.

## 왜 이 스킬들이 필요한가 (Why These Skills Exist)

운영 코드에 AI를 들일 때 반복해서 겪는 실패 모드를, 각각 작게 막는다.

### #1: AI가 운영 코드(main)에 직접 쏟아내 부작용·회귀가 난다

**문제**: 에이전트가 메인 체크아웃에 바로 손대면, 검증 전 변경이 다른 작업과 섞이고 회귀가 조용히 들어온다. 운영 코드에서는 이 비용이 크다.

**해결**: [`worktree`](./skills/worktree/SKILL.md). 격리된 git 워크트리 안에서만 수정하고 → `lint`/`build`로 검증하고 → **`reviewer` 자가검토 게이트에서 사람이 고칠 것을 고르고** → PR로만 반영한다. AI가 main을 직접 건드리지 않는다. (환경 맞게 고쳐 쓰는 참고 구현)

### #2: AI가 쏟아내니 "왜 이렇게 됐는지"를 못 따라간다 (인지 부채)

**문제**: diff를 쓱 훑고 "이해했다"고 넘어가지만, 그건 대개 *낯익음*을 *이해*로 착각한 것이다. 이해 없이 위임만 쌓이면 자기 코드의 흐름에 낄 수 없게 된다.

**해결**: [`explain`](./skills/explain/SKILL.md). 코드만 봐선 안 보이는 것 — 왜 이 결정인가 / 무엇을 버렸나 / 무슨 가정인가 / 어디까지 영향인가 — 을 복원해 `context/`에 남긴다. AI의 생산 속도에 인간의 이해 속도를 맞추는 브레이크.

### #3: 요구사항이 바뀔 때 낡은 전제로 추측한다

**문제**: 운영 앱에 요구사항이 바뀌어 들어오면, "지금 코드로 가능한가 / 정확히 뭘 바꿔야 하나"를 **현재 실제 버전** 기준으로 판별해야 한다. 그 현재-상태 지식이 없으면 AI도 사람도 추측하게 된다.

**해결**: `CLAUDE.md`의 **항상-온 규칙**(설치 시 주입되는 `context-mgmt` 블록)이 `context/`·`decision-log/`를 append-only로 갱신하게 강제해, **현재 상태의 진실**을 유지한다. 그래서 변경을 현실에 맵핑할 수 있다. jiraticket·worktree의 분석 단계가 실제 코드를 읽어 변경안을 `파일:줄`로 근거화하고, **가능성 판단·소통은 개발자가** 한다(= 루프 유지).

### #4: 새 요구사항이 티켓·코드와 따로 논다

**문제**: 들어온 요구사항을 머리로만 관리하면, 실제 브랜치·커밋·PR과 티켓이 어긋나고 무엇을 왜 바꿨는지 추적이 끊긴다.

**해결**: [`jiraticket`](./skills/jiraticket/SKILL.md)(Jira) / [`gh-project`](./skills/gh-project/SKILL.md)(GitHub Projects) / [`issue-mgmt`](./skills/issue-mgmt/SKILL.md). 티켓·아이템 조회 → 선택 → (코드 근거로) 분석 → `worktree`로 구현까지 한 흐름으로 잇고, 브랜치·커밋·PR을 티켓 키(또는 이슈 번호)로 연결한다.

### #5: 시안이 우리 기존 컴포넌트와 무관하게 구현돼 중복·불일치가 쌓인다

**문제**: 디자인 시안을 그대로 새로 구현하면, 이미 있는 컴포넌트와 중복되거나 스타일이 어긋난다. 운영 UI에서는 이 불일치가 곧 부채다.

**해결**: [`figma-depth-find`](./skills/figma-depth-find/SKILL.md). 여러 sub-agent가 큰 Figma 프레임을 깊게 탐색하고(truncate되면 자식으로 재귀), 그 화면을 **우리 코드베이스의 실제 컴포넌트로 매핑**한다. 재사용/부분매칭/신규(갭)로 분류해, 정말 없는 것만 새로 만든다.

### #6: 프로젝트마다 비슷한 스킬 베이스를 매번 새로 만들게 된다

**문제**: 새 프로젝트를 시작할 때마다 엇비슷한 규칙·스킬·폴더 구조를 처음부터 다시 세팅한다. 그러면서 미묘하게 달라져 일관성도 잃는다.

**해결**: **인터랙티브 [`install.sh`](./scripts/install.sh)**. 환경(PM 툴·로컬/원격)을 물어보고 맞는 스킬만·맞는 모양으로 깔고, `CLAUDE.md` 작업 규칙·훅 배선·워크스페이스 폴더를 일관되게 세팅한다. 베이스를 개선하면 다음 프로젝트부터 반영된다.

### #7: 요구사항은 추상적으로 들어오고, 위임은 게이트마다 끊긴다

**문제**: "이거 리팩토링 좀 해줘" 같은 추상 요구는 그대로 AI에 넘기면 매 판단마다 멈춰 물어보게 된다. 반대로 다 맡기면 낡은 전제로 추측해 옆길로 샌다. 개발자는 "촘촘히 정의"와 "루프에서 빠지기" 사이에서 진다.

**해결**: 한 쌍의 오케스트레이터 스킬. [`acceptance-criteria`](./skills/acceptance-criteria/SKILL.md)(앞단)가 [`grill-me`](./skills/grill-me/SKILL.md) 인터뷰로 추상 요구를 **작은 티켓 + AC**로 분해해 트래커에 올리고, [`orchestrate`](./skills/orchestrate/SKILL.md)(뒷단)가 승인된(Ready) 티켓을 **순차 자율로 드레인**한다 — 구현은 `worktree`, 검증은 테스트/스모크, 서술은 `explain`에 위임하고, 판단이 필요한 3지점(권한·데이터·의미갈림)만 큐에 쌓아 멈추지 않는다. 보드가 **관제탑**이라 상태는 스킬 밖(트래커)에 산다. (OpenAI Symphony와 같은 "이슈트래커=control plane" 계열이되, 1인/소규모용으로 사람을 루프에 남긴 게이트형.)

### #8: AI가 테스트를 "양산"하고, 개발자는 그 테스트가 뭘 지키는지 모른다

**문제**: "테스트 좀 짜줘"라고 하면 AI는 커버리지 숫자를 채우는 테스트를 쏟아낸다. 프레임워크 동작을 검증하거나 필드마다 반복하는 무의미한 테스트가 쌓이고, 정작 개발자는 그 테스트가 **어떤 회귀를 막는지** 설명하지 못한다 — 테스트마저 인지 부채가 된다.

**해결**: [`unit-test`](./skills/unit-test/SKILL.md)(API 1개) / [`scenario-test`](./skills/scenario-test/SKILL.md)(여러 API를 순서대로 호출하는 유저 플로우). 실제 앱 진입점 + 실제 테스트 DB로 검증하되, **"이 테스트가 없으면 어떤 버그를 놓치는가"에 답할 수 없는 테스트는 짜지 않는다**(정당화 규율). 작성 후 **브리핑 → 문답**으로 개발자가 사전 데이터·분기 커버리지·놓친 케이스를 직접 설명하게 해 루프에 남긴다. 테스트 러너·앱 진입점·DB/ORM 같은 스택 구체값은 각 파일의 `프로젝트 커스터마이징` 주석대로 채우는 **"고쳐 쓰는 참고 구현"**이다.

### #9: 사람이 정한 것(결정·정의·수치)이 대화에 흘러 사라진다

**문제**: 코드와 `context/`로 복원되는 건 **코드를 읽으면 확인되는 것**뿐이다. 대표가 카톡으로 정한 정책, 도메인 용어의 계산 기준, 광고 단가, "그때 왜 그 숫자로 했는지" — 이것들은 원본이 사라지면 **확인할 길이 자체가 없다.** 그래서 에이전트마다 다르게 추측하고, 반년 뒤엔 사람도 못 되돌린다. 더 나쁜 건 같은 정책이 두 곳에 각각 수정돼 **어느 쪽이 기준인지 사라지는** 것이다.

**해결**: [`knowledgebase-setup`](./skills/knowledgebase-setup/SKILL.md) — 코드로 확인 안 되는 사실만 담는 **별도 git repo**를 세운다. `raw/`는 추가만(원본이 바뀌면 출처 표기가 거짓이 된다), 모든 문장에 **사실 등급**(`[확인:…]`/`[src:n]`/`[추론]`)과 출처 번호를 달고, **확정은 결정권자만**(에이전트는 못 올린다), 검사는 린트가 한다. 규칙은 산문으로 두지 않고 `types.json` 한 벌을 더 둬서 **상태값이 갈라지면 린트가 실패**하게 만든다. 회사 상황(영역·확정 입구·운전 방식)은 `grill-me` 인터뷰로 8갈림을 확정해 `schema/`에 박는다. 원본 적재는 원천별 스킬이 맡는다 — [`…-github`](./skills/knowledgebase-raw-scraping-github/SKILL.md)(사람이 쓴 글만. 코드는 다시 읽으면 확인되므로 안 긁는다) · [`…-youtube`](./skills/knowledgebase-raw-scraping-youtube/SKILL.md)(채널 스크립트. 자동 자막은 기계가 들은 것이라 숫자·고유명사를 `[추론]`으로 묶는다).

### #10: "화면 확인했어요"를 말로만 남겨, 리뷰어가 PR·배포를 판단할 근거가 없다

**문제**: 로딩 순서·단계별 표시처럼 **눈으로 봐야 하는 변경**은 diff 만으로 맞는지 알 수 없다. AI 가 "브라우저로 확인했다"고 말해도 무엇을 어떤 조건에서 봤는지, 캡처는 실제로 그 상태였는지 남지 않는다. 게다가 캡처를 위해 응답을 늦추면 그 숫자가 "속도"로 오인되고, 빠른 서버에선 캡처가 상태 전환을 못 따라간다.

**해결**: [`browser-e2e`](./skills/browser-e2e/SKILL.md). Playwright 로 실제 화면을 띄워 **측정 실행(개입 없음)과 캡처 실행(필요 시 응답 붙잡기·지연)을 분리**하고, 캡처는 직접 열어 확인한 뒤 **단계별 캡처 + 요청 시간표 + 기대/결과 표 + "이 테스트로 알 수 없는 것"** 을 결과 문서로 남긴다. 머지 전엔 로컬(목업 로그인), 머지 후엔 개발서버(배포 완료 확인 후 실제 로그인). 로그인 리다이렉트 경합 같은 함정은 헬퍼(`scripts/e2e-kit.cjs`)가 막는다.

## 개념 정리

### 항상-온 규칙(CLAUDE.md) vs 필요할 때 스킬

이 킷은 "에이전트가 알아야 할 것"을 두 층으로 나눈다. 무엇을 어디에 둘지의 기준은 **"항상 켜져 있어야 하나, 특정 작업일 때만 필요하나"**다.

- **항상-온 규칙 — `CLAUDE.md`** (`base/CLAUDE.block.md`가 설치 시 주입): 작업 종류와 무관하게 **늘 지켜야 하는 계약**. 폴더 구조, context/decision-log 갱신 규칙, "추적 메타는 답변 본문에 출력 금지", "커밋·PR은 사용자 요청 시만". 이건 매 컨텍스트에 항상 있어야 의미가 있어서, 스킬로 빼면 오히려 깨진다.
- **필요할 때 스킬 — `skills/*/SKILL.md`**: "이 작업을 하면 이 절차를 따르라"는 **절차**. 관련 작업이 올 때만 로드돼 컨텍스트를 가볍게 유지한다. (explain·worktree·jiraticket·gh-project·figma-depth-find·issue-mgmt·acceptance-criteria·orchestrate·grill-me·unit-test·scenario-test·browser-e2e·make-plan)

즉 CLAUDE.md의 규칙은 수동적 설정이 아니라 그 자체로 **#3을 막는 Fix 장치**다.

### 구성 요소

- **서브에이전트 (`base/agents/*.md`)** — 격리된 컨텍스트에서 일을 대신 수행하고 결과만 반환하는 대리인(reviewer·frontend·explainer). frontmatter의 `model`로 도는 모델을 바꾼다.
- **스킬 (`skills/*/SKILL.md`)** — 메인 에이전트가 필요할 때 읽어 따르는 절차/노하우. 메인 모델로 실행되므로 `model` 지정은 무의미.
- **훅 (`scripts/hooks/*.py`)** — 특정 이벤트(프롬프트 제출·도구 사용·응답 종료)마다 자동 실행되는 스크립트. 사람·에이전트 개입 없이 배경에서 돈다.

## 구조 (이 repo)

```
.
├── skills/                 # 스킬(절차/노하우) → .claude/skills/  (최상위 = skills.sh 발견 위치)
│   ├── issue-mgmt/         # 이슈/티켓 관리 절차
│   ├── explain/            # 변경/신규 코드를 '참여'용으로 이해·기록
│   ├── jiraticket/         # Jira 티켓 조회·선택 → 분석 → worktree로 구현 위임
│   ├── gh-project/         # GitHub Projects 아이템 조회·선택 → 분석 → worktree로 구현 위임 (gh CLI, 무료)
│   ├── worktree/           # git 워크트리 기반 수정→검증→커밋→PR (공용 구현 절차)
│   ├── figma-depth-find/   # 큰 Figma 프레임을 멀티에이전트로 탐색·우리 컴포넌트 매핑
│   ├── acceptance-criteria/# 큰 작업을 grill-me로 인터뷰 → 티켓+AC로 분해 → 트래커에 생성 (루프 앞단)
│   ├── orchestrate/        # Ready 티켓을 순차 자율로 드레인(구현→검증→PR→explain) (루프 뒷단)
│   ├── grill-me/           # 계획/설계를 한 번에 한 질문씩 파고드는 소크라테스 인터뷰 (Matt Pocock, MIT)
│   ├── unit-test/          # API 1개의 단위 테스트를 정당화 규율로 작성 → 브리핑·문답 (고쳐 쓰는 참고 구현)
│   ├── scenario-test/      # 여러 API를 순서대로 호출하는 유저 플로우(시나리오) 테스트 → 브리핑·문답
│   ├── browser-e2e/        # 브라우저로 실제 화면 E2E 확인 → 단계별 캡처·요청 시간표·기대/결과 문서 (scripts/e2e-kit.cjs 헬퍼)
│   └── make-plan/          # plan·설계 문서를 "화면 → 설계" 순서의 시각적 형식으로 작성 (상위 스킬 plan 단계 공용)
├── scripts/                # 이 repo의 스크립트 모음
│   ├── install.sh          # 대상 프로젝트에 워크스페이스를 설치(환경 질문 포함)
│   └── hooks/              # 세션 추적 훅(python) → 설치 시 .claude/hooks/로 복사
│       ├── context-checkpoint.py  # N프롬프트마다 context 갱신 리마인더
│       ├── log-read.py            # Read/Grep/Glob + Bash 실행 기록 → claude-log/
│       └── summarize-session.py   # 세션 요약·토큰·참고문서·탐색집계 → claude-log/
├── base/                   # install.sh가 target .claude/에 넣는 나머지(비-스크립트)
│   ├── agents/             # 서브에이전트(역할 페르소나) → .claude/agents/
│   │   ├── reviewer.md     # 코드 리뷰어 (읽기 전용)
│   │   ├── frontend.md     # 프론트엔드 작업자
│   │   └── explainer.md    # 코드 설명자 (읽기 전용)
│   ├── settings.hooks.json # 훅 배선(설치 시 .claude/settings.json에 안전 병합)
│   └── CLAUDE.block.md     # 프로젝트 CLAUDE.md에 주입할 관리 규칙(마커 블록)
├── _templates/             # 새 역할 만들 때 복사용 뼈대 (agent.md · SKILL.md)
└── workspaces/             # install.sh 산출물(설치된 작업 워크스페이스) — .gitignore, 추적 안 함
```

## 설치 후 워크스페이스 모습

```
{프로젝트}/                 # 워크스페이스 — 그 자체는 git 저장소가 아니다
├── .claude/               # agents · skills · hooks · settings.json
├── CLAUDE.md              # context-mgmt + config(설치 시 선택값) 블록 주입됨
├── context/               # 프로젝트 맥락        (오래 남는 팀 지식)
├── study/                 # 내 학습 기록          (개인 이해용)
├── decision-log/          # 결정 아카이브         (왜 이걸 택했나 / 무엇을 버렸나)
├── plan/                  # 임시 작업 맥락        (완료 시 삭제)
├── claude-log/            # 세션 추적 로그        (훅이 자동 생성)
└── repository/            # 실제 코드 repo들      (각각 독립 git)
```

## 폴더별 맥락 — 무엇을 어디에 남기나

기준은 **누구를 위한 것이고, 얼마나 오래 남을 것인가**다.

- **`context/`** — 코드만 봐선 알 수 없는 프로젝트의 진실(도메인 동작·확정된 결정·기획 변경). `context/{도메인}/*.md` + `context/README.md` 인덱스. `explain` 스킬이 관리하고, 갱신은 덮어쓰기가 아니라 `## 후속 (날짜)`로 이어 붙인다. 모든 주장에 `파일:줄` 근거와 작성 날짜·대상 커밋을 단다.
- **`study/`** — "이거 어떻게 동작해?"처럼 내가 배우려고 물어본 것. `context/`(프로젝트 진실)와 목적이 달라 섞지 않는다.
- **`decision-log/`** — 판단이 갈렸거나 대안을 버린 결정을 `<YYYY-MM-DD>-<주제>.md`로 append-only 기록. "무엇을 택했고 어떤 대안을 왜 버렸나 / 아직 미결이면 왜 미결인가"가 핵심. 매번이 아니라 **판단이 갈렸을 때만**.
- **`plan/`** — 큰 작업의 임시 계획·메모. 작업이 끝나면 삭제한다.
- **`claude-log/`** — 훅이 세션마다 `<session_id>.md`를 자동 생성·갱신(읽기 기록·요약·토큰·탐색 집계). 사람이 직접 쓰지 않는다.
- **`repository/`** — front·server 등 실제 git repo. **각각 독립 git**이라 워크스페이스가 git이 아니어도 중첩이 꼬이지 않는다. 브랜치·커밋은 해당 repo 안에서, 병렬 작업 워크트리는 `repository/{repo}-worktrees/{작업번호}/`.

## 안전 설치 (기존 프로젝트에 깔아도 안 깨진다)

이미 쓰던 프로젝트에 설치해도 기존 설정을 보존하도록, 두 파일은 **병합**으로 처리한다:

- **CLAUDE.md** — `<!-- BEGIN/END service-kit:context-mgmt -->` 와 `service-kit:config` 마커로 감싼 블록만 삽입/갱신한다. 파일이 없으면 생성, 마커가 있으면 그 블록만 교체, 마커 없는 기존 파일이면 기존 내용을 그대로 둔 채 덧붙인다. 재실행해도 블록은 하나만 유지된다(멱등).
- **settings.json** — 기존 `permissions`·`env`·다른 훅을 보존하고 `hooks`만 union 병합한다. `command` 문자열로 중복을 판단하므로 재실행해도 훅이 중복 배선되지 않는다.
- **워크스페이스 폴더**(`context/ study/ decision-log/ repository/ plan/ claude-log/`)는 각 README 시드와 함께 **없을 때만** 생성한다.
- **git은 건드리지 않는다** — 워크스페이스에 `git init`도, 루트 `.gitignore`도 만들지 않는다.

`--force`는 `.claude/` 안 파일 복사에만 영향을 준다. **CLAUDE.md와 settings.json은 `--force`와 무관하게 절대 통째로 덮지 않는다.**

## Roadmap

- **Linear 티켓 스킬** — Linear가 유료라 우선순위를 낮추고, 무료로 쓸 수 있는 GitHub Projects 연동([`gh-project`](./skills/gh-project/SKILL.md))을 먼저 넣었다. 필요가 생기면 Linear MCP 기반 스킬을 추가한다.
- 그 외 이슈 트래커·CI 연동 스킬은 필요에 따라 추가.

## 새 역할 추가하기

- 서브에이전트: `_templates/agent.md` → `base/agents/<이름>.md` 로 복사해 채운다.
- 스킬: `_templates/SKILL.md` → `skills/<이름>/SKILL.md` 로 복사해 채운다.

베이스를 개선하면 git 커밋 → 다음 프로젝트부터 반영된다. 이미 설치된 프로젝트는 독립 복사본이라 자동 반영되지 않으니, 필요하면 다시 `install.sh`(병합·시드는 없을 때만 생성이라 안전).

## 라이선스 (License)

MIT. 자세한 내용은 [LICENSE](./LICENSE)를 참고한다.
