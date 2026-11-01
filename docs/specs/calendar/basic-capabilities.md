# calendar — 基本能力规范（CALENDAR-001 首版；§4 由 CALENDAR-002 修订）

> 状态：CALENDAR-001 首版已生效；**§4 存储恢复合同由 CALENDAR-002 修订为 v2
> （本文即 r2 候选稿，随 002 merge 复核生效）**。来源合同：
> `docs/plans/archived/001-local-events.md` r2、`docs/plans/002-recovery-revision-and-deletion.md` r1
> 及其冻结证据 `docs/plans/evidence/001/capability-decision.md`、
> `docs/plans/evidence/002/recovery-decision.md`；恢复身份细则见
> `docs/specs/calendar/recovery-identity.md`（SD-02）。

## 1. 首版用户任务（SD-01）

单用户本地日历，双端（Vue web 轨 / VM 原生窗口轨）行为一致：

- 显示真实本地日期（"Today"），月网格高亮今日；月份前后导航与回今日。
- 创建、修改、删除**单次**中文事件（标题/开始/结束/备注）。
- 按日显示事件列表；跨日/跨月事件按其 [start.date, end.date] 区间归属显示。
- 退出重开后事件仍在。

非目标（v1 明确不做，不作为已实现宣称）：CalDAV、邀请、多用户、重复规则、
跨设备同步、后台提醒、Linux 发行版适配（等发行版基础）、时刻（instant）级
时区换算与 DST 歧义消解（见 §3 准确性边界）。

## 2. 数据模型与时间模型（SD-01）

- 事件：`{ id, title, start, end, notes, created_offset_min, created_epoch_ms }`，
  外加后端计算面 `start_ymd / end_ymd`（y*10000+m*100+d，供前端整数归属计算）。
  `id = "ev-<seq>"`，seq 为存储单调计数，稳定且不随修改变化。
- `start/end` 为墙钟字符串 `"YYYY-MM-DD HH:mm"`（本地钟面时间），固定格式定宽；
  约束：日期真实（闰年/月日有效）、`HH:mm` 合法、`end > start`（零时长同样拒绝）。
- **墙钟语义**：事件存储并显示钟面时间，不声明时刻，不做时区换算，不静默改写
  用户输入的钟面值。创建时记录创建设备当时的 UTC 偏移分钟与 epoch 毫秒作为
  创建事实（`created_offset_min / created_epoch_ms`），修改保留不重写。该偏移
  是**信息记录**，不构成完整时区声明（不通过固定偏移伪装时区）。
- **时钟权威**：`GET /api/v1/now` 由后端宿主钟提供
  `{date, time, year, month, day, epoch_ms, offset_min, source}`；前端不取本地
  时钟。今日值只在 Init 与 Today 动作时从 /now 获取（月份导航在前端做纯月历
  推算，不重查）；跨午夜/跨年/闰年由真实数据驱动——今日标记与选择随最近一次
  now 查询走，重开应用必回真实钟。
- 创建事实（`created_offset_min / created_epoch_ms`）由后端在创建那一刻取
  宿主钟生成；宿主钟不可用时事件仍可创建，两字段落零值/空串——它们是信息
  记录，不参与任何合同判定（F-7 说明）。
- 可控时钟（测试合同）：`AUTO_CALENDAR_TEST_MODE=1` 时以
  `AUTO_CALENDAR_FAKE_DATE` / `AUTO_CALENDAR_FAKE_TIME` /
  `AUTO_CALENDAR_FAKE_OFFSET_MIN`（缺省 0=UTC）注入，双端同源；生产环境不设置。

## 3. 准确性边界与具名缺口（SD-01）

- DST 时刻歧义：墙钟存储下不存在歧义时刻解释问题（存什么显什么）；"该钟面
  时间在本地时区是否存在/唯一" 的时刻级校验需要 tz 数据库，当前后端工具链不可达
  （auto-lang 内嵌 a2r_std facade 缺 `time` 模块；生成 workspace 无 chrono/chrono-tz
  注入面）。缺口 owner：auto-lang；关闭后内部换实现、本合同不变，届时可升级为
  时刻级拒绝。
- 后端时钟实现当前走 `shell.exec` → PowerShell（Windows）；Linux 等发行版基础
  完成后按其门档另验。

## 4. 存储、失败与恢复合同（SD-02 → CALENDAR-002 修订为 v2；细则见 recovery-identity.md）

- 数据根解析：`AUTO_CALENDAR_DATA` → `%APPDATA%/auto-calendar` → `XDG_DATA_HOME`
  → `~/.local/share/auto-calendar`（Windows 优先）。布局：
  `<root>/store/manifest.json`（提交点：rev/next_seq/events 索引）+
  `<root>/store/identity.json`（凭据权威：rev_high/seq_high 单调水位、删除墓碑、
  generation）+ `<root>/store/events/ev-<seq>.r<6位rev>.json`（不可变版本文件）。
- 提交序（无 rename/fsync 原语，不宣称掉电级原子性）：
  - create/update：① 写新版本事件文件 → ② 重写 identity（凭据提交点）→
    ③ 重写 manifest（可见提交点）；
  - delete：① identity 加墓碑（删除意图提交点）→ ② 删该 id 全部版本文件 →
    ③ 重写 manifest（去条目、rev+1）。
  崩溃窗口语义：①后孤儿版本文件由恢复折叠并入（数据保全倾向不变）；②后水位
  领先 manifest，恢复按 max 修复，永不回退。
- 删除以墓碑为事实：任何恢复路径不得复活墓碑 id（含删除中断后残留文件的
  折叠排除）；删除失败必须显式报 `storage_unwritable`，不假成功。
- 恢复身份（F-5 窗口关闭）：全局 rev / 分配 seq 以 identity 水位为下界，
  **旧条件凭据（expected_rev）在恢复后不得再次有效**；已分配 id 永不重发；
  「全部删除的历史库」与「从未使用的新空库」可区分（水位 ≠ 0 vs 0）。
- 凭据丢失的拒写保全：identity 与 manifest 同时缺失/损坏且 store 目录有痕迹时，
  存储进入 `recovery_unproven` 只读保全态——原文件一字不动、变更全部拒绝、
  读取降级为尽力扫描；唯一出口是操作者显式
  `AUTO_CALENDAR_RECOVERY_CONSENT=accept-scan` 受控恢复（先写恢复报告再重锚）。
  严禁凭幸存 max 或 fresh 静默重造身份。
- v1 迁移：合法 manifest 而无 identity 的旧存储首次打开时受控迁移——先备份原
  manifest 至 `store/identity-v1-migration.json`，再派生水位（max(manifest, 扫描)）。
  边界（诚实声明）：v1 时代盘上不存在删除事实，迁移前发生的删除中断残留不在
  修复范围；v1 时代已发生的全删+manifest 丢失不可追溯。
- 冲突模型：变更携带 `expected_rev`（全局 store revision，现由水位背书）；
  不匹配 → `err_code:"conflict"`，前端不清空表单、重取后由用户重试，绝不静默覆盖。
  新错误码 `recovery_unproven`（证据不足拒写；旧客户端视作普通错误，不会静默成功）。
- 结构化错误面（HTTP 始终 200 + 信封，或 422 反序列化错误由前端视为传输失败）：
  `invalid_title / invalid_notes / invalid_start / invalid_end / inverted_range /
  not_found / conflict / storage_unwritable / clock_unavailable / invalid_request /
  test_mode_disabled / recovery_unproven`。
- 规模边界（v2 维持 v1 承诺）：整仓快照式重写 + 线性扫描 + 每变更一至两次小文件
  identity 写（delete 为墓碑与水位两笔），数百事件内为设计规模；千级以上需修订
  （届时可评估 notes 已验证的 SQLite 仓储）。

## 5. 交互与双端合同（SD-02）

- 时钟/仓储不可用：显式错误态（横幅/提示），不渲染假数据，不回落固定日期。
- 存储身份未能证明（recovery_unproven）：显式保全横幅 + 变更拒绝提示（含受控
  恢复指引），已保存事件照常展示，保存失败时表单不关闭、输入逐字保留。
- 保存失败：表单不关闭、用户输入逐字保留、错误码可见；成功才关闭并刷新。
- 删除为行内即时操作（v1 无二次确认）；受 expected_rev 保护。
- 双端一致性：同一后端合同、同一 store 源码；两端差异仅渲染层。双端验收以
  `tests/basic/verify_basic.py --profile vue|vm` 与
  `tests/basic/verify_recovery_identity.py --profile vue|vm` 为准（端口
  17820/17821，隔离数据目录，端口被占即失败不漂移，旁观进程永不清理）。

## 6. 验收入口

- 永久回放（001 基本能力）：`python tests/basic/verify_basic.py --profile vue` /
  `--profile vm`（V-01 可控时钟闰日/跨午夜、V-02 同日多事件+跨月+稳定 id+
  重开、V-03 非法日期/倒置拒绝+输入保留）。
- 永久回放（002 恢复身份）：`python tests/basic/verify_recovery_identity.py
  --profile vue` / `--profile vm`（C-01 陈旧凭据拒绝、C-02 id 不重用/全删可辨、
  C-03 拒写保全+迁移+受控恢复、C-04 中文跨月 CRUD/强杀重开、旧策略反控）。
- 运行：仓根 `auto run`（Vue）与 `auto run -r vm`（VM 窗口）；后端 17821；
  需要 auto CLI（版本见 evidence/001/capability-decision.md §1、
  evidence/002/recovery-decision.md §1）。
- 独立准备门：`python tests/free_ports.py --check`（只查不杀；占用即中止，
  本运行只收割自有的进程——`tests/free_ports.py` 模块的 Ownership 纪律）。
