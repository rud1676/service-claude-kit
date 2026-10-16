---
name: infra-diagram
description: >-
  프로젝트의 인프라 코드(terraform·k8s manifest·docker-compose·CI 워크플로·README/문서)를 읽어
  실제 구성을 파악한 뒤, AWS 공식 아이콘을 쓴 draw.io 인프라 구성도(.drawio 원본 + PNG)를 만들어 남기는 스킬.
  Python으로 draw.io XML을 생성하고, draw.io 데스크톱을 헤드리스로 돌려 PNG로 렌더링한 다음,
  렌더된 이미지를 직접 보며 선·라벨이 겹치는 곳을 고친다. "인프라 구성도 그려줘", "아키텍처 다이어그램",
  "draw.io로 구성도", "infra diagram" 같은 요청에 쓰고, /infra-diagram 으로도 호출한다.
user_invocable: true
---

# Infra Diagram (draw.io)

결과물은 두 개다: 편집 가능한 `*.drawio` 원본, 문서에 붙일 `*.png`.
그림은 **코드에 있는 것만** 그린다. 추측으로 채운 부분은 그림에 넣지 않거나, 넣었다면 답변에서 따로 밝힌다.

스킬 경로를 `$SKILL`(= 이 파일이 있는 디렉토리. 프로젝트 설치 시 `<워크스페이스>/.claude/skills/infra-diagram`, 전역 설치 시 `~/.claude/skills/infra-diagram`)이라 부른다.
- `$SKILL/scripts/drawio_lib.py`: XML 생성 헬퍼 (`v`, `e`, `grp`, `icon`, `box`, `memo`, `zone`, `cylinder`, `person`, `title`, `save`, 색상 `C.*`)
- `$SKILL/scripts/render.sh`: `.drawio`를 `.png`로 렌더링한다. draw.io가 없으면 `~/.cache/drawio`에 받아 둔다.
- `$SKILL/references/aws-icons.md`: 검증된 아이콘·그룹 이름과 색 (**아이콘 쓰기 전에 꼭 확인**)
- `$SKILL/examples/bluefield-aws-k3s.py`: 완성 예시 (CloudFront + WAF + EC2 k3s + 외부 DB + GitHub Actions 배포 흐름, 셀 69개)

## 1. 인프라 파악

다음 파일을 찾아 **끝까지 읽는다**. 많으면 Explore 서브에이전트에 맡긴다.
- IaC: `*.tf`(resource·data·variable 기본값), CloudFormation/CDK, Pulumi
- 런타임: k8s/helm manifest(Ingress·Service·Deployment·CronJob·Job), `docker-compose*.yml`, `ecosystem.config.js`
- 배포: `.github/workflows/*`, 그 밖의 CI 설정, Dockerfile
- 문서: infra README, `context/**`이나 `docs/**`에 있는 현재 상태 메모 (코드와 실제 상태가 다를 수 있는 부분은 여기서 확인)

그 다음 아래 항목을 표로 뽑아 둔다. 이 표가 그림의 설계도가 된다.
| 구분 | 무엇을 뽑나 |
|---|---|
| 액터 | 사용자, 운영자, 작업 PC, CI, 외부 검증자(ACME 등) |
| 엣지 | DNS, CDN, WAF, 인증서, 도메인별 라우팅 규칙 |
| 네트워크 | 계정, 리전, VPC/CIDR, 서브넷, SG 인바운드 규칙, EIP, NAT 유무 |
| 컴퓨트 | 인스턴스·클러스터와 그 안의 프로세스/파드/잡 |
| 관리형 서비스 | S3, DB, 메일, 큐, 모니터링, 알람, 시크릿, 레지스트리 |
| 외부 | AWS 밖의 DB, SaaS, 결제 등 |
| 흐름 | 요청 경로(포트·프로토콜), 앱에서 서비스로 가는 호출, 배포 순서(①②③), 모니터링·알람 경로 |

규모가 너무 커서 한 장에 들어가지 않으면(노드 60개 이상) 그리기 전에 사용자에게 어떻게 나눌지 묻는다. 예: 런타임 / 배포 / 네트워크.
대상 환경(live/stage 등)이 여러 개라 무엇을 그릴지 애매할 때도 먼저 묻는다.

## 2. 레이아웃 잡기

`examples/bluefield-aws-k3s.py`의 배치 관례를 따른다.
- **왼쪽에서 오른쪽으로 흐른다.** 왼쪽 열(x≈40–250)은 액터·외부 진입점, 가운데는 AWS Cloud 그룹, 오른쪽은 리전 서비스, 맨 오른쪽(x≈1770 이상)은 AWS 밖 시스템이다.
- 그룹은 바깥에서 안쪽 순서로 놓는다: AWS Cloud → (Edge/Global 리전) · (메인 리전) → VPC → Subnet → EC2/클러스터 → namespace. 각 단계마다 20px씩 안으로 들인다.
- 메인 리전 아래쪽 줄(y≈860)에는 배포·운영용 서비스(ECR, Parameter Store, SSM, IAM)를 가로로 늘어놓는다. 배포 흐름(CI → ①②③)은 그림 맨 아래를 지나가는 선으로 그린다.
- 그림으로 표현하기 어려운 규칙(SG 인바운드, CDN 경로 라우팅, CF Function)은 `memo()` 박스에 글로 적는다.
- 좌표는 10 단위 그리드에 맞춘다. 아이콘은 60×60(CDN은 64), 일반 박스는 140×44에서 170×60 정도로 한다.
- 페이지 크기는 처음에 1960×1160으로 잡고, 내용이 넘치면 늘린다.

## 3. 생성 스크립트 작성

작업 폴더는 `/tmp/infra-diagram-<프로젝트>/`에 둔다. 예시 파일을 복사해서 시작하는 게 가장 빠르다.

```python
import os, sys
sys.path.insert(0, "<$SKILL 실제 경로>/scripts")  # $SKILL을 절대경로로 치환
from drawio_lib import *

title("<프로젝트> 인프라 구성도", "live 환경 · <근거 경로> 기준 · <YYYY-MM-DD>")
# 1) 그룹 먼저 (먼저 추가한 셀이 뒤에 깔린다)
v("g_aws", "AWS Cloud", 290, 80, 1450, 1060, grp("group_aws_cloud_alt", C.DARK))
# 2) 노드
v("cf", "<b>CloudFront</b><br>example.com", 400, 330, 64, 64, icon("cloudfront", C.NET))
# 3) 엣지: 실선 = 요청/데이터, 점선(DASH) = 설정·인증서·보조 흐름
e("e1", "users", "cf", "HTTPS", "strokeColor=#232F3E;")
save(sys.argv[1], page_w=1960, page_h=1160, name="<프로젝트> infra")
```

규칙
- **셀 id는 의미가 드러나게** 짓는다(`p_api`, `cf_front`, `e13`). 나중에 수정 패치를 할 때 문자열로 찾아 바꾸기 쉽다.
- 라벨은 `<b>이름</b><br>핵심 스펙 1–2줄`로 쓴다. 인스턴스 타입, 도메인, 포트, 버킷 이름처럼 **코드에 적힌 실제 값**을 넣는다.
- 엣지 색은 출발지 서비스 카테고리 색에 맞춘다. 주 트래픽 선은 `strokeWidth=2`로 두껍게 한다.
- 선이 박스를 가로지를 것 같으면 처음부터 `pts=[(x,y),...]` 경유점과 `exitX/exitY/entryX/entryY`를 준다.

## 4. 렌더링 → 직접 보기 → 고치기 (2–3회 반복)

```bash
python3 -I /tmp/infra-diagram-<p>/gen.py <출력경로>/infra-architecture.drawio
$SKILL/scripts/render.sh <출력경로>/infra-architecture.drawio   # 같은 이름의 .png 생성
```
렌더가 끝나면 **반드시 Read 도구로 PNG를 열어서 본다.** 렌더가 성공했다고 끝내지 않는다. 확인할 것:
- 아이콘이 빈 사각형으로 나옴 → 아이콘 이름이 틀렸다. `references/aws-icons.md`의 전체 목록에서 다시 찾는다.
- 선이 박스·라벨을 지나감 → 경유점을 바꾸거나 exit/entry 위치를 바꾼다.
- 엣지 라벨끼리 겹침 → 노드를 옮기거나, 라벨을 짧게 줄이거나, 줄을 바꾼다(`<br>`).
- 라벨이 그룹 경계 밖으로 나가거나 잘림 → 그룹 크기를 키운다.
- 한글이 깨짐 → `fonts-noto-cjk` 패키지를 설치한다.

수정할 때는 `gen.py`를 고치고 다시 렌더링한다. 변경이 작으면 `(old, new)` 치환 목록에 `assert old in s`를 붙여 패치하는 방식이 안전하다. `.drawio` XML을 직접 고치지는 않는다.
겹침이 없어지고 사람이 따라 읽을 수 있는 수준이 되면 멈춘다. 대개 2–3회면 된다.

## 5. 저장·보고

- 저장 위치는 프로젝트 관례를 따른다. 프로젝트 CLAUDE.md에 맥락 폴더 규칙이 있으면 그 규칙대로 둔다(예: `./context/infra/`). 없으면 `docs/infra/`에 둔다.
- 다시 만들 수 있도록 생성 스크립트도 프로젝트에 같이 남길지 사용자에게 한 번 묻는다. 남기지 않으면 `/tmp`에 있어서 재부팅하면 사라진다.
- 답변에 넣을 것:
  - 파일 절대경로(png는 해상도 포함)
  - 그림에 담은 것을 영역별로 요약
  - 근거로 삼은 파일
  - **코드와 실제 상태가 다를 수 있는 부분**(점검 모드, 수동으로 만든 리소스 등)
  - 다시 렌더링하는 명령 한 줄
