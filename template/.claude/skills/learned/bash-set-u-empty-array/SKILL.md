---
version: 1
name: bash-set-u-empty-array
description: set -u 환경에서 빈 배열을 안전하게 확장하는 패턴
origin: learned
learned_at: 2026-04-25
---

## When to Activate

bash/zsh 스크립트에 `set -u` (또는 `set -euo pipefail`)가 설정된 상태에서
함수에 variadic 인자를 받아 배열에 담고 `"${arr[@]}"` 로 확장할 때.

## Pattern

```bash
# ❌ set -u 에서 빈 배열이면 "unbound variable" 오류
rsync "${COMMON_OPTS[@]}" "${extra_opts[@]}" "$src" "$dst/"

# ✅ 빈 배열일 때 안전하게 nothing으로 확장
rsync "${COMMON_OPTS[@]}" ${extra_opts[@]+"${extra_opts[@]}"} "$src" "$dst/"
```

`${arr[@]+"${arr[@]}"}` 패턴: 배열이 설정되어 있으면(길이 > 0) 확장, 비어있으면 아무것도 삽입하지 않음.

## Example

```bash
set -euo pipefail

copy_item() {
  local rel="$1"
  shift
  local extra_opts=("$@")   # 인자 없으면 빈 배열

  rsync -a ${extra_opts[@]+"${extra_opts[@]}"} "$rel" "$DEST/"
}

copy_item ".harness"                          # extra_opts 없음 — 안전
copy_item ".harness" --exclude='commit-scopes.md'  # extra_opts 있음 — 안전
```

## Why It Works

`${var+word}` 는 bash parameter expansion의 "설정됐을 때만 word로 치환" 형식.
배열에 적용하면 빈 배열(`()`)과 미설정 변수를 동일하게 처리해 `set -u` 오류를 피한다.
