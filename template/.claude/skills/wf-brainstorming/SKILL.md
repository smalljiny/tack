---
version: 8
name: wf-brainstorming
description: Format-agnostic conversational skill for refining ideas through collaborative dialogue. Use when writing a spec draft or exploring problems in depth. Loaded by /flow-spec during spec draft writing.
origin: sample-claude-env
---

# Brainstorming Ideas Into Specs

## Overview

Help turn ideas into fully formed documents through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the output in small sections (200-300 words), checking after each section whether it looks right so far.

## The Process

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- Ask questions one at a time to refine the idea — always use `AskUserQuestion` (see Asking Questions below)
- Only one question per message — if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs when the direction is not already clear
- If the user has already indicated a direction, validate it rather than forcing alternatives
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Presenting the spec:**
- Once you understand what you're building, write the spec
- Break it into sections of 200-300 words
- Ask after each section whether it looks right so far — use `AskUserQuestion` for section approval too
- If a caller has injected a format (e.g., via `.tack/contracts/spec.md`), follow that format; otherwise use whatever structure fits the output
- Be ready to go back and clarify if something doesn't make sense

## Asking Questions

Always use the `AskUserQuestion` tool when asking the user anything — whether for clarification, confirmation, approach selection, or section approval.

Every question must include a recommended option:
- Mark the recommended choice as the **first option** in the list
- Add `(Recommended)` at the end of its label
- Briefly explain the reasoning behind the recommendation in the option's description

This applies to all question types: exploration, confirmation, and approval.

## Completion Signal

Present the completed output inline in the conversation.
After presenting, announce completion so the caller can save the file:

> 스펙 초안이 완성되었습니다. /flow-spec이 파일로 저장합니다.

The specific document structure (sections, headings, format) is determined by the caller. If the caller has injected a format (e.g., via `.tack/contracts/spec.md`), follow that format. Otherwise, apply the format that best fits the context.

## Key Principles

- **One question at a time** — Don't overwhelm with multiple questions
- **Use AskUserQuestion with a recommended option** — Every question must use the tool and lead with a recommendation
- **YAGNI ruthlessly** — Remove unnecessary features from all designs
- **Explore alternatives** — Propose 2-3 approaches when the direction is not already clear. If the user has indicated a direction, validate it rather than forcing alternatives.
- **Incremental validation** — Present output in sections, validate each
- **Be flexible** — Go back and clarify when something doesn't make sense
- **Mark unknowns** — Put unresolved decisions in Open Questions, never invent answers
- **Format is caller's responsibility** — Do not embed document format rules; follow injected format or adapt freely
