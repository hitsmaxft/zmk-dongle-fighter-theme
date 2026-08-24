# Change: 以 60Hz ROM 证据生成可降采样的 Fighter 时间线

## Why

既有 fast 与 mid 曾混用 500/200ms 人工 cadence、半速保持及额外 `2x` 拉伸，致 ROM
`FrameTotal`、飞行道具显隐、起手与收招硬直不能同一尺度比较，且重复保持会膨胀 Provider
指针、时长及位移表。Athena 缺 Shining Crystal Bit 道具，Geese 缺 Raging Storm 光柱，
Mr Karate 龙虎乱舞末段后跳亦未依原重力逐 tick 复原。

## What Changes

- 以固定反汇编 revision 的 59.7275Hz VBlank 为唯一源时钟；`FrameTotal=N` 计 `N+1`
  source ticks，记录起手、主体、飞行道具、腾空与收招硬直边界。
- 生成器新增 `--source-ticks-per-display-frame`，默认每两个 source ticks 采一 OLED 状态，
  目标约 29.864Hz；参数只改变采样密度，不改变所选 ROM 路径的累计墙钟时长。
- mid 与 fast 共用 schema v2 时间证据；默认生产角色之 mid 不再使用通用 cadence。
- 补入 Athena Shining Crystal Bit 四幅映射与 Geese Raging Storm 四幅光柱映射，并按
  原 projectile code 的寿命及动态速度生成有限时间线。
- 复原 Mr Karate `RyukoRanbuS -> Zenretsuken -> RyukoRanbuD3 -> HaohShoukouKenD`；
  D3 后跳按 `vH=-$0600`、`vV=-$0300`、重力 `+$0060` 逐 tick 求位移后降采样。
- 对采样后连续相同的最终 I1 图、X/Y 位置及移动状态作保持合并；mid/fast 的相同最终
  位图共用单一 Flash 数据，报告源 tick、采样槽与最终播放步三种计数。

## Impact

- Affected specs: `dongle-display-fighter-theme`
- Affected code: Provider 生成器、缓存器、GIF 渲染器、ROM 复合动作脚本、播放计划、
  位图 manifest 与宿主测试
- Runtime: 不新增 LVGL object、timer、堆分配或解压画布；只读 I1 图及表仍由 Flash 直取
- Compatibility: 未带 timing 的旧 action 仍循旧 cadence；显示模块 Provider ABI 不变
- Hardware: 构建可证明 Flash/SRAM 静态占用；实屏节奏仍须硬件另验
