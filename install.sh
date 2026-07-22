#!/usr/bin/env bash
# 프로젝트 스타터 킷 설치 스크립트
#
# 이 repo의 base/ 아래 서브에이전트(agents)와 스킬(skills)을
# 대상 프로젝트의 .claude/ 로 "복사"한다.
# 복사이므로, 프로젝트마다 독립적으로 커스터마이징해도 원본 repo에 영향이 없다.
#
# 사용법:
#   ./install.sh /path/to/project        # 대상 프로젝트에 베이스 설치
#   ./install.sh /path/to/project --force # 이미 있는 파일도 덮어씀
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR/base"

TARGET="${1:-}"
FORCE="${2:-}"

if [[ -z "$TARGET" ]]; then
  echo "사용법: $0 <프로젝트경로> [--force]" >&2
  exit 1
fi

if [[ ! -d "$TARGET" ]]; then
  echo "에러: 대상 디렉토리가 없습니다: $TARGET" >&2
  exit 1
fi

DEST="$TARGET/.claude"
mkdir -p "$DEST/agents" "$DEST/skills"

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
if [[ -d "$BASE_DIR/skills" ]]; then
  rsync "${RSYNC_OPTS[@]}" "$BASE_DIR/skills/" "$DEST/skills/"
  copied=1
fi

if [[ "$copied" -eq 1 ]]; then
  echo "설치 완료 → $DEST"
  echo
  echo "설치된 서브에이전트:"
  ls -1 "$DEST/agents" 2>/dev/null | sed 's/^/  - /' || true
  echo "설치된 스킬:"
  ls -1 "$DEST/skills" 2>/dev/null | sed 's/^/  - /' || true
  echo
  echo "이제 대상 프로젝트에서 각 파일의 '프로젝트 커스터마이징' 부분을 채우세요."
  if [[ "$FORCE" != "--force" ]]; then
    echo "(이미 존재하던 파일은 보존했습니다. 덮어쓰려면 --force)"
  fi
else
  echo "복사할 base/agents 또는 base/skills가 없습니다." >&2
  exit 1
fi
