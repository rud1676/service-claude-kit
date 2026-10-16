#!/usr/bin/env bash
# 사용: render.sh <input.drawio> [output.png] [scale=1.5]
# draw.io 데스크톱이 없으면 ~/.cache/drawio 에 AppImage 를 받아 풀고, xvfb 로 헤드리스 렌더링한다.
set -euo pipefail

IN="$1"
OUT="${2:-${IN%.drawio}.png}"
SCALE="${3:-1.5}"
VER="${DRAWIO_VERSION:-32.4.1}"
CACHE="${HOME}/.cache/drawio"
BIN="${CACHE}/squashfs-root/drawio"

if command -v drawio >/dev/null 2>&1; then
  BIN="$(command -v drawio)"
elif [ ! -x "$BIN" ]; then
  echo "draw.io ${VER} 다운로드 → ${CACHE}" >&2
  mkdir -p "$CACHE"
  curl -fsSL -o "${CACHE}/drawio.AppImage" \
    "https://github.com/jgraph/drawio-desktop/releases/download/v${VER}/drawio-x86_64-${VER}.AppImage"
  chmod +x "${CACHE}/drawio.AppImage"
  (cd "$CACHE" && ./drawio.AppImage --appimage-extract >/dev/null)
fi

command -v xvfb-run >/dev/null || { echo "xvfb-run 필요: sudo apt install xvfb" >&2; exit 1; }
fc-list : family | grep -i "Noto Sans CJK" >/dev/null || echo "경고: Noto Sans CJK 폰트 없음 → 한글 깨질 수 있음 (sudo apt install fonts-noto-cjk)" >&2

xvfb-run -a "$BIN" --no-sandbox -x -f png -s "$SCALE" -o "$OUT" "$IN" 2>&1 \
  | grep -v -i -E "dbus|gpu|vaapi|libva|ozone" || true
[ -s "$OUT" ] && echo "rendered: $OUT" || { echo "렌더 실패: $OUT 없음" >&2; exit 1; }
