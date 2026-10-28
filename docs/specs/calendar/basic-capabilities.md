# calendar — 基本能力规范（CALENDAR-001 首版）

> 状态：随 CALENDAR-001 prepared，merge 复核后生效（本文为 canonical 目标草稿；
> 生效前不作为独立需求来源）。来源合同：`docs/plans/001-local-events.md` r2 及其
> 冻结证据 `docs/plans/evidence/001/capability-decision.md`。

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
  时钟。Init / Today / 月份导航 / 保存前后重查，跨午夜/跨年/闰年由真实数据驱动。
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

## 4. 存储、失败与恢复合同（SD-02）

- 数据根解析：`AUTO_CALENDAR_DATA` → `%APPDATA%/auto-calendar` → `XDG_DATA_HOME`
  → `~/.local/share/auto-calendar`（Windows 优先）。布局：
  `<root>/store/manifest.json`（提交点：rev/next_seq/events 索引）+
  `<root>/store/events/ev-<seq>.r<6位rev>.json`（不可变版本文件）。
- 提交序：先写新版本事件文件，再重写 manifest。无 rename/fsync 原语（工具链
  事实），不宣称掉电级原子性；崩溃窗口语义：
  - 版本文件写一半：未入 manifest ⇒ 视为不存在；
  - 版本文件已写、manifest 未更新：孤儿完整文件，**恢复时并入**
    （数据保全倾向：找回已保存事件优先于丢弃）；
  - manifest 损坏/丢失：扫描 events 目录按 id 取最高版本重建（零填充版本号
    保证文件序=数值序）。
- 删除移除该 id 的全部版本文件（恢复不可复活已删除事件）。
- 冲突模型：变更携带 `expected_rev`（调用方最近可见的全局 store revision）；
  不匹配 → `err_code:"conflict"`，前端不清空表单、重取后由用户重试，绝不静默覆盖。
- 结构化错误面（HTTP 始终 200 + 信封，或 422 反序列化错误由前端视为传输失败）：
  `invalid_title / invalid_notes / invalid_start / invalid_end / inverted_range /
  not_found / conflict / storage_unwritable / clock_unavailable / invalid_request /
  test_mode_disabled`。
- 规模边界（v1 承诺）：整仓快照式重写 + 线性扫描，数百事件内为设计规模；
  千级以上需修订（届时可评估 notes 已验证的 SQLite 仓储）。

## 5. 交互与双端合同（SD-02）

- 时钟/仓储不可用：显式错误态（横幅/提示），不渲染假数据，不回落固定日期。
- 保存失败：表单不关闭、用户输入逐字保留、错误码可见；成功才关闭并刷新。
- 删除为行内即时操作（v1 无二次确认）；受 expected_rev 保护。
- 双端一致性：同一后端合同、同一 store 源码；两端差异仅渲染层。双端验收以
  `tests/basic/verify_basic.py --profile vue|vm` 为准（端口 17820/17821，隔离
  数据目录，端口被占即失败不漂移）。

## 6. 验收入口

- 永久回放：`python tests/basic/verify_basic.py --profile vue` /
  `--profile vm`（V-01 可控时钟闰日/跨午夜、V-02 同日多事件+跨月+稳定 id+
  重开、V-03 非法日期/倒置拒绝+输入保留）。
- 运行：仓根 `auto run`（Vue）与 `auto run -r vm`（VM 窗口）；后端 17821；
  需要 auto CLI（版本见 evidence/001/capability-decision.md §1）。
