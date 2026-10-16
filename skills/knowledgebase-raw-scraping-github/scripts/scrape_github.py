#!/usr/bin/env python3
"""GitHub의 '사람이 쓴 글'을 지식 베이스의 raw/github/ 에 추가만 한다.

설계 불변식 세 개:
  1) 추가만   — 이미 있는 파일 본문은 한 글자도 바꾸지 않는다. 새 것은 끝에 덧붙인다.
                (페이지의 [src:n] 인용이 계속 참이어야 하므로)
  2) 재현 가능 — 두 번 돌려도 결과가 같다 (워터마크 + 본문 해시)
  3) 조용한 성공 금지 — 건너뛴 것·못 읽은 것을 전부 보고한다

판단은 하지 않는다. 페이지를 만들지 않는다. 그건 호출한 에이전트의 일.

필요: gh CLI (인증됨), python3 (표준 라이브러리만)
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

KINDS = ("issues", "pulls", "commits", "releases")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


# ── 유틸 ────────────────────────────────────────────────────────────────

def gh(args, repo=None):
    """gh api/CLI 호출. 실패는 (None, stderr) 로 돌려주고 죽지 않는다."""
    cmd = ["gh"] + args + (["--repo", repo] if repo else [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, p.stderr.strip()
    return p.stdout, None


def local_iso(utc_str):
    """GitHub 의 UTC 문자열을 현지 시각 ISO 로. 안 하면 새벽 수집이 전날로 찍힌다."""
    if not utc_str:
        return ""
    try:
        dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone().isoformat(timespec="seconds")
    except ValueError:
        return utc_str


def local_date(utc_str):
    iso = local_iso(utc_str)
    return iso[:10] if iso else ""


def mask(text, enabled):
    if not text:
        return ""
    return EMAIL_RE.sub("[마스킹:이메일]", text) if enabled else text


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(repo):
    return repo.split("/")[-1]


# ── 파일 쓰기 (추가만) ──────────────────────────────────────────────────

def write_raw(path, header, blocks, meta, today, report):
    """없으면 header+blocks 로 새로 쓰고, 있으면 '새 블록만' 끝에 덧붙인다."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    meta_path = path + ".meta.json"
    old_meta = {}
    if os.path.exists(meta_path):
        try:
            old_meta = json.load(open(meta_path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            old_meta = {}

    seen = set(old_meta.get("block_sha", []))
    fresh = [(h, b) for h, b in blocks if h not in seen]

    if not os.path.exists(path):
        body = header + "\n" + "\n".join(b for _, b in fresh)
        open(path, "w", encoding="utf-8").write(body)
        report["written"].append(path)
    elif fresh:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n## 수집 {today}\n\n" + "\n".join(b for _, b in fresh))
        report["appended"].append(f"{path} (+{len(fresh)})")
    else:
        report["skipped"].append(f"{path} (변경 없음)")
        return

    meta["block_sha"] = sorted(seen | {h for h, _ in fresh})
    meta["appended"] = sorted(set(old_meta.get("appended", [])) | {today})
    if "retrieved_first" not in old_meta:
        meta["retrieved_first"] = meta["retrieved"]
    else:
        meta["retrieved_first"] = old_meta["retrieved_first"]
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def base_meta(source_id, url, do_mask):
    return {
        "source": "github",
        "source_id": source_id,
        "url": url,
        "retrieved": datetime.now().astimezone().isoformat(timespec="seconds"),
        "masked": ["email"] if do_mask else [],
    }


# ── 종류별 수집 ─────────────────────────────────────────────────────────

def scrape_threads(repo, kind, since, limit, do_mask, kb, today, report):
    """이슈·PR — 본문 + 코멘트(+PR 리뷰). 코멘트가 늘면 그만큼만 덧붙는다."""
    endpoint = "issues" if kind == "issues" else "pulls"
    out, err = gh(["api", "-X", "GET", f"repos/{repo}/{endpoint}",
                   "-f", "state=all", "-f", "sort=updated", "-f", "direction=desc",
                   "-F", f"per_page={min(limit, 100)}", "--paginate"])
    if err:
        report["failed"].append(f"{repo} {kind}: {err.splitlines()[0] if err else '?'}")
        return
    items = json.loads(out) if out else []

    newest = since
    for it in items[:limit]:
        # /issues 는 PR 도 함께 준다 — 갈라낸다
        if kind == "issues" and it.get("pull_request"):
            continue
        updated = it.get("updated_at", "")
        if since and updated <= since:
            continue
        newest = max(newest or "", updated)

        num = it["number"]
        blocks = []
        body = mask(it.get("body") or "", do_mask)
        if body.strip():
            blocks.append((sha(body), f"### 본문 — @{it['user']['login']} ({local_date(it['created_at'])})\n\n{body}\n"))

        cout, cerr = gh(["api", f"repos/{repo}/{endpoint.rstrip('s')}s/{num}/comments", "--paginate"])
        if cerr:
            report["failed"].append(f"{repo} {kind}#{num} 코멘트: {cerr.splitlines()[0]}")
        for c in (json.loads(cout) if cout else []):
            cb = mask(c.get("body") or "", do_mask)
            if cb.strip():
                blocks.append((sha(cb), f"### 코멘트 — @{c['user']['login']} ({local_date(c['created_at'])})\n\n{cb}\n"))

        if kind == "pulls":
            rout, _ = gh(["api", f"repos/{repo}/pulls/{num}/reviews", "--paginate"])
            for r in (json.loads(rout) if rout else []):
                rb = mask(r.get("body") or "", do_mask)
                if rb.strip():
                    blocks.append((sha(rb), f"### 리뷰({r.get('state','')}) — @{r['user']['login']} ({local_date(r.get('submitted_at'))})\n\n{rb}\n"))

        if not blocks:
            continue

        header = (f"# [{slug(repo)}#{num}] {it['title']}\n\n"
                  f"- 상태: {it.get('state')}\n- 작성: @{it['user']['login']} {local_date(it['created_at'])}\n"
                  f"- URL: {it['html_url']}\n")
        path = os.path.join(kb, "raw", "github", kind, f"{slug(repo)}-{num}.md")
        meta = base_meta(f"{repo}#{num}", it["html_url"], do_mask)
        meta["title"] = it["title"]
        meta["state"] = it.get("state")
        meta["updated_at"] = updated
        write_raw(path, header, blocks, meta, today, report)

    return newest


def scrape_commits(repo, since, limit, do_mask, kb, today, report, bodies_only=True):
    """커밋 — 기본은 '본문 있는 것만'. 한 줄 커밋엔 지식이 없다."""
    args = ["api", "-X", "GET", f"repos/{repo}/commits", "-F", f"per_page={min(limit,100)}"]
    if since:
        args += ["-f", f"since={since}"]
    out, err = gh(args)
    if err:
        report["failed"].append(f"{repo} commits: {err.splitlines()[0] if err else '?'}")
        return
    commits = json.loads(out) if out else []

    by_month = {}
    for c in commits[:limit]:
        msg = c["commit"]["message"]
        subject, _, body = msg.partition("\n\n")
        if bodies_only and not body.strip():
            continue
        if len(c.get("parents", [])) > 1:          # 머지 커밋 = 기계가 만든 글
            continue
        author = (c.get("author") or {}).get("login") or c["commit"]["author"]["name"]
        if str(author).endswith("[bot]"):
            continue
        d = local_date(c["commit"]["author"]["date"])
        text = (f"### {c['sha'][:7]} — {subject.strip()}\n\n"
                f"- @{author} · {d} · {c['html_url']}\n\n{mask(body.strip(), do_mask)}\n")
        by_month.setdefault(d[:7], []).append((sha(msg), text))

    for month, blocks in by_month.items():
        path = os.path.join(kb, "raw", "github", "commits", f"{slug(repo)}-{month}.md")
        header = f"# [{slug(repo)}] 커밋 메시지 {month}\n\n본문이 있는 커밋만 (한 줄·머지·봇 제외).\n"
        meta = base_meta(f"{repo}@{month}", f"https://github.com/{repo}/commits", do_mask)
        write_raw(path, header, blocks, meta, today, report)


def scrape_releases(repo, limit, do_mask, kb, today, report):
    out, err = gh(["api", f"repos/{repo}/releases", "-F", f"per_page={min(limit,100)}"])
    if err:
        report["failed"].append(f"{repo} releases: {err.splitlines()[0] if err else '?'}")
        return
    for r in (json.loads(out) if out else [])[:limit]:
        notes = mask(r.get("body") or "", do_mask)
        if not notes.strip():
            continue
        tag = re.sub(r"[^\w.-]", "_", r.get("tag_name") or r.get("name") or "untagged")
        path = os.path.join(kb, "raw", "github", "releases", f"{slug(repo)}-{tag}.md")
        header = (f"# [{slug(repo)}] 릴리스 {r.get('tag_name')}\n\n"
                  f"- 공개: {local_date(r.get('published_at'))}\n- URL: {r['html_url']}\n")
        meta = base_meta(f"{repo}@{tag}", r["html_url"], do_mask)
        write_raw(path, header, [(sha(notes), notes + "\n")], meta, today, report)


# ── 메인 ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="GitHub 사람이 쓴 글 → 지식 베이스 raw/github/")
    ap.add_argument("--kb", required=True, help="지식 베이스 루트 (schema/rules.md 가 있는 곳)")
    ap.add_argument("--repo", action="append", required=True, help="owner/name (여러 번)")
    ap.add_argument("--kinds", default="issues,pulls,commits,releases")
    ap.add_argument("--since", help="ISO 날짜. 없으면 워터마크 사용")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--all-commits", action="store_true", help="본문 없는 커밋도 (기본: 본문 있는 것만)")
    ap.add_argument("--no-mask", action="store_true", help="이메일 마스킹 끔")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(os.path.join(a.kb, "schema", "rules.md")):
        sys.exit(f"지식 베이스가 아님 (schema/rules.md 없음): {a.kb}\n"
                 f"→ knowledgebase-setup 스킬로 먼저 세운다.")

    kinds = [k.strip() for k in a.kinds.split(",") if k.strip() in KINDS]
    do_mask = not a.no_mask
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    wm_path = os.path.join(a.kb, "state", "github-watermark.json")
    wm = {}
    if os.path.exists(wm_path):
        try:
            wm = json.load(open(wm_path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            wm = {}

    report = {"written": [], "appended": [], "skipped": [], "failed": []}

    if a.dry_run:
        print("[dry-run] 적재하지 않고 대상만 센다\n")
    for repo in a.repo:
        since = a.since or wm.get(repo, {}).get("updated_at")
        print(f"· {repo}  (since={since or '전체'}, kinds={','.join(kinds)})")
        if a.dry_run:
            for kind in kinds:
                ep = {"issues": "issues", "pulls": "pulls", "commits": "commits", "releases": "releases"}[kind]
                out, err = gh(["api", "-X", "GET", f"repos/{repo}/{ep}", "-F", "per_page=1", "-i"])
                print(f"    {kind}: {'읽기 OK' if not err else 'ERR ' + err.splitlines()[0]}")
            continue

        newest = since
        for kind in kinds:
            if kind in ("issues", "pulls"):
                got = scrape_threads(repo, kind, since, a.limit, do_mask, a.kb, today, report)
                if got:
                    newest = max(newest or "", got)
            elif kind == "commits":
                scrape_commits(repo, since, a.limit, do_mask, a.kb, today, report,
                               bodies_only=not a.all_commits)
            elif kind == "releases":
                scrape_releases(repo, a.limit, do_mask, a.kb, today, report)

        if newest:
            # 적재 성공분까지만 전진시킨다 — rate limit 으로 끊겨도 다음 실행이 이어 받는다
            wm[repo] = {"updated_at": newest, "last_run": today}

    if a.dry_run:
        return

    os.makedirs(os.path.dirname(wm_path), exist_ok=True)
    json.dump(wm, open(wm_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\n새 파일 {len(report['written'])} · 덧붙임 {len(report['appended'])} · "
          f"변경없음 {len(report['skipped'])} · 실패 {len(report['failed'])}")
    for k, label in (("written", "새로"), ("appended", "덧붙임"), ("failed", "실패")):
        for line in report[k]:
            print(f"  [{label}] {line}")
    if report["failed"]:
        sys.exit(1)      # 조용한 실패 금지


if __name__ == "__main__":
    main()
