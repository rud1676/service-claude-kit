# claude-starter-kit

새 프로젝트를 시작할 때 `.claude/`에 기본으로 깔아두는 **공통 역할 베이스**.
Claude Code 타겟. 여기서 베이스를 관리하고, 각 프로젝트에는 **복사**해서 뿌린 뒤 프로젝트 성격에 맞게 커스터마이징한다.

## 구조

```
.
├── install.sh              # 대상 프로젝트의 .claude/ 로 베이스를 복사
├── base/                   # 모든 프로젝트에 깔리는 공통 베이스
│   ├── agents/             # 서브에이전트(역할 페르소나)
│   │   ├── reviewer.md     # 코드 리뷰어 (읽기 전용)
│   │   ├── frontend.md     # 프론트엔드 작업자
│   │   └── explainer.md    # 코드 설명자 (읽기 전용)
│   └── skills/             # 스킬(절차/노하우)
│       └── issue-mgmt/     # 이슈/티켓 관리 절차
│           └── SKILL.md
└── _templates/             # 새 역할 만들 때 복사용 뼈대
    ├── agent.md
    └── SKILL.md
```

## 개념 정리

- **서브에이전트 (`agents/*.md`)** — 일을 대신 수행하는 격리된 대리인. 자기 컨텍스트에서 실행 후 결과만 반환. 리뷰어·프론트작업자·설명자처럼 "역할"인 것들.
- **스킬 (`skills/*/SKILL.md`)** — 메인 에이전트가 필요할 때 읽어 따르는 절차/노하우. 이슈관리처럼 "방법"인 것들.

## 사용법

프로젝트 이름만 주면 현재 위치에 `./<이름>` 폴더를 만들고(없으면) 베이스를 설치한다:

```bash
./install.sh myproject          # ./myproject 생성 + 설치
./install.sh /abs/path/proj     # 절대 경로도 그대로 동작
```

이미 있는 파일까지 덮어쓰려면:

```bash
./install.sh myproject --force
```

설치 후, 각 프로젝트의 `.claude/` 안에서 파일들의 `프로젝트 커스터마이징` 주석 부분을 그 프로젝트에 맞게 채운다.

## 새 역할 추가하기

- 서브에이전트: `_templates/agent.md` → `base/agents/<이름>.md` 로 복사해 채운다.
- 스킬: `_templates/SKILL.md` → `base/skills/<이름>/SKILL.md` 로 복사해 채운다.

베이스를 개선하면 git 커밋 → 다음 프로젝트부터 반영된다. (이미 설치된 프로젝트는 독립 복사본이라 자동 반영되지 않음 — 필요하면 다시 `install.sh`)
