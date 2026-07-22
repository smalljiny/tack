---
version: 1
---

# 검토: 하네스 업그레이드 방법 (OQ1 후속)

**전제**: 배포 = per-project Copier(확정). 업그레이드 = target project가 새 tack 버전을 받는 절차.

**출처**: adapter-exa `/answer` (Copier 공식 문서), 2026-07-21.

## 메커니즘 — `copier update` (4기능 확인)

| 기능 | 확인 | tack 용도 |
|------|------|-----------|
| **migrations** | pre/post-migration task가 버전 경계 통과 시 실행 | **breaking change**(계약 포맷·파일 구조 변경) 자동 이관 |
| **version pinning / rollback** | `copier update --vcs-ref <tag>`로 특정 tag 타깃 | 롤백 = 이전 tag로 재핀 |
| **conflict 처리** | `--conflict` 기본 inline git 마커(또는 `.rej`) | 로컬 편집 충돌을 마커로 해소 |
| **`.copier-answers.yml`** | 답변 기록, **VC 커밋 필수**, 수동 편집 금지 | **버전 기록이 커밋됨 → 멀티머신 일관** |

## 방향 함의

**① 멀티머신 버전 일관 — 해결.** `.copier-answers.yml`(`_commit`=tag)이 커밋 필수라, 프로젝트의 tack 버전이 clone·머신 간 재현된다. 앞서 우려한 "멀티머신 버전 기록 발산"이 Copier 규약으로 닫힘.

**② breaking change 경로 = Copier migrations.** 계약 포맷·파일 구조가 바뀌는 tack 메이저 업그레이드는 pre/post-migration task로 target의 기존 산출물을 이관한다. "계약 변경을 어떻게 안전 전파하나"의 답.

**③ 안전한 업그레이드 타이밍 (session-model 연동).** `copier update`는 **clean working tree** 요구(확인) → 업그레이드는 **hub에서 clean 경계**에 실행하고 worktree impl 중(미커밋 변경)엔 안 함. 추가로 계약-타이밍 통제(per-project 선택 이유): **in-flight story가 구 계약에 걸려 있으면**, 그 story 완료(clean 경계) 후 또는 migration이 포맷을 올린 뒤 업그레이드. → tack 업그레이드는 "story 사이, hub, clean tree" 절차.

**④ 롤백.** 업그레이드가 깨지면 `git reset`(clean tree라 안전) + `copier update --vcs-ref <이전-tag>`로 재핀.

## 플래그 — tracked vs gitignored 긴장 (spec 검증)

Copier smart-update는 git으로 old-재생성↔현재 상태를 diff한다. `.copier-answers.yml`은 커밋 필수이고, diff 신뢰성은 harness 파일이 **git-tracked**일 때 보장된다. 그런데 현 harness는 종종 **gitignored**(target PR diff 오염 방지) 패턴을 쓴다 → **긴장**:

- Copier 채택은 tack 파일을 target에서 **tracked**로 두는 방향으로 민다(재현성·upgrade diff 확보). "gitignored 외부 툴링" 패턴에서 "tracked 프로젝트 파일"로 이동.
- PR-diff 오염 우려는 **분리 커밋**(tack-upgrade 커밋을 feature와 분리)으로 완화. `.copier-answers.yml` + 주기적 `copier update` 커밋은 정당한 이력.
- gitignored 파일에 smart-update가 정확히 어떻게 동작하는지는 **spec에서 실검증**(gitignored여도 on-disk diff 가능한지 vs tracked 필수인지).

이 이동은 worktree 프로비저닝(`wf-worktree-context`의 tracked 자동판별)과도 정합 검토 필요.

## 인용
- Copier updating (migrations·`--vcs-ref`·`--conflict`) — copier.readthedocs.io/en/stable/updating/
- Copier configuring — copier.readthedocs.io/en/stable/configuring/
- Copier FAQ (`.copier-answers.yml` 커밋) — copier.readthedocs.io/en/stable/faq/
