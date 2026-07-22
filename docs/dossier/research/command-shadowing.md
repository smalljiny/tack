---
version: 1
---

# 자료: command file 잔존 여부 (OQ4)

**질문**: A3에서 진입점을 user-invocable 스킬로 단일화했는데, 플러그인 command를 shadow/wrap하는 좁은 용도(현 harness `codex:setup`이 플러그인 `/codex:setup`을 shadow)에 command file이 여전히 필요한가?

**출처**: adapter-exa `/answer` (Claude Code 공식 문서 + 이슈 트래커), 2026-07-21.

## 조사 결과

- **command file은 shadowing에 불필요**: 스킬이 manual·automated 호출의 주 메커니즘. 같은 이름의 skill과 command가 있으면 **skill 우선**.
- **skill 레벨 우선순위**: enterprise > personal > project > bundled.
- **플러그인 skill·command는 `plugin-name:skill-name`으로 네임스페이스**돼 다른 레벨과 충돌 방지.
- **⚠ 그러나 플러그인 command를 가로지르는 shadowing은 버그 영역**: open issues — #44871(plugin command vs skill 네임스페이스 동작 불일치), #62500(plugin이 built-in을 예상외 shadow), #14945(같은 이름 skill이 slash command 차단). 즉 "project skill이 plugin command를 shadow"하는 정확한 경로는 보장되지 않음.

## 🟢 결정 — skills-only, command file 0, shadowing은 설계로 회피

- **tack 진입점 = user-invocable 스킬 전용, command file 없음**(A3 재확인). tack 자체 진입점엔 스킬로 충분(스킬 우선).
- **shadowing 자체를 하지 않는다**: 현 harness가 `/codex:setup`을 shadow한 건 **동일 명령 UX 연속성** 때문이었다. tack은 플러그인 command 이름을 하이재킹하지 않고 **자기 네임스페이스 진입점**(예: `flow-*` 또는 tack 소유 스킬)이 하부 도구를 위임 호출한다. → 버그 많은 네임스페이스-충돌 영역을 **애초에 안 밟음**.
- 근거: shadowing은 platform의 불안정 영역이고, tack은 그것에 의존할 이유가 없다(자기 진입점을 자유롭게 명명 가능). 이 결정은 버그가 어느 쪽으로 해소되든 robust.

**부수**: 현 harness의 나머지 command file(`harness:audit`·`harness:learn`·`add-language-rules`)은 shadow가 아닌 standalone → tack에서 그냥 스킬로 이전(A3). shadowing 대상은 `codex:setup` 하나뿐이었고, 위 회피로 해소.

## 인용
- Extend Claude with skills(우선순위·user-invocable) — code.claude.com/docs/en/slash-commands
- Create plugins(네임스페이스) — code.claude.com/docs/en/plugins.md
- 이슈 #44871·#62500·#14945 — github.com/anthropics/claude-code/issues
