# CALENDAR-001 T-01 能力决策（capability-decision）

日期：2026-10-29 · 执行：/auto-plan:work T-01 · 检出：`D:/autostack/auto-calendar`（独立开发 clone，`main`）
原始运行日志（local-only，不入库）：`docs/plans/attachments/001/run-vue-t01-r{1..5}.log`、`run-vue-t01-fake.log`、`run-vm-t01.log`

## 0. 结论摘要

真实工具链双端 split mode 全部跑通：Vue↔rust、VM↔rust 共用同一 axum 后端（17821）。
后端**真实墙钟已打通**（shell.exec → PowerShell，含偏移分钟）；隔离数据目录 fs 回环全过；
可控时钟注入（test mode）双端可用。stdlib `time` facade 缺失、后端无 chrono/tz 库为具名跨仓缺口，
v1 以「后端权威时钟 + 墙钟事件模型」冻结，不受缺口阻塞。

## 1. 环境与基线核对

| 项 | 值 |
|---|---|
| auto CLI | `0.1.0+v0.0.20-117-g873fa23`，`D:/autostack/auto-man/target/debug/auto.exe`（auto-man master `e6cc06f`，本机无全局安装/不在 PATH） |
| auto-lang 源（stdlib/facade 依据） | master `a748017da`（仅读，未触碰；其工作区有他人 docs WIP，与本计划无关） |
| 本仓基线 | 冻结基线 `6f4d36d` → HEAD `c1e5c56` 仅计划文档变化（`git diff --stat` 零代码文件） |
| 源 hash 复核 | app.at `ed759e5a…`、calendar_store.at `c3b3ded5…`、calendar_util.at `bd15f63a…` 与计划 §4 冻结值一致 |
| 端口 | front 17820 / back 17821（候选，探针时 netstat 空闲；兄弟 app 占 17818/17819，无冲突） |

## 2. 探针结果

### 2.1 可用（运行验证，r5 全绿）

| 面 | 证据 |
|---|---|
| split mode 双端 | vue：`auto run`（back 17821 + vite 17820）；vm：`auto run -r vm`（同一 rust 后端，日志 "Running VM interpreter UI (backend: rust, split over HTTP)"） |
| `#[api]` 端点生成 | api.at → axum api.rs + types.rs（GET→Query 结构、POST→Json body）；生成 TS client 每 endpoint 一个 async fn |
| **真实墙钟** | `shell.exec("powershell -NoProfile -EncodedCommand <const>", 10000)` → `2026-10-29 05:07:25|1793221645153|480`（本地时间、epoch ms、UTC 偏移分钟） |
| 可控时钟 | `AUTO_CALENDAR_TEST_MODE=1` + `AUTO_CALENDAR_FAKE_NOW="2028-02-29 23:59"` + `AUTO_CALENDAR_FAKE_OFFSET_MIN=-330` → now 返回注入值（闰日）✓ |
| 数据根覆盖 | `AUTO_CALENDAR_DATA` → 后端 `env.get` 生效（status 返回隔离目录） |
| fs 回环 | `fs.mkdir_all/write_text/read_text/exists/delete` 全 true，readback 一致（内嵌 facade 为 bool 约定） |
| json | `json.parse/get/as_int/as_string/encode` 正常；shell.exec 返回 JSON envelope 可解析 |
| 测试模式开关 | `AUTO_CALENDAR_TEST_MODE` 透传至 status（test_mode:false/true） |

### 2.2 不可用 / 陷阱（编译级或行为级证据）

| 面 | 证据 / 语义 |
|---|---|
| `time.now_ms()/now_sec()` 后端 | E0432/E0433：路由发 `auto_lang_core::a2r_std::time`，内嵌 facade 无 `time` 模块（独立 a2r-std crate **有** time.rs，但 qualify 统一重写至内嵌面；仅 `sys::`/`sqlite` 豁免）。NOTES-001 2026-10-04 登记的缺口**仍未闭合** |
| `dep chrono` + `use.rs chrono::…` 后端 | use 语句存留于 db.rs，但 api_gen 生成的 workspace Cargo.toml 无 chrono（generate_cargo_toml 固定模板，无外部 crate 注入）→ unresolved import |
| chrono-tz / 任何 tz 库后端 | 同上不可达 ⇒ 后端无 tz 数据库 |
| `datetime.DateTime` | stdlib `datetime.at` 全 `#[vm]`，仅 VM 轨；vue natives.ts 对 VM-only native 抛诚实错误 |
| vue 轨 `Date.format` | 仅时间面（toLocaleTimeString hour/minute/second）；无日期格式化、无时区偏移原语；`Date.now()`（epoch ms）双轨可用 |
| `use auto.shell` | 生成坏 import `use crate::shell;`（use_stmt 重映射缺口）；调用点本就全限定，**省略 use 行即可**（已采用） |
| db 层结构体字面量 | `return {ok: true, …}` 生成裸 `{…}` 无类型路径 = Rust 语法错误 ⇒ db 层一律返回手工拼 JSON 的 str（notes 验证过的模式） |
| `fs.rename/read_dir` | 内嵌 facade 无；`mkdir_all/dir_names/remove_dir` **有**（notes r4 后已补部分缺口） |
| `auto info` 子命令 | 从 CWD 直读 `pac.atom.at`（遗留怪癖，未生成即失败）——不能用作健康检查 |
| dev server 端口漂移 | 前端端口被占时 vite 静默 +1（曾撞上 17821 后端端口）——测试入口必须先核端口空闲（T-05 落地） |
| 冷构建超时 | 首次 `auto run` 需编译整个后端依赖树，超 CLI 120s 后端就绪窗（r1 失败原因，二次运行增量后正常） |

## 3. 冻结决策（v1 最小闭环）

1. **架构**：双端统一 split mode；后端 = a2r rust axum（pac.at `api:"rust"`），端口 17821；每数据目录单写者。
2. **时间模型（后端权威时钟）**：`GET /api/v1/now` → `{date:"YYYY-MM-DD", time:"HH:mm", epoch_ms, offset_min, source:"host"|"test"}`；实现 = shell.exec PowerShell（不变文化输出，Windows；Linux 另等发行版门）。前端**不取本地时钟**：Init / Today / 月份导航 / 保存前后均重查 /now ⇒ 跨午夜、跨年、闰年由真实数据驱动，无固定日期残留（旧 `2026-06-17` 硬编码全部移除）。后端不可达 ⇒ 显式错误态，不显示假数据。
3. **可控时钟（V-01）**：test mode 注入 `AUTO_CALENDAR_FAKE_NOW`（`YYYY-MM-DD HH:mm`）与可选 `AUTO_CALENDAR_FAKE_OFFSET_MIN`（缺省 0=UTC，测试语义显式记录）；双端同源注入。
4. **事件模型（单次事件）**：稳定 id `ev-<seq>`（后端单调）；字段 title / start / end（`YYYY-MM-DD HH:mm` 墙钟）/ notes / created_offset_min（创建时刻设备偏移）/ created_epoch_ms。**墙钟语义：不声明时刻（instant），不伪装完整时区**（满足计划 §2"不通过固定 UTC 偏移伪装完整时区"）。
5. **校验（AC-03）**：后端纯 .at 校验——日历有效性（闰年/月日，datecalc 纯函数）、HH:mm 范围、end > start；非法输入返回结构化 err_code，前端保留原输入。**边界（诚实声明）**：DST 时刻歧义检测需 tz 数据库，当前后端不可达 ⇒ v1 墙钟输入不存在"歧义时刻"解释问题（存什么显什么，不静默改时刻）；instant 级歧义拒绝列为缺口 §4-1 的关闭红利，Spec 增量按此准确表述。
6. **存储（AC-03 重启恢复）**：`<data_root>/store/events.r<N>.json` 版本快照 + `manifest.json {rev, file}` 提交点；写序 = 先 r 文件后 manifest；manifest 损坏恢复 = dir_names 取最高有效版本重写 manifest；根解析 = `AUTO_CALENDAR_DATA` → `%APPDATA%/auto-calendar` → XDG/HOME 兜底。
7. **冲突模型**：变更携带 expected_rev；不匹配 → `err_code:"conflict"`，前端重取后由用户重试（不静默覆盖）。
8. **模块布局**：`src/back/api.at`（类型+路由）、`db.at`（服务层，与 api 同名配对）、`events.at`（存储协议）、`datecalc.at`（纯校验）；伴随模块由 api_gen 一并转译。
9. **启动入口（T-05 记录进 README）**：Vue = `auto run`；VM = `auto run -r vm`；两者均需 17821 后端；测试先核端口空闲再启动。

## 4. 具名跨仓缺口（不在本计划内修）

| # | 缺口 | owner / 关闭条件 | 本计划影响 |
|---|---|---|---|
| 1 | 内嵌 a2r_std facade 缺 `time` 模块（独立 a2r-std 已有）；api_gen workspace 无外部 crate（chrono/chrono-tz）注入面 | auto-lang：facade `pub mod time { pub use a2r_std::time::*; }` + workspace 依赖注入路径 | 时钟走 shell.exec 临时面；tz 级歧义检测延后；关闭后换内部实现、合同不变 |
| 2 | `use auto.<mod>` 对 shell 类模块生成坏 import（use_stmt 重映射缺口） | auto-lang：use_stmt 对已知路由模块发全限定路径 | 工作绕过：省略 use 行（已验证无副作用） |
| 3 | db 层结构体字面量生成裸 `{…}` | auto-lang：db post-process 补类型路径或 a2r 根因修复 | 工作模式：db 层返回 JSON str（notes 同款） |

## 5. 资源边界

- shell.exec 每次调用阻塞 ≤10s 超时（实测 PowerShell ~0.5–1s 冷启）；v1 不缓存 now（新鲜度优先，UI 人机频率）；/now 调用点限于 Init/Today/月导航/保存。
- 存储为整仓快照重写（每变更一次）；v1 规模承诺 = 数百事件；千级以上需修订（届时换 SQLite——notes 已验证后端可用）。
- 端口被占 = 后端启动显式失败，不静默换端口（测试入口负责前置检查）。
