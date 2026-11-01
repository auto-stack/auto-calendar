# auto-calendar：独立可用性路线图

更新：2026-11-01。以Spec与真实交付为准，计划目标不表示已实现。

| 顺序 | 计划/成果 | 当前状态与边界 |
|---|---|---|
| 基础 | [001首轮能力](plans/archived/001-local-events.md) | 001已交付归档/r2、7/7，真实今日和单次事件保持墙钟合同；F-5已由002关闭。 |
| 当前优先 | [CALENDAR-002：恢复后版本凭据与删除保全](plans/002-recovery-revision-and-deletion.md) | r1实施完成（6/8）：恢复身份v2（水位/墓碑/拒写保全/v1迁移）已落地，四门全绿；T-06独立复审、T-07归档待行。 |
| 之后 | AutoOS统一装配 | 另立统一OS计划，接收各app单独验证/推送的精确提交；本轮不改pin |
| 之后 | Linux支持 | WAIT_DISTRO_M1，等Nix＋COSMIC发行版基础；不阻塞本app本机任务 |

旧条件凭据恢复后不再复效（单调水位背书）；删除以墓碑为事实不复活；已分配ID永不重发；新空库与缺证据旧库严格区分，证据不足拒写保全，受控恢复后下一次写入成立。

重复规则、提醒、CalDAV、DST时刻转换另排，保持墙钟语义。

工作位D:/autostack/auto-calendar独立clone main，实施与独立上下文复审顺序共用，一app一写入者。永久回放入口：`tests/basic/verify_basic.py`（001）与 `tests/basic/verify_recovery_identity.py`（002）双profile；独立准备门 `tests/free_ports.py --check` 只查不杀，进程收割仅限本运行自有进程，不清共享缓存、不杀旁观实例。

[README](../README.md) · [现实现规范](specs/calendar/basic-capabilities.md) · [恢复身份规范](specs/calendar/recovery-identity.md)
