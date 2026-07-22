#!/usr/bin/env python3
# UserPromptSubmit 훅: 사용자 프롬프트가 일정 간격(3번)마다 쌓일 때,
# "지금까지 대화에서 확정된 도메인 맥락을 ./wiki/{도메인}/ 에 반영할 게 있는지"
# 검토하라는 리마인더를 (화면엔 안 보이게) 모델 컨텍스트에 주입한다.
#
# - 별도 상태파일 없이 transcript의 실제 사용자 발화 수를 매번 세는 무상태 방식.
# - 도구 결과(toolUseResult)·주입된 <...> 태그 블록은 발화로 치지 않는다.
# - 카운트가 INTERVAL의 배수일 때만 주입. 저장할 게 없으면 모델이 그냥 넘어가면 된다.
#
# stdin으로 들어오는 JSON: session_id, transcript_path, prompt, cwd 등.
import sys
import json

INTERVAL = 3  # 사용자 프롬프트 N번마다 체크포인트

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

transcript = data.get("transcript_path") or ""


def is_real_user_prompt(message):
    """user 메시지가 실제 사용자 발화인지. 주입 태그 블록(<...>)만 있으면 False."""
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
            return True
    return False


count = 0
import os

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
            if o.get("type") != "user":
                continue
            # 도구 결과는 진짜 발화가 아님
            if o.get("toolUseResult") is not None:
                continue
            msg = o.get("message")
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            if is_real_user_prompt(msg):
                count += 1

# 방금 제출한 이번 프롬프트가 transcript에 아직 안 들어왔을 수 있으니 +1
count += 1

if count == 0 or count % INTERVAL != 0:
    sys.exit(0)

reminder = (
    f"[맥락 갱신 체크포인트 · 프롬프트 {count}번째] "
    "지금까지의 대화에서 특정 도메인의 맥락(확정된 사실·결정·기획 변경)이 새로 정해졌다면, "
    "이번 답변에서 해당 `./wiki/{도메인}/` 파일에 반영하고(없으면 생성) 답변 말미에 한 줄로 알려라. "
    "기록할 게 없으면 그냥 넘어가도 된다. 임시 판단·잡담은 기록하지 않는다."
)

print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": reminder,
            },
            "suppressOutput": True,
        }
    )
)
