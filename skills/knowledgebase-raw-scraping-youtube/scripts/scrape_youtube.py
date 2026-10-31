#!/usr/bin/env python3
"""유튜브 채널의 스크립트(자막) + 설명란을 지식 베이스의 raw/youtube/ 에 추가만 한다.

knowledgebase-raw-scraping-github 와 같은 불변식:
  1) 추가만   — 영상 스크립트는 불변이므로 이미 있는 파일은 건드리지 않는다
  2) 재현 가능 — 워터마크 + 본문 해시. 두 번 돌리면 "건너뜀"만 나온다
  3) 조용한 성공 금지 — 자막 없는 영상·실패를 전부 보고한다

이 스킬만의 규칙:
  - 수동 자막 / 자동 자막(ASR)을 구별해 파일 머리와 meta 에 박는다.
    ASR 은 숫자·고유명사를 조용히 틀리므로, 등급을 올리려면 사람이 타임스탬프를 봐야 한다.
  - 모든 줄에 [MM:SS] 를 남긴다 — 사람이 원본 영상으로 돌아가는 유일한 좌표.

필요: yt-dlp (venv/pipx). ffmpeg·whisper 는 필요 없다 — 음성은 건드리지 않는다.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TAG_RE = re.compile(r"<[^>]+>")


def find_ytdlp(explicit):
    for c in filter(None, [explicit, shutil.which("yt-dlp"),
                           os.path.expanduser("~/.local/venv/ytdlp/bin/yt-dlp"),
                           os.path.expanduser("~/.local/bin/yt-dlp")]):
        if os.path.exists(c) or shutil.which(c):
            return c
    sys.exit("yt-dlp 이 없다. 전역 pip 은 PEP 668 로 막혀 있으니 venv/pipx 로 깐다:\n"
             "  python3 -m venv ~/.local/venv/ytdlp && ~/.local/venv/ytdlp/bin/pip install -U yt-dlp\n"
             "  (또는) pipx install yt-dlp\n"
             "설치 후 --ytdlp <경로> 로 지정하거나 PATH 에 넣는다.")


def run(cmd, timeout=180):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return (p.stdout, None) if p.returncode == 0 else (p.stdout, p.stderr.strip())


def mask(t, on):
    return EMAIL_RE.sub("[마스킹:이메일]", t or "") if on else (t or "")


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def parse_vtt(path):
    """VTT → [(초, 텍스트)]. 롤링 중복 줄과 타이밍 태그를 제거한다.

    자동 자막은 스크롤 효과를 내려고 같은 줄을 2~3번 반복해 내려준다.
    그대로 두면 raw 가 3배로 부풀고 사람이 읽을 수 없다.
    """
    raw = open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    out, last = [], ""
    # 자동 자막은 cue 안에 공백 한 칸짜리 줄을 넣으므로 \s 로 cue 를 자르면 시각과 본문이 떨어진다
    for cue in re.split(r"\n\n+", raw):
        lines = cue.strip("\n").split("\n")
        ti = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if ti is None:
            continue
        hh, mm, ss = lines[ti].split("-->")[0].strip()[:8].split(":")
        sec = int(hh) * 3600 + int(mm) * 60 + int(ss)
        # 자동 자막 cue 는 "직전 줄 + 새 줄" 2줄이라 cue 단위가 아니라 줄 단위로 걸러야 한다
        for l in lines[ti + 1:]:
            body = re.sub(r"\s+", " ", TAG_RE.sub("", l)).strip()
            if not body or body == last:
                continue
            last = body
            out.append((sec, body))
    return out


def fmt_ts(sec):
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def list_videos(yt, channel, limit, min_dur):
    url = channel if re.search(r"/(videos|playlist|streams)|list=", channel) else channel.rstrip("/") + "/videos"
    out, err = run([yt, "--flat-playlist", "--playlist-end", str(limit),
                    "--print", "%(id)s\t%(title)s\t%(upload_date)s\t%(duration)s", url], timeout=300)
    if err and not out:
        return [], err.splitlines()[0] if err else "열거 실패"
    vids = []
    for line in out.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        vid, title, up, dur = parts[0], parts[1], parts[2], parts[3]
        try:
            d = int(float(dur))
        except (ValueError, TypeError):
            d = 0            # 라이브·쇼츠는 duration 이 비어 올 수 있다
        if d and d < min_dur:
            continue
        vids.append({"id": vid, "title": title, "upload_date": up if up != "NA" else "", "duration": d})
    return vids, None


def fetch_info(yt, vid, workdir):
    """영상 정보만 받는다(자막 다운로드 없음).

    info.json 에 upload_date·description 과 함께 subtitles/automatic_captions 목록이
    들어 있다. 그래서 자막을 받기 전에 "있는지/수동인지"를 알 수 있다 — dry-run 이 싸진다.
    --flat-playlist 는 채널 페이지에서 upload_date 를 NA 로 주므로, 날짜의 정본은 여기다.
    """
    url = f"https://www.youtube.com/watch?v={vid}"
    base = os.path.join(workdir, vid + ".info")
    out, err = run([yt, "--skip-download", "--write-info-json", "--no-write-subs",
                    "-o", base, url], timeout=180)
    path = base + ".info.json"
    if not os.path.exists(path):
        return None, (err.splitlines()[0] if err else "정보 추출 실패")
    try:
        return json.load(open(path, encoding="utf-8")), None
    except (json.JSONDecodeError, OSError) as e:
        return None, f"info.json 파싱 실패: {e}"


def pick_caption(info, langs):
    """(kind, lang) 또는 (None, None). 수동 자막 우선 — 사람이 쓴 글이므로.

    자동 '번역' 트랙은 제외한다. 유튜브는 `ko-en`(영어에서 번역한 한국어)처럼
    `<목표>-<원본>` 으로 주는데, 번역은 ASR 위에 기계 번역을 한 겹 더 얹은 것이라
    숫자·고유명사가 두 번 깨진다. `ko-orig`·`ko-KR` 같은 원본 변종은 받는다.
    """
    for kind, key in (("manual", "subtitles"), ("auto", "automatic_captions")):
        avail = info.get(key) or {}
        for want in langs:
            for have in sorted(avail):
                if have == want:
                    return kind, have
                if have.startswith(want + "-") and not re.fullmatch(
                        re.escape(want) + r"-[a-z]{2}", have):
                    return kind, have
    return None, None


def fetch_sub(yt, vid, kind, lang, workdir):
    """정해진 종류·언어의 자막만 받는다. 반환: (vtt경로, 에러)"""
    url = f"https://www.youtube.com/watch?v={vid}"
    base = os.path.join(workdir, vid)
    flag = "--write-subs" if kind == "manual" else "--write-auto-subs"
    out, err = run([yt, "--skip-download", flag, "--sub-langs", lang,
                    "--sub-format", "vtt", "-o", base, url], timeout=240)
    hits = sorted(glob.glob(base + ".*.vtt"))
    if hits:
        return hits[0], None
    return None, (err.splitlines()[0] if err else "자막 다운로드 실패")


def main():
    ap = argparse.ArgumentParser(description="유튜브 채널 스크립트 → 지식 베이스 raw/youtube/")
    ap.add_argument("--kb", required=True, help="지식 베이스 루트 (schema/rules.md 가 있는 곳)")
    ap.add_argument("--channel", action="append", required=True, help="채널/재생목록 URL (여러 번)")
    ap.add_argument("--lang", default="ko,en", help="자막 언어 우선순위 (기본 ko,en)")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--since", help="YYYYMMDD. 없으면 워터마크 사용")
    ap.add_argument("--min-duration", type=int, default=60, help="초. 쇼츠 걸러내기 (기본 60)")
    ap.add_argument("--comments", action="store_true", help="댓글도 (기본 제외 — 노이즈)")
    ap.add_argument("--no-mask", action="store_true")
    ap.add_argument("--ytdlp", help="yt-dlp 경로")
    ap.add_argument("--dry-run", action="store_true", help="자막 유무만 세고 적재하지 않는다")
    a = ap.parse_args()

    if not os.path.exists(os.path.join(a.kb, "schema", "rules.md")):
        sys.exit(f"지식 베이스가 아님 (schema/rules.md 없음): {a.kb}\n"
                 f"→ knowledgebase-setup 스킬로 먼저 세운다.")

    yt = find_ytdlp(a.ytdlp)
    langs = [l.strip() for l in a.lang.split(",") if l.strip()]
    do_mask = not a.no_mask
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    wm_path = os.path.join(a.kb, "state", "youtube-watermark.json")
    wm = {}
    if os.path.exists(wm_path):
        try:
            wm = json.load(open(wm_path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            wm = {}

    rep = {"written": [], "skipped": [], "nosub": [], "failed": []}
    tally = {"manual": 0, "auto": 0}

    for channel in a.channel:
        since = a.since or wm.get(channel, {}).get("last_upload")
        vids, err = list_videos(yt, channel, a.limit, a.min_duration)
        if err:
            rep["failed"].append(f"{channel}: {err}")
            continue
        # flat-playlist 는 채널에서 upload_date 를 NA 로 준다 — 날짜를 모르면 남기고 info.json 으로 판정한다
        fresh = [v for v in vids if not since or not v["upload_date"] or v["upload_date"] > since]
        print(f"채널: {channel}\n  영상 {len(vids)}개 (limit={a.limit}, 60초 미만 제외) → "
              f"워터마크({since or '전체'}) 이후 {len(fresh)}개")

        # 워터마크는 뒤로 가지 않는다 — --since 로 백필해도 기존 최신값을 지킨다
        newest = max(since or "", wm.get(channel, {}).get("last_upload", ""))
        ch_slug = re.sub(r"[^\w.-]", "", channel.rstrip("/").split("/")[-1])[:40] or "channel"
        with tempfile.TemporaryDirectory(prefix="ytsub-") as tmp:
            for v in fresh:
                vid = v["id"]

                info, ierr = fetch_info(yt, vid, tmp)
                if not info:
                    rep["failed"].append(f"{vid}: {ierr}")
                    continue
                # 날짜의 정본은 info.json — flat-playlist 는 채널에서 NA 를 준다
                up = info.get("upload_date") or v["upload_date"] or "00000000"
                if since and up <= since:
                    # 목록은 업로드일 역순이라 여기부터는 전부 since 이전이다
                    rep["skipped"].append(f"{vid} (워터마크 이전: {up}) — 이후 목록 생략")
                    break

                dur = int(info.get("duration") or v["duration"] or 0)
                kind, lang = pick_caption(info, langs)
                if not kind:
                    rep["nosub"].append(f"{vid} {(info.get('title') or v['title'])[:40]}")
                    continue
                tally[kind] += 1
                newest = max(newest, up)

                dest = os.path.join(a.kb, "raw", "youtube",
                                    f"{ch_slug}-{up}-{vid}-{kind}.md")
                if os.path.exists(dest):
                    rep["skipped"].append(os.path.basename(dest))
                    continue
                if a.dry_run:
                    continue

                vtt, serr = fetch_sub(yt, vid, kind, lang, tmp)
                if not vtt:
                    rep["failed"].append(f"{vid} 자막({kind}/{lang}): {serr}")
                    continue
                cues = parse_vtt(vtt)
                desc = mask(info.get("description") or "", do_mask)
                warn = ("\n> **자동 자막(ASR)이다.** 기계가 사람 말을 추측한 것이라 "
                        "**숫자·고유명사·인용은 `[추론]`** 으로 취급한다. "
                        "사람이 해당 타임스탬프를 확인하면 문서상으로 올린다.\n"
                        if kind == "auto" else
                        "\n> 수동 자막(uploader 제공)이다. 문서상 등급.\n")
                body = "\n".join(f"[{fmt_ts(s)}] {mask(t, do_mask)}" for s, t in cues)
                head = (f"# [{ch_slug}] {info.get('title') or v['title']}\n\n"
                        f"- 영상: https://www.youtube.com/watch?v={vid}\n"
                        f"- 업로드: {up[:4]}-{up[4:6]}-{up[6:8]} (UTC 기준 upload_date — 현지와 하루 차이 가능)\n"
                        f"- 길이: {fmt_ts(dur)}\n"
                        f"- 자막: {kind} / {lang}\n"
                        f"{warn}")
                sections = [head]
                if desc.strip():
                    sections.append("## 설명란 (uploader 가 쓴 글)\n\n" + desc.strip() + "\n")
                sections.append(f"## 스크립트 ({len(cues)}줄)\n\n" + body + "\n")

                os.makedirs(os.path.dirname(dest), exist_ok=True)
                full = "\n".join(sections)
                open(dest, "w", encoding="utf-8").write(full)
                json.dump({
                    "source": "youtube",
                    "source_id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "retrieved": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "body_sha256": sha(full),
                    "masked": ["email"] if do_mask else [],
                    "caption_kind": kind,
                    "caption_lang": lang,
                    "title": info.get("title") or v["title"],
                    "upload_date": up,
                    "duration_sec": dur,
                    "transcript_lines": len(cues),
                }, open(dest + ".meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                rep["written"].append(os.path.basename(dest))

        if newest and not a.dry_run:
            wm[channel] = {"last_upload": newest, "last_run": today}

    print(f"\n자막 있음: 수동 {tally['manual']} · 자동 {tally['auto']}   "
          f"자막 없음 {len(rep['nosub'])} · 건너뜀 {len(rep['skipped'])} · 실패 {len(rep['failed'])}")
    if a.dry_run:
        for v in rep["nosub"][:20]:
            print(f"  [자막없음] {v}")
        for f in rep["failed"]:
            print(f"  [실패] {f}")
        print("\n[dry-run] 적재하지 않았다. 자막 없는 영상은 이 스킬로 적재할 수 없다"
              " (음성 인식은 범위 밖).")
        return

    os.makedirs(os.path.dirname(wm_path), exist_ok=True)
    json.dump(wm, open(wm_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for k, label in (("written", "새로"), ("nosub", "자막없음"), ("failed", "실패")):
        for line in rep[k][:30]:
            print(f"  [{label}] {line}")
    if tally["auto"]:
        print(f"\n※ 자동 자막 {tally['auto']}개 적재됨 — 여기서 뽑은 숫자·고유명사는 "
              f"사람이 영상을 확인하기 전까지 [추론]이다.")
    if rep["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
