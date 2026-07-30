---
version: 7
name: meta-dev-context
description: Shared contract for reading and writing harness state via the dev_context.py CLI — topic lifecycle in .tack/local/dev-context.json and config in the two-layer store (tracked .tack/config.json plus the local file). Load this skill whenever a command needs to inspect or mutate topic lifecycle state or config.
origin: harness
---

# dev-context Skill

## Overview

All harness state access goes through `.tack/scripts/dev_context.py`. Never read or write the underlying files directly. This skill defines the canonical invocation patterns for each workflow command.

The CLI spans two stores:

| Store | File | Tracked | Holds |
|---|---|---|---|
| Topic lifecycle | `.tack/local/dev-context.json` | no (git-ignored) | `current_topic`, `topics[*]`, and `local`/`cache` layer config keys |
| Shared config | `.tack/config.json` | yes (committed) | `file_format` and `shared` layer config keys |

Topic subcommands touch the first store only. `read --field=config.*` merges both; `set-field --field=config.*` picks one by schema layer. See `### set-field (config variant)`.

## CLI Reference

```
python3 .tack/scripts/dev_context.py <subcommand> [--option=value ...]
```

### `register-topic`

Register a new topic at `spec:drafting`. Sets `current_topic`. Fails if the topic already exists.

```bash
python3 .tack/scripts/dev_context.py register-topic \
  --topic=<name> \
  --spec=<spec-path>
```

### `update-state`

Transition a topic to a new `phase:status`. Validates against the allowed transition table. Fails with non-zero exit on invalid transitions.

```bash
python3 .tack/scripts/dev_context.py update-state \
  --topic=<name> \
  --phase=<phase> \
  --status=<status>
```

### `set-field`

Update a single data field on a topic. `phase` and `status` are protected — use `update-state` for those.

```bash
python3 .tack/scripts/dev_context.py set-field \
  --topic=<name> \
  --field=<field> \
  --value=<value>        # use "null" to set null
```

### `remove-topic`

Remove a topic from dev-context.json. Switches `current_topic` to another remaining topic, or null if none remain. No state validation — the caller (`/flow-done`) is responsible for pre-validation.

```bash
python3 .tack/scripts/dev_context.py remove-topic --topic=<name>
```

### `read`

Print a single field value to stdout.

```bash
# Topic-level field
python3 .tack/scripts/dev_context.py read --topic=<name> --field=<field>

# Global field (current_topic only — no --topic)
python3 .tack/scripts/dev_context.py read --field=current_topic
```

> `--field=current_topic` must NOT be combined with `--topic`.

### `set-field` (global variant)

`set-field` also supports setting the global `current_topic` field without `--topic` (parallel to `read`):

```bash
# Update current_topic globally
python3 .tack/scripts/dev_context.py set-field \
  --field=current_topic --value=<topic>

# Clear current_topic
python3 .tack/scripts/dev_context.py set-field \
  --field=current_topic --value=null
```

> `--field=current_topic` must NOT be combined with `--topic`.

### `set-field` (config variant)

Write one config leaf. The path is exactly three segments — `config.<namespace>.<key>`.

```bash
# Default routing — the schema layer picks the destination file
python3 .tack/scripts/dev_context.py set-field \
  --field=config.<namespace>.<key> --value=<value>

# Personal override of a shared key — writes to the git-ignored local file
python3 .tack/scripts/dev_context.py set-field \
  --field=config.<namespace>.<key> --layer=local --value=<value>
```

**Schema validation.** `.tack/contracts/config-schema.json` declares `type`, `layer`, and `default` for every key and is the source of truth for both. `set-field` rejects an unknown namespace, an unknown key, or a value whose inferred type differs from the declared one, and prints close-match suggestions on a name miss. A missing or unparseable schema file makes config writes exit non-zero.

**`--layer` vocabulary.** The two accepted values are `local` and `shared`. Routing:

| Declared layer | No `--layer` | `--layer=local` | `--layer=shared` |
|---|---|---|---|
| `shared` | `.tack/config.json` | `.tack/local/dev-context.json` | `.tack/config.json` |
| `local` | `.tack/local/dev-context.json` | `.tack/local/dev-context.json` | rejected |
| `cache` | `.tack/local/dev-context.json` | `.tack/local/dev-context.json` | rejected |

Rejecting `--layer=shared` on `local` and `cache` keys is what keeps personal settings and machine detection caches out of the committed file. `--layer` belongs to `set-field` on a `config.*` field — every other subcommand, and `read`, exit non-zero when given it.

`.tack/config.json` is created on the first shared write; the template does not ship it.

### `read` (config variant)

```bash
python3 .tack/scripts/dev_context.py read --field=config.<namespace>.<key>
```

Resolution is per leaf: the local file wins when it owns the key (including a `null`, `false`, or `[]` value), otherwise the tracked file answers, otherwise the output is empty. Arrays replace wholesale — the two layers are never concatenated.

`read` performs no schema lookup, so an unknown key returns empty output and exit 0 rather than blocking the caller. `default` in the schema is declarative metadata: `read` never synthesizes it, so an unset key reads as empty. Treat empty as `false` for the boolean gates, with `config.risk.high_gate_enabled` as the documented exception — it defaults to `true`.

**No clear idiom on config leaves.** `--value=null` stores the literal string `"null"` here, unlike the topic-field and `current_topic` paths. The CLI has no path that removes a config leaf, so a local override keeps winning over the shared value until the local file is edited directly — overwriting it with the shared value hides the override without removing it.

---

## Gate Validation Pattern

Before proceeding in a command, verify the topic is in the expected state using **both fields as a pair**:

```bash
PHASE=$(python3 .tack/scripts/dev_context.py read --topic=<name> --field=phase)
STATUS=$(python3 .tack/scripts/dev_context.py read --topic=<name> --field=status)
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

### `/flow-docs`

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `review:in-progress` |
| After committing reference docs | `update-state --topic=<name> --phase=docs --status=generated` |

### `/flow-pr`

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `docs:generated` |
| After creating the PR | `update-state --topic=<name> --phase=pr --status=created` |

### `/flow-done`

| Step | Call |
|------|------|
| Gate check | `read --topic=<name> --field=phase` + `read --topic=<name> --field=status` → must be `pr:created` |
| After archiving files | `remove-topic --topic=<name>` |

---

## State Transition Table

This table mirrors `VALID_TRANSITIONS` in `.tack/scripts/state_machine.py` (14 directed edges, 10 From-states). `state_machine.py` is the single source of truth — do not redefine or extend here.

| From | Allowed Next States |
|------|---------------------|
| `spec:drafting` | `spec:reviewing` |
| `spec:reviewing` | `spec:confirmed`, `spec:drafting` |
| `spec:confirmed` | `plan:ready` |
| `plan:ready` | `plan:reviewing` |
| `plan:reviewing` | `plan:confirmed`, `plan:ready` |
| `plan:confirmed` | `impl:in-progress` |
| `impl:in-progress` | `review:in-progress` |
| `review:in-progress` | `impl:in-progress`, `docs:generated` |
| `docs:generated` | `pr:created`, `review:in-progress` |
| `pr:created` | `docs:generated` |

Any transition not listed above will exit non-zero with an error message.
