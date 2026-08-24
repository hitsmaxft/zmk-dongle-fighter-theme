# KOF96 Fighter ROM 时间线降采样设计

## Context

原作 Game Boy 主循环约为 59.7275Hz。对象映射的 `FrameTotal=N` 实际可见 `N+1`
updates；move code 又可改速、循环、等待碰撞、生成 projectile 或以速度／重力决定落地。
故只读 OBJ pointer table 不足以复原招式，亦不可把每张导出 BMP 当作等时长。

此前实现把源 tick 映为 66/67ms，动作约为原作四倍；最新目标则是显示端约 30 updates/s，
并允许参数继续降低更新率。故源时间与显示采样必须分离：ROM 分支总 tick 决定墙钟时长，
采样参数只决定期间画多少个状态。

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

生成器先展开 source-tick state，再按 `N=--source-ticks-per-display-frame` 分窗：

- 默认 `N=2`，名义目标率为 `59.7275/2 = 29.86375Hz`；允许 `1..16`。
- 每窗时长由其所含 source ticks 累计换算，故尾窗不足 N tick 亦准确。
- 第一窗、recovery 边界、return 边界与末窗强制取对应状态，免丢起手／收招语义。
- 普通窗轮换采样相位；复合计划另列 `sampling_required_frames`，令 D/S、光柱及 thrown
  等低帧变体至少各入一次。若所选 N 无法容纳全部必保变体，生成期明确失败，不静默丢图。
- 所有输出 duration 由累计 tick 换算；总毫秒等于原分支总 tick 的墙钟时长，采样参数
  不得令动作变快或变慢。

报告同时输出：

- `total_ticks`: ROM 源路径长度；
- `sampled_display_slots`: 降采样后的时间槽；
- `playback_steps`: 相同保持合并后的 Provider 表长；
- `collapsed_hold_slots`: 后两者之差。

三者分开可防止资源优化无意删掉 ROM 时长。

## Character corrections

### Athena

Shining Crystal Bit charge projectile 的 update 明注为跨玩家隔帧执行，即对象更新率原已约
30Hz。复合时间线保留旋绕图及三张 thrown 映射，按 normal-size 分支与有限 orbit／投掷
路径交替人物／道具，不再只播人物本体。

### Geese

Raging Storm S 人物帧为 21/1/61 source ticks。光柱对象寿命 `$3C` tick；初始 speed 0，
余寿命小于 `$10` 时改 speed 1，小于 `$08` 时改 speed 2。生成期模拟四 mapping 的推进，
不在固件移植 projectile 状态机。

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

## Validation

- 宿主测试验证 schema、关键源 ticks、采样参数、墙钟恒定、保持合并及 mid/fast 图共享。
- GIF 与 Provider 共用同一 order、位置及 duration。
- 构建后以 manifest、ELF/map 与 Zephyr RAM/ROM 报告分别量测图片、表、Flash 与 SRAM。
- 静态构建不冒充 SH1106/ST7789 实屏节奏验证。

## Rollback

单角色可移除 timing 条目回旧 cadence；采样参数可改回 1；保持合并可独立关闭而不改源
时间线。无需回滚播放器 ABI。
