# service-claude-kit

[![skills.sh](https://skills.sh/b/rud1676/service-claude-kit)](https://skills.sh/rud1676/service-claude-kit)

**실제로 운영할, 그리고 이미 운영 중인 서비스를 AI와 함께 개발하기 위한 Claude Code 워크스페이스 베이스.**
AI가 운영 코드에 코드를 쏟아내도, 개발자가 **통제권과 이해**를 놓지 않게 한다.

AI 코딩은 "일단 만들어줘"로 시작할 수 있다. 하지만 대상이 **이미 사람이 쓰는 서비스**이거나 **곧 운영할 서비스**라면 이야기가 다르다. 요구사항은 계속 새로 들어오고, 그때마다 개발자는 "지금 코드로 이게 가능한가, 정확히 뭘 바꿔야 하나"를 판단하고 소통해야 한다. 이 판단은 **현재 버전의 실제 상태**를 촘촘히 인지하고 있어야만 가능하다.

문제는, AI가 인간이 따라갈 수 없는 속도로 **운영 코드에도** 변경을 쏟아낸다는 것이다. 부작용·회귀가 쌓이고, "왜 이렇게 됐는지"를 아무도 모르는 채로 코드만 불어난다. 그러면 개발자는 어느 순간 자기 서비스의 흐름에 낄 수 없게 된다 — **인지 부채(cognitive debt)**다.

이 킷은 그 부채를 작게 막기 위한 **초기 세팅**이다. 목표는 에이전트가 더 많이 하게 만드는 것이 아니라, **개발자를 루프 안에 남겨두는 것**이다: 변경을 격리해 검증하고, 결정을 기록하고, 요구사항을 코드 근거로 판별한다. 가능성 판단과 소통은 여전히 개발자의 몫이고 — 이 킷은 그 판단이 추측이 아니라 **현재 상태의 진실**에 근거하도록 받쳐준다.

> 이 킷은 그린필드 MVP를 빠르게 찍어내는 스타터팩이 아니다(그 영역은 [not-agent/starter-skills](https://skills.sh/not-agent/starter-skills) 같은 도구가 잘 한다). 정반대 지점 — **살아있는 서비스 코드에 AI를 안전하게 들이는 쪽**에 집중한다.

## 기본 전제 (Defaults)

- **대상은 운영/실서비스 코드.** 그린필드가 아니라, 이미 돌고 있거나 곧 돌릴 코드베이스에 요구사항이 계속 들어오는 상황을 기본으로 둔다.
- **개발자를 루프에.** 자동화의 목적은 "AI가 알아서 다 하기"가 아니라 "개발자가 촘촘히 인지한 상태를 유지하기"다. 사람이 게이트에서 고를 것을 고르고, 코드 검토는 PR에서 사람이 한다.
- **멀티레포 워크스페이스.** 실제 코드는 `repository/` 아래 각 독립 git repo에 두고, 워크스페이스 자체는 git이 아니다. (front·server·admin 등이 한 워크스페이스에 모이는 실무 구조를 가정)
- **실행축 스킬은 "고쳐 쓰는 참고 구현".** 아래 worktree·jiraticket·figma-depth-find는 실무에서 검증된 절차지만, DDNS·포트·Jira cloudId 같은 구체값은 환경마다 다르다. 정신(격리→검증→게이트→PR 등)은 보편이고, 구체값은 각 파일의 `프로젝트 커스터마이징` 주석대로 자기 환경에 맞게 채운다.

## 빠른 시작 (Quickstart)

프로젝트 이름을 주면 `./<이름>` 폴더를 만들고(없으면) 워크스페이스를 설치한다. 설치 중 환경을 물어보고, **답에 맞는 스킬만·맞는 모양으로** 깔아준다.

```bash
./scripts/install.sh myproject
```

설치 중 두 가지를 묻는다:

1. **프로젝트 관리 툴** — `Jira`(jiraticket 스킬 포함) / `GitHub Projects`(gh-project 스킬 포함, 무료·gh CLI) / `없음`
2. **작업 환경** — `원격 서버`(접속 링크를 내부/외부 2가지로 안내) / `로컬`(localhost만)

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

단, 이 채널은 **`SKILL.md`만** 설치한다 — `install.sh`가 하는 **훅 배선·`CLAUDE.md` 규칙 주입·워크스페이스 폴더(wiki/decision-log/repository) 스캐폴딩은 하지 않는다.** 그리고 `worktree`·`jiraticket`·`figma-depth-find`는 이 워크스페이스 구조와 `CLAUDE.md` 규칙에 엮여 있어, 낱개로 설치하면 반쪽만 동작한다. **풀 킷 경험은 `install.sh`가 정본**이고, skills.sh는 "스킬만 떼어 보고 싶을 때"의 보조 채널로 둔다.

## 왜 이 스킬들이 필요한가 (Why These Skills Exist)

운영 코드에 AI를 들일 때 반복해서 겪는 실패 모드를, 각각 작게 막는다.

### #1: AI가 운영 코드(main)에 직접 쏟아내 부작용·회귀가 난다

**문제**: 에이전트가 메인 체크아웃에 바로 손대면, 검증 전 변경이 다른 작업과 섞이고 회귀가 조용히 들어온다. 운영 코드에서는 이 비용이 크다.

**해결**: [`worktree`](./skills/worktree/SKILL.md). 격리된 git 워크트리 안에서만 수정하고 → `lint`/`build`로 검증하고 → **`reviewer` 자가검토 게이트에서 사람이 고칠 것을 고르고** → PR로만 반영한다. AI가 main을 직접 건드리지 않는다. (환경 맞게 고쳐 쓰는 참고 구현)

### #2: AI가 쏟아내니 "왜 이렇게 됐는지"를 못 따라간다 (인지 부채)

**문제**: diff를 쓱 훑고 "이해했다"고 넘어가지만, 그건 대개 *낯익음*을 *이해*로 착각한 것이다. 이해 없이 위임만 쌓이면 자기 코드의 흐름에 낄 수 없게 된다.

**해결**: [`explain`](./skills/explain/SKILL.md). 코드만 봐선 안 보이는 것 — 왜 이 결정인가 / 무엇을 버렸나 / 무슨 가정인가 / 어디까지 영향인가 — 을 복원해 `wiki/`에 남긴다. AI의 생산 속도에 인간의 이해 속도를 맞추는 브레이크.

### #3: 요구사항이 바뀔 때 낡은 전제로 추측한다

**문제**: 운영 앱에 요구사항이 바뀌어 들어오면, "지금 코드로 가능한가 / 정확히 뭘 바꿔야 하나"를 **현재 실제 버전** 기준으로 판별해야 한다. 그 현재-상태 지식이 없으면 AI도 사람도 추측하게 된다.

**해결**: `CLAUDE.md`의 **항상-온 규칙**(설치 시 주입되는 `context-mgmt` 블록)이 `wiki/`·`decision-log/`를 append-only로 갱신하게 강제해, **현재 상태의 진실**을 유지한다. 그래서 변경을 현실에 맵핑할 수 있다. jiraticket·worktree의 분석 단계가 실제 코드를 읽어 변경안을 `파일:줄`로 근거화하고, **가능성 판단·소통은 개발자가** 한다(= 루프 유지).

### #4: 새 요구사항이 티켓·코드와 따로 논다

**문제**: 들어온 요구사항을 머리로만 관리하면, 실제 브랜치·커밋·PR과 티켓이 어긋나고 무엇을 왜 바꿨는지 추적이 끊긴다.

**해결**: [`jiraticket`](./skills/jiraticket/SKILL.md)(Jira) / [`gh-project`](./skills/gh-project/SKILL.md)(GitHub Projects) / [`issue-mgmt`](./skills/issue-mgmt/SKILL.md). 티켓·아이템 조회 → 선택 → (코드 근거로) 분석 → `worktree`로 구현까지 한 흐름으로 잇고, 브랜치·커밋·PR을 티켓 키(또는 이슈 번호)로 연결한다.

### #5: 시안이 우리 기존 컴포넌트와 무관하게 구현돼 중복·불일치가 쌓인다

**문제**: 디자인 시안을 그대로 새로 구현하면, 이미 있는 컴포넌트와 중복되거나 스타일이 어긋난다. 운영 UI에서는 이 불일치가 곧 부채다.

**해결**: [`figma-depth-find`](./skills/figma-depth-find/SKILL.md). 여러 sub-agent가 큰 Figma 프레임을 깊게 탐색하고(truncate되면 자식으로 재귀), 그 화면을 **우리 코드베이스의 실제 컴포넌트로 매핑**한다. 재사용/부분매칭/신규(갭)로 분류해, 정말 없는 것만 새로 만든다.

### #6: 프로젝트마다 비슷한 스킬 베이스를 매번 새로 만들게 된다

**문제**: 새 프로젝트를 시작할 때마다 엇비슷한 규칙·스킬·폴더 구조를 처음부터 다시 세팅한다. 그러면서 미묘하게 달라져 일관성도 잃는다.

**해결**: **인터랙티브 [`install.sh`](./scripts/install.sh)**. 환경(PM 툴·로컬/원격)을 물어보고 맞는 스킬만·맞는 모양으로 깔고, `CLAUDE.md` 작업 규칙·훅 배선·워크스페이스 폴더를 일관되게 세팅한다. 베이스를 개선하면 다음 프로젝트부터 반영된다.

## 개념 정리

### 항상-온 규칙(CLAUDE.md) vs 필요할 때 스킬

이 킷은 "에이전트가 알아야 할 것"을 두 층으로 나눈다. 무엇을 어디에 둘지의 기준은 **"항상 켜져 있어야 하나, 특정 작업일 때만 필요하나"**다.

- **항상-온 규칙 — `CLAUDE.md`** (`base/CLAUDE.block.md`가 설치 시 주입): 작업 종류와 무관하게 **늘 지켜야 하는 계약**. 폴더 구조, wiki/decision-log 갱신 규칙, "추적 메타는 답변 본문에 출력 금지", "커밋·PR은 사용자 요청 시만". 이건 매 컨텍스트에 항상 있어야 의미가 있어서, 스킬로 빼면 오히려 깨진다.
- **필요할 때 스킬 — `skills/*/SKILL.md`**: "이 작업을 하면 이 절차를 따르라"는 **절차**. 관련 작업이 올 때만 로드돼 컨텍스트를 가볍게 유지한다. (explain·worktree·jiraticket·figma-depth-find·issue-mgmt)

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
│   └── figma-depth-find/   # 큰 Figma 프레임을 멀티에이전트로 탐색·우리 컴포넌트 매핑
├── scripts/                # 이 repo의 스크립트 모음
│   ├── install.sh          # 대상 프로젝트에 워크스페이스를 설치(환경 질문 포함)
│   └── hooks/              # 세션 추적 훅(python) → 설치 시 .claude/hooks/로 복사
│       ├── context-checkpoint.py  # N프롬프트마다 wiki 갱신 리마인더
│       ├── log-read.py            # Read/Grep/Glob 기록 → claude-log/
│       └── summarize-session.py   # 세션 요약·토큰·참고문서·탐색집계 → claude-log/
├── base/                   # install.sh가 target .claude/에 넣는 나머지(비-스크립트)
│   ├── agents/             # 서브에이전트(역할 페르소나) → .claude/agents/
│   │   ├── reviewer.md     # 코드 리뷰어 (읽기 전용)
│   │   ├── frontend.md     # 프론트엔드 작업자
│   │   └── explainer.md    # 코드 설명자 (읽기 전용)
│   ├── settings.hooks.json # 훅 배선(설치 시 .claude/settings.json에 안전 병합)
│   └── CLAUDE.block.md     # 프로젝트 CLAUDE.md에 주입할 관리 규칙(마커 블록)
└── _templates/             # 새 역할 만들 때 복사용 뼈대 (agent.md · SKILL.md)
```

## 설치 후 워크스페이스 모습

```
{프로젝트}/                 # 워크스페이스 — 그 자체는 git 저장소가 아니다
├── .claude/               # agents · skills · hooks · settings.json
├── CLAUDE.md              # context-mgmt + config(설치 시 선택값) 블록 주입됨
├── wiki/                  # 프로젝트 지식 위키   (오래 남는 팀 지식)
├── study/                 # 내 학습 기록          (개인 이해용)
├── decision-log/          # 결정 아카이브         (왜 이걸 택했나 / 무엇을 버렸나)
├── plan/                  # 임시 작업 맥락        (완료 시 삭제)
├── claude-log/            # 세션 추적 로그        (훅이 자동 생성)
└── repository/            # 실제 코드 repo들      (각각 독립 git)
```

## 폴더별 맥락 — 무엇을 어디에 남기나

기준은 **누구를 위한 것이고, 얼마나 오래 남을 것인가**다.

- **`wiki/`** — 코드만 봐선 알 수 없는 프로젝트의 진실(도메인 동작·확정된 결정·기획 변경). `wiki/{도메인}/*.md` + `wiki/README.md` 인덱스. `explain` 스킬이 관리하고, 갱신은 덮어쓰기가 아니라 `## 후속 (날짜)`로 이어 붙인다. 모든 주장에 `파일:줄` 근거와 작성 날짜·대상 커밋을 단다.
- **`study/`** — "이거 어떻게 동작해?"처럼 내가 배우려고 물어본 것. `wiki/`(프로젝트 진실)와 목적이 달라 섞지 않는다.
- **`decision-log/`** — 판단이 갈렸거나 대안을 버린 결정을 `<YYYY-MM-DD>-<주제>.md`로 append-only 기록. "무엇을 택했고 어떤 대안을 왜 버렸나 / 아직 미결이면 왜 미결인가"가 핵심. 매번이 아니라 **판단이 갈렸을 때만**.
- **`plan/`** — 큰 작업의 임시 계획·메모. 작업이 끝나면 삭제한다.
- **`claude-log/`** — 훅이 세션마다 `<session_id>.md`를 자동 생성·갱신(읽기 기록·요약·토큰·탐색 집계). 사람이 직접 쓰지 않는다.
- **`repository/`** — front·server 등 실제 git repo. **각각 독립 git**이라 워크스페이스가 git이 아니어도 중첩이 꼬이지 않는다. 브랜치·커밋은 해당 repo 안에서, 병렬 작업 워크트리는 `repository/{repo}-worktrees/{작업번호}/`.

## 안전 설치 (기존 프로젝트에 깔아도 안 깨진다)

이미 쓰던 프로젝트에 설치해도 기존 설정을 보존하도록, 두 파일은 **병합**으로 처리한다:

- **CLAUDE.md** — `<!-- BEGIN/END service-kit:context-mgmt -->` 와 `service-kit:config` 마커로 감싼 블록만 삽입/갱신한다. 파일이 없으면 생성, 마커가 있으면 그 블록만 교체, 마커 없는 기존 파일이면 기존 내용을 그대로 둔 채 덧붙인다. 재실행해도 블록은 하나만 유지된다(멱등).
- **settings.json** — 기존 `permissions`·`env`·다른 훅을 보존하고 `hooks`만 union 병합한다. `command` 문자열로 중복을 판단하므로 재실행해도 훅이 중복 배선되지 않는다.
- **워크스페이스 폴더**(`wiki/ study/ decision-log/ repository/ plan/ claude-log/`)는 각 README 시드와 함께 **없을 때만** 생성한다.
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
