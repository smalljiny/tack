# Orca 도입 사전 검토

**작성일**: 2026-07-27
**대상**: Orca v1.4.158 (앱), `orca` CLI, `orca-cli`·`orchestration` 스킬
**성격**: 개발 환경 도입 판단을 위한 사전 조사. GitHub 이슈·로드맵 트랙과 별개 검토.
**방법**: 문서 독해 + 실제 CLI 실행(probe). 모든 probe는 실행 후 정리했고 저장소 파일은 변경하지 않았다.

---

## 1. 출발 상태

| 항목 | 실측 |
|---|---|
| Orca 앱 | 실행 중 (pid 16568, v1.4.158, runtime `ready`, capability 24종) |
| 이 저장소 | Orca-managed (repoId `332248e6…`, main worktree `develop`, `workspaceStatus: in-progress`) |
| cmux | **없음** — `cmux ping` 거부, `CMUX_WORKSPACE_ID`·`CMUX_SURFACE_ID` 미설정 |

즉 도입 판단 시점에 이미 Orca가 개발 세션의 호스트였다. 반대로 하네스 `/flow-worktree`의 세션 기동 경로(S4·S5)는 cmux 의존이라 **이 환경에서 이미 무효**(수동 폴백만 동작)였다.

---

## 2. 능력 경계 — 무엇을 Orca에 맡길 수 있는가

### 2.1 하네스가 만든 worktree에 Orca가 붙을 수 있는가

`git worktree add`로 직접 만든 checkout(= Orca가 생성하지 않은 것)을 대상으로 확인:

| 시도 | 결과 |
|---|---|
| `worktree show --worktree path:<경로>` | 해석됨 — id를 `<repoId>::<path>`로 즉석 발급, 브랜치 정확 인식 |
| `terminal create --worktree path:<경로> --command '<일반 명령>'` | 성공 — cwd·브랜치 정확 |
| `terminal read` | 일반 명령 출력은 깨끗하게 회수 |
| `worktree set --comment --workspace-status` | 호출 `ok` (단 카드 UI 노출은 미확인) |
| `worktree list` 등재 | **안 됨** |
| **대화형 `claude` 기동** | **실패 2/2** — `Timed out waiting for terminal handle after creation` |
| headless `claude -p` | 성공 (정상 응답) |
| 대화형 `zsh` | 성공 |
| 래퍼 `zsh -ic claude` | 성공 (handle 발급 + `tui-idle` 대기 통과) |
| Orca-tracked worktree에서 대화형 `claude` | **성공 2/2** |

**결론**: 일반 명령·headless는 임의 worktree에서 자유롭게 되지만, **에이전트 TUI 직접 기동은 Orca-tracked worktree에서만** 된다. runtime capability `agent-session.host-authority.v1`과 일치한다. 래퍼(`zsh -ic claude`)로 우회는 되지만 문서화되지 않은 경로다.

미등재의 원인은 절대적 제약이 아니라 **repo 설정** `externalWorktreeVisibility: 'hide'`로 보인다 — 하네스가 만든 probe worktree들이 `worktreeMeta`에는 기록돼 있었다.

**결정(2026-07-27)**: 상태 조회 대상은 **Orca가 생성한 worktree로 한정**한다. 따라서 external worktree 등재 여부는 검토 항목에서 제외하고, `externalWorktreeVisibility`는 `hide` 그대로 둔다. 이 결정으로 worktree 생성 주체는 Orca로 확정되며, 하네스는 생성 이후 주입·정리만 담당한다(§4).

### 2.2 `worktree ps`의 에이전트 관측

`ps`는 worktree별 살아 있는 에이전트 세션을 함께 보고한다 — `agentType`, `state`, `prompt`, `lastAssistantMessage`, `toolName`, `paneKey`.

**등재 조건은 생성 경로가 아니라 활동(activity)이다.** 초기에 "`terminal create --command claude`로 띄운 세션은 등재되지 않는다"고 판단했으나 오독이었다. 프롬프트를 넣지 않은 idle 세션이 등재되지 않았을 뿐, 프롬프트를 전송하자 즉시 등재됐다(`state: done`, `lastAssistantMessage` 포함). headless `claude -p`도 동일하게 등재된다. 메커니즘은 Orca가 심는 에이전트 훅(`~/.orca/agent-hooks`).

### 2.3 관측성의 한계

`terminal read`는 일반 명령 출력에는 유효하지만 **TUI 세션은 1줄 깨진 스냅샷**만 돌려준다(alternate screen 미포착). "에이전트 진행을 프로그램으로 관찰"하는 이점은 `ps`의 에이전트 필드로 얻고, `terminal read`로는 얻기 어렵다. 반면 `terminal wait --for tui-idle`은 정상 동작해 **프롬프트 주입 시 입력 유실 방지**라는 실익은 확인됐다.

---

## 3. worktree 배치·브랜치 명명

### 3.1 배치 경로 규칙 (앱 코드 확인)

```js
function computeWorktreePath(sanitizedName, repoPath, settings) {
  const workspaceRoot = computeWorkspaceRoot(repoPath, settings);
  if (settings.nestWorkspaces) {
    const repoName = basename(repoPath).replace(/\.git$/, "");
    return join(workspaceRoot, repoName, sanitizedName);
  }
  return join(workspaceRoot, sanitizedName);
}
function getWorktreePathSettings(repo, settings) {
  return { nestWorkspaces: settings.nestWorkspaces,                     // 전역만 참조
           workspaceDir: getEffectiveWorktreeBasePath(repo, settings) }; // 여기만 repo 스코프
}
```

프로젝트 스코프 `worktreeBasePath`는 **베이스 루트만** 대체하고, `nestWorkspaces`는 전역 값을 따라 repo 이름 서브폴더를 추가한다. 두 축이 직교한다.

| worktreeBasePath | nestWorkspaces | 결과 |
|---|---|---|
| (미설정) | on | `<workspaceDir>/tack/<name>` = **repo 내부** (초기 상태) |
| `../tack.worktrees` | on | `tack.worktrees/tack/<name>` (중간 상태) |
| `../tack.worktrees` | **off** | `tack.worktrees/<name>` ← **목표 달성, 현재 설정** |

repo 내부 배치는 (a) 부모 프로젝트 CLAUDE.md 이중 로드, (b) main 작업 트리에 `?? <name>/` 누출(Orca가 gitignore·exclude 등록을 하지 않음)을 유발한다. 실측으로 확인: 목표 배치에서 로드되는 CLAUDE.md는 `~/.claude/CLAUDE.md`(글로벌) + worktree 자신 것 **둘뿐**이었다.

UI 위치 — Settings → Repository 페인의 **"Worktree Location"**(리셋 버튼 "Use Global"), Settings → General → Workspace의 **"Nest Workspaces"**·**"Workspace Directory"**.

**주의**: `nestWorkspaces`는 전역이라 `worktreeBasePath` 미지정 repo(`cygnus`·`muhan`·`marketing-strategist`)는 `<workspaceDir>/<name>`에 repo 구분 없이 평면 배치된다. 각 repo에도 `Worktree Location`을 지정해야 관례가 유지된다.

### 3.2 브랜치 명명 (앱 코드 확인)

```js
computeBranchName(sanitizedName, settings, gitUsername) {
  const prefix = getConfiguredBranchPrefix(settings, gitUsername);
  return prefix ? `${prefix}/${sanitizedName}` : sanitizedName;
}
selectBranchPrefixInput(settings, gitUsername) {
  switch (settings.branchPrefix) {
    case "git-username": return gitUsername;   // 검토 초기값 → smalljiny/
    case "custom":       return settings.branchPrefixCustom ?? null;
    case "none":         return null;
  }
}
sanitizeWorktreeName(input) {
  input.trim().replace(/[^\p{L}\p{N}._-]+/gu, "-")   // 슬래시가 '-'로 치환
}
```

- 접두는 **전역 설정 1개**, 모드 3종(`git-username`/`custom`/`none`).
- `worktree create`에 브랜치 지정 플래그가 **없다**.
- 이름에 접두를 심는 우회도 불가 — `--name feature/login` → `feature-login`.

따라서 작업 성격별 접두(feature/fix/chore/hotfix)를 생성 시점에 고를 수 없다. 대신 **사후 rename이 완전히 동작**한다:

```
git -C <wt> branch -m hotfix/worktree1
→ orca worktree show:  refs/heads/hotfix/worktree1   (즉시 반영)
→ id 불변 (경로 기반), displayName 불변
```

worktree id가 경로 기반이라 브랜치를 바꿔도 핸들·세션·메타데이터가 끊기지 않는다.

**권고**: `branchPrefix = none` + 하네스가 `git branch -m <type>/<topic>`으로 접두 부여.

### 3.3 `autoRenameBranchFromWork` (기본 on, 현재 on) — 위험도 하향 정정

앱 코드에 `buildBranchNamePrompt`가 있어 **에이전트의 첫 프롬프트를 근거로 LLM이 브랜치명을 생성해 자동 rename**한다. 초기에는 이것이 teardown T3(`merge-base --is-ancestor <branch> …`)·T5(`branch -d <branch>`)의 대상을 잃게 만든다고 보고 "끄는 것을 권고"했으나, **게이트 조건을 확인한 결과 CLI 경로에서는 발동하지 않는다.**

앱 UI 설명 문구:

> Auto-rename branch & worktree — When an agent starts working in a new workspace, Orca renames its auto-generated branch (e.g. `Nautilus`) to a short name summarizing the task. **Only branches Orca named itself are renamed, and never after they have been pushed.**

생성 시점 게이트(난독화 해제):

```js
Qa = Ht && settings.autoRenameBranchFromWork === true
     && !explicitName.trim()      // 워크스페이스 이름을 비워 둔 경우만
     && !!selectedAgent           // 컴포저에서 에이전트를 고른 경우만
     && !branchNameOverride
     && !explicitDisplayName;
// → worktree meta 에 pendingFirstAgentMessageRename: Qa 로 기록
```

즉 (a) 이름을 비운 채 UI 컴포저로 만들고 (b) 그 자리에서 에이전트를 선택한 워크스페이스에만, (c) Orca가 스스로 지은 브랜치에 한해, (d) push 전에만 적용된다. 판정은 **생성 시점에 고정**된다.

**실측**: `orca worktree create --name worktree2`(명시 이름) → `git branch -m feature/worktree2` → 에이전트 기동 → 프롬프트 1회 완료(`state: done`) 후 2분간 폴링. 브랜치는 `feature/worktree2` 그대로였다. 발동하지 않았다.

**정정된 권고**: 하네스는 항상 `--name <topic>`을 명시하는 CLI 경로를 쓰므로 이 설정을 **끌 필요가 없다**. 다만 사람이 UI 컴포저에서 이름을 비우고 에이전트를 골라 워크스페이스를 만드는 경우에는 발동하므로, 그 사용 패턴을 병행한다면 끄는 편이 안전하다.

---

## 4. 통합 형태 실증 — 하네스 스크립트 무수정 동작

`worktreeBasePath=../tack.worktrees` + `nestWorkspaces=off` 조합에서 Orca의 배치가 하네스 스크립트의 경로 유도(`$(dirname MAIN)/$(basename MAIN).worktrees/<topic>`)와 **동일**해진다. 그 결과:

| 단계 | 결과 |
|---|---|
| `orca worktree create --name worktree1 --no-parent --base-branch develop` | `~/Workspace/tack.worktrees/worktree1`, 브랜치 `smalljiny/worktree1`, main status clean |
| `bash provision.sh worktree1` | **무수정 동작** — `[1] worktree exists — skip create` → 심링크(`.claude`·`.codex`·`AGENTS.md`·`CLAUDE.md`) + `.harness` copy + `docs/_local` + dev-context 주입 → worktree git status **clean** |
| CLAUDE.md 계보 | worktree 자신 것 1개 (이중 로드 없음) |
| dev-context 격리 | worktree `current_topic=worktree1` / main 빈 값 |
| 에이전트 TUI | 기동 → `tui-idle` → 프롬프트 → 응답, `ps.agents` 등재 |
| `bash teardown.sh worktree1` | **무수정 동작** — done 아카이브 sync-back → main stale 원본 폐기 → `git worktree remove` 성공 → 브랜치 보존 |

즉 통합 형태는 다음과 같이 정리된다. §2.1 결정에 따라 **생성 주체는 Orca로 확정**이며, 하네스가 `git worktree add`로 직접 만드는 경로는 쓰지 않는다.

```
orca worktree create --name <topic> --base-branch develop
                                         ← Orca 소유 (checkout + 카드 + 트래킹). base 지정 필수 — 아래 4.1
bash provision.sh <topic>                ← 하네스 소유 (컨텍스트 주입, 무수정)
git branch -m <type>/<topic>             ← 하네스 소유 (작업 성격별 접두)
orca terminal create --command claude     ← Orca 소유 (세션 + ps 관측)
… 작업 …
[Orca 터미널 정리]                        ← 필수, §6-1
bash teardown.sh <topic>                 ← 하네스 소유 (게이트 → sync-back → 제거)
```

### 4.1 정정 — `--base-branch develop`은 부수 사항이 아니라 필수 (2026-07-27)

위 표 1행은 `--base-branch develop`을 probe 세부로 기록했지만, **이 플래그가 통합 형태를 지탱하고 있었다.**

- `provision.sh`의 base 기본값은 `develop`이지만(`BASE="develop"`, 73행 `git worktree add "$WT" -b "$BRANCH" "$BASE"`), Orca가 먼저 checkout을 만들면 `[ -d "$WT" ]` 멱등 분기가 생성을 건너뛰므로 **그 기본값은 발동하지 않는다.** §4가 "무수정 동작"으로 칭찬한 멱등성이, 동시에 base 결정을 조용히 삼키는 성질이다.
- 플래그를 빼면 Orca는 repo 기본 base를 쓴다. 실측: `orca repo show`에 base ref **미설정**, `git symbolic-ref refs/remotes/origin/HEAD` → `origin/main`. 즉 **현재 설정에서 Orca가 만드는 worktree는 전부 `main` 기반**이며, 하네스 통합 브랜치인 `develop`이 아니다. 기억해야 할 플래그 하나가 아니라 현재 설정이 틀린 상태다.
- 가이드도 같은 방향을 규정한다 — `--no-parent`는 Orca lineage만 정하고 git base는 별개이며, base는 repo 기본값을 쓰라고 한다.

**조치(2026-07-27, 적용 완료)**: repo base ref를 `origin/develop`로 설정했다. 앱 UI로 만든 worktree까지 함께 교정되므로, 매번 플래그를 붙이는 방식보다 낫다.

```
orca repo set-base-ref --repo id:332248e6-8392-42d2-930b-8dc15d5529c2 --ref origin/develop --json
→ repo.worktreeBaseRef: "origin/develop"
```

이로써 `orca worktree create --name <topic>`은 플래그 없이도 develop 기반이 된다. 위 통합 형태 블록의 `--base-branch develop`은 명시성을 위해 남겨 두되, 더는 유일한 방어선이 아니다.

### 철회한 초기 판단 3건

1. **"경로·브랜치 소유권이 통합의 discriminator"** — Orca가 생성을 소유한다는 전제 위의 분석이었다. 배치 설정으로 경로가 일치하면 무력화된다.
2. **"`provision.sh`에 `--wt` 오버라이드가 없어 스크립트 수정이 필요하다"** — `[ -d "$WT" ]` 멱등 구조라 주입 전용으로 그대로 재사용된다.
3. **"`terminal create --command claude`는 `ps.agents`에 등재되지 않아 주입 타이밍과 관측성이 상충한다"** — 등재는 활동 기준이다. 상충 없음.

---

## 5. Orca에 넘기지 말아야 할 것

**`orca worktree rm`** — 주입물(`.harness` copy, `docs/_local`)이 있는 worktree를 `--force` 없이 경고 없이 삭제했고 **브랜치까지 제거**했다(plain `git worktree remove`는 거부해서 `--force`가 필요했던 상황). sync-back 개념이 없으므로 `docs/_local/done/<topic>/` 같은 git-ignored 산출물이 조용히 소실된다.

→ **완료 게이트 → sync-back → 제거** 순서는 어떤 통합 형태에서도 하네스가 소유한다. 제거 실행 자체는 Orca가 해도 된다.

---

## 6. 남은 실무 이슈

1. **고아 터미널** — `teardown.sh`가 worktree를 제거해도 Orca 터미널(fallback 셸 + claude 세션)이 사라진 경로를 가리킨 채 남는다. Orca가 자동 회수하지 않는다. 제거 **전에** `terminal list --worktree <selector>` → 각 handle `terminal close`가 필요하다.
2. **브랜치명 하드코딩** — `teardown.sh` 출력과 `flow-worktree` T3·T5가 `feature/<topic>`을 가정한다. 작업 성격별 접두를 쓰려면 브랜치명을 dev-context에 기록하고 T3·T5가 그것을 읽어야 한다.
3. **bare create의 fallback 셸** — `--agent` 없이 만들면 셸 탭이 하나 생기고, 뒤에 `terminal create --command claude`를 붙이면 탭이 2개가 된다(실측 `liveTerminals=2`). **해소(2026-07-27)**: 버전 정합 가이드가 agent-first(`worktree create --agent <agent>`)를 규정하며, 정확히 이 셸+에이전트 쌍을 피하기 위한 것이라고 명시한다. 2단계 경로는 커스텀 argv(Codex `--model`·effort)가 필요할 때만 쓴다.
4. **`terminal close`의 `tab_not_found`** — 종료되는 `--command`는 탭을 함께 데려간다. close 실패는 best-effort로 흘려야 한다.
5. **CLI 이름 위험** — 실행체 해석은 `ORCA_CLI_COMMAND` → `orca-dev` → `orca-ide` → `orca` 순. **Linux에서 bare `orca`는 GNOME 스크린리더**를 켠다.

---

## 7. 설정 현황·권고

| 설정 | 스코프 | 현재 | 권고 |
|---|---|---|---|
| `worktreeBasePath` | repo | `../tack.worktrees` | 유지 ✅ |
| `nestWorkspaces` | 전역 | off | 유지 ✅ (타 repo도 `Worktree Location` 지정 필요) |
| `workspaceDir` | 전역 | `/Users/mario/Workspace` | 유지 |
| `branchPrefix` | 전역 | **`none`** ✅ | 유지 (실측: 브랜치 `worktree2` — 접두 없음) |
| `autoRenameBranchFromWork` | 전역 | on | 유지 가능 — CLI 경로 미발동 확인(§3.3). UI 컴포저 병행 시에만 off |
| `externalWorktreeVisibility` | repo | `hide` | 유지 — Orca 생성 worktree만 조회하기로 결정(§2.1), 검토 종료 |
| `setupScriptLaunchMode` / `hookSettings.scripts.setup` | repo | `new-tab` / 빈 값 | 현행 유지 (주입을 setup hook에 넣을 필요가 없어짐 — §4 철회 3) |
| `worktreeBaseRef` | repo | **`origin/develop`** ✅ (2026-07-27 설정, 이전 미설정 → `origin/main` 상속) | 유지 — §4.1. 이 표에서 유일하게 CLI로 변경 가능: `orca repo set-base-ref` |

base ref를 제외한 위 설정은 CLI에 setter가 없어(206개 커맨드 전수 확인) 앱 UI에서 변경한다.

---

## 8. orchestration 스킬 검토

**가용성**: `orca orchestration task-list --json` → `ok, tasks: []` 정상 응답. `orchestration.db`(94KB) 존재. 설정 목록에 orchestration 전용 실험 플래그 키는 보이지 않았다(가이드는 Settings > Experimental 활성화를 전제로 명시).

**미해결 — 실험 플래그가 무엇을 게이트하는가(2026-07-27)**: `task-list`가 응답한다는 사실은 플래그 활성화의 증거가 아니다. 읽기 RPC는 열어 두고 `dispatch --inject`만 막을 수 있다. `orca status --json`의 runtime capability 24종에 orchestration 항목이 없고 CLI에 settings setter도 없어(206개 커맨드 전수 확인) 비파괴적으로 판정할 수단이 없다. **실제 dispatch 시도가 유일한 판별자이며, 이것이 §8.2 P1을 그대로 가로막는다** — 파일럿을 재개한다면 첫 단계는 앱 UI에서 플래그 상태를 눈으로 확인하는 것이다.

**참조 방식**: 스킬 파일(`~/.claude/skills/orchestration/SKILL.md`, 83줄)은 **discovery stub**이고, 실제 커맨드 표면은 `orca skills get orchestration`(254줄)이 바이너리에서 버전 정합으로 발급한다. stub은 "릴리스마다 플래그가 바뀌므로 캐시된 사본에서 서브커맨드를 추측하지 말 것"을 명시한다 — 아래 분석은 v1.4.158 발급본 기준이다.

**제공하는 것**: 터미널 단위 다중 에이전트 코디네이션 — 스레드 메시지(`send`/`reply`/`ask`/`check`), 태스크·디스패치(`task-create`/`dispatch --inject`/`task-list`), DAG 의존성, 결정 게이트(`gate-create`/`gate-resolve`), 코디네이터 루프(`run`), 워커 생애주기(`worker_done`/`heartbeat`/`escalation`). 상태는 **runtime-global**이며 `reset`도 전역이다.

**하네스와의 층위 비교**

| 층 | 대상 | 상태 | 교차 벤더 |
|---|---|---|---|
| Claude Code 서브에이전트 | 한 세션 안의 in-process 에이전트 | 세션 한정, 비영속 | 불가 |
| Orca orchestration | 별도 터미널의 에이전트 CLI 프로세스 | runtime-global 영속 | 가능 (claude·codex·opencode·gemini…) |
| 하네스 `flow-*` | 워크플로우 단계·상태 머신 | `dev-context.json`, per-worktree | — |

**적합해 보이는 용처**: (a) Codex spec/plan 리뷰를 추적 가능한 dispatch로 승격(현재 `adapter-codex-review`는 `codex exec` 일회성), (b) 병렬 story 운용(로드맵 CP2), (c) 리뷰 패널을 별 프로세스로 병렬화, (d) 장시간 작업 감독(`check --wait` 롤링).

**(a)가 가장 강한 정합 신호**: 가이드는 **review-only `worker_done`은 소견을 보고할 뿐 코디네이터의 파일 편집을 승인하지 않는다**고 규정하고, 리뷰 완료 후 코디네이터는 소견을 종합해 결정 게이트를 걸거나 수정을 별도 dispatch·handoff하라고 한다. 이는 `adapter-codex-review`가 Decision(`READY`/`READY WITH NOTE`/`NOT READY`)만 반환하고 수정은 호출자가 소유하는 현행 계약과 **구조적으로 동일**하다. 위 C1~C5와 달리 이 지점에는 충돌이 없다.

**마찰·리스크** (가이드 확인 후 구체화, 2026-07-27):

| # | 충돌 | 가이드 근거 | 하네스 측 |
|---|---|---|---|
| C1 | **워커 배치 정책이 정반대** — 가이드는 "독립 태스크·병렬 실행·편의·별도 checkout 선호는 격리 요구가 아니다"라며 신규 worktree 생성을 기본 금지하고 같은 worktree에 fresh 터미널을 권한다. 하네스는 토픽별 worktree 격리(per-worktree `dev-context.json`)가 설계 전제다 | 가이드 "Worker Terminals" | `/flow-worktree`, `wf-worktree-context` |
| C2 | **서브에이전트 금지 규정** — "비-Orca 서브에이전트 도구·generic agent-spawn API·chat-only 병렬 워커로 대체하지 말 것". 하네스는 code-reviewer·tdd-specialist in-process 자동 활성화를 강제한다. dispatch된 워커 안에서 두 지시가 정면 충돌 | 가이드 "Tool Boundary" | `.claude/rules/common/agents.md` |
| C3 | **진실 원천 이중화** — orchestration 상태는 runtime-global, `dev-context.json`은 per-worktree. 태스크 status(`pending`/`ready`/`dispatched`/`completed`/`failed`/`blocked`)와 phase\:status가 독립 전이 | 가이드 "Ownership" | `meta-dev-context` |
| C4 | **git base 규정** — `--no-parent`는 Orca lineage만 정하고 git base는 별개이며, 명시 요청 없이 현재 feature 브랜치를 base로 삼지 말라고 규정. §3.2의 `branchPrefix=none` + 사후 `git branch -m <type>/<topic>` 결정과 맞물린다 | 가이드 "Full Handoffs" | §3.2, `teardown.sh` |
| C5 | **handoff/supervised 오분류** — 구분이 자연어 트리거("hand off", "supervise") 기반이라 하네스 커맨드가 프로그램적으로 부를 때 어느 쪽으로 분류되는지 불명 | 가이드 "When To Use" | `flow-*` 호출 경로 |
| C6 | 워커마다 별도 CLI 세션 → 토큰 비용 곱셈 / worktree 제거 시 dispatch·터미널 고아화(§6-1) | — | — |

**lifecycle 권한 모델 (P3 실패 모드가 구체화됨)**: 권한은 터미널 handle이 아니라 활성 dispatch의 `taskId`+`dispatchId`를 **dispatch된 pane과 대조**해 검증한다. handle은 라우팅 메타데이터일 뿐이라 재시작 후 바뀔 수 있고, 다른 pane에서 보낸 `worker_done`·`heartbeat`는 런타임이 **조용히 무시**한다. 따라서 P3는 "충돌을 관찰해 보자"가 아니라 "워커가 하네스 규칙을 따라 서브에이전트로 분기하면 lifecycle 신호가 무효화돼 코디네이터가 무한 대기한다"는 특정 실패 모드 검증이다.

**§8이 놓쳤던 운영 계약 4건**:
- 한 태스크에서 **3회 연속 실패 시 dispatch 컨텍스트가 circuit-break**되고 태스크가 failed로 마킹된다.
- `check --wait`는 **한 번에 메시지 1건**만 반환 — N개 워커가 동시에 끝날 수 있으면 N회 루프하고 매 완료마다 ready 태스크를 재디스패치한다.
- DAG 의존 체인은 **3~4단계 이내** 권장, `task-list --ready`를 외부 메모리로 사용.
- `check --wait` 타임아웃·`{count:0}`은 실패가 아닌 checkpoint다(실코딩 태스크 15~60분 상정). heartbeat·화면 활동은 "살아 있음"이지 "완료"가 아니다.

**로드맵 영향(중요)**: 로드맵 E4는 "ContextStore + Mongo shared registry + lease + CLI 대시보드"를 계획한다. orchestration + `worktree ps`가 태스크 레지스트리·소유권(디스패치)·상태 대시보드를 **이미 상당 부분 제공**한다. 도입을 결정하면 E4 범위를 재산정할 필요가 있다.

**판별 기준(E4 재산정 여부)**: orchestration 상태는 **runtime-global이자 단일 런타임 로컬**이다(`orchestration.db`, `reset`도 전역). E4의 Mongo shared registry는 **세션·머신을 가로지르는 공유**가 목적이다. 두 요구가 같은 범위인지가 재산정의 판별 기준이며, 현 시점에 E4가 흡수된다고 단정하지 않는다.

**adapter 설계 제약**: stub이 "릴리스마다 바뀌므로 캐시 사본에서 플래그를 추측하지 말 것"을 명시하므로, `adapter-orca-orchestration`은 커맨드 표면을 SKILL.md에 동결할 수 없고 **런타임에 `orca skills get orchestration`으로 가이드를 받아 따라야** 한다. 이는 하네스의 "Stated Invocation Form" 규칙(`.claude/rules/common/agents.md` — 명세에 적힌 호출 형태를 그대로 쓴다)과 형식상 충돌하므로, 그 스킬의 stated form 자체를 **"가이드를 받아 그것을 따른다"**로 정의해 해소한다. 어댑터 작성 전에 확정할 설계 결정이다.

### 8.1 결정: 미채택 (2026-07-27)

**orchestration 스킬은 채택하지 않는다.** §4의 orca-cli 계층(worktree·터미널·`tui-idle`·`ps`)은 그대로 유지한다 — 별개 계층이고 이미 무수정 end-to-end로 실증됐다.

**근거 3가지**

1. **정책 층위 정면 충돌 (결정적)** — C1(worktree 격리 금지 vs 토픽별 격리 전제)·C2(비-Orca 서브에이전트 금지 vs code-reviewer·tdd-specialist 자동 활성화)는 튜닝으로 흡수되지 않는다. 각 층위에서 둘 다 옳은 규정이라 예외 한 줄로 접히지 않고, 도입하려면 하네스가 자기 설계 전제 둘을 dispatch 컨텍스트 한정으로 꺼야 한다. 그 조건부 규칙이 워커 프롬프트 안에서 신뢰성 있게 지켜진다고 볼 근거가 없다.
2. **얻는 것이 작다** — 정합이 확인된 유일한 용처(Codex 리뷰 dispatch화)에서 추가되는 것은 task/dispatch provenance인데, 하네스는 이미 `spec-review-*.md` 파일 + `dev-context.json` phase로 같은 추적을 한다. 실제 빈칸은 병렬 story 운용(CP2)이고, 거기가 C1이 정통으로 때리는 지점이다.
3. **부수 비용이 한 방향** — Experimental 플래그 의존(P0 미확인), runtime-global 상태로 인한 진실 원천 이중화 + 전역 `reset`, 커맨드 표면 동결 불가로 런타임 가이드 페치가 강제되는 어댑터, 워커당 CLI 세션 토큰 곱셈.

**인정하는 반례**: `check --wait --types worker_done,escalation`의 롤링 감독 루프는 자체 구현하면 성가시다(타임아웃≠실패, 한 번에 1건, 3연속 실패 circuit-break). CP2에서 이 루프를 직접 짜게 되면 그 자체가 재검토 신호다.

**재검토 조건** — 둘 이상 성립 시 §8.2 파일럿을 재개한다:
- (a) orchestration이 experimental 단계를 벗어남
- (b) 워커 배치를 호출자가 지정할 수 있게 되어 C1 해소
- (c) CP2 병렬 운용에서 자체 감독 루프가 실제 부채로 드러남

**보존 사유**: 아래 §8.2와 위 C1~C6·운영 계약 분석은 삭제하지 않고 남긴다. 재검토 조건 충족 시 그대로 재사용하며, 사전 등록한 판정 기준을 결과에 맞춰 사후 조정하지 않기 위해서다.

### 8.2 파일럿 계획 — **보류** (미실행, 재검토 조건 충족 시 재개)

**상태**: 2026-07-27 §8.1 결정으로 보류. 실행하지 않았다. 아래는 사전 등록된 원안 그대로이며, 재개 시 수정 없이 사용한다.

문서 독해만으로는 판단이 서지 않는 항목을 실측으로 좁히기 위한 최소 시나리오. **실행 전에 기록해 두어, 결과에 맞춰 기준을 사후 조정하지 않도록 한다.**

**대상**: 신규 worktree를 파일럿 시점에 만든다. 당초 대상이던 `worktree2`는 2026-07-27 probe 정리로 제거됐다(부록). 하네스 규칙 충돌(P3) 관측이 목적이면 `provision.sh <topic>`으로 컨텍스트를 선행 주입한다.

**절차**: `task-create` → `dispatch --to <handle> --inject` → `check --wait --types worker_done,escalation,decision_gate` → `dispatch-show`/`task-list`로 상태 확인.

**측정 항목**

| # | 질문 | 판정 기준 |
|---|---|---|
| P0 | Settings > Experimental의 orchestration 플래그가 켜져 있는가 (읽기 RPC 응답은 증거가 아님 — §8 "미해결") | 앱 UI에서 육안 확인. 꺼져 있으면 P1 이후 전부 실행 불가 |
| P1 | `--inject`가 실행 중인 claude TUI에 preamble을 실제로 전달하는가 | 워커 화면에 TASK 블록이 뜨고, `dispatch-show`가 dispatch 존재를 보고 |
| P2 | 워커가 `worker_done`을 자력으로 보내는가 | 코디네이터의 `check --wait`가 `worker_done` 1건 수신, `task-list` 상태가 `completed` |
| P3 | 주입된 preamble이 하네스 규칙(CLAUDE.md·`.claude/rules`)과 충돌하는가 — 특히 C2(서브에이전트 금지 vs 자동 활성화) | 워커가 code-reviewer 등 in-process 서브에이전트로 분기하는지, 그 경우 `worker_done`이 다른 pane에서 발신돼 무시되며 코디네이터가 무한 대기하는지 |
| P4 | 상태 이중화가 실제 문제인가 | orchestration 태스크 상태와 `dev-context.json` phase가 어긋나는 지점을 기록 |
| P5 | 비용 | 워커 세션 1건의 토큰 소비를 `ps`·워커 화면으로 개략 확인 |

**중단 조건**: `--inject` 2회 연속 실패, 또는 워커가 하네스 규칙을 깨는 파일 수정을 시도할 때 즉시 중단한다.

**정리 절차**: `orchestration reset --tasks`는 **runtime-global**이라 다른 진행 중 코디네이션까지 지운다. 파일럿 종료 시에는 `task-list`로 잔여를 확인하고 개별 `task-update`로 닫는 것을 우선하며, `reset`은 잔여가 이 파일럿 것뿐임을 확인한 뒤에만 쓴다.

---

## 9. 종합 판단

범위를 둘로 나눠 판단한다.

**worktree·터미널 계층(orca-cli, §2~§7) — 조건부 도입 권장.** 근거: (a) 이미 개발 세션의 호스트이고 cmux는 부재라 현행 경로가 무효, (b) 배치·브랜치 설정을 맞추면 하네스 스크립트가 **무수정으로** 동작함을 end-to-end로 실증, (c) `tui-idle` 대기·`ps` 에이전트 관측은 blind `cmux send` 대비 실질적 개선.

**두 계층의 판정이 갈리는 구조적 이유** (양쪽 버전 정합 가이드 대조, 2026-07-27):

1. **금지 규정의 소재** — C1(병렬·독립 작업을 위한 worktree 생성 금지)과 C2(비-Orca 서브에이전트 금지)는 **orchestration 가이드의 "Worker Terminals"·"Tool Boundary"에만** 있다. orca-cli 가이드(331줄)에는 둘 다 없고, `worktree create`·lineage 플래그·`--parent-worktree`를 자유롭게 제공한다. orchestration을 탈락시킨 검사를 orca-cli가 통과하는 것은 이 비대칭 때문이다.
2. **의존 방향** — `provision.sh`·`teardown.sh`는 순수 `git worktree` + 파일 조작이고 `orca`를 호출하지 않는다. Orca는 **선택적 호스트**이지 런타임 의존이 아니다. Orca가 꺼져 있거나 미설치여도 worktree 생애주기는 그대로 돈다. orchestration은 도입되면 필수 경로가 됐겠지만, orca-cli는 그렇지 않다.

**이 계층의 마찰 2건** (해소 가능, 차단 사유 아님):
- 가이드는 "`terminal send` 전에 `terminal read`를 쓰라"고 하지만, §2.3 실측대로 TUI 세션의 `terminal read`는 깨진 1줄만 반환한다(alternate screen 미포착). cursor 페이징도 이를 해결하지 않는다. 하네스의 send 경로는 `terminal wait --for tui-idle`에 의존한다 — 실측으로 정상 동작을 확인한 쪽이다.
- 가이드가 `worktree rm`의 통상 형태로 `--force`를 예시한다. §5가 주입물·브랜치 소실을 확인한 바로 그 호출이다. 따라서 도입 규칙 1을 "쓰지 않는다"로 **명시 진술**해야 하며, 기본값으로 안전할 거라 가정하지 않는다.

**활용 기회 1건** (설계는 별도): `worktree set --workspace-status <todo|in-progress|in-review|completed>`·`--comment`가 하네스 phase 전이와 대응한다. 단 두 번째 쓰기 대상이 생기므로 **투영 전용**으로 한정한다 — 진실 원천은 `dev-context.json`, 카드 상태는 파생 표시.

**orchestration 계층(§8) — 미채택.** C1(worktree 격리 정책 정면 충돌)·C2(서브에이전트 금지 규정)가 결정적이고, 정합이 확인된 유일한 용처는 기존 추적 수단과 중복된다. 결정 근거·재검토 조건은 §8.1, 보류된 파일럿 원안은 §8.2.

**도입 규칙 3개** (worktree·터미널 계층)
1. `orca worktree rm`을 하네스 토픽에 직접 쓰지 않는다(§5).
2. worktree 제거 전에 Orca 터미널을 닫는다(§6-1).
3. 브랜치 접두는 하네스가 rename으로 부여한다 — `branchPrefix=none` 전제(§3.2).

**열린 확인거리 없음.** orchestration 파일럿은 §8.1 미채택 결정으로 보류(§8.2), `branchPrefix=none` 재실측·자동 rename 게이트는 2026-07-27 완료(§3.2·§3.3·§7), `externalWorktreeVisibility`는 §2.1 결정으로 종료, bare create fallback 셸은 가이드 확인으로 해소(§6-3). 남은 것은 아래 수정 과제 2건뿐이다.

**하네스 쪽 수정 과제 3건** (도입 확정 시)
1. worktree 제거 전 Orca 터미널 정리 단계 추가 — `flow-worktree` T7을 T4(제거)보다 앞으로(§6-1).
2. `teardown.sh`·`flow-worktree` T3·T5의 `feature/<topic>` 하드코딩을 dev-context 기록 기반으로 전환(§6-2).
3. ~~base 브랜치 확정~~ — **완료(2026-07-27)**: repo base ref를 `origin/develop`로 설정(§4.1). 배포 대상 프로젝트에 하네스를 옮길 때는 해당 repo에도 같은 설정이 필요하다.

---

## 부록: probe 이력

probe는 실행 후 정리했고, 매회 다음을 검증했다 — `git worktree list` 정리, 브랜치 삭제, `.git/info/exclude` 백업 대비 무변경, main `docs/_local/dev-context.json` 무변경, main `git status` clean.

**정리 완료(2026-07-27)**: 마지막까지 남아 있던 `worktree2`도 제거했다 — Orca 터미널 2개 close(1건 성공, 1건 `tab_not_found`로 best-effort 통과 §6-4) → `git worktree remove` → `git branch -d feature/worktree2`(develop에 이미 포함, 고유 커밋 0). 잔여 worktree는 main(`develop`) 하나뿐이며 main status clean.

| probe | 목적 | 산출 |
|---|---|---|
| `__orca_probe` | 하네스 생성 worktree에 Orca 부착 가능성 | path 셀렉터 해석·터미널 생성 성공 |
| `orca-probe` | 에이전트 TUI 기동 경계 | 대화형 claude 2/2 실패, headless·zsh·래퍼 성공 |
| `orcaprov` | Orca 생성 + 수동 주입 | 격리 성립, TUI 성공, `rm`이 주입물·브랜치 삭제 |
| `orcaprov2` | `--agent` 경로의 `ps` 등재 | `agents[{state,lastAssistantMessage}]` 확인 |
| `wtplace` | `worktreeBasePath` 적용 | `tack.worktrees/tack/wtplace` (nest 잔존) |
| `worktree1` | 최종 형태 end-to-end | 배치 일치, provision·teardown 무수정 통과, 브랜치 rename 추적 확인 |
| `worktree2` | `branchPrefix=none` 재실측 + 자동 rename 검증 | 브랜치 `worktree2`(접두 없음), 사후 rename 반영(수 초 지연 후 일치), 자동 rename 미발동 |
