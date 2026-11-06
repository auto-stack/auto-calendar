---
plan_id: CALENDAR-003
status: executing
feature_name: 当前SDK文件写入与删除确认兼容
author: [Codex]
created_at: 2026-11-06
updated_at: 2026-11-06
plan_revision: 4
current_step: 1
total_steps: 4
base_branch: main
base_commit: 936423929b1773ee4e683cc4e5c16adf201a67d4
supersedes_spec_components: [docs/specs/calendar/recovery-identity.md]
new_spec_components: []
touched_goals: []
---

# CALENDAR-003：当前 SDK 文件写入与删除确认兼容

## 0. 变更摘要

auto-os/PLAN-054 正式当前 SDK Rust 构建发现旧 `fs.write_text` 布尔用法与现行整数返回不匹配。保留应用的布尔确认边界，以目标为普通文件且全文读回一致确认所需状态；不改变标准库、公共API或存储格式。

## 1. 目标

- G1：当前固定 SDK 下正式 Rust 生成编译成功，既有用户任务成立。
- G2：写入拒绝/缺父目录/目录冒充文件时不得把旧或缺失内容确认成功；删除以目标确已不存在确认，失败保留原文件并按原协议返回失败。
- G3：九个原布尔写调用；manifest/identity/版本文件/迁移备份/恢复报告沿原顺序，不改变generation/水位/墓碑协议。

## 2. 架构方案

唯一实施/复审目录 D:/autostack/auto-calendar，独立真实clone/main（按用户2026-10-29应用规约覆盖通用技能的框架worktree惯例）。不在auto-os/apps内编辑；已知src/front临时未跟踪目录保留。实现函数 `write_confirmed` 使用现有 fs 写入、目录判断、存在与全文读取，不以状态码真假猜测。目标为目录先拒绝。既有相同普通文件内容可被再次确认；true不证明本次发生物理写入。失败的不同内容请求必须false并保留旧内容。

## 3. 技术栈

现有.at与fs；永久Python测试提取实际函数，用已选CLI执行真实VM/文件系统；正式原生生成编译与父054实机/网页消费验证。无新库。

## 4. 需求分析与背景调查

继承用户“解决问题并最终完成054”及独立复审授权；这是原8应用/双端任务所必需的兼容前置，无新功能、预算或支持收窄。基线936423929b1773ee4e683cc4e5c16adf201a67d4；Langf03226e10、UIa1db3d79、Man2a9b16e、OS5e186935，冻结SDK176。正式失败：Notes E0308 bool/i64；Calendar当前源码九个布尔调用，正式构建10个类型错误。读过docs/specs/calendar/recovery-identity.md与Lang956字节/文件SDK实现；VM底层写入返回码也不能独立证明成功，因此须读回确认。原日志位于父唯一scratch D:/autostack/plan-artifacts/plan-054/t07；本子计划使用同一具名子目录，不复制到另一证据根。

## 5. 详细设计

T00定位已观察的真实调用与失败；T01完成 `write_confirmed`、`delete_confirmed` 及同因调用收口。调用参数单次传递，先拒绝目录，写入后检查存在并全文比对；删除辅助函数先拒绝目录、目标已不存在可幂等确认，否则调用原删除原语后检查不存在；仅替换event_delete_files的一个旧布尔删除判断，不改变墓碑先写/失败返回的原顺序。不新增状态全局变量。永久测试实际提取生产函数，fixture和输出仅在显式仓外scratch。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | AC |
|---|---|---|---|---|---|
| SD01 | modify | docs/specs/calendar/recovery-identity.md | 保留原存储合同，补辅助文件写入按普通文件及全文读回确认、删除按目标不存在确认；不承诺物理写/删次数 | 现行SDK整数返回与VM错误码不足以单独确认内容 | AC01/02 |

拟落地段落：辅助文件写入确认不依赖 `fs.write_text` 返回值真假；目录拒绝，普通文件存在且全文读回一致才返回true。已存在相同内容允许幂等确认。目录拒绝；删除成功须确认目标不存在，失败原文件保留，原身份水位/墓碑先写与删除协议不变。

## 6. 测试设计

实施本会话；独立上下文在同一clone复审，沿用户已授权054独立复审前置；无实现委派。work做定向红绿/生成编译；父054共同SDK实机任务为必要集成，review可明确冻结其merge-owned执行点；无整仓cargo测试。

| case | owner/AC | 实际入口/输入 | 观察判据与边界 |
|---|---|---|---|
| V01 | work/AC01 | 正式auto build -r rust；生产write_confirmed | 旧版本已红，新版编译0；不得复用旧exe |
| V02 | work/AC02 | tests/sdk_file_write.py，提取生产函数→实际VM：中文多行创建/覆盖、空普通文件、缺父目录、目录+空内容、只读不同内容、已有相同内容 | 真bool结果与实际文件全文/旧数据一致；只读不同内容false且原件SHA不变；目录不能因空读默认值误绿 |
| V04 | work/AC02 | tests/sdk_file_delete.py提取实际删除辅助函数→VM：已有/缺失文件、存活拒删句柄、目录及带子项目录 | 真Bool与实际不存在一致，失败文件全文/目录子项不变；只对既有应用普通文件路径，不扩展设备/IPC资源 |
| V03 | merge/AC03 | 父054公开Vue/iced入口受影响真实任务 | Notes保存重开/辅助文件确认，Calendar增改删重开与恢复身份文件一致；最终共同SDK与pin具名绑定 |

## 7. 验收标准

- AC01 owner_stage=work：当前SDK正式Rust构建成功，实际源/生成/产物身份一致。
- AC02 owner_stage=work：V02/V04实际执行，各有效/错误控制符合确认合同，无数据格式或API变更。
- AC03 owner_stage=merge：独立pass、规范落地、父054新SDK实际消费成功、main提交push、归档回执完整；所有未达项保持pending。

## 8. 执行步骤

- [x] T00 owner_stage=work：复核失败/生产路径/现行SDK，确认有界方案。
- [ ] T01 owner_stage=work：实现兼容与永久V02，正式生成编译V01，提交工作完成。
- [ ] T02 owner_stage=review：同一clone独立上下文复审当前源/Spec提案及结果。
- [ ] T03 owner_stage=merge：规范、父集成、提交push与归档；保留永久开发clone。

## 9. 复审记录

- stage:new | revision:r1 | outcome:pass | next:work/T00；父054授权覆盖原目标必要修复，禁止借本计划升级无关依赖或改应用功能。当前仅合同登记，未实施。

## 10. 待澄清事项

无新用户语义决定。独立复审、正式编译与父实际消费均未完成；不以新计划登记冒称已修复。


- stage:work | revision:r1 | round:1 | outcome:T00 complete/T01 in progress
  Source/repository/clone main ownership checked, pre-existing front tmp/tests directories preserved. Notes formal native E0308 and Calendar formal10 type errors reproduced with SDK176. Notes permanent extraction test on original helper actually returned seven numeric0 values instead of required Bool values (exit1), exposing the VM return-code ambiguity too. This is not a compile-only fix: full-content confirmation and directory-empty control close the common cause. All9 Calendar original call sites route through one helper; only its primitive call remains. New permanent production-helper execution is pending green; no execution_done or app pin upgrade.


- stage:new | revision:r2 | round:2 | outcome:pass | next:work/T01 deletion compatibility
  Current formal native buildr180 eliminated nine write type errors but isolated the tenth original error: event_delete_files uses !fs.delete although current File::delete returns i64. This is the same current-SDK filesystem compatibility goal; update bounded design/SD01/AC02 supplementary path while retaining all prior write work and evidence. No task total, public API, storage schema, recovery/deletion intent or user goal changes. Inventory of all changed file-operation types across the six native app sources also identified Todo's ignored-result wrapper, separately owned by TODO-003; other apps use numeric results or ignore them. No new framework coercion. Parent054 original full-delivery authorization covers this necessary repair; review still pending, not a failed final-review cycle.


- stage:new/work | revision:r3 | round:3 | outcome: valid failure fixture and deletion helper verified | next: current SDK formal build
  Same invariant/design asr2; correct the proposed invalid-input representative: Windows/Rust permits unlinking a file with a readonly attribute, so that attribute did not establish a delete rejection. First test incorrectly assumed the file survived and its cleanup raised FileNotFoundError; not a product failure or accepted pass. A real live Python CRT read handle without FILE_SHARE_DELETE now denies unlink, and source helper reportsfalse while original bytes survive. Current permanent deletion5/5Bool controls green: existing/missing true, locked/emptydir/populateddir false, children intact; write7/7 remains green on same production source. No OS input/Win32 activation/ctypes operations, only owned ordinary file handles. Source change is one deletion call routed through delete_confirmed plus helper; original tombstone-before-delete/manifest-after-delete order untouched.
  New Notes source formally compiledr179 exit0/189s. Calendar r180 has only the remaining old bool/int delete error (writes repaired); final formal rerun pending. Historical clone generated GPU locks reconciled with standard offline cargo update -p gpu-allocator@0.27.0 --recursive: only allocator's windows binding0.57→0.58, no package version changes, matching validated SDK. Source and Spec closure still needs independent review and actual parent consumption.


### T03 跨仓整合的阶段顺序（有界合同澄清）

用户应用规约要求独立clone/main开发、提交验证push后再更新AutoOS组合。此计划源码已在main开发；独立review通过当前代码/规范提案与work全部AC后，先推送具名“已审源码阶段”供父054候选组合验证。该动作不代表本计划已归档或最终交付pass。父候选只消费已提交/push/独立审核的源码，正式AutoOS gitlink交付仍等父验收关闭。随后完成本计划要求的父新SDK实际任务、规范落地、最终文档提交push与归档；最终Doc后继须证明src/pac与已测源码完全相等。所有AC/实际任务及原协议不变，未完成项不被转为pass。此顺序解决“应用先可获取、组合才可验证”的源发布依赖，不删减或转移任何既定验收。

- stage:work | revision:r4 | round:4 | outcome:execution_done2/4 | code_commit:f007ef76fb5df374952432fb4fca3ef7a39d03ca | next: independent source/Spec review
  Actual currentSDK formal native build and scoped checks: r182 exit0/44.46s; VMwrite7/7+delete5/5; actual generated Rust write4/4+delete4/4. SDK CLI84ffcd0782475f4a9f77ac626042c7a1354b23270930b985531f74212602425b / UItool56e50b44b3ff33c44a7fd61c1860e0fefeaa0efe7dd55fd6d1e7c9cf60382ea7, selected Langf032/UIa1db/Man2a9/OS5e18. Published artifact hash, generation inputs and exact current core dependency were checked for the actual generated-Rust execution; no copied implementation, stale binary or GUI/OS input synthesis. Unknown untracked front tmp/tests remain untouched; Notes formal receipt has no untracked src input.
  Legacy generated GPU lock reconciliation is configuration only: cargo offline recursive update of allocator changes only its windows0.57→0.58 edge (no package version changes), identical to SDK. Before locks/logs retained; failed old-lock builds explicitly not counted. Scope ordinary app data files/directories, not arbitrary device/IPC resources. Existing unrelated application/UI/schema mechanisms remain unchanged; parent current-SDK actual tasks and final closeout still pending.
  Native evidence: D:/autostack/plan-artifacts/plan-054/t07/generated-file-confirm-r178.json SHA256 768fda79093f9a13bb559a556215814dd08309fa3605855318c51fadc9052a96.
  Native evidence: D:/autostack/plan-artifacts/plan-054/t07/generated-delete-confirm-r184.json SHA256 dc0b4d9fd5b0aef1eba8c7f2e80fa856d62de30d7ab8a6187138d60ae59ea5b5.


### Independent source / Spec review — 2026-11-06

- stage: review | review_scope: final | reviewer_identity: delegated independent Codex context /root/review_app_sdk (no implementation performed; model identity not exposed) | plan_revision: 4 | outcome: needs_fix
- worktree_path: D:/autostack/auto-calendar | branch: main | reviewed_commit: 33408cdcd39b9a954c32a999d011c4a80b782ab4 | base_commit: 936423929b1773ee4e683cc4e5c16adf201a67d4. Existing real clone and single worktree verified with `git worktree list --porcelain`; user app-main rule governs. Implementation writes paused; tracked source clean at entry and verdict. Foreign untracked directories retained. Review skill and verification-contract read in full.
- dependency_revisions: Lang f03226e10 / UI a1db3d79 / Man 2a9b16e / OS 5e186935; SDK frozen-sdk-r176 CLI SHA256 84ffcd0782475f4a9f77ac626042c7a1354b23270930b985531f74212602425b.
- spec_inputs SHA256: bba8bf3c450628f5b42515319ecdeeb08942e44f510b348524b1fd2fd75ae2d0; frozen proposed `### 规范增量` text SHA256: 2415636071a2ca420e50e5d712c9d213a4cb8d4aaf9402d03c5ae402f2788039. Canonical Specs and legacy ledger untouched. `touched_goals: []` is appropriate: this is existing goal compatibility, no new goal identity.
- acceptance_results: AC01 pass — reuse formal native build r179 (Notes, exit0/189s) or r182 (Calendar, exit0/44.46s); independently matched generation.json pac/src input hashes to current files and published executable hashes to receipts. AC02 fail — original permanent VM write7/7 independently replayed exit0 with exact Bool and file assertions, but holdout F-SDK-EMPTY-01 below fails. Calendar delete5/5 independently replayed exit0 including real locked handle; original tombstone → all versions delete → manifest ordering remains unchanged. AC03 pending merge-owned, not claimed complete.
- source/provenance: complete baseline→HEAD source diff inspected; Notes only fs_write, Calendar all nine writes and one deletion predicate share helpers. No API/schema/SQLite/watermark/tombstone changes. Native generated helper evidence source extraction, current Cargo fingerprint→core RLIB linkage, published hash, ordinary-file controls inspected: generated-file-confirm-r178.json SHA256 768fda79093f9a13bb559a556215814dd08309fa3605855318c51fadc9052a96 (8 controls); generated-delete-confirm-r184.json SHA256 dc0b4d9fd5b0aef1eba8c7f2e80fa856d62de30d7ab8a6187138d60ae59ea5b5 (4 controls). GPU reconciliation changes only existing allocator windows dependency edge 0.57→0.58; no package version upgrade. No Cargo/global suite repeated.
- F-SDK-EMPTY-01 | P1 | AC02/T01 | existing rule failure: rejected different-content write must return false and old bytes survive. Setup a normal file containing bytes `ff fe 80`, mark readonly, invoke actual production write helper with empty string through frozen SDK real VM. Expected false + original bytes; observed true + original bytes `fffe80` in both Notes and Calendar, exit0. This is a regular file and a supported empty-content request, not a device, symlink or physical-write-count claim. Root cause: read failure falls back to empty string (`auto-lang-core/src/a2r_std.rs` fs::read_text uses read_to_string(...).unwrap_or_default()), so equality with empty desired text cannot prove successful full read. Runtime VM reproduces the ambiguity too. The directory guard closes only another empty-default path.
- minimal replay: run frozen-sdk-r176/auto.exe against the matching probe.at referenced in D:/autostack/plan-artifacts/plan-054/t07/review-app-sdk/invalid-utf8-review.json, with its readonly fixture re-established (otherwise the write can succeed). Receipt SHA256 3fee4497a43a26f6bbed5234bdcd1e8cc759f2c22e90a1ba3afb87778bbd559e; durable setup/expected/observed above permits recreation after scratch removal. Independent regular UTF-8 create/overwrite/empty, missing parent, directory, readonly different-text and readonly same-text controls all pass; retain them.
- closing oracle: permanent source-extracted test covers readonly non-UTF8 old bytes + empty desired content, false plus old-byte preservation, with existing legitimate empty-file and idempotent controls retained; independently verify affected VM/native confirmation behavior using actual supported SDK facilities. This receipt does not prescribe an unverified fix or require framework changes. SD01 proposal states the right enduring contract but implementation does not yet satisfy its full-content claim; source/Spec approval withheld.
- pending_closeout_gates: T03 parent054 common-SDK actual Vue/iced tasks, canonical Spec landing, source-bound final doc successor, push/pin and archive all remain pending. T03 ordering is explicit and self-consistent: after successful independent source/Spec review, publish named reviewed-source stage for candidate fetch, then actual parent tasks and final Spec/docs/push/archive. It grants no final delivery pass and does not waive any AC. This needs_fix prevents the source-stage publication until repaired/re-reviewed.
- next: work in the same clone, close F-SDK-EMPTY-01 with targeted checks, commit repair then independent affected re-review. T01 reopened; T00 retained; current_step=1/4.
