# skills-eval — 스킬 트리거 평가

각 스킬의 frontmatter(라우팅 근거)를 그대로 라우터에 먹여, 정해둔 프롬프트마다
"어떤 스킬이 떠야 하는가"를 `claude -p` 로 판정시키고 정답과 비교한다.
스킬이 **필요할 때 뜨는가 / 엉뚱할 때 안 뜨는가**를 자동 채점한다.

## 실행

```bash
cd skills-eval
python3 run.py                 # 전체 케이스 1회씩
python3 run.py --runs 3        # 케이스당 3회 — 트리거 흔들림(비결정성) 측정
EVAL_MODEL=claude-haiku-4-5-20251001 python3 run.py   # 라우터 모델 지정
```

의존성: `claude` CLI, `python3`. 정확도 100%면 exit 0, 실패 있으면 exit 1 (CI 연동 가능).

## 판정 분류

| 분류 | 의미 |
|------|------|
| `PASS` | 예측 == 정답 |
| `FALSE_POS` | 정답=none 인데 스킬이 떴다 — **오발동, 제일 위험** |
| `FALSE_NEG` | 정답=스킬 인데 안 떴다 — 미발동 |
| `WRONG_SKILL` | 정답=A 인데 B가 떴다 — 라우팅 충돌 |

## 케이스 추가 (cases.jsonl)

한 줄 = 한 케이스. `expect` 는 발동해야 할 스킬 이름 또는 `"none"`.

```json
{"prompt": "내 지라 티켓 목록 보여줘", "expect": "jiraticket", "note": "무엇을 검증하는지 메모"}
```

좋은 케이스 = 긍정(당연히 떠야) + 하드 네거티브(비슷한데 뜨면 안 됨) 를 섞는 것.
예: "워크트리가 뭔지 설명해줘" → `none` (단어만 언급, 발동 금지).

## 원리와 한계

- 라우팅은 description 이 결정하므로, description 을 그대로 라우터에 먹여 판정을 **근사 재현**한다.
- 실제 Claude Code 의 전체 시스템 프롬프트와 100% 동일하진 않다 → 절대 점수보다 **description 을
  고치기 전후의 상대 변화**를 보는 용도로 쓴다.
- 트리거 판정은 비결정적일 수 있으니, 경계가 애매한 스킬은 `--runs 3~5` 로 적중률(fire rate)을 본다.
