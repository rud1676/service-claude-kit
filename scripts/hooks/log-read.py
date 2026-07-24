#!/usr/bin/env python3
# PostToolUse 훅: Read/Grep/Glob/Bash 호출을 세션별 파일(./claude-log/<session_id>.md)에 기록한다.
# Claude Code가 stdin으로 넘기는 JSON(session_id, cwd, tool_name, tool_input, tool_response)을 파싱한다.
# Read 는 tool_response.file 의 startLine/numLines/totalLines 로 "어디까지 봤는지" 범위를 같이 남긴다.
# Bash 는 실행한 명령어를 그대로 남겨(문제 발생 시 어떤 명령을 쳤는지 검토용), 범위 칸에 종료코드/설명을 붙인다.
import sys
import os
import json
import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session = data.get("session_id") or "unknown-session"
# cwd 는 Bash 의 cd 로 옮겨다닐 수 있어 claude-log 가 하위 폴더로 흩어진다.
# 훅 파일 위치(<root>/.claude/hooks/) 기준으로 프로젝트 루트를 고정한다 (CLAUDE_PROJECT_DIR 우선).
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
tool = data.get("tool_name") or "?"
ti = data.get("tool_input") or {}
tr = data.get("tool_response")


def file_meta(obj):
    """tool_response 안에서 Read 결과 메타(startLine/numLines/totalLines)를 찾는다."""
    if isinstance(obj, dict):
        if "totalLines" in obj or "numLines" in obj:
            return obj
        for v in obj.values():
            r = file_meta(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = file_meta(v)
            if r:
                return r
    return None


def cell(s):
    """마크다운 테이블 칸이 깨지지 않게 개행은 공백으로, `|` 는 이스케이프한다."""
    return " ".join(str(s).splitlines()).replace("|", "\\|").strip()


if tool == "Grep":
    target = ti.get("pattern", "")
    if ti.get("path"):
        target += f"  @{ti.get('path')}"
elif tool == "Glob":
    target = ti.get("pattern", "")
    if ti.get("path"):
        target += f"  @{ti.get('path')}"
elif tool == "Bash":
    target = ti.get("command", "")
else:
    target = ti.get("file_path") or ti.get("path") or ti.get("pattern") or ""

target = cell(target)

# Read 범위 계산: 전체 vs 일부(L시작~끝/전체줄). Grep/Glob 은 범위 없음.
# Bash 는 범위 칸에 설명(description)과 종료코드를 남긴다.
rng = ""
if tool == "Bash":
    parts = []
    desc = ti.get("description")
    if desc:
        parts.append(cell(desc))
    code = None
    if isinstance(tr, dict):
        for k in ("exit_code", "exitCode", "returnCode", "code"):
            if k in tr and tr[k] is not None:
                code = tr[k]
                break
        if tr.get("interrupted"):
            parts.append("중단됨")
    if code is not None:
        parts.append(f"exit {code}")
    rng = " · ".join(parts)
elif tool == "Read":
    meta = file_meta(tr)
    if meta:
        start = meta.get("startLine") or 1
        n = meta.get("numLines") or 0
        total = meta.get("totalLines")
        end = start + n - 1 if n else start
        if total is not None:
            if start <= 1 and end >= total:
                rng = f"전체 ({total}줄)"
            else:
                rng = f"L{start}~{end}/{total}줄"
        else:
            rng = f"L{start}~{end}"
    else:
        off = ti.get("offset")
        lim = ti.get("limit")
        if off or lim:
            s = off or 1
            rng = f"L{s}~{s + lim - 1}" if lim else f"L{s}~"

logdir = os.path.join(root, "claude-log")
os.makedirs(logdir, exist_ok=True)
path = os.path.join(logdir, f"{session}.md")
is_new = not os.path.exists(path)
now = datetime.datetime.now()

with open(path, "a", encoding="utf-8") as f:
    if is_new:
        f.write("# 세션 읽기 로그\n\n")
        f.write(f"- session: `{session}`\n")
        f.write(f"- started: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| 시각 | tool | 대상 | 범위 |\n| --- | --- | --- | --- |\n")
    f.write(f"| {now.strftime('%H:%M:%S')} | {tool} | {target} | {rng} |\n")
