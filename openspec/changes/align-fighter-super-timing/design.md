# KOF96 Fighter ROM 时间线降采样设计

## Context

原作 Game Boy 主循环约为 59.7275Hz。对象映射的 `FrameTotal=N` 实际可见 `N+1`
updates；move code 又可改速、循环、等待碰撞、生成 projectile 或以速度／重力决定落地。
故只读 OBJ pointer table 不足以复原招式，亦不可把每张导出 BMP 当作等时长。

此前实现把源 tick 映为 66/67ms，动作约为原作四倍；最新目标则是显示端约 30 updates/s，
且保留原作死亡慢放式的逐状态可见性。故源时间与显示时间必须分离：ROM 分支总 tick 是
证据基线；默认显示量化保证每一逻辑状态至少占一个 OLED 槽，短态可被拉长。若调用者明确
接受丢帧，方可另选维持源墙钟时长的窗口抽样。

## Timing evidence model

mid 与 fast 均使用 schema v2：

```json
{
  "schema": 2,
  "rom_move": "MOVE_GEESE_RAGING_STORM_S",
  "clock": "gb-vblank",
  "branch": "finite-demo",
  "disassembly_revision": "47acd3002897ccd6b46df70809e8d6236ed3ebc3",
  "evidence": {
    "animation_table": "src/bank03.asm:MoveAnimTbl_Geese",
    "move_code": "src/bank06.asm:MoveC_Geese_RagingStorm",
    "projectile_code": "src/bank06.asm:ProjC_Geese_RagingStorm",
    "object_table": "data/objlst/proj.asm:OBJLstPtrTable_Proj_Geese_RagingStormS"
  },
  "step_ticks": [21, 1, 61],
  "total_ticks": 83
}
```

- `clock` 恒为 `gb-vblank`；不再以 `gb-half-speed` 或 display stretch 混入源证据。
- `startup` 指第一张人物图已绘出后的源保持；Super Sparkle `$14` tick 与人物并行，
  除非 move code 明确阻塞，否则不叠加。
- `recovery` 是最后攻击／特效边界至 `Play_Pl_EndMove` 的可见后缀。
- 输入、碰撞、随机与对手状态须选定有限分支；物理落地则以原 8.8 速度及重力模拟。

## 60Hz to display sampling

生成器先展开 source-tick state，再按 `N=--source-ticks-per-display-frame` 量化：

- 默认 `N=2`，名义目标率为 `59.7275/2 = 29.86375Hz`；允许 `1..16`。
- 默认对每一步分配 `ceil(step_ticks/N)` 个显示槽，时长按完整槽累计；一 tick 的显示与
  隐藏状态在 N=2 时皆可见约 33.5ms，不因偶奇相位消失。
- `order`、图片、X/Y、movement、return 与 recovery 边界逐项保留；仅相邻完全相同的保持
  可合并 duration。`source_total_ms` 记录 ROM 基线，`total_ms` 记录实际 OLED 时长。
- 显式 `--allow-source-frame-drop` 才恢复分窗：第一、recovery、return、末态及
  `sampling_required_frames` 强制保留；若 N 无法容纳必保变体则明确失败。

报告同时输出：

- `total_ticks`: ROM 源路径长度；
- `sampled_display_slots`: 降采样后的时间槽；
- `playback_steps`: 相同保持合并后的 Provider 表长；
- `collapsed_hold_slots`: 后两者之差。
- `source_total_ms`／`total_ms`: ROM 基线与量化后实播时长。

三者分开可防止资源优化无意删掉 ROM 时长。

## Character corrections

### Athena

Shining Crystal Bit charge projectile 的 update 明注为跨玩家隔帧执行，即对象更新率原已约
30Hz。复合时间线保留旋绕图及三张 thrown 映射：蓄球位于手侧，释放后以有限向前路径
交替人物／道具，不再只播人物本体；未移植完整对手／输入状态机。

### Geese

Raging Storm S 人物帧为 21/1/61 source ticks。光柱对象寿命 `$3C` tick；初始 speed 0，
余寿命小于 `$10` 时改 speed 1，小于 `$08` 时改 speed 2。生成期模拟四 mapping 的推进，
并把对象表 XOffset／XFLIP 转为左右相位；同形两相仍复用 I1，不在固件移植 projectile
状态机。

### Goenitz

Yonokaze 对象表有左形、中间细形、右翻转形三 mapping。复合器提取三者，以左／中／右
相位同举起帧交替两轮；三相不得因逐图居中而落在同一坐标。

### Mr Karate

选择隐藏 D 成功路径：Ryuko Ranbu、四轮 Zenretsuken、D3 后跳、Haoh D。D3 可见 hop
mapping 为 2/13/1 ticks；逐 tick 以 `vH=-$0600`、`vV=-$0300`、gravity `+$0060`
积分，生成多级 X 与固定 `-10px` 腾空偏移，落地恢复 0。Haoh 人物帧为 2/2/2/31/5
ticks，道具 D/S 映射与人物状态交替。

## Flash and SRAM decisions

1. 最终画面先转 LVGL I1，再以 `(canvas width, height, packed bytes)` 作精确去重；去重表
   跨同一角色之四档存在，故 mid 复用 fast 的相同图只发出一个 `static const` payload。
2. 降采样后，若连续槽的图、X/Y 及移动语义全同，则把毫秒相加而不再发出 pointer、
   duration、movement、offset 项；return 边界不得跨越合并。
3. 图、描述符与动作表均为 `static const`，直接驻 Flash；生成器不引入运行时缓存。
4. 暂不引入 atlas／tile dictionary。现 ABI 可由 LVGL 直接读取 I1；atlas 若需裁切或重组，
   至少会增加可写画布、清屏／拷贝和索引逻辑。仅当离线量测证明 tile 数据与元数据之和
   显著低于当前 I1，且可用一个有界共享缓冲保持 SRAM 净不增时，方另案实施。
5. 跨角色量测显示：生产十四角无相同 payload，可省 0B；全二十角的 29 组重复主要来自
   普通／暴走及千鹤／万龟克隆，理论约 15.7KiB，但彼等不入生产编译。故不增公共 gate，
   免令禁用角色素材意外编入。
6. 多段人物动作在合成期共用联合边界与缩放；飞行物单图归一后以 int8 相位复原对象表
   坐标，故同形 payload 可去重，且不增加运行时画布。
7. mid/fast 战斗 action 在运行时按屏底对齐，故生成 I1 可删除统一透明顶部行；image 高度
   随联合内容缩短而屏幕内容坐标不变，SRAM 与对象数不增。

## Validation

- 宿主测试验证 schema、关键源 ticks、默认全状态保留、显式丢帧、保持合并及 mid/fast
  图共享。
- GIF 与 Provider 共用同一 order、位置及 duration。
- 构建后以 manifest、ELF/map 与 Zephyr RAM/ROM 报告分别量测图片、表、Flash 与 SRAM。
- 静态构建不冒充 SH1106/ST7789 实屏节奏验证。

## Rollback

单角色可移除 timing 条目回旧 cadence；采样参数可改回 1；保持合并可独立关闭而不改源
时间线。无需回滚播放器 ABI。
