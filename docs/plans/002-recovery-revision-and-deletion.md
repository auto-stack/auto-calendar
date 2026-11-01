---
plan_id: CALENDAR-002
status: drafting
feature_name: "恢复后版本凭据与删除保全"
author: [Codex]
created_at: 2026-11-01
updated_at: 2026-11-01
plan_revision: 1
current_step: 0
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

- [ ] T-00（owner_stage=work；依赖001；AC-01..03）：复现恢复反例，冻结版本/删除/ID/迁移/提交故障设计和实际SDK能力，输出决策稿。
- [ ] T-01（owner_stage=work；依赖T-00；AC-01）：复用旧门收窄自有进程/端口清理并固定独立准备/工具身份。
- [ ] T-02（owner_stage=work；依赖T-00及确需最小前置；AC-02/03）：实现最小恢复身份/删除/分配器保护及旧v1受控迁移，先后回放C-01..03。
- [ ] T-03（owner_stage=work；依赖T-01/02；AC-04）：前端消费恢复/冲突契约，真实UI跑跨月/失败保稿/退出重开后下一次写入。
- [ ] T-04（owner_stage=work；依赖T-03；AC-04）：使补充入口可执行，跑C-01..05、旧墙钟/事件门及真实故障反控，准备SD候选。
- [ ] T-05（owner_stage=work；依赖T-04；AC-01..04）：核对漂移/覆盖和README/roadmap，提交execution_done。
- [ ] T-06（owner_stage=review；依赖T-05；AC-05）：同clone独立上下文最终复审。
- [ ] T-07（owner_stage=merge；依赖T-06 pass；AC-06）：仅app规范/归档/提交push收尾。

## 9. 复审记录

- stage: new | plan_id: CALENDAR-002 | plan_revision: 1 | outcome: pass（有界T-00准备就绪；本轮没有实现或产品验收） | next: work/T-00（等待后续实施指令）。
- 已归档001、现实现Spec和产品源码保持不变；规划结构/链接通过不等于功能通过。review以同一clone的独立上下文核验，不自动创建agent/chat或指定模型。

## 10. 待澄清事项

当前没有需要用户重复确认的产品方向。技术不确定性由T-00记录真实证据、owner与依赖任务；若需要改变目标、削减必需验收或扩大跨仓写入范围，先明确报告，受影响任务保持未完成。归档/merge只完成本app的Spec/计划/提交push与自有临时产物收尾，不更新AutoOS gitlink、manifest或.gitmodules；后续OS统一计划接收已单独验证的固定SHA。
