---
version: 1
name: control-no-rules
description: Anti-vacuity control fixture. A plausible component body that contains none of the routing rules the assertions look for.
origin: fixture
---

# control-no-rules

이 파일은 통제군(anti-vacuity control)이다. 실제 컴포넌트 본문처럼 보이지만 라우팅 규칙·Type 분기·단계 분리·fallback 문구를 전혀 담지 않는다. 6개 assertion이 이 텍스트에 대해 모두 실패해야 assertion이 vacuous하지 않음이 증명된다.

## Role and Scope

You are a component that reads an input document and reports what it found.

**Input**: a markdown document path.

**Output**: a one-paragraph summary.

## Process

1. Read the document.
2. Extract the headings.
3. Report the headings in order.

## Key Principles

- **입력을 바꾸지 않는다** — 읽기 전용으로 동작한다
- **요약은 한 문단** — 길이를 늘리지 않는다
