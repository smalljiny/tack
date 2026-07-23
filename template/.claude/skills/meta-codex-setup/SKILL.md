---
version: 1
name: meta-codex-setup
description: Run the codex companion setup and refresh the codex status cache in dev-context.json. Harness entry point, user-invocable via /meta-codex-setup.
origin: harness
user-invocable: true
---

# /meta-codex-setup

Check codex CLI availability, authentication status, and optionally toggle the stop-time review gate. After completing the standard setup check, updates `config.codex.*` in `dev-context.json` so harness commands (e.g., `/dev:review` adversarial-review) can read codex availability without re-running setup.

## Notes: Relation to the external plugin codex setup

This skill is the harness entry point for codex setup. It runs the codex companion setup and refreshes the harness codex cache in one step.

Earlier this logic lived at `.claude/commands/codex/setup.md`, a command file that **shadowed** the plugin-provided `/codex:setup` (Claude Code loads `.claude/commands/` before plugin commands). Migrating that wrapper to this skill removes the shadowing: `/meta-codex-setup` and the external plugin `/codex:setup` now coexist under distinct names.

The external plugin `/codex:setup` still works unchanged. The harness codex cache also stays fresh independently: the `session-start` hook calls `.claude/scripts/codex/detect-and-cache.js` on every session start, so `config.codex.*` (and the availability gate that reads it) does not depend on running this skill.

## Notes: Single Source of Truth

All codex detection logic (companion glob, semver sorting, containment validation, field mapping, TTL cache, silent failure) lives exclusively in `.claude/scripts/codex/detect-and-cache.js`. Both this skill and `session-start.js` delegate to that script — do not duplicate the logic here.

## Execution Flow

### 1. Run codex companion setup (original behavior)

Find the companion using the detect-and-cache script's logic, then run:
```bash
node "$(node -e "
const {existsSync,readdirSync}=require('fs');
const {join,resolve,sep}=require('path');
const {homedir}=require('os');
const base=join(homedir(),'.claude/plugins/cache/openai-codex/codex');
if(!existsSync(base)){process.exit(1);}
const vs=readdirSync(base,{withFileTypes:true})
  .filter(d=>d.isDirectory()&&/^\d+\.\d+\.\d+$/.test(d.name))
  .map(d=>d.name)
  .sort((a,b)=>{const pa=a.split('.').map(Number),pb=b.split('.').map(Number);for(let i=0;i<3;i++){if((pb[i]??0)!==(pa[i]??0))return(pb[i]??0)-(pa[i]??0);}return 0;});
if(!vs.length){process.exit(1);}
const p=join(base,vs[0],'scripts/codex-companion.mjs');
if(!resolve(p).startsWith(resolve(base)+sep)||!existsSync(p)){process.exit(1);}
process.stdout.write(p);
")" setup --json "$ARGUMENTS"
```

If the companion is not found, print a warning:
```
⚠ codex companion을 찾을 수 없습니다.
codex가 설치되어 있는지 확인하세요: npm install -g @openai/codex
```

Display the companion output to the user (same as original plugin command behavior).

### 2. Refresh codex cache in dev-context.json

Run the shared detection script with `--force` to bypass TTL and write the latest state:

```bash
node .claude/scripts/codex/detect-and-cache.js --force
```

This script handles all field mapping, containment validation, and silent failure — no duplication needed here.

Show completion:
```
codex 상태가 dev-context.json에 갱신되었습니다.
```

Read and display the updated values:
```bash
node .tack/scripts/dev-context.js read --field=config.codex.available
node .tack/scripts/dev-context.js read --field=config.codex.authenticated
node .tack/scripts/dev-context.js read --field=config.codex.version
node .tack/scripts/dev-context.js read --field=config.codex.checked_at
```
