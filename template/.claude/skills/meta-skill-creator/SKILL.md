---
version: 5
name: meta-skill-creator
description: This skill should be used whenever a user wants to create a new skill from scratch, update or refine an existing skill, understand how skills are structured in this harness, or learn best practices for writing effective skill descriptions and eval loops. Use it for any question about skill anatomy, skill authorship, or skill quality — even if the user doesn't explicitly say "create a skill."
origin: sample-claude-env+anthropic-official
---

# Skill Creator

A meta-guide for writing new skills and improving existing ones in this harness.

## About Skills

Skills are modular, self-contained packages that extend Claude's capabilities by providing
specialized knowledge, workflows, and tools. Think of them as "onboarding guides" for specific
domains or tasks — they transform Claude from a general-purpose agent into a specialized agent
equipped with procedural knowledge.

### What Skills Provide

1. **Specialized workflows** — Multi-step procedures for specific domains
2. **Tool integrations** — Instructions for working with specific file formats or APIs
3. **Domain expertise** — Project-specific knowledge, schemas, business logic
4. **Bundled resources** — Scripts, references, and assets for complex and repetitive tasks

---

## Anatomy of a Skill

Every skill consists of a required `SKILL.md` and optional bundled resources:

```
skill-name/
├── SKILL.md                  (required)
│   ├── YAML frontmatter      (required)
│   │   ├── version:          integer, starts at 1
│   │   ├── name:             skill identifier
│   │   ├── description:      triggering signal — see "Writing Effective Descriptions"
│   │   ├── origin:           source reference (e.g. "sample-claude-env")
│   │   └── capabilities:     optional array, see skill-registry
│   └── Markdown instructions (required)
└── Bundled Resources         (optional)
    ├── scripts/              Executable code (Python/Bash/etc.)
    ├── references/           Documentation loaded into context as needed
    └── assets/               Files used in output (templates, icons, fonts, etc.)
```

### SKILL.md (required)

The `name` and `description` in frontmatter determine when Claude will use the skill.
Write `description` in third-person: "This skill should be used when…"

### Bundled Resources (optional)

#### `scripts/`

Executable code for tasks that require deterministic reliability or are repeatedly rewritten.

- **When to include**: When the same code is rewritten repeatedly or reliability matters
- **Example**: `scripts/rotate_pdf.py` for PDF rotation tasks
- **Benefits**: Token-efficient, deterministic, executable without loading into context

#### `references/`

Documentation and reference material to be loaded into context as needed.

- **When to include**: For documentation Claude should reference while working
- **Examples**: `references/schema.md`, `references/api_docs.md`
- **Best practice**: If files are large (>10k words), include grep search patterns in SKILL.md
- **Avoid duplication**: Information should live in either SKILL.md or references files, not both

#### `assets/`

Files not loaded into context but used within Claude's output.

- **When to include**: When the skill produces output that needs template files
- **Examples**: `assets/template.docx`, `assets/logo.png`, `assets/frontend-template/`

---

## Progressive Disclosure

Skills use a three-level loading system to manage context efficiently:

| Level | Content | When Loaded |
|-------|---------|-------------|
| **1 — Metadata** | `name` + `description` (~100 words) | Always in context |
| **2 — SKILL.md body** | Full instructions (<5k words) | When skill triggers |
| **3 — Bundled resources** | Scripts, references, assets | As needed by Claude |

**Keep SKILL.md under 500 lines.** If approaching this limit, add pointers to references files
rather than expanding inline.

---

## Writing Effective Descriptions

The `description` field is the **primary triggering mechanism**. Claude decides whether to
consult a skill based solely on this field — write it to maximize triggering accuracy.

### Principles

1. **Third-person, imperative form**: "This skill should be used when…"
2. **Be specific about triggers**: Name exact contexts, file types, user phrases, and domains
3. **Be appropriately pushy**: Claude tends to undertrigger skills. Make the description
   push toward using the skill even when the user doesn't explicitly ask for it.
   - Too passive: "Use when working with PDFs."
   - Better: "Use whenever the user mentions a PDF, needs to extract text, rotate pages,
     or work with any document file — even if they don't say 'PDF' explicitly."
4. **Include adjacent triggers**: List related terms and contexts that should also trigger the skill
5. **Avoid over-triggering**: Don't make the description so broad that it fires on unrelated queries

### Example Pattern

```yaml
description: >
  Guide for building React components with this project's design system.
  Use this skill whenever the user asks to create, modify, or review a React
  component, mentions the UI library, or asks about styling conventions —
  even if they don't explicitly say "component" or "React."
```

---

## Skill Creation Process

### Step 1: Understand with Concrete Examples

Before writing, clarify how the skill will be used:
- What tasks should the skill help accomplish?
- What would a user say to trigger it?
- What's the expected output format?

### Step 2: Plan Reusable Contents

For each example use case, decide what would need to be recreated each time:
- Code that's rewritten repeatedly → `scripts/`
- Reference docs looked up repeatedly → `references/`
- Template files copied repeatedly → `assets/`

### Step 3: Initialize

Create the directory and `SKILL.md`:

```bash
mkdir -p .claude/skills/<name>
touch .claude/skills/<name>/SKILL.md
```

For projects with Python available, the official Anthropic skill-creator plugin provides
`scripts/init_skill.py` that scaffolds the full structure automatically.

### Step 4: Edit the SKILL.md

Before editing SKILL.md content — the rules apply to skill prompt body as well as any agent/command prompts:

Load .claude/rules/common/prompt-authoring.md and follow its process.

Write for another Claude instance that has no prior context:
- Explain *why* things matter, not just *what* to do
- Prefer imperative/infinitive form ("To accomplish X, do Y")
- Avoid second-person declarative ("you should do X") — imperative form is preferred
- Reference bundled resources clearly with guidance on when to read them

### Step 5: Package (external distribution only)

This harness distributes skills by directory copy (project template model), not as `.skill`
zip files. Only use the official plugin's `scripts/package_skill.py` if publishing the skill
outside this harness for standalone distribution.

### Step 6: Iterate

After using the skill on real tasks, refine based on observed behavior:
- Did it trigger when it should have?
- Did it produce the right output?
- Is there repeated work that should move into a script?

---

## Eval Loop Concept

This harness does not ship automated eval tooling. The following describes the manual
concept. For automated benchmarking, refer to the official plugin linked in Related References.

To validate a skill works as intended, compare outputs with and without the skill.

### with-skill vs baseline

- **with-skill run**: Claude executes the task with access to this skill's SKILL.md
- **baseline run**: Claude executes the same task without the skill

Compare outputs qualitatively to identify where the skill adds value — or where it causes
the model to take unnecessary detours.

### Test Case Writing

Write 2–3 realistic test prompts — the kind a real user would actually type.
For each prompt, define:
1. **Expected outcome**: What should the output contain or accomplish?
2. **Should trigger**: Does this prompt warrant loading the skill?
3. **Edge cases**: Near-miss prompts that share keywords but shouldn't trigger

**Good test prompt example** (specific, contextual):
> "I have a BigQuery table called `user_events` with columns `user_id`, `event_type`,
> and `timestamp`. How many unique users triggered a `purchase` event last week?"

**Poor test prompt** (too generic):
> "Query some data"

### Triggering Accuracy

The description field is evaluated for triggering accuracy by checking whether Claude
loads the skill for should-trigger queries and skips it for should-not-trigger queries.
Iterate on the description when accuracy is low.

The official Anthropic skill-creator plugin provides a full automated eval pipeline
(`scripts/run_loop.py`, `eval-viewer/`) for quantitative benchmarking. Refer to
`https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator`
for details.

---

## Harness Conventions

When adding a skill to this harness:

| Convention | Rule |
|------------|------|
| **Path** | `.claude/skills/<name>/SKILL.md` |
| **Frontmatter fields** | `version` (int), `name`, `description`, `origin` — required; `capabilities` — optional array for registry discovery (see `.claude/skills/skill-registry/SKILL.md` for spec and taxonomy); `category` optional (e.g. `dev-process`, `session-management`) |
| **Version** | Starts at `1`, increments by 1 on each edit |
| **Instruction language** | English (harness component files rule) |
| **Style reference** | See `.claude/skills/wf-brainstorming/SKILL.md` for a well-formed example |

**Do not** add `scripts/`, `references/`, or `assets/` unless there is a concrete reason
(repeated code, large reference docs, template files). Most meta-guide skills need only SKILL.md.

**`wf-*` and `meta-*` skills intentionally omit `capabilities:`.** They follow the direct-load pattern and are not intended for registry-based discovery.

---

## Related References

- `references/sample-claude-env/.claude/skills/skill-creator/SKILL.md` — source basis (Apache 2.0; derived work — see repo LICENSE)
- `references/everything-claude-code/commands/skill-create.md` — git-history pattern extractor (alternative to `/meta-harness-learn` for existing repos)
- Anthropic official plugin: `https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator`
- `.claude/skills/wf-brainstorming/SKILL.md` — style reference within this harness
