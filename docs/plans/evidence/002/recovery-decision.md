# CALENDAR-002 T-00 恢复身份决策（recovery-decision）

日期：2026-11-01 · 执行：/auto-plan:work T-00 · 检出：`D:/autostack/auto-calendar`（独立开发 clone，`main`，base `3db7cdd`）
原始运行证据（local-only，不入库）：
`D:/autostack/plan-artifacts/plan-002/evidence/t00-repro-20261101-223021.json`（探针逐项结果+存储清单）、
`D:/autostack/plan-artifacts/plan-002/probe_t00_recovery.py`（探针脚本，复跑入口）、
`D:/autostack/plan-artifacts/plan-002/evidence/t00-app-run.log`（后端运行日志）。

## 0. 结论摘要

四个恢复窗口在真实后端全部复现（HTTP 级、隔离数据目录、故障仅注入隔离副本）：
F-5 ABA 陈旧凭据复效、已删最高 ID 重用、全删≡新空库混淆、删除中途崩溃后残留文件折叠复活。
当前 SDK（auto-lang master `367258e7a`，内嵌 facade）仍无 rename/fsync/原子写原语，
`fs.write_text` = truncate+write——001 的「无跨文件原子性」结论在当前工具链复核成立，
v2 不造事务，改用**持久化单调高水位 + 删除墓碑 + 证据不足拒写**的文件协议（§4）。
设计冻结后 T-02 方可实施。

## 1. 环境与工具身份

| 项 | 值 |
|---|---|
| auto CLI | `0.1.0+plan-890-verified-r7-t19-5-g55c98c7`，`D:/autostack/auto-man/target/debug/auto.exe`，sha256 `390e664ead5fc7559085693f0b2256566eb06b9f6369ac295e4953850c7d2e90` |
| auto-lang 源（facade 依据，只读） | master `367258e7a`（001 时为 `a748017da`，已大幅前进） |
| 本仓基线 | `3db7cdd`（工作树 clean，无 WIP 代码） |
| 后端就绪 | 56.6s（温增量构建；001 冷构建 >120s 的超时风险由探针 900s 窗口覆盖） |
| 端口 | front 17820 / back 17821，启动前核验空闲；探针结束自有进程收割干净、无孤儿、旁观者零接触 |

## 2. 当前 SDK 持久化原语事实（auto-lang-core/src/a2r_std.rs 内嵌 facade，master 367258e7a）

| 原语 | 现状 | 对本计划的意义 |
|---|---|---|
| `fs.write_text/write` | `std::fs::write`（截断+写，**非原子**，无 fsync） | 提交点文件可能写一半；损坏必须可检测且走向拒写（fail-closed），不能走向回退 |
| `fs.rename` / 原子替换 | **仍无**（001 结论复核成立；新增的是 copy/walk/bytes 系） | 不造事务、不做 rename 换轮；维持「先数据文件后提交点」写序 |
| `fs.read_text / exists / delete / mkdir_all / dir_names` | 可用（`dir_names` 排序、跳过点文件）——本探针 S1..S5 经真实后端全路径行使 | 扫描/恢复/删除协议照旧可行 |
| `fs.copy_recursive` | 新增可用（**未在本探针行使**） | T-02 迁移备份不依赖它：单文件备份用已验证的 read_text+write_text，零新原语风险 |
| json 面 | `parse/get/as_int/as_string/get_at/len/encode` 可用（repository.at 既有模式） | identity.json 读写沿用同款；无新面 |

## 3. 反例实证（红基线；全部「期望=观察」）

| # | 场景 | 构造 | 观察到的红 | 关闭归属 |
|---|---|---|---|---|
| S1a | F-5 恢复回退 | rev=4 后 B 对 ev-5 推到 rev=7 再删 ev-5；manifest 损坏 | 恢复后 rev=4 == 陈旧凭据 | AC-02 |
| S1b | ABA 接纳 | 同上，A 持 expected_rev=4 提交 update | `ok=true`，落 rev=5（历史已烧掉的序号），陈旧内容真实落盘 | AC-02 |
| S2 | 已删 ID 重用 | 删 ev-5 → 丢 manifest → 恢复 | next_seq 回退到 5，新事件再发 `ev-5` | AC-03 |
| S3a | 全删≡新空库 | 全删后丢 manifest vs 从未用过的目录 | 两者 status 完全相同（rev=0/count=0），历史不可辨 | AC-03 |
| S3b | 全量 ID 重发 | 同上后 create | `ev-1` 重新发出（已确认删除的 id） | AC-03 |
| S4a | 删除中途崩溃→折叠复活 | 删 ev-2 只删了 r2（模拟中断），残留 r3，丢 manifest | 折叠把 ev-2 按 r3 复活进 manifest | AC-03 |
| S4b | 控制组：锁文件删除 | 打开 r 文件句柄后 delete | `storage_unwritable` + manifest 不动（**v1 不假成功合同成立，保留**） | 保留 |
| S5 | 控制组：孤儿折叠 | ev-2.r2 在盘、manifest 不可用 | 恢复 rev=2、ev-1+ev-2 都在（**v1 数据保全倾向成立，保留**） | 保留 |

另有第一轮探针（`t00-repro-20261101-222847.json`）佐证 S1 需要把高 rev 集中到被删 id 上
（create 各自携带 rev 文件，必须用 update 推高同一 id 再删）——构造记录在案供 C-01 复用。

## 4. 冻结设计：v2 存储协议（单调高水位 + 墓碑 + 拒写）

**最低不变式（不可妥协）**：旧条件凭据（expected_rev）在恢复后不得意外再次有效；
已确认删除的事件在任何恢复路径不得复活；后续新事件不得复用已确认分配过的 id。

### 4.1 新文件 `<root>/store/identity.json`（schema_version 2）

```json
{"schema_version":2,"generation":"g-<epoch_ms>-<rev>-<seq>","rev_high":N,"seq_high":M,"tombstones":["ev-5"]}
```

- `rev_high`：曾持久化确认的最大全局 rev，**单调不减**，是条件写凭据的唯一权威。
- `seq_high`：曾分配的最大事件 seq，单调不减，是分配器高水位（id 不重用的权威）。
- `tombstones`：已持久化「删除意图」的 id 列表；折叠恢复必须排除墓碑 id 的残留文件。
- `generation`：诊断用 store 身份串（创建时刻派生；不参与合同判定）。
- 大小 O(墓碑数)，数百事件规模内为 KB 级小文件。

### 4.2 提交序（无原子原语下的故障安全排序）

create/update：① 写事件版本文件 → ② 写 identity.json（凭据提交点）→ ③ 重写 manifest.json（可见提交点）。
delete：① 写 identity.json 加墓碑（删除意图提交点）→ ② 尽力删该 id 全部版本文件（任一失败→`storage_unwritable`，manifest 不动）→ ③ 重写 manifest（去条目、rev+1）。

各中断点的恢复语义（保证不回退）：

| 中断点 | 盘面 | 恢复行为 |
|---|---|---|
| ①后（create/update） | 孤儿文件，水位旧 | 折叠并入（v1 保全倾向保留），水位抬到折叠 rev → 旧凭据保持死 |
| ②后（create/update） | 水位新、manifest 旧 | manifest 重建取 max(水位， 扫描)；孤儿文件坏也不回退 rev |
| ①后（delete） | 墓碑已记，文件/manifest 旧 | 读仍见事件（删除未可见）；丢 manifest 时墓碑排除该 id，不复活 |
| ②后（delete） | 墓碑+部分/全删文件，manifest 旧 | 同上；残留文件永不复活 |
| identity 写一半损坏 | identity 不可解析 | **走拒写（case D），不回退、不静默重造** |

### 4.3 manifest_ensure 恢复分案

- **A：identity 有效 + manifest 有效** — 水位=两者 max；墓碑合并并修剪（无文件且不在条目才可剪）；
  manifest 需要抬升/去墓碑时就地修复重写。读写在水位内正常。
- **B：identity 有效 + manifest 丢/坏** — 扫描重建（排除墓碑 id 文件），rev=max(水位， 扫描非墓碑 max)，
  next_seq=max(水位 seq, 扫描 max)+1，写 manifest。
- **C：identity 丢/坏 + manifest 有效** — 视为 **v1 存储迁移**：read_text+write_text 备份原 manifest 至
  `store/identity-v1-migration.json`（覆盖式单文件），派生水位=max(man.rev, 扫描)（扫描含 v1 孤儿），
  墓碑=[], 写 identity.json → 转 A。每存储至多发生一次。
- **D：identity 丢/坏 + manifest 丢/坏 + store 目录存在任何痕迹** — **证据不足，拒写保全**：
  读路径内存态尽力扫描（不落盘、不写 manifest/identity），所有变更返回新 err_code
  `recovery_unproven`，原文件一字不动。全新初始化仅当 store 目录完全不存在（或全空）时走
  fresh（新 identity rev_high=0/seq_high=0）。**「历史数据缺证据」与「新空库」就此严格区分。**

### 4.4 受控恢复路径（case D 的唯一出口）

环境变量 `AUTO_CALENDAR_RECOVERY_CONSENT=accept-scan`（显式、非常规命名；操作者启动时设置）：
ensure 检测到 unproven 且同意标志在场 → ① 写 `store/recovery-report.json`（扫描清单、采纳水位、
generation、时间戳、原 identity 残片原文）→ ② 派生 identity（rev_high=seq_high=扫描 max，墓碑=[]）→
③ 重建 manifest → 恢复正常。未设标志时永不自动执行。
**披露残余 R-1（诚实边界）**：同意恢复的水位只能取自幸存证据；若身份丢失前存在「凭据恰等于幸存
max rev」的陈旧写者，ABA 窗口在该残余内重新打开——这是证据物理丢失后的不可证边界，
v2 的 identity.json 正是为把该风险压缩到「操作者主动同意的灾难恢复」一级；v1 是每次 manifest
丢失都裸奔。恢复报告必须向操作者陈述该残余。v1 时代已发生的全删+丢 manifest（升级前）不可追溯，
不宣称修复（迁移边界，AC-04 如实表述）。

### 4.5 API 与前端契约（增量，双轨同步消费）

- `StoreStatus` 增 `recovery_state: str`（"ok"|"unproven"）与 `generation: str`（诊断）；
- `EventResult.err_code` 新值 `"recovery_unproven"`（refuse 路径，rev 回显当前只读视图 rev 或 0）；
- 前端 Init 增一次 `GET /api/v1/status`，`recovery_state=unproven` → 显式横幅+禁写提示（不渲染假数据）；
  变更失败 err_code=`recovery_unproven` → 表单不关闭、输入逐字保留（沿 AC-03 语义）、错误码可见。
- 旧客户端（v1 构建）收到未知 err_code 走通用错误分支——不会静默成功；「旧客户端拒绝/刷新」即此。
- manifest.json 结构与 schema_version 保持 1 不变（提交点格式零改动；id/rev 语义由 identity 权威化）。

### 4.6 冲突模型不变

`expected_rev` 仍是唯一条件凭据；v2 只保证它引用的 rev 不再被恢复重发（S1 窗口关闭）。
create 仍无条件凭据（v1 语义），但 id 分配走 seq_high+1，不再重发已确认 id。

## 5. 规模与资源边界

- 数百事件设计规模不变（v1 §4 承诺）；恢复扫描 O(文件数)，identity O(墓碑数)，均线性小文件。
- 每次变更新增两次小文件写（identity + 原有 manifest），无引入数据库、无后台线程、无网络面。
- 故障注入仅限隔离副本（临时数据目录）；不触碰共享 target、不停他人实例（探针已示范）。

## 6. 不做（非目标重申）

掉电级 fsync/原子性承诺、rename 事务、CalDAV/重复/提醒/DST 时刻语义、多写者、SQLite 迁移、
跨版本降级读（v2 存储被 v1 代码打开的行为不在合同内，spec 注记）。

## 7. 测试映射（§6 用例 ← 本决策）

| Case | 依赖本决策的锚点 |
|---|---|
| C-01 | §4.2/§4.3A：S1 构造移植为永久断言——陈旧凭据必须 conflict、新读取者取新水位后可写 |
| C-02 | §4.3B：删最高 id/全删+丢 manifest → next_seq/rev 由水位兜底；真实新空根走 fresh 对照 |
| C-03 | §4.3D+§4.4：双凭据丢失 → `recovery_unproven` 拒写+原件 hash 不变；consent 后下一次写成功；S4b/S5 控制组保留 |
| C-04 | §4.3C：手造 v1 store（合法 manifest+事件文件、无 identity）→ 迁移备份+核对；中文跨月 UI CRUD 与强杀重开为 001 既有门回放 |
| C-05 | §1/§4：双端独立准备；强制旧 max 策略（删 identity+坏 manifest）必须表现为拒写——C-01/02 断言在新策略下转绿、旧策略下转红（总门非零） |
