# 기획 작업 공간

이슈 하나를 놓고 **사람 ↔ Claude가 대화로 기획**하는 곳이다. 기획은 글이 아니라 **화면으로** 한다.

> 한 문장: **실제 서비스 화면 위에 새 기능을 얹은 목업(HTML)을 만들고, 그 캡처를 박은 md로 정리한다.**

절차·가이드라인의 정본은 `make-prd` 스킬(`.claude/skills/make-prd/SKILL.md`)이다. 이 문서는 폴더 안내다.

## 구조

```
<기획 폴더>/
  README.md                 이 안내
  prd/<slug>/               기획 1건 = 폴더 1개
    prd.md                  기획서 — 캡처가 박힌 md (GitHub·Obsidian에서 그대로 읽힌다)
    mockup.html             실제 화면을 본뜬 목업 — 상태(state)별로 전환
    assets/
      asis*.html|css|png    개발 서버 스냅샷 (snapshot.mjs)
      NN-<state>.png        목업 상태별 캡처 (capture.mjs) → prd.md에 박힌다
  plan/<slug>-plan.md       합의된 PRD를 "어떻게 만들까"로 푼 구현 계획 (make-plan 형식)
  _kit/                     도구 — 스냅샷·캡처·목업 키트·뷰어·PRD 템플릿
```

## 상태 (`status`)

| 상태 | 표시 | 뜻 |
|---|---|---|
| `draft` | 📝 | 대화 중. 목업·결정이 계속 바뀐다 |
| `agreed` | 🤝 | 합의 끝. plan을 쓸 수 있다 |
| `planned` | 📐 | `plan/`이 생겼다. 구현은 아직 시작 전 |
| `building` | 🚧 | STEP 하나라도 커밋됐다 |
| `done` | ✅ | 모든 STEP이 운영까지 반영됐다 |
| `dropped` | 🗑 | 접었다 — 지우지 않고 왜 접었는지 한 줄 남긴다 |

## 보기

```bash
cd <기획 폴더>
python3 -m http.server 3000 --bind 0.0.0.0
```

- 목록: `http://localhost:3000/_kit/viewer.html`
- PRD: `http://localhost:3000/_kit/viewer.html?prd=<slug>` — 왼쪽 prd.md, 오른쪽 살아있는 목업(상태·PC/모바일 전환)

## 비밀

로그인 세션 파일(`*.storage.json`)·비밀번호는 커밋하지 않는다.
