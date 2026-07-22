---
version: 1
---

# 자료: Claude 플러그인의 비-Claude 파일 프로비저닝 가능성

**조사 대상 (OQ1 유효 미지수)**: Claude Code 플러그인이 `.codex/`·`.harness/`·`AGENTS.md` 같은 비-Claude 파일을 target project에 provision할 수 있는가? 가능하다면 **단일 버전드 플러그인이 전체를 부트스트랩**해 Claude↔Codex 계약 버전 정합을 유지할 수 있는가?

**출처**: Claude Code 공식 문서(code.claude.com/docs) + GitHub 이슈 트래커. claude-code-guide 에이전트 조사(2026-07-21).

## 결론 — 기술적 가능, 그러나 단일-버전 보장 실패

**가능한 메커니즘 (confidence: high)**:
- 플러그인은 임의 파일·스크립트를 번들할 수 있고(`scripts/`, `bin/` 등), 훅에서 `${CLAUDE_PLUGIN_ROOT}`로 참조한다.
- 플러그인이 SessionStart 훅을 실을 수 있고, 그 훅은 `type: "command"`로 임의 스크립트를 실행한다.
- 훅은 샌드박스 없이 `${CLAUDE_PROJECT_DIR}`(프로젝트 루트)에 파일을 쓸 수 있다 → `bootstrap.sh`가 `.codex/`·`.harness/`·`AGENTS.md`를 provision 가능.

**그러나 단일-버전 보장이 깨진다 (이게 핵심)**:
| 문제 | 영향 |
|------|------|
| **비지원 패턴** | SessionStart는 문서상 "컨텍스트 로딩" 용도. 프로젝트 파일 프로비저닝은 의도된 use case 아님. `.codex`·`AGENTS.md`는 플러그인 스코프 밖 |
| **매 세션 재실행** | SessionStart는 install 시 1회가 아니라 매 세션 발화 → 멱등 필수(부담) |
| **업데이트 순서 버그** (GH #52218, #60219) | autoUpdate가 런타임을 SessionStart **이전에** 갱신하고 `installed_plugins.json`을 안 고쳐, 번들 훅이 **stale install 경로에 고정**됨 → 프로비저너가 **구 버전 경로로 실행** |
| **무음 실패** | 훅이 조용히 실패하면 비-Claude 파일이 stale → 이중 에이전트 버전 정합이 **소리 없이 깨짐** |

→ 즉 "단일 플러그인이 전체를 provision해 스큐를 없앤다"던 기대와 **반대로**, 업데이트 순서 버그가 정확히 그 **버전 스큐를 되살린다.**

## 방향 함의

- **OQ1 제약 유지·강화**: 플러그인-provisions-everything 경로는 기술적으로 실재하나 **비지원 + 스큐 재발**로 **신뢰할 base가 못 됨.** 앞서 확정한 "base는 도구-중립, 플러그인-only 배제"가 그대로 유지된다.
- **에이전트 권고(플러그인=Claude + 별도 채널=Codex/공유)는 채택 안 함** — 이는 우리가 이미 함정으로 배제한 **하이브리드**(계약을 두 버전 스트림으로 분할)다. 조사 에이전트는 이 사전 결정을 모르고 제안한 것.
- **플러그인의 역할**: 최대 **선택적 얇은 편의 계층(Claude 표면 한정)**. 비-Claude 파일 프로비저닝은 신뢰도 부족으로 base 판단에 영향 없음.
- **남는 결정(변동 없음)**: 도구-중립 base의 패키징 — 복사 스크립트 유지 vs 버전드 인스톨러. 이건 여전히 열림.

## 인용
- Plugins Reference — code.claude.com/docs/en/plugins-reference.md (훅·`${CLAUDE_PLUGIN_ROOT}`·버전·컴포넌트)
- Hooks Reference — code.claude.com/docs/en/hooks.md (SessionStart, `cwd`/`${CLAUDE_PROJECT_DIR}`)
- GH Issue #52218 — autoUpdate가 `installed_plugins.json` 미갱신
- GH Issue #60219 — plugin auto-update가 캐시 버전 고아화
