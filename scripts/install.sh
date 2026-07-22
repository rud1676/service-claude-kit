#!/usr/bin/env bash
# service-claude-kit 설치 스크립트
#
# 최상위 skills/ 의 스킬, base/agents 의 서브에이전트, scripts/hooks 의 훅을
# 대상 프로젝트의 .claude/ 로 "복사"한다.
# 복사이므로, 프로젝트마다 독립적으로 커스터마이징해도 원본 repo에 영향이 없다.
#
# 설치 중 프로젝트 환경을 물어보고(프로젝트 관리 툴 / 작업 환경),
# 답에 맞는 스킬만·맞는 모양으로 세팅한다. (구조 결정만 자동화 —
# cloudId·DDNS 같은 인스턴스 비밀값은 각 파일에서 직접 채운다.)
#
# 인자로 프로젝트 이름(또는 상대/절대 경로)을 받는다.
# 상대 경로는 "이 스크립트를 실행한 현재 위치" 기준으로 해석되고,
# 해당 폴더가 없으면 새로 만든다.
#
# 사용법(repo 루트에서 실행):
#   ./scripts/install.sh myproject          # ./myproject 를 만들고(없으면) 베이스 설치(질문 포함)
#   ./scripts/install.sh myproject --force  # 이미 있는 파일도 덮어씀
#   ./scripts/install.sh /abs/path/proj     # 절대 경로도 그대로 동작
#
# 비대화(스크립트/CI) 환경에서는 질문을 건너뛰고 기본값(jira + remote,
# 즉 아무것도 제거하지 않음)으로 설치한다. 환경변수로 지정할 수도 있다:
#   SCK_PMTOOL=jira|linear|none  SCK_ENV=remote|local  ./scripts/install.sh myproject
set -euo pipefail

# 이 스크립트는 scripts/ 안에 있으므로, repo 루트는 한 단계 위다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$REPO_ROOT/base"        # agents · settings.hooks.json · CLAUDE.block.md
SKILLS_DIR="$REPO_ROOT/skills"    # 최상위 스킬 정본(skills.sh 발견 위치)
HOOKS_DIR="$SCRIPT_DIR/hooks"     # scripts/hooks

NAME="${1:-}"
FORCE="${2:-}"

if [[ -z "$NAME" ]]; then
  echo "사용법: $0 <프로젝트이름|경로> [--force]" >&2
  exit 1
fi

# 상대 경로는 현재 작업 디렉토리 기준, 없으면 생성한다.
TARGET="$NAME"
if [[ ! -d "$TARGET" ]]; then
  echo "프로젝트 폴더 생성: $TARGET"
  mkdir -p "$TARGET"
fi

DEST="$TARGET/.claude"
mkdir -p "$DEST/agents" "$DEST/skills" "$DEST/hooks"

# --- 프로젝트 환경 질문 (대화형일 때만) ---
# 답에 따라 어떤 스킬을 깔고 worktree를 어떤 모양으로 둘지 결정한다.
PMTOOL="${SCK_PMTOOL:-}"
WORKENV="${SCK_ENV:-}"

if [[ -t 0 ]]; then
  if [[ -z "$PMTOOL" ]]; then
    echo
    echo "프로젝트 관리 툴을 선택하세요:"
    echo "  1) Jira        — jiraticket 스킬 포함"
    echo "  2) Linear      — (준비 중) 관련 스킬은 추후 제공"
    echo "  3) 없음/기타    — 티켓 연동 스킬 없이 설치"
    read -r -p "선택 [1]: " _ans
    case "$_ans" in
      2) PMTOOL=linear;;
      3) PMTOOL=none;;
      *) PMTOOL=jira;;
    esac
  fi
  if [[ -z "$WORKENV" ]]; then
    echo
    echo "작업 환경을 선택하세요:"
    echo "  1) 원격 서버   — 접속 링크를 내부/외부 2가지로 안내 (worktree)"
    echo "  2) 로컬        — localhost 링크만"
    read -r -p "선택 [1]: " _ans
    case "$_ans" in
      2) WORKENV=local;;
      *) WORKENV=remote;;
    esac
  fi
fi

# 비대화 or 미지정 시 기본값: 아무것도 제거하지 않는 쪽
PMTOOL="${PMTOOL:-jira}"
WORKENV="${WORKENV:-remote}"
echo
echo "설치 설정 → 프로젝트 관리 툴: $PMTOOL / 작업 환경: $WORKENV"

# rsync 옵션: --force면 덮어쓰기, 아니면 기존 파일 보존(--ignore-existing)
RSYNC_OPTS=(-a)
if [[ "$FORCE" != "--force" ]]; then
  RSYNC_OPTS+=(--ignore-existing)
fi

copied=0
if [[ -d "$BASE_DIR/agents" ]]; then
  rsync "${RSYNC_OPTS[@]}" "$BASE_DIR/agents/" "$DEST/agents/"
  copied=1
fi
if [[ -d "$SKILLS_DIR" ]]; then
  rsync "${RSYNC_OPTS[@]}" "$SKILLS_DIR/" "$DEST/skills/"
  copied=1
fi
if [[ -d "$HOOKS_DIR" ]]; then
  rsync "${RSYNC_OPTS[@]}" "$HOOKS_DIR/" "$DEST/hooks/"
  chmod +x "$DEST/hooks/"*.py 2>/dev/null || true
  copied=1
fi

# --- 답에 맞게 스킬 취사 (구조 결정 자동화) ---
# 프로젝트 관리 툴: Jira 가 아니면 Jira 전용 jiraticket 스킬은 빼둔다.
case "$PMTOOL" in
  jira) : ;;  # jiraticket 유지
  linear)
    rm -rf "$DEST/skills/jiraticket"
    echo "ℹ️  Linear 티켓 스킬은 준비 중입니다 — jiraticket(Jira 전용)은 설치하지 않았습니다."
    ;;
  *)
    rm -rf "$DEST/skills/jiraticket"
    echo "ℹ️  프로젝트 관리 툴 미선택 — jiraticket 스킬은 설치하지 않았습니다."
    ;;
esac

# 작업 환경: worktree 스킬에서 원격 전용 안내 블록을 취사한다.
WT="$DEST/skills/worktree/SKILL.md"
if [[ -f "$WT" ]]; then
  tmp="$(mktemp)"
  if [[ "$WORKENV" == "local" ]]; then
    # 로컬: SCK:REMOTE-ONLY 마커와 그 사이 내용을 통째로 제거
    awk '
      /<!-- SCK:REMOTE-ONLY:START -->/ { skip=1; next }
      /<!-- SCK:REMOTE-ONLY:END -->/   { skip=0; next }
      !skip { print }
    ' "$WT" > "$tmp" && mv "$tmp" "$WT"
    echo "ℹ️  로컬 환경 — worktree 스킬의 원격 접속(내부/외부 링크) 안내를 제거했습니다."
  else
    # 원격: 마커 주석 줄만 제거하고 내용은 유지
    grep -v 'SCK:REMOTE-ONLY' "$WT" > "$tmp" && mv "$tmp" "$WT"
  fi
fi

# --- settings.json 훅 배선 안전 병합 (python3, 멱등) ---
# 기존 settings.json 의 permissions/env 등을 보존하고 hooks 만 union 병합한다.
# command 문자열(훅 파일명 포함)로 중복을 판단해 재실행해도 안 겹친다.
HOOKS_JSON="$BASE_DIR/settings.hooks.json"
if [[ -f "$HOOKS_JSON" ]] && command -v python3 >/dev/null 2>&1; then
  python3 - "$DEST/settings.json" "$HOOKS_JSON" <<'PY'
import json, os, sys
settings_path, hooks_path = sys.argv[1], sys.argv[2]
add = json.load(open(hooks_path, encoding="utf-8")).get("hooks", {})
cur = {}
if os.path.exists(settings_path):
    try:
        cur = json.load(open(settings_path, encoding="utf-8"))
    except Exception:
        cur = {}
cur.setdefault("hooks", {})

def cmds(entry):
    return [h.get("command", "") for h in entry.get("hooks", [])]

changed = False
for event, entries in add.items():
    existing = cur["hooks"].setdefault(event, [])
    have = {c for e in existing for c in cmds(e)}
    for e in entries:
        if any(c in have for c in cmds(e)):
            continue  # 이미 배선됨
        existing.append(e)
        changed = True
if changed or not os.path.exists(settings_path):
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("설치됨" if changed else "확인됨")
PY
  echo "settings.json 훅 배선 병합 → $DEST/settings.json"
fi

# --- CLAUDE.md 관리 블록 주입 (안전 병합, 멱등) ---
# CLAUDE.md는 기존 규칙을 담고 있을 수 있으므로 절대 통째로 덮지 않는다.
# 마커로 감싼 블록만 삽입/갱신한다. (파일이 담고 있는 블록에 마커가 포함돼 있음)
CLAUDE_MD="$TARGET/CLAUDE.md"

inject_block() {
  # inject_block <claude_md> <begin_marker> <end_marker> <block_file> <label>
  local claude_md="$1" begin="$2" end="$3" block_file="$4" label="$5" tmp
  if [[ ! -f "$claude_md" ]]; then
    { printf '# 작업 규칙\n\n'; cat "$block_file"; } > "$claude_md"
    echo "CLAUDE.md 생성 ($label) → $claude_md"
  elif grep -qF "$begin" "$claude_md"; then
    tmp="$(mktemp)"
    awk -v bf="$block_file" -v b="$begin" -v e="$end" '
      BEGIN { while ((getline l < bf) > 0) blk = blk l "\n" }
      index($0,b){ skip=1; printf "%s", blk; next }
      index($0,e){ skip=0; next }
      !skip { print }
    ' "$claude_md" > "$tmp" && mv "$tmp" "$claude_md"
    echo "CLAUDE.md '$label' 블록 갱신 → $claude_md"
  else
    { printf '\n'; cat "$block_file"; } >> "$claude_md"
    echo "CLAUDE.md '$label' 블록 추가(기존 내용 보존) → $claude_md"
  fi
}

BLOCK_FILE="$BASE_DIR/CLAUDE.block.md"
if [[ -f "$BLOCK_FILE" ]]; then
  inject_block "$CLAUDE_MD" \
    "<!-- BEGIN service-kit:context-mgmt -->" \
    "<!-- END service-kit:context-mgmt -->" \
    "$BLOCK_FILE" "context-mgmt"
fi

# 설치 시 선택한 값을 항상-온 설정 블록으로 기록한다(다음 세션 에이전트가 읽음).
CFG_TMP="$(mktemp)"
cat > "$CFG_TMP" <<EOF
<!-- BEGIN service-kit:config -->
## 프로젝트 설정 (service-claude-kit)

- 프로젝트 관리 툴: ${PMTOOL}
- 작업 환경: ${WORKENV}

(설치 시 선택된 값. install.sh 재실행 시 갱신된다. cloudId·프로젝트키·DDNS 호스트 등
 인스턴스 비밀값은 각 스킬 파일의 "프로젝트 커스터마이징" 주석대로 직접 채운다.)
<!-- END service-kit:config -->
EOF
inject_block "$CLAUDE_MD" \
  "<!-- BEGIN service-kit:config -->" \
  "<!-- END service-kit:config -->" \
  "$CFG_TMP" "config"
rm -f "$CFG_TMP"

# --- 워크스페이스 폴더 스캐폴딩 (없을 때만 생성. 워크스페이스 자체는 git 아님) ---
if [[ ! -f "$TARGET/wiki/README.md" ]]; then
  mkdir -p "$TARGET/wiki"
  cat > "$TARGET/wiki/README.md" <<'EOF'
# `wiki/` — 프로젝트 지식 위키 (인덱스)

`wiki/{도메인}/*.md` 는 코드만 봐선 알 수 없는 프로젝트 지식(분석·결정·기획·동작원리)을 담는다.
이 문서는 그 목차이자 진입점이다. (관리 규칙은 프로젝트 `CLAUDE.md`, 문서 생성은 `explain` 스킬)

## 도메인 목차

| 도메인 | 설명 |
|---|---|
| _(아직 없음)_ | 새 도메인을 만들면 여기에 한 줄 추가 |
EOF
  echo "wiki 시드 생성 → $TARGET/wiki/README.md"
fi
if [[ ! -f "$TARGET/study/README.md" ]]; then
  mkdir -p "$TARGET/study"
  cat > "$TARGET/study/README.md" <<'EOF'
# `study/` — 내 학습 기록

"이 함수/개념 어떻게 동작해?"처럼 내가 배우려고 물어본 것을 담는 곳.
프로젝트 진실인 `wiki/`와 목적이 달라 섞지 않는다(서로 승격 안 함).
EOF
  echo "study 시드 생성 → $TARGET/study/README.md"
fi
if [[ ! -f "$TARGET/decision-log/README.md" ]]; then
  mkdir -p "$TARGET/decision-log"
  cat > "$TARGET/decision-log/README.md" <<'EOF'
# `decision-log/` — 결정 아카이브

판단이 갈렸거나 대안을 버린 결정을 시점별로 남기는 append-only 아카이브.
"무엇을 택했고 어떤 대안을 왜 버렸나 / 아직 미결이면 왜 미결인가"가 핵심.
상태(미결/확정)를 표기하고 `wiki/` 문서와 상호 링크한다.

파일명: `<YYYY-MM-DD>-<주제>.md` · 포맷과 작성 시점은 `explain` 스킬 참고.
EOF
  echo "decision-log 시드 생성 → $TARGET/decision-log/README.md"
fi
if [[ ! -f "$TARGET/repository/README.md" ]]; then
  mkdir -p "$TARGET/repository"
  cat > "$TARGET/repository/README.md" <<'EOF'
# `repository/` — 실제 코드 repo

front·server 등 실제 git repo를 여기에 clone 한다. 각각 독립 git repo다.
(워크스페이스 자체는 git이 아님)

- 브랜치·커밋은 반드시 해당 repo 폴더 안에서 실행한다.
- 병렬 작업 시 워크트리: `repository/{repo}-worktrees/{작업번호}/` (worktree 스킬 참고)
EOF
  echo "repository 시드 생성 → $TARGET/repository/README.md"
fi
if [[ ! -f "$TARGET/plan/README.md" ]]; then
  mkdir -p "$TARGET/plan"
  cat > "$TARGET/plan/README.md" <<'EOF'
# `plan/` — 임시 작업 맥락

큰 작업의 임시 계획·맥락을 둔다. 작업이 끝나면 삭제한다. (영구 지식은 `wiki/`)
EOF
  echo "plan 시드 생성 → $TARGET/plan/README.md"
fi
if [[ ! -f "$TARGET/claude-log/README.md" ]]; then
  mkdir -p "$TARGET/claude-log"
  cat > "$TARGET/claude-log/README.md" <<'EOF'
# `claude-log/` — 세션 추적 로그

`.claude/hooks/` 의 훅이 세션마다 `<session_id>.md`를 자동 생성·갱신한다.
사람이 직접 쓰는 곳이 아니다. (읽기 로그·세션 요약·능동 참고 문서·토큰 사용량)
EOF
  echo "claude-log 시드 생성 → $TARGET/claude-log/README.md"
fi

if [[ "$copied" -eq 1 ]]; then
  echo
  echo "설치 완료 → $DEST"
  echo
  echo "설치된 서브에이전트:"
  ls -1 "$DEST/agents" 2>/dev/null | sed 's/^/  - /' || true
  echo "설치된 스킬:"
  ls -1 "$DEST/skills" 2>/dev/null | sed 's/^/  - /' || true
  echo "설치된 훅:"
  ls -1 "$DEST/hooks" 2>/dev/null | sed 's/^/  - /' || true
  echo
  echo "생성/갱신: CLAUDE.md(context-mgmt + config 블록) · settings.json(훅 배선)"
  echo "워크스페이스 폴더: wiki/ study/ decision-log/ repository/ plan/ claude-log/"
  echo "(이 워크스페이스 자체는 git 저장소가 아닙니다. 코드 git은 repository/ 안에서.)"
  echo "이제 각 스킬 파일의 '프로젝트 커스터마이징' 주석(cloudId·프로젝트키·DDNS·포트 등)을 채우세요."
  if [[ "$FORCE" != "--force" ]]; then
    echo "(이미 존재하던 파일은 보존했습니다. 덮어쓰려면 --force)"
  fi
else
  echo "복사할 base/agents 또는 skills가 없습니다." >&2
  exit 1
fi
