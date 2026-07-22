#!/usr/bin/env python3
# Stop 훅: 응답 끝 시점에 Claude가 마지막 메시지에 남긴 HTML 주석 마커를 긁어
# 세션 로그(./claude-log/<session_id>.md)에 기록한다. (채팅 본문엔 안 보이게 주석으로 옴)
#
#  - 📝 요약: 헤더의 "- 요약:" 한 줄로 갱신. 마커가 없고 요약이 한 번도 없으면
#            첫 user 프롬프트로 시드. 이미 있으면 사소한 턴이 덮지 않게 유지.
#  - 📖 read: 파일 끝 "## 능동 참고 문서" 섹션에 누적(중복 줄 생략).
#
# stdin으로 들어오는 JSON: session_id, transcript_path, cwd 등.
import sys
import os
import re
import json

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

session = data.get("session_id") or "unknown-session"
# cwd 대신 훅 파일 위치 기준 프로젝트 루트로 고정 (log-read.py 와 동일, CLAUDE_PROJECT_DIR 우선).
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
transcript = data.get("transcript_path") or ""


def text_of(message):
    """assistant/user 메시지의 content에서 텍스트만 뽑아 합친다."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return "\n".join(parts)
    return ""


def user_prompt_of(message):
    """user 메시지에서 실제 사용자 발화 블록만 고른다.
    주입된 <system-reminder>/<context> 등 태그 블록은 건너뛴다."""
    content = message.get("content")
    blocks = [content] if isinstance(content, str) else (content or [])
    for b in blocks:
        if isinstance(b, str):
            t = b
        elif isinstance(b, dict) and b.get("type") == "text":
            t = b.get("text", "")
        else:
            continue
        t = t.strip()
        if t and not t.startswith("<"):
            return t
    return ""


last_assistant = ""
first_user = ""
# 토큰 누계: transcript 전체를 매 Stop마다 다시 훑어 재계산하므로 항상 세션 총합이 된다.
# (메인 transcript의 assistant 메시지 usage만 합산. 서브에이전트는 별도 파일이라 제외.)
tok = {"in": 0, "out": 0, "cache_w": 0, "cache_r": 0}

if transcript and os.path.exists(transcript):
    with open(transcript, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") != "user" and o.get("type") != "assistant":
                continue
            msg = o.get("message")
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            if role == "assistant":
                u = msg.get("usage")
                if isinstance(u, dict):
                    tok["in"] += u.get("input_tokens", 0) or 0
                    tok["out"] += u.get("output_tokens", 0) or 0
                    tok["cache_w"] += u.get("cache_creation_input_tokens", 0) or 0
                    tok["cache_r"] += u.get("cache_read_input_tokens", 0) or 0
                t = text_of(msg).strip()
                if t:
                    last_assistant = t
            elif role == "user":
                # 도구 결과(toolUseResult)는 진짜 사용자 발화가 아님 → 첫 프롬프트만 잡는다
                if first_user or o.get("toolUseResult") is not None:
                    continue
                t = user_prompt_of(msg)
                if t:
                    first_user = t


# 이번 턴에서 Claude가 직접 남긴 마커를 긁는다. 마커는 렌더링 안 되는 HTML 주석
# 형태(<!-- 📝 요약: ... -->, <!-- 📖 read: ... -->)로 오므로 꼬리(-->)를 떼어낸다.
def strip_marker(s):
    return re.sub(r"-->\s*$", "", s).strip()


def human(n):
    """토큰 수를 K/M 단위로 짧게."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


# --- 탐색 집계용 헬퍼 -------------------------------------------------------
# log-read 훅은 메인세션 Read/Grep/Glob 만 표에 남긴다. 하지만 실제 탐색의 상당수는
# (a) 메인세션의 Bash grep/find/ls 등, (b) 서브에이전트(별도 transcript) 안에서 일어나
# 그 표엔 안 잡힌다. 여기서 메인 transcript + <session>/subagents/*.jsonl 을 훑어
# "진짜 탐색량"을 매 Stop마다 재집계해 로그 파일 끝 섹션으로 덮어쓴다(누적 아님).
EXPLORE_BASH = {
    "grep", "rg", "find", "fd", "ls", "cat", "head", "tail", "glob", "awk", "sed", "wc",
}


def _bash_first_token(cmd):
    cmd = (cmd or "").strip()
    return cmd.split()[0] if cmd else ""


def count_explore(jsonl_path):
    """한 transcript(.jsonl)에서 탐색 도구 사용 횟수를 센다."""
    c = {"Read": 0, "Grep": 0, "Glob": 0, "BashX": 0, "Agent": 0}
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                cont = msg.get("content")
                if not isinstance(cont, list):
                    continue
                for x in cont:
                    if not (isinstance(x, dict) and x.get("type") == "tool_use"):
                        continue
                    nm = x.get("name")
                    if nm in ("Read", "Grep", "Glob"):
                        c[nm] += 1
                    elif nm == "Agent":
                        c["Agent"] += 1
                    elif nm == "Bash":
                        cmd = (x.get("input") or {}).get("command", "")
                        if _bash_first_token(cmd) in EXPLORE_BASH:
                            c["BashX"] += 1
    except Exception:
        pass
    return c


# 토큰 한 줄: 출력·입력(비캐시)·캐시생성·캐시읽기 + 총합.
# 총합은 모든 API 호출이 청구 기준으로 처리한 토큰 누계(턴마다 컨텍스트 재투입분 포함).
token_line = ""
tok_total = tok["in"] + tok["out"] + tok["cache_w"] + tok["cache_r"]
if tok_total > 0:
    token_line = (
        f"- 토큰: 출력 {human(tok['out'])} · 입력 {human(tok['in'])} · "
        f"캐시생성 {human(tok['cache_w'])} · 캐시읽기 {human(tok['cache_r'])} "
        f"(총 {human(tok_total)})\n"
    )


marker_summary = ""
read_citations = []
if last_assistant:
    m = re.search(r"📝\s*요약\s*[:：]\s*(.+)", last_assistant)
    if m:
        marker_summary = strip_marker(m.group(1))
    for rm in re.findall(r"📖\s*read\s*[:：]\s*(.+)", last_assistant):
        cit = strip_marker(rm)
        if cit:
            read_citations.append(cit)

logdir = os.path.join(root, "claude-log")
path = os.path.join(logdir, f"{session}.md")

# 기존 로그 파일/요약 유무 파악
lines = []
has_summary = False
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    has_summary = any(ln.startswith("- 요약:") for ln in lines)


def strip_section(lines, header_prefix):
    """'## <header>' 로 시작하는 섹션을 다음 '## ' 또는 EOF까지 제거한다(재생성용)."""
    out = []
    skip = False
    for ln in lines:
        if ln.startswith(header_prefix):
            skip = True
            continue
        if skip and ln.startswith("## "):
            skip = False
        if not skip:
            out.append(ln)
    return out


# 이전 턴이 남긴 탐색 집계 섹션/헤더 줄을 먼저 걷어낸다. 그래야 '능동 참고 문서'가
# 그 사이에 끼지 않고, 탐색 집계는 항상 파일 맨 끝에 새로 붙는다(항상 현재 총합).
lines = strip_section(lines, "## 탐색 집계")
lines = [ln for ln in lines if not ln.startswith("- 탐색:")]

# 탐색 집계: 메인 transcript + <session>/subagents/*.jsonl 를 훑어 재계산.
explore_header = ""
explore_section = []
try:
    if transcript and os.path.exists(transcript):
        main_c = count_explore(transcript)
        subdir = os.path.join(os.path.dirname(transcript), session, "subagents")
        subs = []  # (표시라벨, 타입, counts)
        if os.path.isdir(subdir):
            import glob as _glob

            for sf in sorted(_glob.glob(os.path.join(subdir, "*.jsonl"))):
                sc = count_explore(sf)
                if sc["Read"] + sc["Grep"] + sc["Glob"] + sc["BashX"] == 0:
                    continue
                atype, desc = "?", ""
                meta_fp = sf[:-6] + ".meta.json"
                try:
                    with open(meta_fp, "r", encoding="utf-8") as mf:
                        md = json.load(mf)
                    atype = md.get("agentType") or "?"
                    desc = (md.get("description") or "").strip()
                except Exception:
                    pass
                subs.append((desc, atype, sc))

        def ex(c):
            return c["Read"] + c["Grep"] + c["Glob"] + c["BashX"]

        main_ex = ex(main_c)
        sub_ex = sum(ex(c) for _, _, c in subs)
        total_ex = main_ex + sub_ex
        if total_ex > 0:
            share = (100 * sub_ex // total_ex) if total_ex else 0
            explore_header = (
                f"- 탐색: 메인 {main_ex} · 서브에이전트 {sub_ex}"
                f"(에이전트 {len(subs)}개) · 전체 {total_ex} (서브 {share}%)\n"
            )
            explore_section = [
                "\n## 탐색 집계 (메인+서브에이전트, 매 턴 갱신)\n",
                f"- 메인세션: Read {main_c['Read']} · Grep {main_c['Grep']} · "
                f"Glob {main_c['Glob']} · Bash탐색 {main_c['BashX']} "
                f"(Agent 스폰 {main_c['Agent']})\n",
                f"- 서브에이전트 {len(subs)}개 합: Read {sum(c['Read'] for _,_,c in subs)} · "
                f"Grep {sum(c['Grep'] for _,_,c in subs)} · Glob {sum(c['Glob'] for _,_,c in subs)} · "
                f"Bash탐색 {sum(c['BashX'] for _,_,c in subs)}\n",
                f"- 전체 탐색 op: {total_ex} (서브에이전트 비중 {share}%)\n",
            ]
            if subs:
                explore_section.append(
                    "\n| # | 서브에이전트 | 타입 | Read | Grep | Glob | Bash탐색 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- |\n"
                )
                for i, (desc, atype, c) in enumerate(subs, 1):
                    d = (desc or "-").replace("|", "/")[:60]
                    explore_section.append(
                        f"| {i} | {d} | {atype} | {c['Read']} | {c['Grep']} | "
                        f"{c['Glob']} | {c['BashX']} |\n"
                    )
except Exception:
    explore_header = ""
    explore_section = []

# 요약 결정:
#  - 마커가 있으면 그걸로 갱신
#  - 마커가 없는데 아직 요약이 한 번도 없으면 첫 프롬프트로 시드(최초 1회)
#  - 마커가 없고 이미 요약이 있으면 → 손대지 않음 (사소한 턴이 기존 요약을 덮지 않게)
summary = ""
if marker_summary:
    summary = marker_summary
elif not has_summary and first_user:
    for ln in first_user.splitlines():
        ln = ln.strip()
        if ln:
            summary = ln
            break
if summary:
    summary = " ".join(summary.split())
    if len(summary) > 200:
        summary = summary[:197] + "…"

# 남길 게 아무것도 없으면 종료
if not summary and not read_citations and not token_line and not explore_section:
    sys.exit(0)

# 파일이 없으면 최소 헤더를 메모리에 만든다
if not lines:
    lines = ["# 세션 읽기 로그\n", "\n", f"- session: `{session}`\n"]

# 요약: 헤더의 "- 요약:" 교체, 없으면 session/started 뒤에 삽입
if summary:
    summary_line = f"- 요약: {summary}\n"
    replaced = False
    for i, ln in enumerate(lines):
        if ln.startswith("- 요약:"):
            lines[i] = summary_line
            replaced = True
            break
    if not replaced:
        insert_at = len(lines)
        for i, ln in enumerate(lines):
            if ln.startswith("- started:") or ln.startswith("- session:"):
                insert_at = i + 1
        lines.insert(insert_at, summary_line)

# 토큰: 헤더의 "- 토큰:" 교체, 없으면 요약/started/session 뒤에 삽입
if token_line:
    replaced = False
    for i, ln in enumerate(lines):
        if ln.startswith("- 토큰:"):
            lines[i] = token_line
            replaced = True
            break
    if not replaced:
        insert_at = len(lines)
        for i, ln in enumerate(lines):
            if (
                ln.startswith("- 요약:")
                or ln.startswith("- started:")
                or ln.startswith("- session:")
            ):
                insert_at = i + 1
        lines.insert(insert_at, token_line)

# 탐색 한 줄: 토큰 줄(없으면 요약/started/session) 뒤에 삽입
if explore_header:
    insert_at = len(lines)
    for i, ln in enumerate(lines):
        if (
            ln.startswith("- 토큰:")
            or ln.startswith("- 요약:")
            or ln.startswith("- started:")
            or ln.startswith("- session:")
        ):
            insert_at = i + 1
    lines.insert(insert_at, explore_header)

# 능동 참고 문서: 파일 끝의 "## 능동 참고 문서" 섹션에 누적(중복 줄은 생략)
if read_citations:
    existing = set(ln.strip() for ln in lines)
    if not any(ln.startswith("## 능동 참고 문서") for ln in lines):
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append("\n## 능동 참고 문서\n")
    for cit in read_citations:
        entry = f"- 📖 read: {cit}\n"
        if entry.strip() not in existing:
            lines.append(entry)
            existing.add(entry.strip())

# 탐색 집계 섹션: 항상 파일 맨 끝에 새로 붙인다(앞서 이전 섹션은 걷어냄 = 덮어쓰기).
if explore_section:
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.extend(explore_section)

os.makedirs(logdir, exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
