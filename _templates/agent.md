---
name: agent-name
description: 이 서브에이전트가 무슨 일을 하는지, 그리고 언제 호출되어야 하는지 트리거를 구체적으로 적는다. Claude는 이 문장을 보고 위임 여부를 판단하므로, 실제 사용자 표현("~해줘")을 예시로 넣으면 좋다.
tools: Read, Grep, Glob
model: sonnet
---

<!--
서브에이전트 뼈대. 새 역할을 만들 때 이 파일을 base/agents/<이름>.md 로 복사해서 채우세요.

frontmatter 규칙:
- name: 소문자-하이픈, 파일명과 일치.
- description: 필수. 무엇을 + 언제(트리거)를 구체적으로.
- tools: 이 에이전트가 쓸 도구만 최소로. 파일 수정이 필요 없으면 Edit/Write는 빼세요 (읽기 전용 역할이면 안전).
- model: sonnet(기본) / opus(어려운 추론) / haiku(가벼운 작업).
-->

너는 이 프로젝트의 <역할>이다. <임무 한 줄>.

## 작업 원칙
- 

## 작업 흐름
1. 

## 보고 형식
- 
