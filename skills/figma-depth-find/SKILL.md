---
name: figma-depth-find
description: 큰 Figma 프레임 하나(MCP 링크)를 여러 sub-agent로 깊게 탐색하고(truncate되면 자식 nodeId로 재귀), 어느 코드베이스(예: front/admin)에 속하는지 스스로 판단해 우리 코드베이스의 실제 컴포넌트로 매핑해서, 해당 화면을 "우리 코드 맥락"으로 이해한 구조화 결과를 반환하는 스킬. **사용자가 Figma design URL(figma.com/design/...)을 공유하거나, /figma-depth-find로 호출하거나, 상위 스킬이 위임할 때 발동한다.** 단, PRD·기획 요구사항 정리가 목적인 요청은 prd-from-figma로 보낸다. Figma design URL이 없는 단순 언급("피그마가 뭐야")에는 발동하지 않는다.
---

# figma-depth-find (서브 스킬 · 멀티 에이전트)

큰 Figma 프레임을 **여러 Scout 에이전트가 병렬로 깊게 파고**, 각 Scout가 자기 영역을 **우리 코드베이스의 실제 컴포넌트로 매핑**한 뒤, 메인이 취합해 "이 화면을 우리 코드 맥락으로 이해한" 구조화 산출물을 반환한다.

> 이 스킬은 **여러 코드베이스(예: 소비자용 front + 운영자용 admin)** 를 가진 프로젝트를 전제로 쓰였다. 코드베이스가 하나면 아래 "front/admin 판정"을 건너뛰고 그 하나를 타깃으로 고정한다.

## 언제 발동하나

아래 중 하나면 발동한다:
- 사용자가 **Figma design URL**(`figma.com/design/...`)을 공유하며 그 화면을 봐달라/이해해달라/우리 코드로 매핑해달라고 할 때
- 사용자가 `/figma-depth-find <URL>` 로 직접 호출할 때
- 상위 스킬이 "이 Figma를 우리 컴포넌트 맥락으로 이해해와" 라고 위임할 때

발동하지 **않는** 경우:
- **PRD·기획 요구사항 정리**가 목적이면 → `prd-from-figma` 로 보낸다. (그쪽이 필요 시 이 스킬을 부른다)
- Figma design URL 없이 "피그마가 뭐야" 같은 **단순 언급**만 있을 때.

- 단독 호출 가능. 산출물은 **콘솔 출력 + (상위 호출자가 있으면) 구조화 데이터 반환**이다. 파일 저장은 명시 요청할 때만.

## 왜 멀티 에이전트인가

- 메인이 raw Figma 응답(스크린샷 URL, XML 메타데이터, 코드 스니펫)으로 오염되면 매핑·합성 단계에서 토큰이 바닥난다. Scout를 **격리된 컨텍스트**에서 굴려 매핑된 신호만 받는다.
- Claude가 한 프레임을 한 번에 보는 depth는 제한적이고 **truncate**된다. Scout가 자기 영역 안에서 자식 nodeId로 재귀해 잘린 부분을 복원한다 — 메인은 그 진행을 신경 쓰지 않는다.
- frame이 N개면 Scout N개를 한 메시지에 병렬로 띄워 직렬 대비 훨씬 빠르다.

## 역할 분담

| 역할 | 누가 | 무엇을 |
|---|---|---|
| **Cartographer** | 메인 (직접) | URL 파싱 → `get_metadata`로 트리 스캔 → 분석 단위 frame 카탈로그 작성 → **타깃 코드베이스 판정** |
| **Scout+Mapper** | sub-agent (Agent tool, 병렬 N개) | 할당 frame 1개를 깊게 탐색(truncate 시 자식 재귀) → 같은 컨텍스트에서 타깃 프로젝트 컴포넌트로 매핑 → 표준 스키마 반환 |
| **Synthesizer** | 메인 (직접) | Scout 결과 통합, 공용 컴포넌트 중복 매핑 정리, 갭(신규 필요) 목록화, 최종 이해 문서 반환 |

---

## 입력

```
/figma-depth-find <Figma URL>
```

또는 상위 스킬이 `{ url, target?: "front" | "admin" }` 형태로 위임.

- URL이 빠졌으면 **한 번만** 묻는다.
- `target`이 호출자에게서 명시되면 판정을 건너뛰고 그 값을 쓴다. 명시 안 되면 Cartographer가 스스로 판정한다(아래).

**URL 파싱 규칙** (Figma MCP 서버 인스트럭션 그대로):
- `figma.com/design/:fileKey/:fileName?node-id=1-2` → fileKey=`:fileKey`, nodeId=`1:2` (`-`→`:`)
- `figma.com/design/:fileKey/branch/:branchKey/...` → fileKey는 **branchKey**
- node-id 없으면 `0:1`

---

## 1단계 — Cartographer (메인이 직접)

### 1-1. 트리 스캔

**`mcp__figma__get_metadata`** 를 입력 nodeId에 호출한다. `get_design_context`는 여기서 부르지 않는다 — truncate되면 메인 컨텍스트만 더럽힌다.

받은 XML에서 분석 단위 frame 카탈로그를 만든다:

```
[
  { nodeId: "123:456", name: "상세 화면", type: "FRAME", role_guess: "screen", w: 375, h: 1200 },
  { nodeId: "123:789", name: "상세 화면 - Empty", role_guess: "state-variant of 상세 화면" },
  ...
]
```

선정 규칙:
- **이름 있는 frame/component이면서 화면·모달·섹션 단위**만 카탈로그에 올린다. 깊은 자식(버튼/인풋 1개)은 Scout가 안에서 본다.
- **상태 변형**(loading/empty/error)은 별도 화면이 아니라 같은 화면의 변형으로 묶는다(`X - Empty`, `X / Loading` 패턴).
- frame이 **20개 이상**이면 호출자(또는 사용자)에게 카탈로그를 보여주고 범위를 한 번 확인받는다.
- frame이 없거나 1~2개면 멀티 에이전트는 오버킬 — 메인이 2단계를 인라인 처리한다.

### 1-2. 타깃 코드베이스 판정 (스스로)

코드베이스가 여러 개인 프로젝트에서 `target`이 안 넘어왔으면 메인이 판정한다. 루트 nodeId에 **`mcp__figma__get_screenshot`** 한 번(default 옵션, base64 금지)으로 전체 느낌을 보고 + 메타데이터 폭/구조로 결정한다.

| 신호 | → front (소비자/모바일) | → admin (운영자/데스크톱) |
|---|---|---|
| 프레임 폭 | 좁음 (~360–430, 모바일) | 넓음 (~1280+, 데스크톱) |
| 레이아웃 | 세로 스택, BottomSheet, 하단 고정 CTA | 사이드바 + 데이터 테이블, 페이지네이션, 탭 |
| 인터랙션 | 스와이프/스크롤, 풀스크린 모달 | CRUD 폼, 정렬/필터, 다중 컬럼 |
| 도메인 어조 | 소비자 UX | 운영자(관리/통계/CS/상품 관리) |

- 판정 결과와 **한 줄 근거**를 출력한 뒤 묻지 말고 진행한다(서브 스킬이라 질문은 흐름을 끊는다).
- 애매하면 더 가능성 높은 쪽을 택하되, 산출물 헤더에 "판정 신뢰도: 낮음 — 호출자 확인 권장"을 표기한다.
- 한 카탈로그에 front 화면과 admin 화면이 섞여 보이면(드묾) frame별로 타깃을 따로 정해 Scout에 전달한다.
- 코드베이스가 하나뿐인 프로젝트면 이 판정을 건너뛰고 그 하나를 타깃으로 고정한다.

**타깃별 우리 자산 힌트** (Scout 프롬프트에 그대로 넘긴다 — 아래 커스터마이징 주석 값으로 채운다):

- **front** (`{FRONT_REPO}/src`): 신규/리팩토링에 쓰는 UI 라이브러리·공통 컴포넌트·디렉토리 규칙.
  - 공통 컴포넌트: `{공통 CTA 버튼 경로}`, `{공통 입력 필드 경로}`, `{공통 바텀시트/모달 경로}`
  - 컴포넌트 루트: `src/components/`, 페이지: `src/pages/`(또는 프로젝트 규칙)
- **admin** (`{ADMIN_REPO}/src`): 프레임워크(예: Next.js App Router) + UI 라이브러리.
  - 컴포넌트 루트: `src/components/`(도메인별 하위 폴더), 라우트: `src/app/`(또는 프로젝트 규칙)
  - 공용 UI: `src/components/common/`, `src/components/ui/`

---

## 2단계 — Scout+Mapper 출격 (Agent tool 병렬)

각 분석 단위(또는 frame group)마다 **Agent tool 호출 1건**. **모든 Scout를 한 메시지 안에서 병렬로** 띄운다.

`subagent_type`은 **`general-purpose`** (Figma MCP + Read/Grep/Glob + 자율 재귀가 필요).

각 Scout는 자기 컨텍스트 안에서 **(A) Figma 깊은 탐색 → (B) 우리 컴포넌트 매핑**을 둘 다 한다. 이전 대화를 못 보므로 자기 완결적으로 쓴다.

### Scout 프롬프트 템플릿

```
너는 Figma 한 frame을 깊게 탐색한 뒤, 그 화면을 우리 코드베이스의 실제 컴포넌트로 매핑하는 Scout다. 목적은 "이 화면을 우리 코드 맥락으로 이해"하는 것이다. 코드를 작성하지 말고, 매핑과 갭만 보고하라.

**할당 frame**
- fileKey: <fileKey>
- nodeId: <nodeId>
- 이름: <name>
- 추정 역할: <role_guess>
- 그룹된 변형 nodeId(있으면): <variant_nodeIds>

**타깃 프로젝트**: <front | admin>
**프로젝트 루트**: <{FRONT_REPO}/src | {ADMIN_REPO}/src>
**우리 자산 힌트**: <위 1-2의 타깃별 힌트 블록 그대로>

### A. Figma 깊은 탐색
1. `mcp__figma__get_screenshot` 을 nodeId에 호출(default, base64 금지 — URL로 받음). 변형 nodeId 있으면 각각도.
2. `mcp__figma__get_design_context` 를 nodeId에 호출. clientFrameworks/clientLanguages는 "unknown".
3. **truncation 판정**. 다음 중 하나라도 있으면 잘린 것:
   - 응답에 "truncated"/"metadata only"/"too large"
   - 코드 스니펫에 자식 자리가 placeholder/주석만 있고 비어 있음
   - 자식 frame 수가 명백히 부족
4. **잘렸으면 자식으로 재귀**: `mcp__figma__get_metadata`로 자식 nodeId 목록 → 각 자식에 2~4 반복. **방문 집합 유지(같은 nodeId 재호출 금지).** 의미 있는 잎 노드(텍스트/아이콘/인풋 수준)까지 내려간다.
5. dev-mode annotation/노트가 보이면 원문 채집. 디자인 토큰(hex/spacing) 나열은 금지.

이렇게 해서 화면을 **UI 요소 단위로 분해**한다: 헤더/네비, 버튼(CTA), 입력 필드, 리스트/카드/테이블, 모달/바텀시트, 탭, 토스트, 상태 변형(loading/empty/error) 등.

### B. 우리 컴포넌트 매핑
분해한 각 UI 요소에 대해, 타깃 프로젝트 코드베이스에서 **이미 존재하는 재사용 컴포넌트**를 찾는다.
1. `우리 자산 힌트`의 공통 컴포넌트부터 확인(Read로 props 확인).
2. `Glob`/`Grep`으로 컴포넌트 루트에서 유사 컴포넌트 탐색(이름/역할 키워드: Button, Modal, BottomSheet, Table, Card, TextField, Tab, Toast 등).
3. 각 요소를 다음 중 하나로 분류:
   - **재사용 가능**: 기존 컴포넌트 경로 + 어떤 props로 이 디자인을 재현하는지
   - **부분 매칭**: 기존 컴포넌트 + 필요한 확장/variant(무엇이 부족한지)
   - **신규 필요(갭)**: 대응 컴포넌트 없음 — 어디에 만들면 되는지(디렉터리) 제안

확인한 컴포넌트는 반드시 실제 파일을 Read해 경로·props가 진짜인지 검증한다. 추측 경로 금지.

### 채집할 화면 신호 (디자인에 명시된 것만; 추측은 "(추정)")
- 진입/이탈(CTA가 어디로), 상태 변형, 입력 필드+검증(placeholder/helper/error에서), 데이터 표시+포맷, 인터랙션, 권한·조건부 렌더링, 다국어 토큰(`{{var}}`)

### 금지
- 코드 작성/수정 (이건 이해·매핑 단계다)
- 디자인 토큰 나열로 분량 채우기
- `enableBase64Response: true`
- 검증 안 한 컴포넌트 경로 단정

### 반환 형식 (이 마크다운 그대로, 다른 산문 없이; 500단어 이내)
```
## Scout 결과: <화면명>
- nodeId: <nodeId> | 타깃: <front|admin>
- 방문 자식 nodeId 수: <N> | truncation 만난 횟수: <N>

### 화면 요약
한 문단 (이 화면이 무엇을 하는지)

### UI 요소 → 우리 컴포넌트 매핑
| 디자인 요소 | 분류 | 우리 컴포넌트(경로) | 비고/props/부족분 |
|---|---|---|---|
| 하단 CTA "참여하기" | 재사용 | {공통 CTA 버튼 경로} | variant="solid" color="primary" fullWidth |
| 입력 필드 | 부분 | {공통 입력 필드 경로} | maxLength counter variant 없음 → 확장 필요 |
| OO 카드 | 신규 | (없음) | src/components/<도메인>/ 에 신규 제안 |

### 진입 / 이탈
- 진입: ... / 이탈·CTA: ...

### 상태 변형
- default / loading / empty / error (없으면 "디자인에 없음")

### 입력
| 필드 | 타입 | 검증(출처) |

### 데이터 표시
| 필드 | 포맷 | 비고 |

### 인터랙션 · 권한 · 다국어 토큰
- ...

### 갭 (우리 코드에 없어서 새로 만들어야 할 것)
- [ ] ...

### 열린 질문 (이 화면 한정)
- [ ] ...
```
```

### 병렬 출격 규칙
- 한 응답에 Agent tool 호출 여러 개로 병렬화. 동시 출격 수 = frame 수(50 초과 시 범위 재확인).
- **Cartographer가 분석 단위를 잘 묶는 게 핵심.** 같은 화면의 변형 5개를 Scout 5개로 띄우지 말고 1개로 묶는다.

---

## 3단계 — Synthesizer (메인이 직접)

Scout가 모두 반환하면 메인이 통합한다. **이 단계에서 Figma MCP를 추가 호출하지 않는다.**

1. **공용 컴포넌트 중복 정리.** 여러 Scout가 같은 공통 컴포넌트(공통 CTA 버튼, 공용 헤더 등)를 매핑했으면 한 번만 기술하고, 화면별로는 참조만.
2. **갭 통합.** 여러 화면에서 반복 등장한 "신규 필요" 요소는 글로벌 신규 컴포넌트 후보로 끌어올린다(한 번만 만들면 되는 것).
3. **화면 간 플로우 연결.** 각 Scout의 진입/이탈을 모아 화면 전이를 잇는다.
4. **열린 질문 우선순위화** (P0 구현 막힘 / P1 결정 필요 / P2 후순위).

### 반환 산출물 형식

```markdown
# figma-depth-find 결과: <화면군 이름>

**원본 Figma**: <URL>
**타깃 프로젝트**: front | admin  (판정 근거: 한 줄 / 신뢰도)
**커버 frame**: N개 (Scout M명 병렬 탐색)

## 1. 화면 목록
| # | 화면명 | nodeId | 역할 | 변형 |

## 2. 컴포넌트 매핑 (코드 맥락)
### 재사용 가능 (그대로 씀)
| 디자인 요소 | 우리 컴포넌트(경로) | props/사용법 | 등장 화면 |
### 부분 매칭 (확장 필요)
| 요소 | 기존 컴포넌트 | 부족분 | 등장 화면 |
### 갭 — 신규 필요
| 요소 | 제안 위치 | 재사용 횟수 |

## 3. 화면별 상세
### 3.1 <화면명>
- 진입/이탈 · 상태 변형 · 입력+검증 · 데이터 표시 · 인터랙션 · 권한 · 다국어
(반복)

## 4. 사용자 플로우
화면 간 전이

## 5. 열린 질문
### P0 / P1 / P2

## 6. 상위 스킬에게 (다음 단계 제언)
- 어느 컴포넌트부터 손대면 되는지, 신규 갭 우선순위, 주의점
```

### Scout 부족 시 추가 출격
- 진입/이탈이 가리키는 화면이 카탈로그에 없음 → 누락 frame 추가 후 Scout 재출격(병렬)
- 어떤 Scout가 "truncation 0회"인데도 정보가 빈약 → 같은 nodeId에 더 깊은 탐색 지시로 재출격

추가 출격도 한 메시지에 병렬로.

---

## 절대 하지 말 것

- **메인이 `get_design_context`를 직접 호출.** Cartographer는 `get_metadata`(+판정용 스크린샷 1회)만. 깊은 탐색은 Scout 책임.
- **Scout를 직렬로 띄우기.** 한 메시지에 병렬.
- **변형(state)별로 Scout 1개씩.** 같은 화면 변형은 한 Scout가 묶어 본다.
- **검증 안 한 컴포넌트 경로를 결과에 단정.** Scout는 반드시 실제 파일 Read로 확인.
- **이 단계에서 코드 작성/수정.** 여긴 "이해·매핑"까지다. 구현은 상위 스킬 몫.
- **레거시 스타일 방식 제안.** 프로젝트가 지정한 UI 라이브러리/스타일 규칙을 따른다(커스터마이징 주석 참고).
- **base64 스크린샷 / 디자인 토큰(hex/spacing) 나열.**
- **자동 발동.** 명시 호출(상위 스킬 또는 `/figma-depth-find`) 외에는 동작하지 않는다.

---

## 호출 순서 요약

```
1. URL 파싱 → fileKey, rootNodeId   (target 넘어왔으면 채택)
2. [메인] get_metadata(root) → frame 카탈로그
3. [메인] (target 미지정 시) 스크린샷 1회 + 메타로 타깃 코드베이스 판정 + 근거 출력
4. (선택) frame 20+개면 범위 1회 확인
5. [병렬] Scout × N (한 메시지에 Agent tool N개)
     각 Scout: Figma 깊은 탐색(truncate→자식 재귀) → 우리 컴포넌트 매핑(파일 Read 검증)
6. [메인] 통합 → 누락 발견 시 추가 Scout 병렬
7. [메인] 코드 맥락 이해 문서 반환 (콘솔 + 호출자 반환)
```

<!-- 프로젝트 커스터마이징:
- 코드베이스 개수: 하나면 1-2 판정을 지우고 타깃 고정. 둘 이상이면 각 코드베이스의 성격(모바일/데스크톱 등)과 판정 신호를 조정.
- {FRONT_REPO} / {ADMIN_REPO}: repository/ 아래 실제 repo 이름.
- 우리 자산 힌트: 각 타깃의 UI 라이브러리(MUI/Chakra/…), 공통 컴포넌트 경로(CTA 버튼·입력 필드·모달/바텀시트), 컴포넌트/페이지 디렉토리 규칙, 스타일 방식(레거시로 취급할 것 포함).
- Figma MCP 서버 연결(인증)이 되어 있어야 동작한다.
-->
