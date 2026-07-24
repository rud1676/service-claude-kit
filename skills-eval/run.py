#!/usr/bin/env python3
"""
스킬 트리거 평가 하네스.

각 스킬의 frontmatter(라우팅 근거)를 그대로 라우터 프롬프트에 넣고,
cases.jsonl 의 프롬프트마다 "어떤 스킬이 떠야 하는가"를 claude -p 로 판정시켜
미리 정한 정답(expect)과 비교한다.

분류:
  PASS          예측 == 정답
  FALSE_POS     정답=none 인데 스킬이 떴다        (오발동 — 제일 위험)
  FALSE_NEG     정답=스킬 인데 none 이 나왔다       (미발동)
  WRONG_SKILL   정답=A 인데 B 가 떴다              (라우팅 충돌)

사용:
  python3 run.py                    # 전체 케이스 1회씩
  python3 run.py --runs 3           # 케이스당 3회 (트리거 흔들림 측정)
  python3 run.py --skills-dir ../skills --cases cases.jsonl
  EVAL_MODEL=claude-haiku-4-5-20251001 python3 run.py   # 라우터 모델 지정
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_skills(skills_dir):
    skills = []
    for path in sorted(glob.glob(os.path.join(skills_dir, "*/SKILL.md"))):
        text = open(path, encoding="utf-8").read()
        m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
        fm = m.group(1) if m else ""
        nm = re.search(r"^name:\s*(.+)$", fm, re.M)
        name = nm.group(1).strip() if nm else os.path.basename(os.path.dirname(path))
        skills.append({"name": name, "frontmatter": fm.strip()})
    return skills


def build_router_prompt(skills, user_msg):
    catalog = "\n\n".join(f"### {s['name']}\n{s['frontmatter']}" for s in skills)
    names = ", ".join(s["name"] for s in skills)
    return f"""너는 Claude Code 의 스킬 라우터다. 아래는 설치된 스킬들의 frontmatter(name + description)다.
Claude Code 는 사용자 메시지가 어떤 스킬의 description 과 맞을 때 그 스킬을 발동한다.

규칙:
- description 에 "명시 호출 때만", "/slash 로만", "자동 발동하지 않는다" 같은 제약이 있으면 그대로 존중한다.
  (예: 사용자가 그 슬래시 명령을 직접 쓰지 않았다면 발동하지 않음)
- 딱 맞는 스킬이 없으면 "none" 이다. 애매하면 억지로 고르지 말고 none.
- 정확히 하나만 고른다.

사용 가능한 스킬: {names}

=== 스킬 목록 ===
{catalog}
=== 끝 ===

사용자 메시지:
\"\"\"{user_msg}\"\"\"

이 메시지에 어떤 스킬이 발동해야 하는가? 오직 아래 JSON 한 줄만 출력하라. 다른 말 금지.
{{"skill": "<스킬이름 또는 none>", "reason": "<한 줄 근거>"}}"""


def route(prompt, model=None, timeout=180):
    cmd = ["claude", "-p", "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    try:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"skill": "ERROR", "reason": "timeout"}
    if r.returncode != 0:
        return {"skill": "ERROR", "reason": (r.stderr or "nonzero exit")[:200]}
    try:
        outer = json.loads(r.stdout)
        text = outer.get("result", r.stdout)
    except json.JSONDecodeError:
        text = r.stdout
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"skill": "ERROR", "reason": f"no json in output: {text[:120]}"}
    try:
        inner = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"skill": "ERROR", "reason": f"bad json: {m.group(0)[:120]}"}
    skill = str(inner.get("skill", "none")).strip()
    return {"skill": skill, "reason": str(inner.get("reason", "")).strip()}


def classify(expect, predicted):
    if predicted == "ERROR":
        return "ERROR"
    if predicted == expect:
        return "PASS"
    if expect == "none" and predicted != "none":
        return "FALSE_POS"
    if expect != "none" and predicted == "none":
        return "FALSE_NEG"
    return "WRONG_SKILL"


C = {
    "PASS": "\033[32mPASS\033[0m",
    "FALSE_POS": "\033[31mFALSE_POS\033[0m",
    "FALSE_NEG": "\033[33mFALSE_NEG\033[0m",
    "WRONG_SKILL": "\033[35mWRONG\033[0m",
    "ERROR": "\033[90mERROR\033[0m",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default=os.path.join(ROOT, "..", "skills"))
    ap.add_argument("--cases", default=os.path.join(ROOT, "cases.jsonl"))
    ap.add_argument("--runs", type=int, default=1, help="케이스당 반복 횟수 (흔들림 측정)")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--model", default=os.environ.get("EVAL_MODEL"))
    args = ap.parse_args()

    skills = load_skills(args.skills_dir)
    if not skills:
        print(f"스킬을 못 찾음: {args.skills_dir}", file=sys.stderr)
        sys.exit(2)
    valid = {s["name"] for s in skills} | {"none"}

    cases = []
    with open(args.cases, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            c = json.loads(line)
            if c["expect"] not in valid:
                print(f"[경고] {args.cases}:{i} expect '{c['expect']}' 는 존재하지 않는 스킬", file=sys.stderr)
            cases.append(c)

    print(f"스킬 {len(skills)}개 · 케이스 {len(cases)}개 · runs={args.runs} · model={args.model or 'default'}\n")

    # (case_idx, run_idx) 단위로 병렬 실행
    jobs = [(ci, r) for ci in range(len(cases)) for r in range(args.runs)]
    results = defaultdict(list)  # case_idx -> [predicted skill,...]

    def work(job):
        ci, _ = job
        prompt = build_router_prompt(skills, cases[ci]["prompt"])
        return ci, route(prompt, model=args.model)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for ci, res in ex.map(work, jobs):
            results[ci].append(res["skill"])

    rows = []
    verdict_counts = Counter()
    per_skill = defaultdict(lambda: Counter())  # expect -> verdict counts (majority 기준)

    for ci, c in enumerate(cases):
        preds = results[ci]
        majority = Counter(preds).most_common(1)[0][0]
        verdict = classify(c["expect"], majority)
        verdict_counts[verdict] += 1
        per_skill[c["expect"]][verdict] += 1
        hit = sum(1 for p in preds if classify(c["expect"], p) == "PASS")
        rows.append((verdict, c["expect"], majority, f"{hit}/{len(preds)}", c["prompt"], c.get("note", "")))

    # 표 출력
    w_prompt = 46
    print(f"{'결과':<10} {'정답':<16} {'예측':<16} {'적중률':<7} 프롬프트")
    print("-" * 100)
    for verdict, expect, pred, rate, prompt, note in rows:
        p = prompt if len(prompt) <= w_prompt else prompt[: w_prompt - 1] + "…"
        badge = C.get(verdict, verdict)
        pad = " " * max(0, 10 - len(verdict))
        print(f"{badge}{pad} {expect:<16} {pred:<16} {rate:<7} {p}")

    total = len(cases)
    passed = verdict_counts["PASS"]
    print("\n" + "=" * 60)
    print(f"정확도: {passed}/{total}  ({100*passed//total if total else 0}%)")
    for k in ["FALSE_POS", "FALSE_NEG", "WRONG_SKILL", "ERROR"]:
        if verdict_counts[k]:
            print(f"  {k:<12}: {verdict_counts[k]}")

    print("\n스킬별 (majority 기준):")
    for expect in sorted(per_skill):
        cc = per_skill[expect]
        tot = sum(cc.values())
        print(f"  {expect:<18} {cc['PASS']}/{tot} pass"
              + (f"  ⚠ FP={cc['FALSE_POS']}" if cc['FALSE_POS'] else "")
              + (f"  ⚠ FN={cc['FALSE_NEG']}" if cc['FALSE_NEG'] else "")
              + (f"  ⚠ WRONG={cc['WRONG_SKILL']}" if cc['WRONG_SKILL'] else ""))

    # 실패한 케이스 근거 재조회는 생략 — 실패 프롬프트만 다시 보여줌
    fails = [r for r in rows if r[0] not in ("PASS",)]
    if fails:
        print("\n실패 케이스:")
        for verdict, expect, pred, rate, prompt, note in fails:
            print(f"  [{verdict}] expect={expect} got={pred}  «{prompt}»" + (f"  ({note})" if note else ""))

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
