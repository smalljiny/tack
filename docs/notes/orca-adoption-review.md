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
orca worktree create --name <topic>      ← Orca 소유 (checkout + 카드 + 트래킹)
bash provision.sh <topic>                ← 하네스 소유 (컨텍스트 주입, 무수정)
git branch -m <type>/<topic>             ← 하네스 소유 (작업 성격별 접두)
orca terminal create --command claude     ← Orca 소유 (세션 + ps 관측)
… 작업 …
[Orca 터미널 정리]                        ← 필수, §6-1
bash teardown.sh <topic>                 ← 하네스 소유 (게이트 → sync-back → 제거)
```

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
3. **bare create의 fallback 셸** — `--agent` 없이 만들면 셸 탭이 하나 생기고, 뒤에 `terminal create --command claude`를 붙이면 탭이 2개가 된다(실측 `liveTerminals=2`).
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

CLI에 settings setter가 없다(206개 커맨드 전수 확인). 위 설정은 모두 앱 UI에서 변경한다.

---

## 8. orchestration 스킬 검토

**가용성**: `orca orchestration task-list --json` → `ok, tasks: []` 정상 응답. `orchestration.db`(94KB) 존재. 설정 목록에 orchestration 전용 실험 플래그 키는 보이지 않았다(스킬 문서는 Settings > Experimental 활성화를 전제로 명시).

**제공하는 것**: 터미널 단위 다중 에이전트 코디네이션 — 스레드 메시지(`send`/`reply`/`ask`/`check`), 태스크·디스패치(`task-create`/`dispatch --inject`/`task-list`), DAG 의존성, 결정 게이트(`gate-create`/`gate-resolve`), 코디네이터 루프(`run`), 워커 생애주기(`worker_done`/`heartbeat`/`escalation`). 상태는 **runtime-global**이며 `reset`도 전역이다.

**하네스와의 층위 비교**

| 층 | 대상 | 상태 | 교차 벤더 |
|---|---|---|---|
| Claude Code 서브에이전트 | 한 세션 안의 in-process 에이전트 | 세션 한정, 비영속 | 불가 |
| Orca orchestration | 별도 터미널의 에이전트 CLI 프로세스 | runtime-global 영속 | 가능 (claude·codex·opencode·gemini…) |
| 하네스 `flow-*` | 워크플로우 단계·상태 머신 | `dev-context.json`, per-worktree | — |

**적합해 보이는 용처**: (a) Codex spec/plan 리뷰를 추적 가능한 dispatch로 승격(현재 `adapter-codex-review`는 `codex exec` 일회성), (b) 병렬 story 운용(로드맵 CP2), (c) 리뷰 패널을 별 프로세스로 병렬화, (d) 장시간 작업 감독(`check --wait` 롤링).

**마찰·리스크**: 상태가 runtime-global이라 per-topic `dev-context.json`과 **진실 원천이 둘**이 된다 / lifecycle 계약이 프롬프트 preamble 주입 방식이라 하네스 규칙과 지시 충돌 소지 / 워커마다 별도 CLI 세션이라 토큰 비용이 곱해짐 / 스킬이 "비-Orca 서브에이전트 도구로 대체하지 말 것"을 강하게 규정해 하네스 에이전트 모델과 정책 충돌 가능 / worktree 제거 시 dispatch·터미널 고아화(§6-1) / handoff와 supervised 구분이 자연어 트리거 기반이라 오분류 위험.

**로드맵 영향(중요)**: 로드맵 E4는 "ContextStore + Mongo shared registry + lease + CLI 대시보드"를 계획한다. orchestration + `worktree ps`가 태스크 레지스트리·소유권(디스패치)·상태 대시보드를 **이미 상당 부분 제공**한다. 도입을 결정하면 E4 범위를 재산정할 필요가 있다.

**현 시점 판단**: 보류. 워크트리·세션 계층(§4)이 먼저 안정화된 뒤, (a) Codex 리뷰 dispatch화, (b) 병렬 story 운용 두 건을 파일럿 후보로 둔다. 하네스에 넣는다면 tier는 `adapter-*`(가용성 게이트 + 폴백 보유).

### 8.1 파일럿 계획 (실행 전 사전 등록)

문서 독해만으로는 판단이 서지 않는 항목을 실측으로 좁히기 위한 최소 시나리오. **실행 전에 기록해 두어, 결과에 맞춰 기준을 사후 조정하지 않도록 한다.**

**대상**: `worktree2`(`~/Workspace/tack.worktrees/worktree2`, 브랜치 `feature/worktree2`, claude 세션 1개 가동 중). 하네스 컨텍스트는 미주입 상태이므로, 규칙 충돌 관측이 목적이면 `provision.sh worktree2`를 선행한다.

**절차**: `task-create` → `dispatch --to <handle> --inject` → `check --wait --types worker_done,escalation,decision_gate` → `dispatch-show`/`task-list`로 상태 확인.

**측정 항목**

| # | 질문 | 판정 기준 |
|---|---|---|
| P1 | `--inject`가 실행 중인 claude TUI에 preamble을 실제로 전달하는가 | 워커 화면에 TASK 블록이 뜨고, `dispatch-show`가 dispatch 존재를 보고 |
| P2 | 워커가 `worker_done`을 자력으로 보내는가 | 코디네이터의 `check --wait`가 `worker_done` 1건 수신, `task-list` 상태가 `completed` |
| P3 | 주입된 preamble이 하네스 규칙(CLAUDE.md·`.claude/rules`)과 충돌하는가 | 워커가 하네스 워크플로우를 무시하거나, 반대로 preamble 지시를 무시하는지 관찰 |
| P4 | 상태 이중화가 실제 문제인가 | orchestration 태스크 상태와 `dev-context.json` phase가 어긋나는 지점을 기록 |
| P5 | 비용 | 워커 세션 1건의 토큰 소비를 `ps`·워커 화면으로 개략 확인 |

**중단 조건**: `--inject` 2회 연속 실패, 또는 워커가 하네스 규칙을 깨는 파일 수정을 시도할 때 즉시 중단한다.

**정리 절차**: `orchestration reset --tasks`는 **runtime-global**이라 다른 진행 중 코디네이션까지 지운다. 파일럿 종료 시에는 `task-list`로 잔여를 확인하고 개별 `task-update`로 닫는 것을 우선하며, `reset`은 잔여가 이 파일럿 것뿐임을 확인한 뒤에만 쓴다.

---

## 9. 종합 판단

**조건부 도입 권장.** 근거: (a) 이미 개발 세션의 호스트이고 cmux는 부재라 현행 경로가 무효, (b) 배치·브랜치 설정을 맞추면 하네스 스크립트가 **무수정으로** 동작함을 end-to-end로 실증, (c) `tui-idle` 대기·`ps` 에이전트 관측은 blind `cmux send` 대비 실질적 개선.

**도입 규칙 3개**
1. `orca worktree rm`을 하네스 토픽에 직접 쓰지 않는다(§5).
2. worktree 제거 전에 Orca 터미널을 닫는다(§6-1).
3. 브랜치 접두는 하네스가 rename으로 부여한다 — `branchPrefix=none` 전제(§3.2).

**다음 확인거리**: orchestration 파일럿 — 시나리오·측정 항목·중단 조건은 §8.1에 사전 등록했다. (`branchPrefix=none` 재실측·자동 rename 게이트는 2026-07-27 완료 — §3.2·§3.3·§7. `externalWorktreeVisibility`는 §2.1 결정으로 종료.)

**하네스 쪽 수정 과제 2건** (도입 확정 시)
1. worktree 제거 전 Orca 터미널 정리 단계 추가 — `flow-worktree` T7을 T4(제거)보다 앞으로(§6-1).
2. `teardown.sh`·`flow-worktree` T3·T5의 `feature/<topic>` 하드코딩을 dev-context 기록 기반으로 전환(§6-2).

---

## 부록: probe 이력

probe는 실행 후 정리했고, 매회 다음을 검증했다 — `git worktree list` 정리, 브랜치 삭제, `.git/info/exclude` 백업 대비 무변경, main `docs/_local/dev-context.json` 무변경, main `git status` clean.

**예외**: `worktree2`는 orchestration 파일럿(§8.1) 대상으로 **유지 중**이다. 파일럿 종료 후 정리한다.

| probe | 목적 | 산출 |
|---|---|---|
| `__orca_probe` | 하네스 생성 worktree에 Orca 부착 가능성 | path 셀렉터 해석·터미널 생성 성공 |
| `orca-probe` | 에이전트 TUI 기동 경계 | 대화형 claude 2/2 실패, headless·zsh·래퍼 성공 |
| `orcaprov` | Orca 생성 + 수동 주입 | 격리 성립, TUI 성공, `rm`이 주입물·브랜치 삭제 |
| `orcaprov2` | `--agent` 경로의 `ps` 등재 | `agents[{state,lastAssistantMessage}]` 확인 |
| `wtplace` | `worktreeBasePath` 적용 | `tack.worktrees/tack/wtplace` (nest 잔존) |
| `worktree1` | 최종 형태 end-to-end | 배치 일치, provision·teardown 무수정 통과, 브랜치 rename 추적 확인 |
| `worktree2` | `branchPrefix=none` 재실측 + 자동 rename 검증 | 브랜치 `worktree2`(접두 없음), 사후 rename 반영(수 초 지연 후 일치), 자동 rename 미발동 |
