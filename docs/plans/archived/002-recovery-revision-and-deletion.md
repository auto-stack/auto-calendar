---
plan_id: CALENDAR-002
status: archived
feature_name: "恢复后版本凭据与删除保全"
author: [Codex]
created_at: 2026-11-01
updated_at: 2026-11-02
plan_revision: 1
current_step: 8
total_steps: 8
base_branch: main
base_commit: 411805cba8283082ad88de47a15686053d46a0f7
depends_on: ["CALENDAR-001"]
supersedes_spec_components: ["docs/specs/calendar/basic-capabilities.md"]
new_spec_components: ["docs/specs/calendar/recovery-identity.md"]
touched_goals: []
---

# CALENDAR-002：恢复后版本凭据与删除保全

## 0. 变更摘要

接续001已交付的单次本地事件，关闭manifest恢复时版本/序号仅取幸存事件最大值的窗口，保留删除事实和条件写保护，并收口独立运行。原有墙钟语义不改，不扩重复/提醒。

## 1. 目标

删除高版本/最高ID事件、manifest损坏或丢失之后恢复，陈旧写者不能因版本凭据重用而被接纳，已删事件不复活，后续新ID不冒充旧对象。无法证明恢复身份时明确拒写并保留原件；恢复完成后真实UI下一次创建/编辑能成功。

非目标：掉电级fsync保证、CalDAV/重复规则/后台提醒/DST时刻语义、多写者数据库重构、OS/Linux。

## 2. 架构方案

本仓为主导仓，开发/检查/最终复审顺序使用 `D:/autostack/auto-calendar` 独立clone的 `main`，一app一写入者，复审时暂停实现写入；不在AutoOS子模块开发，不建junction/symlink。框架若确有缺项，先核实现有公共能力和当前实际owner，再在owner仓另立最小前置并遵守其worktree规约，本计划不授权越仓改实现。

应用业务保持纯.at；复用既有仓储、UI、测试，不手写业务Rust、不改生成Rust/Vue来交付。源知识为docs/specs；本轮只列Spec提案，不写canonical、旧specs.json或手工索引。未知技术方案由T-00有界调查，不能靠占位/必需skip关闭验收。

独立运行门使用新建且本次拥有的临时数据/端口/构建输出；不删除既有app/框架target、不停止他人实例。CLI和真实编译/渲染tool都记版本/hash及发现路径；进程清理按本次spawn归属，不凭端口或命令行相似就杀进程。冷准备允许耗时，但须有阶段、就绪判定、有界超时和非零失败；预算及资源边界在T-00先冻结。

复用versioned事件文件、manifest和条件写；T-00先验证当前SDK的原子文件/持久化原语，不沿001的旧“无原语”结论直接造一套事务。优先最小持久化高水位/删除记录或可验证generation＋revision方案，正确性由ABA与删除反例决定，不预定机械文件名。

## 3. 技术栈

现有.at、Rust生成服务、版本化JSON、calendar_store、双端verify_basic.py；独立文件/JSON/hash oracle。保持现有真实时钟/测试墙钟接口；已交付time能力只在T-00核对，不顺便改时间模型。

## 4. 需求分析与背景调查

用户2026-11-01要求接续其余原B类应用的下一步计划，沿上一轮“计划/README/roadmap、提交push，不开始实现、不更新OS子模块”的范围执行。Reader已转另一个会话按Readest新目标跟踪；Blog现有上游阻塞由原计划继续，Chat/Charts不在本轮改面。应用单独运行不等OS装配或其他app；Linux仍WAIT_DISTRO_M1（Nix＋COSMIC基础）。

Spec§4/F-5已登记全局rev回退：manifest_recover仅从幸存事件取max_rev/max_seq；event_delete_files删除该id所有版本；manifest_ensure还可回落fresh。因而删除最高项/全部删除后的恢复，可能重用版本或ID（后两者须先以隔离反例实证），不能靠旧顺利重开案例关闭。当前tests/free_ports.py会按默认端口和auto-calendar命令行终止监听者，实施前须收窄自有进程纪律，不能把它当准备步骤自动运行。

| 来源文件 | SHA256 |
|---|---|
| `docs/specs/calendar/basic-capabilities.md` | `91774a5f46e59016a11d771d614e67bdef12a3a761c6f79c35fbc4b70b78495b` |
| `src/back/repository.at` | `9ee22b878d5731ac51a0c30642181e8430bc4695eb6fa4dfa0b1f3306f20cde9` |
| `src/back/db.at` | `cbb8993466fcb545bafa9c1fc8d2b80b8a5ff3fe75a002a67256c42874374074` |
| `src/front/calendar_store.at` | `2f1fd2eb82fb0c0ea6b08582b405a6c801fe4c539150421797c77f416c17e093` |
| `tests/basic/verify_basic.py` | `f34e7cba4c2cbc39f9dcfd7cb6fcd81ebded726af41e8d72d6e10a7c7432d717` |
| `tests/free_ports.py` | `fc43c9794c5bed64dc55534cb86e2093de541d3a5fe266ffd7320fcb57a1c6b4` |

实施漂移核对（T-05，全部为计划授权变更，无计划外漂移）：

| 文件 | r1 基线 hash → 实施 hash (sha256 前位) | 变更来源 |
|---|---|---|
| docs/specs/calendar/basic-capabilities.md | 91774a5f → 00917b72 | SD-01（§4 r2 修订+§5/§6 入口） |
| src/back/repository.at | 9ee22b87 → a87122c3 | T-02 v2 协议 |
| src/back/db.at | cbb89934 → 765f3bc7 | T-02 五入口改门 |
| src/front/calendar_store.at | 2f1fd2eb → 3ab194ac | T-03 recovery_state 消费 |
| tests/basic/verify_basic.py | f34e7cba → 90b3a013 | T-01 自有进程收窄 + extra_env |
| tests/free_ports.py | fc43c979 → f994078a | T-01 所有权门重写 |
| src/back/api.at | （新增字段）→ 2ede8df8 | T-02 recovery_state/generation |
| src/front/app.at | → 1b261736 | T-03 保全横幅/拒写文案 |
| tests/basic/recovery_driver.mjs | 新文件 d6f2a54e | T-03 |
| tests/basic/verify_recovery_identity.py | 新文件 45372414 | T-03/T-04 |
| docs/specs/calendar/recovery-identity.md | 新文件 32dd603f | SD-02 候选 |

## 5. 详细设计

T-00新增 `docs/plans/evidence/002/recovery-decision.md`：复现F-5与最高ID/全删状态；确定可验证的版本身份、删除事实、分配器高水位及v1迁移。实现前冻结每个持久化步骤的成功/中断/拒写选择、支持资源规模和可靠原语；保留数百事件规模，不能宣称无限/掉电原子性。

最低不变式是**旧条件凭据不得在恢复后意外再次有效**。可用单调高水位，也可用不重用的generation＋revision；后者不能继续只靠旧int expected_rev授权。若需扩API，前端同步消费并明确旧客户端拒绝/刷新流程；不能隐式降级兼容。T-00闭合这项设计后才实施依赖任务。

旧v1数据可控迁移，先备份/核对；正常新空目录仍可初始化，历史数据缺证据与新空库严格区分。所有可信恢复凭据丢失/损坏时不得凭幸存max或fresh默默制造新身份；给出保全诊断/受控恢复路径。删除完成后即使manifest重建也不得复活；删除部分失败必须有可恢复且不假成功的结果。后续新事件不得复用旧已确认ID，高水位或generation策略以T-00方案明确。

复用 `python tests/basic/verify_basic.py --profile vue|vm`；拟新增 `tests/basic/verify_recovery_identity.py` 由T-04落地。真实UI生成/编辑/删除，故障仅在隔离副本注入，独立文件oracle验证；未来新元数据路径先记录为拟议，不在规划期创建。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | modify | docs/specs/calendar/basic-capabilities.md | 幸存max回退边界→版本身份不重用、删除/ID保全与兼容；墙钟不变 | 关闭F-5与同源恢复窗口 | AC-02/03/04 |
| SD-02 | add | docs/specs/calendar/recovery-identity.md | 明确持久化提交/故障/迁移/拒写与独立运行门 | 让恢复选择可复验 | AC-01..04 |

## 6. 测试设计

以下C用例owner_stage=work，T-04使补充入口可运行。正常与故障按真实文件提交点注入，不把测试进程异常等同持久化阶段已发生。

| Case ID | AC | 输入/入口/状态 | oracle/预期 | 边界 |
|---|---|---|---|---|
| C-01 | AC-02 | A持旧凭据；B多次写后删最高rev项；破坏manifest并恢复，A提交 | A被明确拒绝，现有内容hash不改；新读取者取得新凭据后可写 | 直接区分ABA，非只看数值增长 |
| C-02 | AC-03 | 删除最高ID和全部事件，再损坏/丢manifest、冷重开/新建 | 已删不复活、新事件身份不重用；仍有合法空库正常对照 | 含全删与真实新空根 |
| C-03 | AC-02/03 | 冻结的高水位/删除/manifest提交各关键失败；恢复凭据双损坏 | 无假成功、原件保全、不能fresh重置旧身份；合法修复后下一次写成功 | T-00先列真实步骤/诊断 |
| C-04 | AC-04 | 正常v1迁移/取消或失败、中文跨月事件UI CRUD、正常/强杀重开 | 原id/墙钟正文不改，失败表单保留，后续编辑可保存 | 不加入时刻/DST合同 |
| C-05 | AC-01/04 | 独立准备/双端启动及旁观监听者；强制旧max策略反例 | 自有资源收割、旁观不受影响；旧策略必须被C-01/02检测且总门非零 | 不执行旧free_ports广域清理 |

review独立上下文必须核对C-01/C-02的新旧写者身份、文件状态和下一次真实读取/写入，不能只采信绿总数或回退时“还有事件”。

## 7. 验收标准

- AC-01（owner_stage=work）：独立准备/启动、错误及自有进程清理可复验，C-05相关路径通过。
- AC-02（owner_stage=work）：恢复不接纳旧条件凭据；证据不足安全拒写，恢复后合法新写可继续，C-01/C-03通过。
- AC-03（owner_stage=work）：删除事实/ID不重用、全删/新空库区分和失败保全，C-02/C-03通过。
- AC-04（owner_stage=work）：旧v1兼容/墙钟/双端真实操作与下一次写入、永久门和反控成立，C-04/C-05通过，文档/SD一致。
- AC-05（owner_stage=review）：冻结实现和依赖独立复审AC-01..04、SD-01/02及提交/恢复状态。
- AC-06（owner_stage=merge）：仅app规范/新计划归档计数/提交push收尾，不更新OSpin、不改001历史。

## 8. 执行步骤

- [x] T-00（owner_stage=work；依赖001；AC-01..03）：复现恢复反例，冻结版本/删除/ID/迁移/提交故障设计和实际SDK能力，输出决策稿。
  - [✅ 已完成] 决策稿 docs/plans/evidence/002/recovery-decision.md；4 窗口全复现（F-5 ABA 陈旧凭据落盘、删最高ID重用ev-5、全删≡新空库+ev-1重发、删中途残留r3折叠复活），控制组2项成立（锁文件删除不假成功、孤儿折叠保全）；SDK复核：内嵌 facade 仍无 rename/原子写，write_text=截断写，设计走持久化单调高水位+墓碑+证据不足拒写（§4.3分案A..D+consent出口），manifest格式不动、StoreStatus增recovery_state/generation、新err_code recovery_unproven。证据：plan-artifacts/plan-002/evidence/t00-repro-20261101-223021.json（红7/控制2、逐项观察+存储清单）、probe_t00_recovery.py（复跑入口）、auto CLI 0.1.0+plan-890-verified-r7-t19-5-g55c98c7 sha256 390e664e…（全量入证）、auto-lang master 367258e7a（只读）。
  - [修复轮 r1-review] F-1/F-2/F-3：决策稿 §4.1 generation 改按因常量披露、§4.2 表①/②后行改快路径推迟折叠+corrupt_count 措辞、§4.3C 迁移改覆盖式可再发生——措辞对齐实际行为，设计不变式零变更。
- [x] T-01（owner_stage=work；依赖T-00；AC-01）：复用旧门收窄自有进程/端口清理并固定独立准备/工具身份。
  - [✅ 已完成] tests/free_ports.py 重写为所有权门：正识别（image路径在仓内或cmdline含仓路径，且启动晚于运行起点）才可收割，旁观者只报告不杀；`--check` 只查不杀（占用即 rc=1+pid/image 明细）。verify_basic.py 同步收窄：删除 image名 级 taskkill 与 free_ports 广域清理，kill_all=Ownership.harvest（只杀注册pid/树），端口占用中止改为明细报告，证据 JSON 固化工具身份（auto --version、node --version、sha256、cleanup 报告、纪律声明）。探针 5/5：check 报告占用不杀、verify 中止 rc=2 旁观者存活、栈识别、自有收割只杀自有（后端+auto树）、旁观者全程存活。证据：plan-artifacts/plan-002/evidence/t01-ownproc-20261101-223625.json + probe_t01_ownproc.py。
- [x] T-02（owner_stage=work；依赖T-00及确需最小前置；AC-02/03）：实现最小恢复身份/删除/分配器保护及旧v1受控迁移，先后回放C-01..03。
  - [✅ 已完成] 无跨仓前置需要（当前SDK原语足够）。实现：repository.at 增 identity.json（schema 2：generation/rev_high/seq_high/tombstones）、scan_view（墓碑感知折叠扫描）、store_recover 分案A..D（快路径+慢修复、v1迁移先备份 identity-v1-migration.json、case D 拒写、consent 出口写 recovery-report.json 后重锚 g-recovered），manifest_recover/manifest_ensure 退役；db.at 五入口改 store_recover 门（unproven→recovery_unproven 拒写+只读扫描视图）、create/update ②identity水位→③manifest、delete ①墓碑→②删文件→③manifest；api.at StoreStatus/EventsList 增 recovery_state+generation。回放30/30：C-01 冷重启后水位rev=8、陈旧凭据conflict、新读取者可写、事件文件逐字节不变；C-02 删最高ID后新id=ev-6、全删rev=6 vs 新空rev=0、id续ev-4；C-03 墓碑压残留文件不复活、双凭据丢失拒写且原件hash不变、v1迁移备份字节一致+g-v1、consent后写入rev=3、孤儿折叠控制保留。证据：plan-artifacts/plan-002/evidence/t02-replay-20261101-225947.json + probe_t02_replay.py。
  - [修复轮 r1-review] F-4：repository.at scan_view 去 mkdir_all（只读扫描不再创建目录）；F-1 头注 crash-window 措辞对齐快路径推迟语义。受影响共享检查=全电池在修复码上重跑 30/30（t02-replay-20261102-001500.json）+ F-4 专项探针 PASS（store 仅残破 identity 时 unproven 读零目录创建、拒写保持，f4-closure.json）；产品语义不变（其余门证据按不变输入沿用）。
- [x] T-03（owner_stage=work；依赖T-01/02；AC-04）：前端消费恢复/冲突契约，真实UI跑跨月/失败保稿/退出重开后下一次写入。
  - [✅ 已完成] calendar_store.at 增 recovery_state/generation 字段，Init/月导航/SelectDay/三变更/SaveForm 全路径捕获列表态，recovery_unproven 失败时置 unproven 且不动 store_rev；app.at 增保全横幅（unproven 显式态+consent 指引）与表单专用拒写文案（输入保留不变）。新增 tests/basic/recovery_driver.mjs（seed/restart/unproven/consent 四相）与 tests/basic/verify_recovery_identity.py（双 profile 永久入口：C-01/02 HTTP 反例+C-03 UI 面+C-04 中文跨月 CRUD/强杀重开/墙钟不改/下一次写入+consent 后真实 UI 写入），verify_basic.launch_app 增 extra_env。vue 轨 31/31（r04 墙钟字段与 id 稳定、r03 横幅+拒写+保稿、c01/c02 反例、c03 consent 重锚+4事件保全），清理 clean。证据：docs/plans/attachments/002/verify-rec-vue-20261101-231622.json（local-only）。
- [x] T-04（owner_stage=work；依赖T-03；AC-04）：使补充入口可执行，跑C-01..05、旧墙钟/事件门及真实故障反控，准备SD候选。
  - [✅ 已完成] 双轨补充入口可执行：verify_recovery_identity.py --profile vue|vm（vm 轨 MCP 驱动；首轮 23/28 暴露 5 处探针 oracle 缺陷——编辑按首行、双次"<"跨过一月、month_events 渲染为 vmref、横幅/f_title 查错字段——修复后 28/28，产品零改动）。总门：recovery vue 31/31 + vm 28/28；旧门 verify_basic vue 19/19 + vm 11/11（001 墙钟/事件/重开合同无回归）；深电池 probe_t02_replay 30/30（真实冷重启、迁移备份字节、consent 报告）。旧 max 策略反控=c01-stale-refused/c02-id-not-reissued 断言（旧策略必红）。SD 候选已备：basic-capabilities.md §4 r2 修订稿 + 新 recovery-identity.md（canonical 候选，随 merge 生效）。证据：attachments/002/verify-rec-{vue-20261101-231622,vm-20261101-234520}.json、verify-{vue-20261101-232913,vm-20261101-233228}.json（local-only）、plan-artifacts/plan-002/evidence/t02-replay-20261101-233229.json。
  - [修复轮 r1-review] F-1/F-2/F-3 + 非阻塞注记：recovery-identity.md §3 表改写（快路径推迟折叠+晚到孤儿披露段+墓碑可见窗口变更语义）与 §2 generation/§4 case C 措辞对齐；F-5：basic-capabilities.md §4 "每变更一至两次 identity 写（delete 两笔）"。
- [x] T-05（owner_stage=work；依赖T-04；AC-01..04）：核对漂移/覆盖和README/roadmap，提交execution_done。
  - [✅ 已完成] 漂移核对：§4 六文件中 4 个按计划授权变更（上表 11 项含新增，无计划外漂移；git log 无越权文件）。覆盖核对：AC-01=t01 探针 5/5+各门 ports-free/cleanup clean；AC-02=c01-stale-refused（冷重启后 rev=8、陈旧 conflict）+c03 拒写/consent/再写（双轨+深电池 30/30）；AC-03=c02 id 不重用/全删 rev=6 vs 新空 0/墓碑压残留（双轨）；AC-04=旧门 vue 19/19 + vm 11/11（墙钟/重开/输入保留零回归）+C-04 中文跨月 CRUD/强杀重开（id 与墙钟字段逐字节稳定）+SD 候选与 README/roadmap 一致。AC-05=review 持有、AC-06=merge 持有（pending，不标记完成）。README/roadmap 已同步 002 实施态与新验收入口。
  - [修复轮 r1-review] README 计数措辞改"门全绿"分族列报；roadmap 无需变更（措辞本就准确）。
- [x] T-06（owner_stage=review；依赖T-05；AC-05）：同clone独立上下文最终复审。
  - [✅ 已完成] 独立 fresh 子代理终审两轮：首轮 764380e needs_fix（F-1..F-5，AC-01..04 全 pass 自有 60 探针+两门重放）；修复轮 1d30fa9 **pass**——F-1..F-5 逐项闭环双验证（probe4/probe5 于修复码重建：快路径推迟折叠实演、unproven 读全树字节零变更、缺 events 目录空视图落水位合同、迁移备份字节相等），无新增发现，AC-01..04 沿用。证据：plan-artifacts/plan-002/review/final-review-report.md。
- [x] T-07（owner_stage=merge；依赖T-06 pass；AC-06）：仅app规范/归档/提交push收尾。
  - [✅ 已完成] 见 §9 merge 收据：canonical 两文档随实现已在 main（22503e8 备/1d30fa9 修），归档+push+plan-artifacts 整删+registry 刷新；OS pin 移交显式记录（本仓不可代行）。

## 9. 复审记录

- stage: new | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass（有界T-00准备就绪；本轮没有实现或产品验收） | next: work/T-00（等待后续实施指令）。
- 已归档001、现实现Spec和产品源码保持不变；规划结构/链接通过不等于功能通过。review以同一clone的独立上下文核验，不自动创建agent/chat或指定模型。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass | worktree_path: D:/autostack/auto-calendar（独立clone main，按计划§2覆盖默认worktree规约） | branch: main | base_commit: 3db7cdd | code_commit: 见T-00提交 | dependency_revisions: auto CLI 0.1.0+plan-890-verified-r7-t19-5-g55c98c7（sha256 390e664e…）；auto-lang master 367258e7a（只读facade依据） | task_ids: T-00 | evidence=docs/plans/evidence/002/recovery-decision.md（红基线7红+2控制全记录：S1 F-5 ABA、S2 删ID重用、S3 全删≡新空库、S4 删中断复活+锁文件不假成功、S5 孤儿折叠保全；SDK当前原语复核、v2协议冻结§4.1..4.6、逐中断点语义、迁移/consent边界、残余R-1披露） | blockers=无 | next_responsible_role=work（T-02）。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: 67b5827 | code_commit: 见T-02提交 | dependency_revisions: 同T-00 | task_ids: T-02 | evidence=plan-artifacts/plan-002/evidence/t02-replay-20261101-225947.json（30/30：C-01..03全绿+R0/S5/S9控制，含真实冷重启与consent重启两轮进程级注入）+ src/back/{repository,db,api}.at（v2协议实现） | blockers=无 | next_responsible_role=work（T-03）。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: a8417ae | code_commit: 见T-03提交 | dependency_revisions: 同T-00 | task_ids: T-03 | evidence=docs/plans/attachments/002/verify-rec-vue-20261101-231622.json（vue 轨 31/31：跨月 CRUD/强杀重开/墙钟不改/unproven 横幅+拒写+保稿/consent 后下一次写入，local-only）+ src/front/{calendar_store,app}.at + tests/basic/{recovery_driver.mjs,verify_recovery_identity.py} | blockers=无（vm 轨由 T-04 统一门跑） | next_responsible_role=work（T-04）。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: 662c6f6 | code_commit: 见T-04提交 | dependency_revisions: 同T-00 | task_ids: T-04 | evidence=四门全绿（rec-vue 31/31、rec-vm 28/28 修复 oracle 后、basic-vue 19/19、basic-vm 11/11、深电池 30/30）+ docs/specs/calendar/{basic-capabilities.md §4 r2, recovery-identity.md} 候选稿 | blockers=无 | next_responsible_role=work（T-05）。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass（execution_done） | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: 22503e8 | code_commit: 见T-05提交（文档同步，产品代码冻结于 22503e8） | dependency_revisions: auto CLI 0.1.0+plan-890-verified-r7-t19-5-g55c98c7（sha256 390e664e…）；auto-lang master 367258e7a（只读） | task_ids: T-05 | readiness: 工作面 AC-01..04 全部绑定实测断言（rec-vue 31/31、rec-vm 28/28、basic-vue 19/19、basic-vm 11/11、深电池 30/30，终态代码）；开放契约发现=无；受影响旧用例回放=basic 双 profile 即旧门全量；测试=四门族+三探针，本轮修复仅探针 oracle（vm 5 处），产品代码自 22503e8 前无变更；统一回归门 pending（owner=复审/merge，按仓工作流） | evidence=本文件§4漂移表+§8 T-05行+attachments/002 各 verify JSON（local-only） | blockers=无 | next_responsible_role=review（T-06 final review, review_scope=final）。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass（F-1..F-5 有界修复轮） | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: 204d36f | code_commit: 见修复轮提交（repository.at scan_view 一行码+头注；其余全为文档措辞） | dependency_revisions: 同前 | task_ids: T-00/T-02/T-04/T-05(重开，修复范围) | findings_closure: F-1→决策稿§4.2+repository.at头注+SD-02§3披露对齐快路径推迟折叠（设计不变式零变更，v1同源语义显式披露）；F-2→迁移改"覆盖式可再发生"（决策稿+SD-02）；F-3→generation 按因常量披露（决策稿+SD-02）；F-4→scan_view 去 mkdir_all+专项探针 PASS（unproven 读零目录创建）；F-5→basic-capabilities §4 两笔措辞；注记→delete②后 corrupt_count 措辞、README 分族计数 | evidence=plan-artifacts/plan-002/evidence/t02-replay-20261102-001500.json（修复码全电池 30/30）+f4-closure.json | blockers=无 | next_responsible_role=review（受影响范围复审）。
- stage: review | review_scope: final（受影响范围复审） | reviewer_identity: 同一独立 fresh 子代理（延续首轮会话，跨轮记忆仅限其自有审查工件；限制同前：Windows-only、UI 证据经提交 harness/驱动） | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | reviewed_commit: 1d30fa9 | base_commit: 764380e（首轮终审基线） | dependency_revisions: 同前 | spec_inputs: basic-capabilities.md §4 r2 + recovery-identity.md（F-1..F-5 措辞对齐后版本） | acceptance_results: F-1..F-5 逐项闭环双验证（复审者自有 probe4/probe5 于修复码重建：快路径推迟折叠实演、unproven 读全树字节零变更、缺 events 目录空视图走水位合同、迁移备份字节相等）；AC-01..04 沿用首轮结论（产品增量仅读路径 mkdir 移除，复审者直接探明新行为落水位合同）；AC-05=本复审 pass；AC-06 pending（merge） | pending_closeout_gates: 统一回归门（merge 持有） | findings: 无新增（修复 diff 恰定域：scan_view+头注+五文档；无 ledger 写入；树 clean） | evidence: D:/autostack/plan-artifacts/plan-002/review/final-review-report.md（re-review 记录+probe_review4/5+JSON） | next: merge（T-07）。
- stage: merge | plan_id: CALENDAR-002:r1 | outcome: pass | delivery_commit: 1d30fa9（产品代码终态）| main tip: 归档簿记提交 | prepared: 开发按§2直接在独立clone main进行（无开发分支/worktree，landing 无 ff/rebase 步骤；默认分支 tip 即交付线） | landed: 默认分支 tip=交付线（线性历史，无 merge commit；`git log --oneline` 53587a4..归档tip 全链可溯） | canonical_verified: docs/specs/calendar/basic-capabilities.md（§4 r2 修订，sha256 d100777e3cf178c9…）+ docs/specs/calendar/recovery-identity.md（新增，sha256 bba8bf3c450628f5…）@ 归档 tip；SD-01/SD-02 与实现一致经终审逐条核对（修订稿 22503e8 落、1d30fa9 对齐 F-1..F-5） | archived: docs/plans/archived/002-recovery-revision-and-deletion.md（status: archived，git mv，簿记随 default 分支提交） | cleaned: 无 worktree/分支可清（§2 独立clone纪律，wt-guard 不适用）；plan-artifacts/plan-002 整删（证据先折叠：红基线 t00-repro-20261101-223021.json、修复码全电池 t02-replay-20261102-001500.json 30/30、F-4 专项 f4-closure.json、复审报告 review/final-review-report.md 两轮+probe JSON、门运行摘要数字已录本文件§8/§9）；registry D:/autostack/plan-artifacts/.retention/policy.json 已刷新 auto-calendar/CALENDAR-002 条目（deleted_scopes=[plan-002]，无 holds） | landing_checks: 本app为按需运行（`auto run` 即构建即运行，无独立 release 守护/构建产物），无 stale artifact 可记；统一回归门=四门族已在终态代码全绿（本文件§8 T-04/T-05），merge 无独立批量回归机制（本仓无 .last-batch-regression.json，非 auto-lang 约定）；OS 侧移交见 §10（gitlink/总表/detach，owner=AutoOS 统一计划） | push: origin/main ff 推送（AC-06） | next: done。
- stage: merge | plan_id: CALENDAR-002:r1 | checkpoint: cleaned | cleaned_at: 2026-11-02 | 归档态核验：docs/plans/archived/002-recovery-revision-and-deletion.md（status: archived、8/8 任务 [x]、current_step 8）、README/roadmap 链接已指向 archived 路径、canonical 两文档在 main tip（hash 见上行）、无残留 docs/plans/002 未归档链接；plan-artifacts/plan-002 已整删（1.8M，含复审自有探针数据，证据摘要已全部折叠入本文件）；registry auto-calendar/CALENDAR-002 条目刷新（deleted_scopes=[plan-002]、无 holds） | next: done（merge 全部 checkpoint：prepared/landed/canonical_verified/archived/cleaned 全录）。
- stage: goal | plan_id: CALENDAR-002 | plan_revision: 1 | round: 1 | from: drafting | to: work | status: execution_done | outcome: pass | worktree: D:/autostack/auto-calendar（独立clone main，按计划§2覆盖默认worktree规约） | commit: 25070e6 | next: review（授权链：用户 /goal 经 auto-plan-goal 一线授权 work→review→bounded repair→merge；T-00..T-05 六提交 53587a4..25070e6，四门族全绿，统一回归门 pending owner=review/merge）。
- stage: goal | plan_id: CALENDAR-002 | plan_revision: 1 | round: 2 | from: work | to: review | status: execution_done | outcome: pass | worktree: D:/autostack/auto-calendar（独立clone main） | commit: 764380e | next: review（终审基线 764380e，树 clean，代码 diff 基线 3db7cdd）。
- stage: goal | plan_id: CALENDAR-002 | plan_revision: 1 | round: 3 | from: review | to: work | status: executing | outcome: needs_fix | worktree: D:/autostack/auto-calendar | commit: 204d36f | next: work（有界修复 F-1..F-5，修复轮提交 1d30fa9）。
- stage: goal | plan_id: CALENDAR-002 | plan_revision: 1 | round: 4 | from: work | to: review | status: executing→reviewed | outcome: pass | worktree: D:/autostack/auto-calendar | commit: 1d30fa9 | next: merge（授权链继续：merge→done；修复轮 1d30fa9 复审通过，AC-06 待 merge）。
- stage: goal | plan_id: CALENDAR-002 | plan_revision: 1 | round: 5 | from: merge | to: done | status: archived | outcome: pass | worktree: D:/autostack/auto-calendar（独立clone main） | commit: 归档簿记 tip | 交付核对：canonical 两 Spec 在 main（basic-capabilities §4 r2 + recovery-identity 新增）、计划归档 docs/plans/archived/、8/8 任务、线性历史推送 origin/main、无 worktree/分支、plan-artifacts/plan-002 整删+registry 刷新、无 holds；OS 侧移交显式记录（§10）。目标「完成计划002」达成。
- stage: review | review_scope: final | reviewer_identity: 独立 fresh 子代理上下文（general-purpose agent，同检出 764380e，无实现会话记忆；限制：Windows-only、UI 证据经提交 harness/驱动判定、复审自有探针为本机时序） | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: needs_fix | worktree_path: D:/autostack/auto-calendar | branch: main | reviewed_commit: 764380e | base_commit: 3db7cdd（代码 diff 基线） | dependency_revisions: auto CLI 0.1.0+plan-890-verified-r7-t19-5-g55c98c7（sha256 一致）；auto-lang master 367258e7a | spec_inputs: basic-capabilities.md §4 r2 候选 + recovery-identity.md 候选（随实现核对） | acceptance_results: AC-01/02/03/04 全 pass（复审者自有 60 探针检查+两门重放 rec-vm 28/28、basic-vue 19/19；C-01/C-02 新旧写者身份/盘面/下一次真实读写均亲自核对：恢复 rev=8 非 4、陈旧 conflict、新写 rev=9、ev-6 不重发、全删 rev 10 vs 新空 0、墓碑压残留、迁移备份字节相等）；AC-05=本复审；AC-06 pending（merge） | pending_closeout_gates: 统一回归门（merge 持有） | findings: F-1(medium,§4.2措辞vs快路径实际：crash-① 孤儿折叠被快路径推迟到下次慢路径/manifest丢失——v1同源语义、不变式无破口，修复=决策稿§4.2行+repository.at头注+SD-02§3披露对齐)；F-2(low,再迁移覆盖备份与"至多一次"措辞冲突)；F-3(info,generation为按因常量非每store唯一)；F-4(info,unproven 读路径 mkdir events/ 目录与"不落盘"措辞差)；F-5(info,§4"每变更一次identity写"实为delete两次) | evidence: D:/autostack/plan-artifacts/plan-002/review/final-review-report.md（复审探针 probe_review*.py+JSON+两门日志） | next: work（有界修复 F-1..F-5：文档对齐为主+scan_view 去.mkdir_all 一行码，产品语义不变）。
- stage: work | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: 53587a4 | code_commit: 见T-01提交 | dependency_revisions: 同T-00 | task_ids: T-01 | evidence=plan-artifacts/plan-002/evidence/t01-ownproc-20261101-223625.json（5/5：旁观者三路径存活、自有收割只及注册pid）+ tests/free_ports.py（所有权门）+ tests/basic/verify_basic.py（kill_all/端口门收窄+工具身份入证） | blockers=无 | next_responsible_role=work（T-02）。

## 10. 待澄清事项

当前没有需要用户重复确认的产品方向。技术不确定性由T-00记录真实证据、owner与依赖任务；若需要改变目标、削减必需验收或扩大跨仓写入范围，先明确报告，受影响任务保持未完成。归档/merge只完成本app的Spec/计划/提交push与自有临时产物收尾，不更新AutoOS gitlink、manifest或.gitmodules；后续OS统一计划接收已单独验证的固定SHA。

归档移交项（owner=AutoOS 侧统一计划，本仓不可代行）：apps/auto-calendar gitlink 更新至本计划交付提交（当前 main tip，含 1d30fa9 代码线）；B类总表行刷新为已交付；子模块显式 detach 流程沿 001 先例。
