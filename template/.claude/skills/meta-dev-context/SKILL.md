---
version: 5
name: meta-dev-context
description: Shared contract for reading and writing dev-context.json via the dev-context.js CLI. Load this skill whenever a command needs to inspect or mutate topic lifecycle state.
origin: harness
---

# dev-context Skill

## Overview

All dev-context.json access goes through `.harness/scripts/dev-context.js`. Never read or write the file directly. This skill defines the canonical invocation patterns for each workflow command.

## CLI Reference

```
node .harness/scripts/dev-context.js <subcommand> [--option=value ...]
```

### `register-topic`

Register a new topic at `spec:drafting`. Sets `current_topic`. Fails if the topic already exists.

```bash
node .harness/scripts/dev-context.js register-topic \
  --topic=<name> \
  --spec=<spec-path>
```

### `update-state`

Transition a topic to a new `phase:status`. Validates against the allowed transition table. Fails with non-zero exit on invalid transitions.

```bash
node .harness/scripts/dev-context.js update-state \
  --topic=<name> \
  --phase=<phase> \
  --status=<status>
```

### `set-field`

Update a single data field on a topic. `phase` and `status` are protected — use `update-state` for those.

```bash
node .harness/scripts/dev-context.js set-field \
  --topic=<name> \
  --field=<field> \
  --value=<value>        # use "null" to set null
```

### `remove-topic`

Remove a topic from dev-context.json. Switches `current_topic` to another remaining topic, or null if none remain. No state validation — the caller (`/flow-done`) is responsible for pre-validation.

```bash
node .harness/scripts/dev-context.js remove-topic --topic=<name>
```

### `read`

Print a single field value to stdout.

```bash
# Topic-level field
node .harness/scripts/dev-context.js read --topic=<name> --field=<field>

# Global field (current_topic only — no --topic)
node .harness/scripts/dev-context.js read --field=current_topic
```

> `--field=current_topic` must NOT be combined with `--topic`.

### `set-field` (global variant)

`set-field` also supports setting the global `current_topic` field without `--topic` (parallel to `read`):

```bash
# Update current_topic globally
node .harness/scripts/dev-context.js set-field \
  --field=current_topic --value=<topic>

# Clear current_topic
node .harness/scripts/dev-context.js set-field \
  --field=current_topic --value=null
```

> `--field=current_topic` must NOT be combined with `--topic`.

---

## Gate Validation Pattern

Before proceeding in a command, verify the topic is in the expected state using **both fields as a pair**:

```bash
PHASE=$(node .harness/scripts/dev-context.js read --topic=<name> --field=phase)
STATUS=$(node .harness/scripts/dev-context.js read --topic=<name> --field=status)
```

Then check `$PHASE:$STATUS` against the required state. If it does not match, halt and show:

```
<command>를 실행할 수 없습니다.
현재 상태: <phase>:<status>
<required-state> 상태여야 합니다.
```

---

## Command-by-Command Invocation Map

### `/flow-spec`

| Step | Call |
|------|------|
| After saving spec draft | `register-topic --topic=<name> --spec=<backlog-path>` |
| Before Codex review loop | `update-state --topic=<name> --phase=spec --status=reviewing` |
| Codex returns NOT READY | `update-state --topic=<name> --phase=spec --status=drafting` |
| Spec confirmed | `update-state --topic=<name> --phase=spec --status=confirmed` |

### `/flow-plan`

> `plan:confirmed` is set by the Codex `plan-review` skill (not by Claude directly) when it returns READY or READY WITH NOTE.

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `spec:confirmed` |
| After moving files to active/ | `set-field --topic=<name> --field=spec --value=<active-spec-path>` |
| After moving files to active/ | `set-field --topic=<name> --field=specReview --value=<active-review-path>` |
| After planner generates plan | `set-field --topic=<name> --field=plan --value=<plan-path>` |
| After planner completes | `update-state --topic=<name> --phase=plan --status=ready` |
| Before Codex plan-review | `update-state --topic=<name> --phase=plan --status=reviewing` |
| *(Codex plan-review)* READY / READY WITH NOTE | `update-state --topic=<name> --phase=plan --status=confirmed` |
| *(Codex plan-review)* NOT READY | `update-state --topic=<name> --phase=plan --status=ready` |
| *(Codex plan-review)* After writing review file | `set-field --topic=<name> --field=planReview --value=<review-path>` |

### `/flow-impl`

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `plan:confirmed` |
| On first Story start | `update-state --topic=<name> --phase=impl --status=in-progress` |
| After each Story | `set-field --topic=<name> --field=currentStory --value=<story-id>` |

### `/flow-review`

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `impl:in-progress` |
| On start | `update-state --topic=<name> --phase=review --status=in-progress` |

### `/flow-verify`

No `dev-context.json` calls. This command runs quality gates (build, type-check, lint, test, security) without mutating lifecycle state.

### `/flow-done`

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `review:in-progress` |
| After archiving files | `remove-topic --topic=<name>` |

---

## State Transition Table

| From | Allowed Next States |
|------|---------------------|
| `spec:drafting` | `spec:reviewing` |
| `spec:reviewing` | `spec:confirmed`, `spec:drafting` |
| `spec:confirmed` | `plan:ready` |
| `plan:ready` | `plan:reviewing` |
| `plan:reviewing` | `plan:confirmed`, `plan:ready` |
| `plan:confirmed` | `impl:in-progress` |
| `impl:in-progress` | `review:in-progress` |
| `review:in-progress` | `impl:in-progress` (review failure → re-impl) |

Any transition not listed above will exit non-zero with an error message.
