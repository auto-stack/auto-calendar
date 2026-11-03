# 主题采纳合同（theme-adoption）

> 来源：auto-os/PLAN-056（2026-11-03 work 候选 T-02；本仓候选见 git log
> plan-056 提交）。宿主主合同：auto-os `docs/specs/shell/host-theme-policy-and-delivery.md`；
> 本批登记页：auto-os `docs/specs/apps/product-theme-batch-056.md`。

## 消费形态

- **固定快照**：`vendor/themes` = UI 管理渠道发布的官方主题包快照
  （`themes` 0.2.0，内容 digest
  `9fa07742dc68aa5377ae06cb2d966386002063f184c515b6c5dddf8a6bef838e`，
  per-file sha256 与源包校验同律）。快照不可二次编辑、非第二权威源；
  升级 = UI 发新快照替换 + 本仓重验。
- **pac 声明**：`dep themes { path: "vendor/themes" }`；`theme` 键保持
  缺省 = **follow 宿主**（宿主策略完整快照 > 本 design 默认 > legacy 回退；
  显式值会以 pac 优先级压过跟随——本仓原有显式 theme 键已按此退役/保持缺省）。
- **源内导入**：`use themes.themes: Auto`——缺此行包主题不入收集链，
  design/follow 候选按 C-11 未注册整帧拒绝（031 合同）。
- **design 默认**：dark_mode 位派生（默认 false=浅色，与退役 pac `theme:"light"` 语义等价）；
  `dark_mode` 模型位语义沿 458 机制（family 链激活时由已提交策略派生 mode
  驱动，被拒候选的 legacy 翻转不得污染）。

## 豁免与不变量

- 外观面板 Dark/Light 两键与 accent 色板既有语义原样（store SetTheme/SetAccent 链不变）。
- 原完整适用业务门在采纳前后保持：standalone follow probe **5/5**（像素级：boot 恢复 dark/外写跟随 light/未知 family 具名拒绝保旧/重开追最新 dark/往返后 snapshot 存活）+ tampered 包源腿（具名拒绝+design 默认色）+ 第二有效根腿（任意绝对路径 clean 副本验证后照常驱动策略）

## 验证与测试设施（os-056 冻结工具链：auto.exe 5858593b + auto-ui-tool 3493e746）

- 无改动（follow probe 为 plan-artifacts 探针，产品测试设施未动）。
- 恢复身份/墓碑/不复用 ID 原门（verify_basic/verify_recovery_identity）不属本包改动面，交付记录见 CALENDAR-001/002。
