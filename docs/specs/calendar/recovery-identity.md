# calendar — 恢复身份与删除保全规范（CALENDAR-002，SD-02）

> 状态：随 CALENDAR-002 prepared，merge 复核后生效。来源合同：
> `docs/plans/002-recovery-revision-and-deletion.md` r1 及其冻结证据
> `docs/plans/evidence/002/recovery-decision.md`（红基线 7 红复现 + v2 协议冻结）。
> 本文与 `basic-capabilities.md` §4（r2 修订）共同构成存储恢复合同；
> 冲突时以本文（更具体的恢复身份面）为准。

## 1. 目的与不变式

关闭 CALENDAR-001 F-5 登记的恢复窗口：manifest 丢失后全局 rev/序号仅取幸存
事件最大值，使陈旧条件凭据复效（ABA）、已删最高 id 重发、全删库与新空库混淆、
删除中断残留文件折叠复活。

不变式（不可妥协）：

1. **旧条件凭据不得在恢复后意外再次有效**——`expected_rev` 引用的全局 rev
   由单调水位背书，恢复只升不降。
2. **已确认删除的事件在任何恢复路径不得复活**——墓碑优先于残留文件。
3. **已分配的 id 永不重发**——分配器高水位单调。
4. **历史数据缺证据与新空库严格区分**——前者拒写保全，后者正常初始化。

## 2. 存储布局与文件角色

```
<root>/store/
  manifest.json        可见提交点（schema 1 结构不变）：rev/next_seq/events 索引
  identity.json        凭据权威（schema 2）：
                       {"schema_version":2,"generation":G,"rev_high":N,
                        "seq_high":M,"tombstones":["ev-5",...]}
  events/ev-<seq>.r<6位rev>.json   不可变版本文件
  identity-v1-migration.json       v1 迁移一次性备份（原 manifest 字节）
  recovery-report.json             受控恢复报告（consent 时先写后重锚）
```

- `rev_high`：曾持久化确认的最大全局 rev，单调不减。
- `seq_high`：曾分配的最大事件 seq，单调不减。
- `tombstones`：已持久化删除意图的 id；折叠/重建必须排除；仅当该 id 既无
  版本文件也不在 manifest 条目时才可修剪。
- `generation`：诊断用身份串（按因常量 `g-new`/`g-v1`/`g-recovered`，**不保证
  每 store 唯一**，非合同字段）；不参与合同判定。
- 内嵌 facade 无 rename/fsync/原子写（auto-lang master 367258e7a 复核）；
  所有提交点为截断重写的小文件，损坏可检测（json_ok + 字段校验）。

## 3. 提交序与中断点语义

| 操作 | 顺序 | 中断点语义 |
|---|---|---|
| create/update | ① 版本文件 → ② identity 水位（凭据提交点）→ ③ manifest（可见提交点） | ①后：孤儿文件待折叠——manifest 丢/坏的扫描重建（case B）折叠并入（v1 保全倾向）；identity+manifest 一致的快路径**推迟折叠**（不扫描、孤儿不可见，v1 同源语义），直至下次慢路径或 manifest 丢失才并入，内容可能晚到复活（披露）；②后：水位领先 manifest，恢复按 max 修复（孤儿并入；文件损坏则 rev 空烧、无假数据） |
| delete | ① identity 加墓碑（意图提交点）→ ② 删该 id 全部版本文件 → ③ manifest 去条目 rev+1 | ①后：删除不可见、可重试，墓碑已挡复活（此窗口内该 id 的变更/删除仍被接受，最终随条目一起消亡——设计如此）；②失败：`storage_unwritable`、manifest 不动、墓碑保留（不假成功）；②后读按 manifest 呈现，缺失文件计 corrupt_count；③后：水位由 max 规则补齐 |

**晚到孤儿披露（v1 同源）**：崩溃于①的孤儿版本文件在快路径下不参与恢复扫描；
若其 rev 后被新提交复用，随后 manifest 丢失重建时按「每 id 最高 rev 胜」规则
可能以孤儿内容呈现该 id——单调水位/墓碑/id 不重用三个不变式均不受影响；该
行为与 v1 一致，属数据保全倾向的边界而非 v2 回归。

## 4. 恢复分案（store_recover）

| 案 | 盘面 | 行为 |
|---|---|---|
| A | identity + manifest 均有效 | 快路径（水位一致且无墓碑→免扫描）；否则 max(三源) 修复 + 折叠孤儿 + 修剪墓碑 |
| B | identity 有效，manifest 丢/坏 | 墓碑感知扫描重建，rev=max(水位， 扫描)，seq 同 |
| C | manifest 有效，identity 丢/坏 | v1 受控迁移：先备份原 manifest 字节，派生水位 max(manifest, 扫描)，墓碑=[]，generation=`g-v1`；备份为覆盖式单文件——identity 再次丢失而 manifest 幸存时 case C 可再次发生，备份随之覆盖为当次原 manifest 字节 |
| D | 双双丢/坏且 store 有任何痕迹 | **`recovery_unproven` 拒写保全**：读为内存尽力扫描（不落盘），变更全拒，原文件一字不动 |
| fresh | store 目录不存在（或全空） | 正常初始化（`g-new`，水位 0） |

## 5. 受控恢复（case D 唯一出口）

操作者以 `AUTO_CALENDAR_RECOVERY_CONSENT=accept-scan` 启动：先写
`recovery-report.json`（扫描清单、采纳水位、原 identity/manifest 残片、
deletion_facts=unknown、残余声明），再重锚 identity（`g-recovered`，水位=扫描
max，墓碑=[]）并重建 manifest。未设标志永不自动执行。

**残余 R-1（披露）**：同意恢复的水位只能取自幸存证据；若身份丢失前存在凭据恰
等于幸存 max rev 的陈旧写者，该写者会通过校验——这是证据物理丢失后的不可证
边界，必须由恢复报告向操作者陈述。identity.json 的存在正是把该风险从「每次
manifest 丢失都裸奔（v1）」压缩到「操作者主动同意的灾难恢复」一级。

## 6. v1 迁移边界（披露）

- v1 盘上不存在删除事实：迁移前发生的删除中断残留（同 id 孤儿版本文件）会按
  v1 折叠规则并入——不可追溯，不宣称修复。
- v1 时代已发生的全删 + manifest 丢失不可追溯（无凭据可派生）。
- 迁移本身失败（备份/写 identity 任一步）= `storage_unwritable`，原状保留。

## 7. API 与双端消费

- `StoreStatus` / `EventsList` 增 `recovery_state`（"ok"|"unproven"|""）与
  `generation`；变更失败新增 err_code `recovery_unproven`（rev 回显 0）。
- 前端：unproven 时显式保全横幅（含 consent 指引）+ 表单拒写文案；保存失败
  表单不关闭、输入逐字保留；事件照常展示（内存扫描视图），不渲染假数据。
- 旧客户端：未知 err_code 走通用错误分支——不会静默成功（拒绝/刷新流程即此）。

## 8. 独立运行门（C-05）

- 准备：`python tests/free_ports.py --check` 只查不杀；端口被占即中止、不漂移。
- 收割：仅本运行正识别的进程（image 在仓内或 cmdline 引用仓路径且晚于运行
  起点）可杀；旁观监听者只报告、永不终止（v1 的按端口/命令行广域清理已退役）。
- 工具身份：CLI/exe 版本 + 全量 sha256 + 发现路径入证据 JSON。
- 强制旧 max 策略反例：C-01/C-02 断言在 v2 下转绿；回退旧策略即转红（总门
  非零）——verify_recovery_identity 的 HTTP 反控即永久反例。

## 9. 验收入口

- `python tests/basic/verify_recovery_identity.py --profile vue|vm`（C-01..04
  UI+HTTP 合成门、旧策略反控、consent 重启流程）。
- `python tests/basic/verify_basic.py --profile vue|vm`（001 基本能力不回归）。
- 探针存档：`plan-artifacts/plan-002/probe_t00_recovery.py`（红基线复现）、
  `probe_t02_replay.py`（30/30 协议电池，含冷重启/迁移/consent 注入）、
  `probe_t01_ownproc.py`（旁观者三路径）。

## 10. 规模与非目标

规模：数百事件（线性扫描 + KB 级 identity），每变更多一次小文件写。
非目标：掉电级 fsync/原子性承诺、rename 事务、CalDAV/重复/提醒/DST 时刻语义、
多写者、SQLite 迁移、v2 存储被 v1 代码打开的降级读行为。

## 当前 SDK 兼容确认（2026-11-07）

辅助文件写入确认不依赖 `fs.write_text` 返回值真假；目录拒绝，普通文件存在且全文读回一致才返回true；目标为空时另须实际文件字节长度为0，避免文本读取失败默认空串造成误判。已存在相同内容允许幂等确认。目录拒绝；删除成功须确认目标不存在，失败原文件保留，原身份水位/墓碑先写与删除协议不变。

来源：[本次交付计划](../../plans/archived/003-current-sdk-file-write-confirmation.md)；沿独立复审冻结的规范增量落地。
