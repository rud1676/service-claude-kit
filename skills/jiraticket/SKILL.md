---
name: jiraticket
description: 내 Jira 티켓 목록을 조회하고, 선택한 티켓의 코드를 분석하여 수정 및 PR 생성까지 수행하는 워크플로우. /jiraticket으로 호출. (이슈 트래커가 Jira일 때. 다른 트래커면 조회 부분을 커스터마이징.)
user_invocable: true
---

아래 단계를 순서대로 수행해줘.

> **Tip**: 이 워크플로우는 도구 호출이 많아 매번 승인하기 번거로울 수 있습니다.
> 원활한 진행을 위해 **Shift+Tab**을 눌러 auto-accept 모드를 활성화하는 것을 권장합니다.

## 0단계: 사전 환경 확인

코드 수정/PR 생성이 필요할 수 있으므로, 워크플로우 시작 전에 아래 도구들이 사용 가능한지 확인해줘.
문제가 있으면 즉시 안내하고 해결한 뒤 다음 단계로 진행해줘.

### 0-1. GitHub CLI (`gh`)

```bash
gh auth status
```

- `gh`가 설치되어 있지 않으면 설치를 안내(macOS `brew install gh` 등)
- 인증이 안 되어 있으면: 사용자에게 `! gh auth login` 실행을 안내
- **주의**: shell alias/함수가 `gh`를 덮어쓸 수 있으므로, 이상하면 절대경로/`command gh`로 실행

### 0-2. Atlassian MCP (Jira)

- `getJiraIssue`, `searchJiraIssuesUsingJql` 등 Atlassian MCP 도구가 사용 가능한지 확인
- 사용 불가하면 사용자에게 MCP 서버 연결(인증)을 안내해줘

## 1단계: 내 지라 티켓 목록 조회

Atlassian MCP 도구를 사용해서 아래 JQL로 지라 티켓을 검색해줘.

- cloudId: `{JIRA_CLOUD_ID}`
- JQL:

```
created >= -30d AND project = {PROJECT_KEY} AND assignee = currentUser() AND type IN (Task, Epic, Story, Bug, Sub-task) AND status IN ("To Do", "In Progress") ORDER BY created DESC
```

- fields: summary, status, issuetype, priority, created, updated
- responseContentFormat: markdown

> 상태 이름(예: 프로젝트 고유의 "재수정 요청" 등)이나 프로젝트 키는 이 프로젝트 워크플로에 맞게 아래 커스터마이징 주석대로 조정한다.

## 2단계: 목록 출력

조회 결과를 아래 형식의 번호 목록으로 보여줘:

```
번호. [티켓키] 제목
   유형: __ | 상태: __ | 우선순위: __ | 생성일: __
```

목록 하단에 다음 안내를 추가해줘:

> 상세 조회할 티켓 번호를 입력해주세요. (예: 1)

## 3단계: 사용자 선택 대기

사용자가 번호를 입력하면, 해당 티켓의 키(예: {PROJECT_KEY}-1234)로 `getJiraIssue`를 호출해서 상세 정보를 조회하고 아래 항목을 보여줘:

- 티켓 키 및 제목
- 유형 / 상태 / 우선순위
- 담당자 / 보고자
- 생성일 / 수정일
- 설명 (description) 전문
- 댓글 (있으면)
- 하위 작업 (있으면)

## 4단계: 이미지 확인 안내 및 대기

Jira 티켓의 이미지는 Atlassian 내부 미디어 서버에 저장되어 있어 직접 조회가 불가능하므로, 아래와 같이 안내해줘:

1. 해당 티켓의 웹 URL을 제공해줘 (예: `https://{JIRA_HOST}/browse/{PROJECT_KEY}-1413`)
2. 피그마 링크가 있다면 함께 제공해줘
3. 다음 안내를 출력해줘:
   > 티켓의 이미지는 직접 조회할 수 없습니다. 아래 방법으로 이미지를 공유해주세요:
   >
   > - Jira 웹에서 이미지를 다운로드하여 여기에 붙여넣기
   > - 또는 스크린샷을 찍어서 여기에 붙여넣기
4. 다음 안내를 추가해줘:
   > 이미지를 붙여넣거나, **"분석"**을 입력하면 이미지 없이 바로 코드 분석을 시작합니다.
5. 사용자가 이미지를 붙여넣으면, 해당 이미지를 분석하고 티켓 내용과 함께 맥락을 파악한 뒤 5단계로 진행해줘
6. 사용자가 "분석"을 입력하면, 이미지 없이 바로 5단계로 진행해줘

## 5단계: 코드 분석 → 수정 승인 → **`worktree` 스킬로 구현 위임**

> ⚠️ `jiraticket`은 **티켓 조회·선택·이미지 수집(1~4단계) + 코드 분석·수정 계획(5-1)**까지 담당한다.
> **워크트리 생성 → 수정 → 검증 → 커밋 → PR** 은 `worktree` 스킬이 담당한다.
> 5단계에서 Edit·Write·Bash(파일 수정)를 **메인 체크아웃에 직접** 호출하는 것은 이 워크플로우의 위반이다 — 실제 파일 수정은 워크트리 안에서만 일어나야 한다.

### 5-1. 코드 분석 & 수정 계획

티켓 내용(+공유된 이미지)을 근거로 관련 코드를 읽어(`repository/` 아래) 원인을 추정하고, **무엇을 어디서 어떻게 고칠지** 수정 계획을 세운다.

- 관련 파일·호출부를 실제로 읽고, 추측이 아니라 `파일:줄` 근거로 원인을 정리한다.
- 어느 repo(들)를 수정해야 하는지 확정한다.
- 수정 계획(변경 요지)을 사용자에게 제시하고 **"이대로 진행할까요?" 승인을 받는다.**

> 프로젝트에 코드 분석→수정을 전담하는 별도 스킬(예: `fix-issue`)이 있으면, 5-1을 그 스킬에 위임해도 된다. 없으면 위 절차를 인라인으로 수행한다.

### 5-2. `worktree` 스킬 호출 (구현)

승인이 떨어지면 `Skill` 도구로 `skill: 'worktree'`를 호출한다. 아래 값을 넘긴다:

```
<티켓번호>: <선택한 티켓 키, 예: {PROJECT_KEY}-1413>   ← 이미 티켓이 있으므로 브랜치명에 그대로 쓴다(티켓 자동 생성 안 함)
<type>: <fix | feat | refactor …>
수정 대상 repo: <5-1에서 확정한 repo 목록>
변경 요지: <5-1의 수정 계획>
```

- `worktree`가 워크트리 생성 → 수정 → 검증 → 자가검토 게이트 → 커밋 → push → PR까지 처리한다.
- 브랜치명·커밋 메시지는 **선택한 티켓번호**(예: `{PROJECT_KEY}-1413`)를 그대로 사용한다.

### 5-3. 마무리 안내

`worktree` 스킬이 PR URL을 출력하면, 아래를 추가로 안내해줘:

> PR이 생성되었습니다. 코드 검토는 GitHub PR 화면에서 진행해주세요.
> Jira 티켓 상태를 변경할까요? (예: 진행 중 → 검토 요청)

- 사용자가 원하면 `transitionJiraIssue`로 상태를 옮긴다.

<!-- 프로젝트 커스터마이징:
- {JIRA_CLOUD_ID}: Atlassian getAccessibleAtlassianResources 로 확인한 cloudId.
- {JIRA_HOST}: 예 yourorg.atlassian.net
- {PROJECT_KEY}: Jira 프로젝트 키(예 PROJ).
- 1단계 JQL 의 status 목록: 이 프로젝트 워크플로에 실제로 쓰는 상태 이름으로 교체(고유 상태 포함).
- 이슈 트래커가 Jira 가 아니면(GitHub Issues/Linear 등) 1·3·4단계 조회를 해당 도구로 교체하고, issue-mgmt 스킬과 규칙을 맞춘다.
- 코드 분석 전담 스킬(fix-issue 등)이 있으면 5-1 위임 대상으로 지정.
-->
