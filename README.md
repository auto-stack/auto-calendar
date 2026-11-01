# auto-calendar

日历，使用 AutoLang / AutoUI 开发的独立应用。

更新：2026-11-01。002 已实施（T-00..T-05）：恢复身份 v2（水位/墓碑/拒写保全）
落地，F-5 恢复后 rev 回退窗口关闭；门全绿（recovery vue 31/31、vm 28/28；
001 基本门 vue 19/19、vm 11/11；深电池 30/30）， awaiting 独立复审。墙钟合同不变。

## 运行

安装对应版本的 `auto` CLI 后，从本仓根执行：

```sh
auto run        # Vue（后端 17821 + 前端 17820）
auto run -r vm  # VM 原生窗口（同一 rust 后端 17821）
```

- 后端端口 `17821`、前端 `17820`（`pac.at`）。启动前端口必须空闲：`auto run` 对端口被占不静默换位。`python tests/free_ports.py --check` 只查不杀；进程收割仅限本运行自有进程（`tests/free_ports.py` Ownership 纪律，002 起），旁观实例永不清理。
- 用户数据根：`AUTO_CALENDAR_DATA` 覆盖，缺省 `%APPDATA%/auto-calendar`。
- 测试可控时钟：`AUTO_CALENDAR_TEST_MODE=1` + `AUTO_CALENDAR_FAKE_DATE` /
  `AUTO_CALENDAR_FAKE_TIME` / `AUTO_CALENDAR_FAKE_OFFSET_MIN`。
- 基本能力验收（隔离数据目录，双端）：`python tests/basic/verify_basic.py --profile vue`
  与 `--profile vm`（需 tests/node_modules：`cd tests && pnpm install`）。
- 恢复身份验收（002，双端）：`python tests/basic/verify_recovery_identity.py --profile vue|vm`。

共享 StyleKit 已固定在 `vendor/stylekit`，无需相邻 auto-lang 示例目录。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/auto-calendar`](https://github.com/auto-stack/auto-os/tree/main/apps/auto-calendar) submodule 固定本仓版本；教学 Demo 保留在来源仓。

已有测试随源导入；端口与平台相关测试需要按本仓配置准备运行环境。安装/启动与双端完整功能验收是不同检查项。

## 基本能力补齐计划（2026-10-29）

[CALENDAR-001：真实日期与本地事件日历](docs/plans/archived/001-local-events.md) 为本app的基础能力执行合同，已交付（r2，复审通过并归档，2026-10-29）；基本能力规范见 [docs/specs/calendar/basic-capabilities.md](docs/specs/calendar/basic-capabilities.md)（已生效）。AutoOS 子模块 pin 更新与总表登记由 AutoOS 侧计划跟进。
总状态与前置见 [AutoOS B类总跟踪表](https://github.com/auto-stack/auto-os/blob/main/docs/plans/b-apps-basic-capabilities.md)。基础能力通过后再考虑Linux；A类统一等待 auto-os-distro 完成 Nix＋COSMIC 基础，后续增强另会话。

开发使用独立 clone `D:/autostack/auto-calendar` 的 main；AutoOS 内对应子模块仅固定已交付提交，流程见 [App开发与子模块](https://github.com/auto-stack/auto-os/blob/main/docs/design/strategy/app-submodule-workflow.md)。


## 当前后续计划（2026-11-01）

[CALENDAR-002：恢复后版本凭据与删除保全](docs/plans/002-recovery-revision-and-deletion.md) 为 **r1、实施完成（6/8，T-06 复审 / T-07 归档待行）**。恢复身份 v2 已落地：`store/identity.json` 单调水位（rev_high/seq_high）+ 删除墓碑 + 证据不足拒写（`recovery_unproven` 只读保全态，唯一出口 `AUTO_CALENDAR_RECOVERY_CONSENT=accept-scan` 受控恢复）+ v1 迁移先备份。规范见 [docs/specs/calendar/recovery-identity.md](docs/specs/calendar/recovery-identity.md) 与 [basic-capabilities.md](docs/specs/calendar/basic-capabilities.md) §4（r2 修订稿随 merge 生效）。

[路线图](docs/roadmap-v0.6.md) · [现实现规范](docs/specs/calendar/basic-capabilities.md)。开发与顺序复审在D:/autostack/auto-calendar独立clone main，一app一写入者；不在OS组合子模块开发，不建junction/symlink。不更新AutoOS pin；各app独立验收后由统一OS计划装配，Linux仍WAIT_DISTRO_M1。
