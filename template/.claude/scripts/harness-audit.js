#!/usr/bin/env node

/**
 * Harness Audit — deterministic health scorer for the harness repo.
 *
 * Usage:
 *   node .claude/scripts/harness-audit.js [scope] [--format text|json] [--root path]
 *
 * Scope: repo (default) | hooks | skills | commands | agents
 */

import fs from 'node:fs';
import path from 'node:path';

const RUBRIC_VERSION = '2026-04-15';

const CATEGORIES = [
  'Tool Coverage',
  'Context Efficiency',
  'Quality Gates',
  'Memory Persistence',
  'Eval Coverage',
  'Security Guardrails',
  'Cost Efficiency',
];

// ---------------------------------------------------------------------------
// Arg parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args   = argv.slice(2);
  const parsed = {
    scope:  'repo',
    format: 'text',
    help:   false,
    root:   path.resolve(process.env.AUDIT_ROOT || process.cwd()),
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--help' || arg === '-h') { parsed.help = true; continue; }
    if (arg === '--format') { parsed.format = (args[++i] || '').toLowerCase(); continue; }
    if (arg === '--scope')  { parsed.scope  = normalizeScope(args[++i]); continue; }
    if (arg === '--root')   { parsed.root   = path.resolve(args[++i] || process.cwd()); continue; }
    if (arg.startsWith('--format=')) { parsed.format = arg.split('=')[1].toLowerCase(); continue; }
    if (arg.startsWith('--scope='))  { parsed.scope  = normalizeScope(arg.split('=')[1]); continue; }
    if (arg.startsWith('--root='))   { parsed.root   = path.resolve(arg.slice('--root='.length)); continue; }
    if (arg.startsWith('-')) throw new Error(`Unknown argument: ${arg}`);
    parsed.scope = normalizeScope(arg);
  }

  if (!['text', 'json'].includes(parsed.format))
    throw new Error(`Invalid format: ${parsed.format}. Use text or json.`);

  return parsed;
}

function normalizeScope(s) {
  const v = (s || 'repo').toLowerCase();
  if (!['repo', 'hooks', 'skills', 'commands', 'agents'].includes(v))
    throw new Error(`Invalid scope: ${s}`);
  return v;
}

// ---------------------------------------------------------------------------
// File helpers
// ---------------------------------------------------------------------------

function exists(root, rel) {
  return fs.existsSync(path.join(root, rel));
}

function safeRead(root, rel) {
  try { return fs.readFileSync(path.join(root, rel), 'utf8'); }
  catch { return ''; }
}

function countFiles(root, relDir, ext) {
  const dir = path.join(root, relDir);
  if (!fs.existsSync(dir)) return 0;
  let count = 0;
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    for (const e of fs.readdirSync(cur, { withFileTypes: true })) {
      const p = path.join(cur, e.name);
      if (e.isDirectory()) stack.push(p);
      else if (!ext || e.name.endsWith(ext)) count++;
    }
  }
  return count;
}

// ---------------------------------------------------------------------------
// Checks
// ---------------------------------------------------------------------------

function getChecks(root) {
  const hooksJson    = safeRead(root, '.claude/hooks/hooks.json');
  const settingsJson = safeRead(root, '.claude/settings.json');

  // hooks guard: PreToolUse or SessionStart present in either config
  const hasHookGuard = hooksJson.includes('PreToolUse') ||
                       hooksJson.includes('SessionStart') ||
                       settingsJson.includes('PreToolUse') ||
                       settingsJson.includes('SessionStart');

  return [
    // ── Tool Coverage ────────────────────────────────────────────────────
    {
      id: 'tool-hooks-config',
      category: 'Tool Coverage',
      points: 2,
      scopes: ['repo', 'hooks'],
      path: '.claude/hooks/hooks.json',
      description: 'Hook configuration file exists',
      pass: exists(root, '.claude/hooks/hooks.json'),
      fix: 'Create .claude/hooks/hooks.json and define baseline hook events.',
    },
    {
      id: 'tool-hooks-scripts',
      category: 'Tool Coverage',
      points: 2,
      scopes: ['repo', 'hooks'],
      path: '.claude/scripts/hooks/',
      description: 'At least 5 hook implementation scripts exist',
      pass: countFiles(root, '.claude/scripts/hooks', '.py') >= 5,
      fix: 'Add hook scripts under .claude/scripts/hooks/.',
    },
    {
      id: 'tool-agent-count',
      category: 'Tool Coverage',
      points: 2,
      scopes: ['repo', 'agents'],
      path: '.claude/agents/',
      description: 'At least 5 agent definitions exist',
      pass: countFiles(root, '.claude/agents', '.md') >= 5,
      fix: 'Add agent definitions under .claude/agents/.',
    },
    {
      id: 'tool-skill-count',
      category: 'Tool Coverage',
      points: 2,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/',
      description: 'At least 2 skill definitions exist',
      pass: countFiles(root, '.claude/skills', 'SKILL.md') >= 2,
      fix: 'Add skill directories with SKILL.md under .claude/skills/.',
    },
    {
      id: 'tool-settings',
      category: 'Tool Coverage',
      points: 2,
      scopes: ['repo'],
      path: '.claude/settings.json',
      description: 'settings.json exists with permissions',
      pass: exists(root, '.claude/settings.json') && settingsJson.includes('permissions'),
      fix: 'Add .claude/settings.json with permissions and hook wiring.',
    },

    // ── Context Efficiency ───────────────────────────────────────────────
    {
      id: 'context-claude-md',
      category: 'Context Efficiency',
      points: 3,
      scopes: ['repo'],
      path: 'CLAUDE.md',
      description: 'CLAUDE.md exists with project instructions',
      pass: exists(root, 'CLAUDE.md'),
      fix: 'Add CLAUDE.md so Claude Code has project-specific instructions.',
    },
    {
      id: 'context-performance-rules',
      category: 'Context Efficiency',
      points: 3,
      scopes: ['repo'],
      path: '.claude/rules/common/performance.md',
      description: 'Model selection and context window rules documented',
      pass: exists(root, '.claude/rules/common/performance.md'),
      fix: 'Add .claude/rules/common/performance.md with model routing and context guidance.',
    },
    {
      id: 'context-wf-compact',
      category: 'Context Efficiency',
      points: 2,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/wf-compact/SKILL.md',
      description: 'Strategic compaction skill exists',
      pass: exists(root, '.claude/skills/wf-compact/SKILL.md'),
      fix: 'Add .claude/skills/wf-compact/SKILL.md for compaction guidance.',
    },
    {
      id: 'context-dev-workflow',
      category: 'Context Efficiency',
      points: 2,
      scopes: ['repo'],
      path: '.claude/rules/common/development-workflow.md',
      description: 'Development workflow rules documented',
      pass: exists(root, '.claude/rules/common/development-workflow.md'),
      fix: 'Add .claude/rules/common/development-workflow.md.',
    },

    // ── Quality Gates ────────────────────────────────────────────────────
    {
      id: 'quality-verify-command',
      category: 'Quality Gates',
      points: 3,
      scopes: ['repo', 'commands'],
      path: '.claude/commands/dev/verify.md',
      description: '/dev:verify command exists',
      pass: exists(root, '.claude/commands/dev/verify.md'),
      fix: 'Add .claude/commands/dev/verify.md as a pre-PR gate.',
    },
    {
      id: 'quality-review-command',
      category: 'Quality Gates',
      points: 2,
      scopes: ['repo', 'commands'],
      path: '.claude/commands/dev/review.md',
      description: '/dev:review command exists',
      pass: exists(root, '.claude/commands/dev/review.md'),
      fix: 'Add .claude/commands/dev/review.md for code review workflow.',
    },
    {
      id: 'quality-checkpoint-command',
      category: 'Quality Gates',
      points: 2,
      scopes: ['repo', 'commands'],
      path: '.claude/commands/dev/checkpoint.md',
      description: '/dev:checkpoint command exists',
      pass: exists(root, '.claude/commands/dev/checkpoint.md'),
      fix: 'Add .claude/commands/dev/checkpoint.md for mid-session state snapshots.',
    },
    {
      id: 'quality-testing-rules',
      category: 'Quality Gates',
      points: 3,
      scopes: ['repo'],
      path: '.tack/rules/testing.md',
      description: 'Testing rules with 80%+ coverage requirement documented',
      pass: exists(root, '.tack/rules/testing.md') &&
            safeRead(root, '.tack/rules/testing.md').includes('80'),
      fix: 'Add .tack/rules/testing.md with 80%+ coverage requirement.',
    },

    // ── Memory Persistence ───────────────────────────────────────────────
    {
      id: 'memory-session-start',
      category: 'Memory Persistence',
      points: 3,
      scopes: ['repo', 'hooks'],
      path: '.claude/scripts/hooks/session-start.py',
      description: 'Session start hook restores context',
      pass: exists(root, '.claude/scripts/hooks/session-start.py'),
      fix: 'Add .claude/scripts/hooks/session-start.py to restore dev-context on session start.',
    },
    {
      id: 'memory-session-logger',
      category: 'Memory Persistence',
      points: 3,
      scopes: ['repo', 'hooks'],
      path: '.claude/scripts/hooks/session-logger.py',
      description: 'Session logger captures tool usage',
      pass: exists(root, '.claude/scripts/hooks/session-logger.py'),
      fix: 'Add .claude/scripts/hooks/session-logger.py to record sessions/<date>.jsonl.',
    },
    {
      id: 'memory-sessions-dir',
      category: 'Memory Persistence',
      points: 2,
      scopes: ['repo'],
      path: '.claude/sessions/',
      description: 'sessions/ directory exists for log storage',
      pass: exists(root, '.claude/sessions'),
      fix: 'Create .claude/sessions/ (with .gitignore for *.jsonl).',
    },
    {
      id: 'memory-continuous-learning',
      category: 'Memory Persistence',
      points: 2,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/wf-continuous-learning/',
      description: 'Continuous learning skill exists',
      pass: exists(root, '.claude/skills/wf-continuous-learning/SKILL.md'),
      fix: 'Add .claude/skills/wf-continuous-learning/SKILL.md for pattern extraction guidance.',
    },

    // ── Eval Coverage ────────────────────────────────────────────────────
    {
      id: 'eval-tdd-skill',
      category: 'Eval Coverage',
      points: 3,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/wf-tdd/SKILL.md',
      description: 'TDD workflow skill exists',
      pass: exists(root, '.claude/skills/wf-tdd/SKILL.md'),
      fix: 'Add .claude/skills/wf-tdd/SKILL.md.',
    },
    {
      id: 'eval-verification-skill',
      category: 'Eval Coverage',
      points: 3,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/wf-verification/SKILL.md',
      description: 'Verification loop skill exists',
      pass: exists(root, '.claude/skills/wf-verification/SKILL.md'),
      fix: 'Add .claude/skills/wf-verification/SKILL.md.',
    },
    {
      id: 'eval-learn-skill',
      category: 'Eval Coverage',
      points: 2,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/meta-harness-learn/SKILL.md',
      description: '/meta-harness-learn skill exists for pattern extraction',
      pass: exists(root, '.claude/skills/meta-harness-learn/SKILL.md'),
      fix: 'Add .claude/skills/meta-harness-learn/SKILL.md to extract reusable patterns from sessions.',
    },
    {
      id: 'eval-roadmap',
      category: 'Eval Coverage',
      points: 2,
      scopes: ['repo'],
      path: 'docs/roadmap.md',
      description: 'Roadmap tracks component backlog',
      pass: exists(root, 'docs/roadmap.md'),
      fix: 'Add docs/roadmap.md to track planned harness improvements.',
    },

    // ── Security Guardrails ──────────────────────────────────────────────
    {
      id: 'security-agent',
      category: 'Security Guardrails',
      points: 3,
      scopes: ['repo', 'agents'],
      path: '.claude/agents/security-reviewer.md',
      description: 'Security reviewer agent exists',
      pass: exists(root, '.claude/agents/security-reviewer.md'),
      fix: 'Add .claude/agents/security-reviewer.md.',
    },
    {
      id: 'security-rules',
      category: 'Security Guardrails',
      points: 3,
      scopes: ['repo'],
      path: '.tack/rules/security.md',
      description: 'Security rules documented',
      pass: exists(root, '.tack/rules/security.md'),
      fix: 'Add .tack/rules/security.md.',
    },
    {
      id: 'security-hook-guard',
      category: 'Security Guardrails',
      points: 2,
      scopes: ['repo', 'hooks'],
      path: '.claude/hooks/hooks.json',
      description: 'Hooks include PreToolUse or SessionStart guards',
      pass: hasHookGuard,
      fix: 'Add PreToolUse or SessionStart entries in hooks/settings.',
    },
    {
      id: 'security-console-audit',
      category: 'Security Guardrails',
      points: 2,
      scopes: ['repo', 'hooks'],
      path: '.claude/scripts/hooks/console-log-audit.py',
      description: 'console.log audit hook exists',
      pass: exists(root, '.claude/scripts/hooks/console-log-audit.py'),
      fix: 'Add console-log-audit.py to catch accidental console.log before commits.',
    },

    // ── Cost Efficiency ──────────────────────────────────────────────────
    {
      id: 'cost-performance-rules',
      category: 'Cost Efficiency',
      points: 4,
      scopes: ['repo'],
      path: '.claude/rules/common/performance.md',
      description: 'Model selection rules prevent unnecessary Opus usage',
      pass: exists(root, '.claude/rules/common/performance.md'),
      fix: 'Add .claude/rules/common/performance.md with Haiku/Sonnet/Opus routing guidance.',
    },
    {
      id: 'cost-async-hooks',
      category: 'Cost Efficiency',
      points: 3,
      scopes: ['repo', 'hooks'],
      path: '.claude/hooks/hooks.json',
      description: 'Session logger hook is async (non-blocking)',
      pass: hooksJson.includes('"async": true') || hooksJson.includes('"async":true'),
      fix: 'Mark the session-logger hook as async in hooks.json to avoid blocking tool use.',
    },
    {
      id: 'cost-wf-compact',
      category: 'Cost Efficiency',
      points: 3,
      scopes: ['repo', 'skills'],
      path: '.claude/skills/wf-compact/SKILL.md',
      description: 'Strategic compact skill prevents runaway context costs',
      pass: exists(root, '.claude/skills/wf-compact/SKILL.md'),
      fix: 'Add wf-compact skill to control context window costs.',
    },
  ];
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

function score(checks, scope) {
  const filtered = checks.filter(c => c.scopes.includes(scope));
  const byCategory = {};
  for (const cat of CATEGORIES) {
    const inCat = filtered.filter(c => c.category === cat);
    const max   = inCat.reduce((s, c) => s + c.points, 0);
    const earned = inCat.filter(c => c.pass).reduce((s, c) => s + c.points, 0);
    byCategory[cat] = { score: max === 0 ? 0 : Math.round((earned / max) * 10), earned, max };
  }
  const maxTotal     = filtered.reduce((s, c) => s + c.points, 0);
  const overallScore = filtered.filter(c => c.pass).reduce((s, c) => s + c.points, 0);
  const failed       = filtered.filter(c => !c.pass);
  const topActions   = [...failed]
    .sort((a, b) => b.points - a.points)
    .slice(0, 3)
    .map(c => ({ action: c.fix, path: c.path, category: c.category, points: c.points }));

  return {
    scope,
    rubric_version: RUBRIC_VERSION,
    overall_score:  overallScore,
    max_score:      maxTotal,
    categories:     byCategory,
    checks: filtered.map(c => ({
      id: c.id, category: c.category, points: c.points,
      path: c.path, description: c.description, pass: c.pass,
    })),
    top_actions: topActions,
  };
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

function printText(report) {
  const pct = report.max_score === 0 ? 0 : Math.round((report.overall_score / report.max_score) * 100);
  console.log(`\nHarness Audit (${report.scope}): ${report.overall_score}/${report.max_score}  [${pct}%]`);
  console.log(`Rubric: ${report.rubric_version}\n`);

  for (const cat of CATEGORIES) {
    const d = report.categories[cat];
    if (!d || d.max === 0) continue;
    const icon = d.score >= 8 ? '✅' : d.score >= 5 ? '⚠️ ' : '❌';
    console.log(`  ${icon} ${cat.padEnd(22)} ${d.score}/10  (${d.earned}/${d.max} pts)`);
  }

  const failed = report.checks.filter(c => !c.pass);
  console.log(`\nChecks: ${report.checks.length} total, ${failed.length} failing\n`);

  if (report.top_actions.length > 0) {
    console.log('Top Actions:');
    report.top_actions.forEach((a, i) => {
      console.log(`  ${i + 1}. [${a.category}] ${a.action}`);
      console.log(`     → ${a.path}`);
    });
    console.log('');
  }
}

function showHelp() {
  console.log(`
Usage: node .claude/scripts/harness-audit.js [scope] [--format text|json] [--root path]

Scopes: repo (default), hooks, skills, commands, agents
`);
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  try {
    const args = parseArgs(process.argv);
    if (args.help) showHelp();

    const checks = getChecks(args.root);
    const report = score(checks, args.scope);

    if (args.format === 'json') {
      console.log(JSON.stringify(report, null, 2));
    } else {
      printText(report);
    }
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

main();
