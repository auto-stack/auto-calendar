---
plan_id: CALENDAR-001
status: drafting
feature_name: local-events
author: [Codex]
created_at: 2026-10-29
updated_at: 2026-10-29
plan_revision: 2
current_step: 2
total_steps: 7
supersedes_spec_components: []
new_spec_components: [docs/specs/calendar/basic-capabilities.md]
touched_goals: []
---

# CALENDAR-001：真实日期与本地事件日历

## 0. 变更摘要

把固定日期的月历演示补为可保存事件的本地日历。

本轮只起草执行合同：没有实施功能、运行功能验收或将本app升为A类。auto-calendar 的基本能力补齐不依赖 auto-os-distro；Linux 支持另等 Nix＋COSMIC 基础完成，增强设计另会话。

## 1. 目标

显示真实今日，能创建、修改、删除本地事件，切月/选日后正确显示，退出重开事件仍在。

非目标：CalDAV、邀请、多用户、重复规则、跨设备同步、后台提醒、Linux 适配。

## 2. 架构方案

应用逻辑继续纯 `.at`，前端/后端沿 AutoUI 现有结构；本仓为主导仓。应用工作检出固定 `D:/autostack/auto-calendar`（独立开发clone），工作分支 `main`；执行/复审共用此检出，一个写入者。**复用该独立clone，不在组合子模块内并行开发，不建任何junction/symlink**。框架缺口在实际owner仓另立前置并按其worktree纪律执行，不在app手写Rust、修改生成Rust或绕过公开SDK。

事件含稳定 id、title、start、end、notes 与创建时的本地时区/偏移信息，单次事件为首版。采用可验证的日期/时间原语，start/end 必须有效且顺序明确；不通过固定 UTC 偏移伪装完整时区。AUTO_CALENDAR_DATA 覆盖用户数据根；版本化存储与失败恢复复用平台能力。时区歧义/无效日期明确拒绝并保留输入，不静默改时刻。

跨仓总表：[B类基本能力总跟踪表](https://github.com/auto-stack/auto-os/blob/main/docs/plans/b-apps-basic-capabilities.md)。源Spec以所属仓 `docs/specs/` 为准；当前没有该app的canonical模块规范，旧根 `SPEC.md`（如有）只是历史Demo观察/再生描述，不能据此宣布真实功能已完成。新规范路径将在实际复审/merge后落地，本轮不写入已实现Spec。

## 3. 技术栈

Auto / AutoUI、当前匹配的AutoLang/AutoUI/AutoMan工具组合、各app已有widget/store/API；具体存储与平台接缝由T-01用实际源码和探针确认。Vue / VM 两端均需真实任务验收，不因某一后端不通就删掉原任务；如必须显式指定 server=vm 等启动profile，应先验证并记录到执行入口/README，不能静默换成mock。

## 4. 需求分析与背景调查

授权：用户于2026-10-29要求建立总跟踪表、复用Notes/Reader/Blog现有计划，并为其余B类应用准备基本能力补齐计划。此处授权的是**计划准备和必要的文档/组合版本登记**，不宣称已授权/完成本计划具体功能实现，不推定全量竞品复刻或Linux开发已启动。

2026-10-29用户明确改用 `D:/autostack/<产品仓名>` 独立clone开发，先push应用再更新子模块pin；此修订仅更新工作位置、跨仓链接和交付状态描述，功能目标、T-01..07依赖、work验收与Spec增量不变，不重置任务。旧开发位置被此用户决定替代。

冻结的观察基线：`6f4d36d34476adc0656494fb45fca9b7c1b05860`（在本app `main` fetch origin后ff核对）；执行前重新核对HEAD/pin/WIP并记录变化。主产品统计为27个去重产品，B类9个；AutoJade旧名Jade Garden不重复计数。

calendar_store.at 的 Init/Today 固定 2026-06-17；calendar_util.at 已有闰年与月网格纯函数。当前无事件模型、后端、tests 或 docs/specs。

已读来源（源码/文档观察，不是本轮实测）：

- `src/front/app.at`：SHA256 `ed759e5aaf11825292f9ead8fcdd023b7960d3efe8d54d1fdd5355233784c5f4`。
- `src/front/calendar_store.at`：SHA256 `c3b3ded5d4f04e7cb7b019440992e2c87197b8959ce4e5c93d1f8ff6e702e200`。
- `src/front/calendar_util.at`：SHA256 `bd15f63a28533da344dcd128ddebfd797ca7a4f11ecaebad6cac5db0169cf33f`。
- `pac.at`：SHA256 `187b5005f3cde003dcffcfb476edd0a9b382e848463df71ad616e474799afa5d`。

## 5. 详细设计

### 执行入口和依赖

首个就绪任务仅T-01：在上述应用检出核对版本、清单、当前工具链、真实API与测试入口，用隔离数据跑能力探针。输出允许后续实现依赖的接口与不支持项；缺口需具名指向owner/前置计划及关闭条件。不得假造未存在API、跳过基础正确性，或以“将来Linux会解决”替代当前端的基本能力。

T-02..04按下列任务依赖顺序推进；T-05将本节拟议测试做成真实可复现入口，T-06/07保持未来阶段未勾选。合并后只有基础合同的全部必需工作/复审通过且父仓pin指向交付版本，才更新总表分类。发布包/所有Linux发行版不在本计划的成功声明里。

### 规范增量

| delta_id | action | docs/specs target | before/after rule | rationale | AC |
|---|---|---|---|---|---|
| SD-01 | add | `docs/specs/calendar/basic-capabilities.md`（新） | Demo/未定义 → 本计划首版用户任务、数据模型和准确支持范围 | 以真实基本能力作为产品准入 | AC-01/02 |
| SD-02 | add | 同上，失败/恢复及交互节 | 未定义 → 保存/输出/失败、重启和两端行为的可验合同 | 防止假成功、旧数据丢失和单端冒充 | AC-03/04 |

根README/历史SPEC在实现落地时反链canonical目标，保留历史来源、不覆盖未经审查的旧约定；本计划不在draft阶段修改canonical知识或ledger。

## 6. 测试设计

本轮没有执行下列功能测试。先以真实应用入口和真实文件/服务为准，既有脚本若只验证演示数据，需要补有辨别力的真实数据正反例；禁止仅把UI文案变绿或用相同生产函数生成期望值。

| case_id | AC/task与责任 | 输入/设置 | 实际入口 | 必须观察的结果 |
|---|---|---|---|---|
| V-01 | T-01..05 / AC-01..04；由T-05制作永久回放 | 2028-02-29、跨年和跨午夜的可控时钟 | 真实 Today 和月份导航入口 | 显示真实注入时间，不再回到 2026-06-17；网格与事件日期一致。 |
| V-02 | T-01..05 / AC-01..04；由T-05制作永久回放 | 同日多事件与跨月单次事件 | 表单→仓储→切月→重启 | 稳定 ID/起止/归属不变，无因排序/切月写回错事件。 |
| V-03 | T-01..05 / AC-01..04；由T-05制作永久回放 | 无效日期、倒置时间、DST 歧义和保存失败 | 真实事件提交入口 | 明确拒绝或要求消歧；未改变原事件，用户输入仍在。 |

测试隔离：所有文件/数据库/服务均使用临时用户数据目录及明确测试端口，不接触真实用户数据；占用端口/不可写/损坏时明确失败。多个实例/取消/退出与恢复按本计划声明范围验证。资源预算若需限制，T-01明确单位/语义/拒绝或截断结果并在dependent实现前冻结；没有提出上限不等于无限规模承诺，不以隐藏硬上限代替验收。

可复现入口（**均由T-05新增/接通**）：`python tests/basic/verify_basic.py --profile vue`、`python tests/basic/verify_basic.py --profile vm`。入口应实际调用应用后端与两端UI，记录源码/工具/依赖版本、fixture hash及运行结果；不得仅调内存helper替代。按可用工具复用现有Playwright或VM MCP/autoui-verifier驱动。T-01记录真实启动命令、数据env、端口与适用CLI参数；两端都要证实实际支持的用户任务。

角色：本轮仅起草，没有派执行/复审agent。实现与最终复审按四技能分阶段；无明确独立上下文时如实声明并从工件重建，不能自称独立或擅自创建新会话/agent。只改app不触auto-lang crates时禁止跑其cargo t/docs_gen；框架前置按owner自己的门档验证。

## 7. 验收标准

| ID | owner_stage | observable / verification |
|---|---|---|
| AC-01 | work | 真实日期：可控时钟下 Today 与本地日期一致，跨年/闰年/月份切换及跨午夜无固定日期残留。 |
| AC-02 | work | 事件闭环：新建、编辑、删除中文单次事件，稳定 ID 与所选日期/时间一致；跨月显示符合冻结合同，退出重开可恢复。 |
| AC-03 | work | 时间与失败：非法日期、起止倒置、时区歧义被明确拒绝；写失败/损坏/重启保留已保存事件与原件，不把提醒当作已实现。 |
| AC-04 | work | 双端任务：Vue/VM 各从空库完成选日→建事件→改时间→重启回读→删除，界面数据与实际仓储一致。 |
| AC-05 | review | 冻结已提交实现与依赖，逐个重验AC-01..04和独立反例；核对SD-01/02与范围、实际证据，输出明确review结论；未闭项不可忽略。 |
| AC-06 | merge | 通过对应最终门后交付main并推送，父仓gitlink和组合验证可追溯；canonical/ledger/归档收尾完成，组合子模块显式detached，独立开发clone留在main；总表有证据地标A，A类Linux仍等待发行版前置。 |

## 8. 执行步骤

- [x] T-01（owner_stage=work；依赖 无；AC-01..04）：基线与全路径探针：验证真实本地日期（跨午夜/月份/闰年）、日期/时区可用 API、持久化与两端输入；冻结单次事件的精确时间模型。若需后端，17821 为候选并先核 manifest 无冲突；缺能力先具名立前置，不用写死日期替代。 输出新文件 `docs/plans/evidence/001/capability-decision.md`，记录可用API、版本/资源边界、缺项owner和最小闭环。
  - [✅ 已完成] 探针全绿（2026-10-29）：双端 split mode（vue/vm ↔ rust axum:17821）跑通；后端真实墙钟经 shell.exec→PowerShell（时间+epoch+偏移分钟）；可控时钟 AUTO_CALENDAR_TEST_MODE/FAKE_NOW 注入双端可用；AUTO_CALENDAR_DATA 隔离目录 fs 回环通过；基线复核 6f4d36d→c1e5c56 仅计划文档、源 hash 与 §4 一致。缺项具名：内嵌 facade 无 time 模块、后端无 chrono/tz（owner auto-lang，见决策文件 §4）；时间模型冻结为「后端权威时钟 + 墙钟事件」（决策文件 §3）。证据：docs/plans/evidence/001/capability-decision.md（原始日志 attachments/001/*.log 本地留存）。
- [x] T-02（owner_stage=work；依赖 T-01；AC-01..04）：事件模型与存储：新增事件模块和仓储（拟议 src/back/events.at / repository.at / api.at）；新增隔离数据目录与版本化空库；持久保存真实单次事件。
  - [✅ 已完成] 交付 `src/back/{api,db,repository}.at`（模块调整：events.at+datecalc.at 合并入 repository.at——生成器对 db.rs 伴随模块借用修正硬编码 `repository` 名；证据=capability-decision §3.8）。HTTP 级验证全过（真实生成后端，隔离数据目录）：创建中文/跨年/闰日事件 ✓；拒绝 2029-02-29、25:00（invalid_start）、起止倒置（inverted_range）、空标题（invalid_title）✓；范围检索归属正确 ✓；expected_rev 冲突拒绝 ✓；更新保留创建时区/epoch ✓；删除连版本文件清除 ✓；硬杀重启后事件在（rev/ids 不变）✓；manifest 损坏→按文件重建（数据保全倾向）✓；可控时钟 date/time/offset 注入 ✓（rev 5 峰值，日志 attachments/001/run-t02-r*.log 本地）。
- [ ] T-03（owner_stage=work；依赖 T-02；AC-01..04）：日历与事件行为：沿 calendar_util.at 的月份算法接真实今日，完成日期范围检索、事件创建/改动/删除，跨月事件归属按时间模型显示。
- [ ] T-04（owner_stage=work；依赖 T-03；AC-01..04）：界面与真实日期：扩展 calendar_store.at / app.at 的事件列表与编辑表单；月导航保留，Today 使用实际本地日期；失败保留表单，不显示虚假保存。
- [ ] T-05（owner_stage=work；依赖 T-02..04；AC-01..04）：完成独立数据/失败回放和两端真实UI验收，新建 `tests/basic/verify_basic.py` 调度入口（可复用既有脚本），同时保存命令/输入hash/真实结果与原始失败；准备 canonical Spec 增量，提交实现，转 execution_done。
- [ ] T-06（owner_stage=review；依赖 T-05；AC-05）：在同一app检出暂停实现，按冻结提交、真实数据和独立反例最终复审；核对Spec增量与双端结果，说明上下文独立性限制；未满足返回修复，不将数据错误降为债务。
- [ ] T-07（owner_stage=merge；依赖 T-06；AC-06）：完成实际提交/推送/父仓gitlink验证，沉淀canonical Spec与derived ledger、归档；刷新总表A/B与证据，组合子模块显式detach，独立开发clone留在main。Linux仍等待发行版门，不因文档或脚本存在宣布已可用。

## 9. 复审记录

- 历史 r1起草回执见 `611d1e5e1933a519db8cf82824aab4427c5a4424`；其开发位置/收尾状态描述由本次修订替代，既有功能与验收合同保留。
- stage: new | plan_id: CALENDAR-001 | plan_revision: 2 | outcome: pass（独立clone路径修订就绪；功能未实施/未验收） | next: work/T-01（另行执行）。
- stage: goal | plan_id: CALENDAR-001 | plan_revision: 2 | round: 1 | from: drafting | to: work | status: drafting→executing | outcome: pass | worktree: D:/autostack/auto-calendar（独立clone，main，按计划§2覆盖默认worktree规约） | commit: （T-01提交见下） | next: work（授权链：用户 /goal 经 auto-plan-goal 一线授权 work→review→bounded repair→merge）。
- stage: work | plan_id: CALENDAR-001 | plan_revision: 2 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: c1e5c56 | code_commit: 见T-01提交 | dependency_revisions: auto CLI 0.1.0+v0.0.20-117-g873fa23（auto-man e6cc06f build）；auto-lang a748017da（只读依据） | task_ids: T-01 | evidence=docs/plans/evidence/001/capability-decision.md（探针：双端split mode、后端真实墙钟shell.exec/PowerShell、可控时钟注入、隔离目录fs回环全过；缺项time facade/chrono/tz具名归auto-lang） | blockers=无 | next_responsible_role=work（T-02）。
- stage: work | plan_id: CALENDAR-001 | plan_revision: 2 | outcome: pass | worktree_path: D:/autostack/auto-calendar | branch: main | base_commit: 1f457e3 | code_commit: 见T-02提交 | dependency_revisions: 同上 | task_ids: T-02 | evidence=src/back/{api,db,repository}.at + capability-decision §3.8/§3.10（HTTP级电池：创建/拒绝/范围/冲突/更新保留/删除清理/重启持久/损坏恢复/可控时钟全过，日志 attachments/001/run-t02-r*.log） | blockers=无（转译层约束已固化为写码规则，见决策文件 §3.10） | next_responsible_role=work（T-03）。
- 本次只改工作位置、跨仓链接与AC-06/T-07的检出收尾说明，不变更基础能力要求；独立clone开发，组合子模块只固定已交付版本。
- 本轮核对源码/Spec缺口、历史任务、路径、基线和计划唯一性；未执行实现/功能测试，所有7项任务保持未勾选；通过的是草案结构/相互引用检查，不是产品验收。

## 10. 待澄清事项

无必须先向用户确认的产品身份问题；技术可行性与资源边界由 T-01 冻结，缺口保持具名阻塞。
