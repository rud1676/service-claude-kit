---
name: gh-project
description: 내 GitHub Projects(Projects V2) 아이템 목록을 조회하고, 선택한 아이템(이슈)의 코드를 분석하여 수정 및 PR 생성까지 수행하는 워크플로우. /gh-project로 호출. (이슈 트래커가 GitHub Projects일 때. Linear가 유료라 GitHub Project로 연동하는 무료 대안 — 조회는 gh CLI로 한다.)
user_invocable: true
---

아래 단계를 순서대로 수행해줘.

> **Tip**: 이 워크플로우는 도구 호출이 많아 매번 승인하기 번거로울 수 있습니다.
> 원활한 진행을 위해 **Shift+Tab**을 눌러 auto-accept 모드를 활성화하는 것을 권장합니다.

> 이 스킬은 별도 MCP 없이 **`gh` CLI 하나로** GitHub Projects·이슈를 다룬다.
> (Jira를 쓰는 프로젝트라면 이 스킬 대신 `jiraticket`을 쓴다.)

## 0단계: 사전 환경 확인

코드 수정/PR 생성이 필요할 수 있으므로, 워크플로우 시작 전에 아래를 확인해줘.
문제가 있으면 즉시 안내하고 해결한 뒤 다음 단계로 진행해줘.

### 0-1. GitHub CLI (`gh`) 인증

```bash
gh auth status
```

- `gh`가 설치되어 있지 않으면 설치를 안내(macOS `brew install gh` 등)
- 인증이 안 되어 있으면: 사용자에게 `! gh auth login` 실행을 안내
- **주의**: shell alias/함수가 `gh`를 덮어쓸 수 있으므로, 이상하면 절대경로/`command gh`로 실행

### 0-2. Projects 접근 스코프 확인

`gh project` 명령은 토큰에 `project`(읽기 전용은 `read:project`) 스코프가 있어야 동작한다.
`gh auth status`의 스코프 목록에 없으면 사용자에게 아래 실행을 안내해줘:

```bash
! gh auth refresh -s project
```

- 상태 변경(마무리 단계)까지 하려면 읽기 전용(`read:project`)이 아니라 `project`가 필요하다.
- 조회만 할 거면 `read:project`로도 충분하다.

## 1단계: 내 프로젝트 아이템 목록 조회

`gh project item-list`로 프로젝트 아이템을 가져온 뒤, **나에게 할당됐고 진행 대상 상태**인 것만 골라낸다.
(GitHub Projects는 서버측 필터가 없으므로 `jq`로 걸러낸다.)

```bash
ME="$(gh api user --jq .login)"
gh project item-list {GH_PROJECT_NUMBER} --owner {GH_PROJECT_OWNER} --format json --limit 200 \
  | jq --arg me "$ME" '
      [ .items[]
        | select((.assignees // []) as $a
                 | (($a | type) == "array" and ($a | index($me)))
                   or (($a | type) == "string" and ($a | contains($me))))
        | select(.status == "Todo" or .status == "In Progress")
      ]'
```

- `{GH_PROJECT_OWNER}`는 사용자 또는 org 로그인, `{GH_PROJECT_NUMBER}`는 프로젝트 번호(URL의 `/projects/N`).
- `assignees`·`status` 필드의 실제 JSON 모양(문자열/배열, 상태 옵션 이름)은 `gh` 버전·프로젝트마다 다르니, 첫 실행에서 한 아이템의 원본 JSON을 확인하고 위 `jq`를 실제 필드명/상태값에 맞게 조정한다(아래 커스터마이징 주석 참고).
- 정렬은 결과에서 최신순(예: `.content.number` 내림차순)으로 보여주면 된다.

## 2단계: 목록 출력

조회 결과를 아래 형식의 번호 목록으로 보여줘:

```
번호. [#이슈번호] 제목
   상태: __ | 유형: Issue/Draft | 저장소: owner/repo | 라벨: __
```

- 아이템이 이슈면 `#<이슈번호>`와 `저장소`를, Draft(이슈 미연결)면 그 사실을 표기한다.
- 목록 하단에 다음 안내를 추가해줘:

> 상세 조회할 아이템 번호를 입력해주세요. (예: 1)

## 3단계: 사용자 선택 대기

사용자가 번호를 입력하면, 해당 아이템의 연결 이슈를 `gh issue view`로 조회해서 상세를 보여줘:

```bash
gh issue view <이슈번호> --repo <owner/repo> --comments \
  --json number,title,body,state,assignees,labels,milestone,url,comments
```

아래 항목을 보여줘:

- 이슈 번호 및 제목 (`#123`)
- 상태(프로젝트 Status) / GitHub state(open/closed) / 라벨 / 마일스톤
- 담당자
- 본문(body) 전문
- 댓글 (있으면)
- 이슈 URL

> 아이템이 Draft(이슈 미연결)면 `gh issue view` 대신 1단계에서 받은 프로젝트 아이템의 `title`/`body`를 그대로 보여준다. 코드 작업으로 이어지려면 실제 이슈로 승격하는 게 좋다고 안내한다.

## 4단계: 이미지 확인 안내 및 대기

GitHub 이슈 본문·댓글의 이미지는 보통 `![](https://github.com/user-attachments/...)` 형태로 들어 있다. **비공개 저장소의 첨부는 인증 없이는 직접 조회되지 않을 수 있으므로**, 아래와 같이 안내해줘:

1. 이슈 본문/댓글에 이미지가 있으면 그 URL을 정리해서 보여줘.
2. 피그마 링크가 있다면 함께 제공해줘.
3. 다음 안내를 출력해줘:
   > 이슈의 이미지(특히 비공개 저장소 첨부)는 직접 조회가 안 될 수 있습니다. 아래 방법으로 이미지를 공유해주세요:
   >
   > - GitHub 웹에서 이미지를 다운로드하여 여기에 붙여넣기
   > - 또는 스크린샷을 찍어서 여기에 붙여넣기
4. 다음 안내를 추가해줘:
   > 이미지를 붙여넣거나, **"분석"**을 입력하면 이미지 없이 바로 코드 분석을 시작합니다.
5. 사용자가 이미지를 붙여넣으면, 해당 이미지를 분석하고 이슈 내용과 함께 맥락을 파악한 뒤 5단계로 진행해줘.
6. 사용자가 "분석"을 입력하면, 이미지 없이 바로 5단계로 진행해줘.

> 공개 저장소의 이미지는 WebFetch로 직접 볼 수 있는 경우가 많으니, 먼저 시도해보고 실패할 때만 붙여넣기를 요청해도 된다.

## 5단계: 코드 분석 → 수정 승인 → **`worktree` 스킬로 구현 위임**

> ⚠️ `gh-project`는 **아이템 조회·선택·이미지 수집(1~4단계) + 코드 분석·수정 계획(5-1)**까지 담당한다.
> **워크트리 생성 → 수정 → 검증 → 커밋 → PR** 은 `worktree` 스킬이 담당한다.
> 5단계에서 Edit·Write·Bash(파일 수정)를 **메인 체크아웃에 직접** 호출하는 것은 이 워크플로우의 위반이다 — 실제 파일 수정은 워크트리 안에서만 일어나야 한다.

### 5-1. 코드 분석 & 수정 계획

이슈 내용(+공유된 이미지)을 근거로 관련 코드를 읽어(`repository/` 아래) 원인을 추정하고, **무엇을 어디서 어떻게 고칠지** 수정 계획을 세운다.

- 관련 파일·호출부를 실제로 읽고, 추측이 아니라 `파일:줄` 근거로 원인을 정리한다.
- 어느 repo(들)를 수정해야 하는지 확정한다.
- 수정 계획(변경 요지)을 사용자에게 제시하고 **"이대로 진행할까요?" 승인을 받는다.**

> 프로젝트에 코드 분석→수정을 전담하는 별도 스킬(예: `fix-issue`)이 있으면, 5-1을 그 스킬에 위임해도 된다. 없으면 위 절차를 인라인으로 수행한다.

### 5-2. `worktree` 스킬 호출 (구현)

승인이 떨어지면 `Skill` 도구로 `skill: 'worktree'`를 호출한다. 아래 값을 넘긴다:

```
<티켓번호>: <브랜치 식별자, 예: issue-142-login-toast>   ← 이미 이슈가 있으므로 브랜치명에 그대로 쓴다(티켓 자동 생성 안 함)
<type>: <fix | feat | refactor …>
수정 대상 repo: <5-1에서 확정한 repo 목록>
변경 요지: <5-1의 수정 계획>
이슈 링크: https://github.com/<owner>/<repo>/issues/<이슈번호>   ← PR 본문에 "Closes #<이슈번호>"로 자동 닫힘 링크
```

- GitHub 브랜치명에는 `#`을 쓸 수 없으므로 **`issue-<번호>-<짧은설명>`** 같은 슬러그를 브랜치 식별자로 넘긴다.
- `worktree`가 워크트리 생성 → 수정 → 검증 → 자가검토 게이트 → 커밋 → push → PR까지 처리한다.
- 커밋/PR 본문에는 **이슈 번호(`#<번호>`)** 로 연결하고, PR 본문에 `Closes #<번호>`를 넣어 머지 시 이슈가 자동 닫히게 한다. (worktree의 PR 본문 `이슈:` 줄을 GitHub 이슈 URL로 채우도록 위 "이슈 링크"를 넘긴다.)

### 5-3. 마무리 안내

`worktree` 스킬이 PR URL을 출력하면, 아래를 추가로 안내해줘:

> PR이 생성되었습니다. 코드 검토는 GitHub PR 화면에서 진행해주세요.
> 프로젝트 보드의 상태를 옮길까요? (예: Todo → In Progress, 또는 In Progress → In Review)

- 사용자가 원하면 프로젝트 아이템의 Status 필드를 아래처럼 갱신한다. (필드/옵션 ID가 필요하므로 한 번만 조회해 커스터마이징 주석에 적어두면 다음부터 빠르다.)

```bash
# (준비) 프로젝트 ID·Status 필드 ID·옵션 ID 조회 — 최초 1회만
gh project view {GH_PROJECT_NUMBER} --owner {GH_PROJECT_OWNER} --format json --jq .id            # → PROJECT_ID
gh project field-list {GH_PROJECT_NUMBER} --owner {GH_PROJECT_OWNER} --format json \
  | jq '.fields[] | select(.name=="Status") | {id, options}'                                       # → FIELD_ID, OPTION_ID들

# (실행) 아이템 상태 변경. 아이템 ID는 1단계 item-list 결과의 .id
gh project item-edit \
  --project-id {PROJECT_ID} \
  --id <아이템 ID> \
  --field-id {STATUS_FIELD_ID} \
  --single-select-option-id {옵션 ID}
```

- PR을 이슈에 `Closes #<번호>`로 연결해 두면, PR 머지 시 이슈가 닫히고 프로젝트 워크플로 설정에 따라 상태도 자동으로 옮겨질 수 있다(수동 갱신이 불필요할 수 있음).

<!-- 프로젝트 커스터마이징:
- {GH_PROJECT_OWNER}: 프로젝트 소유자(사용자 또는 org 로그인). 예 my-org
- {GH_PROJECT_NUMBER}: 프로젝트 번호(프로젝트 URL의 /projects/N 의 N).
- 1단계 jq: 이 프로젝트의 실제 assignees JSON 모양(문자열/배열)과 Status 옵션 이름(Todo/In Progress/In Review/Done 등)에 맞게 조정.
- 상태 전환 ID: {PROJECT_ID} {STATUS_FIELD_ID} 와 각 상태 옵션 ID를 5-3의 조회 명령으로 한 번 뽑아 여기 적어두면 매번 조회 안 해도 된다.
- 이슈가 여러 저장소에 흩어져 있으면, item-list 결과의 .content.repository 로 각 이슈의 repo를 판별한다.
- 코드 분석 전담 스킬(fix-issue 등)이 있으면 5-1 위임 대상으로 지정.
- 이슈 트래커가 GitHub Projects 가 아니면(Jira 등) 이 스킬 대신 jiraticket 을 쓰고, issue-mgmt 스킬과 규칙을 맞춘다.
-->
