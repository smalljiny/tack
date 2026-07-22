---
version: 3
---
# Security Rules

## Pre-Commit Checklist

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs are validated
- [ ] NoSQL/SQL injection prevention in place
- [ ] XSS prevention (HTML sanitization)
- [ ] Authentication/authorization verified
- [ ] Rate limiting applied to all endpoints
- [ ] Error messages do not contain sensitive information

## Secret Management

```typescript
// NEVER: hardcoded
const apiKey = "sk-proj-xxxxx"

// ALWAYS: environment variables
const apiKey = process.env.API_KEY
if (!apiKey) {
  throw new Error('API_KEY not configured')
}
```

## PII Handling

Mask personally identifiable information (email, phone number, etc.) in logs:

```typescript
// WRONG
logger.info({ email: 'user@example.com' }, 'Processing user')

// CORRECT
function maskEmail(email: string): string {
  const [local, domain] = email.split('@')
  const d = domain.split('.')
  return `${local[0]}***@${d[0][0]}***.${d[d.length - 1]}`
  // user@example.com -> u***@e***.com
}

logger.info({ email: maskEmail(user.email) }, 'Processing user')
```

## Security Response Protocol

When a security issue is found:
1. **Stop immediately**
2. Use the **security-reviewer** agent
3. Fix CRITICAL issues before continuing
4. Replace exposed secrets immediately
5. Review the entire codebase for similar issues

## Shell Injection Defense

AI 출력·사용자 입력을 셸 명령 인자로 보간하면 백틱·`$()`·따옴표 escape 실패로 임의 명령이 실행될 수 있다. `git commit -m "<AI-generated>"` 패턴이 대표적 위험 사례다.

셸에 동적 문자열을 전달할 때는 반드시 HEREDOC(`<<'EOF' ... EOF`, 단일 따옴표 delimiter) 또는 stdin 파이프를 사용한다. `<<'EOF'`는 변수 확장과 `$()` 명령 치환을 완전히 비활성화하지만, `<<EOF`(따옴표 없음)는 확장이 여전히 동작하므로 방어가 되지 않는다.

```bash
# WRONG: 메시지가 보간되어 임의 명령 실행 가능
git commit -m "$AI_GENERATED_MSG"
git commit -m "$(generate-message)"

# CORRECT: HEREDOC으로 보간 없이 전달
git commit -m "$(cat <<'COMMIT_MSG'
feat: add shell injection defense section
COMMIT_MSG
)"
```

직접 `-m "$VAR"` 또는 문자열 연결로 셸 인자를 구성하는 패턴은 금지한다.

## CLI Dynamic Key Access

CLI에서 동적 키로 JSON 객체를 조작할 때는 두 층의 방어가 필요하다.

**쓰기 방어 — 예약 키 차단:**

```js
const RESERVED_KEYS = new Set(['__proto__', 'constructor', 'prototype'])
if (RESERVED_KEYS.has(key)) throw new Error(`Reserved key: ${key}`)
obj[key] = value
```

**읽기 방어 — `hasOwn` 가드:**

```js
if (!Object.hasOwn(obj, key)) return undefined
return obj[key]
```

두 방어를 모두 적용한다. 쓰기 차단만으로는 prototype 속성에 대한 읽기 혼동을 막지 못하고, 읽기 가드만으로는 쓰기 오염을 막지 못한다.
