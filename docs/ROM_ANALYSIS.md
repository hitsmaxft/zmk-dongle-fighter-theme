# `ntkof96.gb` 角色位图与动作时间线析取记

支持输入为日版 `NETTOU KOF 96`，MBC1、512KiB。SHA-1
`63f25bff422a591907b83ab9f14709e938172839`，SHA-256
`dbb3b21e278803c484826a1fae99dc4b167fab86b506cb0694132d716c0f83de`，与
Kak2X/kof96 所标日版逐字相合。ROM 不在本模块版本库；zmk-config 工作区仍保存于
`graphs/ntkof96.gb`，extractor 须显式传入该路径。

角色图形以 Game Boy 2bpp、8×16 OBJ 存之。角色本体 1,702 个 GFX 块，主体位于 ROM
banks `0B–1B`，四块溢入 `1C`。一动画帧由一或二组 OBJ（A/B）合成；每组含图形指针、
坐标表、X/Y 翻转及偏移。`scripts/extract_character_bitmaps.py` 以反汇编资产核验 ROM
字节，再依动作表复原帧序与坐标；输出在 `assets/character_bitmaps/`，manifest 记录原点、
尺寸、动作名、header、ROM offset 与长度。低帧 projectile 由
`scripts/extract_projectile_bitmaps.py` 从公开反汇编的压缩图与对象表复原至
`assets/projectile_bitmaps/`。

## 动作表与执行路径

OBJ pointer table 只列可引用映射，完整招式仍须追 move/projectile code：

- `FrameTotal=N` 实际保持 `N+1` 个约 59.7275Hz source ticks；
- Kyo MAX 大蛇薙会依蓄力输入回跳；
- Mai MAX 忍蜂以 `vV=-$0500`、gravity `+$0060` 决定落地前 8/9 循环；
- Orochi Leona Super Moon Slasher 的 4/5/6 由 `$08` loop timer 循环八轮，随后反向后跳；
- 投技、命中、格挡、随机及对手状态须在 `data/fighter_playback.json` 选定有限演示分支。

Dongle 不移植战斗状态机。生成期把已选路径展开为 frame、X/Y、movement、source ticks，
再生成只读 Provider；此有限路径不宣称复刻输入、碰撞箱、双方受击或随机数系统。

## 复合 projectile

- 普通 Iori 八稚女终段之 `PF3_FIRE` 是独立命中特效，Dongle 以人物终结帧与两张火焰
  映射交替三轮，不增加第二 LVGL object。
- Terry hidden MAX 的十五枚前置 Power Geyser 会被后枚覆盖，末枚方走完对象映射；
  人物与现存 projectile 以单 image 时间线交替。
- Athena Shining Crystal Bit 收录 swirl 与三张 thrown 映射；charge projectile code 明注
  跨玩家隔帧执行，即对象路径本已约 30Hz。
- Geese Raging Storm S 光柱寿命 `$3C` source ticks，初速 0；余寿命小于 `$10` 改速 1，
  小于 `$08` 改速 2，四张 mapping 由生成器有限模拟。
- Mr Karate 采用隐藏成功路径
  `RyukoRanbuS -> Zenretsuken -> RyukoRanbuD3 -> HaohShoukouKenD`。D3 后跳 mapping
  保持 2/13/1 ticks，并以 `vH=-$0600`、`vV=-$0300`、gravity `+$0060` 求多级位移；
  Haoh D 的人物映射与 D/S projectile 交替。

## 60Hz 源时钟与 30Hz 显示

所有已迁移 mid/fast 的 `timing.clock` 为 `gb-vblank`。生成器先展开 59.7275Hz source
timeline，再按 `--source-ticks-per-display-frame N` 分窗。默认 N=2，目标约 29.86375Hz；
N 可为 1..16。参数降低显示更新数，不改变源分支总 ticks 或累计毫秒。

采样后若相邻槽的最终 I1 图、X/Y 与移动语义相同，便把 duration 合并；故报告同时记录
ROM ticks、`sampled_display_slots`、`playback_steps` 与 `collapsed_hold_slots`。图片数据按
最终 `(width,height,I1 bytes)` 在同一角色四档间去重，mid 与 fast 复用同图时只发出一个
Flash payload。所有图、描述符与表为 `static const`，无运行时解压或合成画布。

默认 N=2 的 fast 摘要：

| 人物 | ROM ticks | 采样槽 | Provider 步 | 总时长 ms |
|---|---:|---:|---:|---:|
| Kyo | 59 | 30 | 20 | 988 |
| Daimon | 217 | 109 | 24 | 3633 |
| Terry | 199 | 100 | 54 | 3332 |
| Andy | 58 | 29 | 6 | 971 |
| Ryo | 102 | 51 | 23 | 1708 |
| Robert | 92 | 46 | 22 | 1540 |
| Athena | 137 | 69 | 63 | 2294 |
| Mai | 51 | 26 | 17 | 854 |
| Orochi Leona | 82 | 41 | 22 | 1373 |
| Geese | 83 | 42 | 31 | 1390 |
| Krauser | 26 | 13 | 13 | 435 |
| Goenitz | 69 | 35 | 19 | 1155 |
| Mr Karate | 132 | 66 | 36 | 2210 |
| Orochi Iori | 66 | 33 | 21 | 1105 |

## 复现

```sh
git clone https://github.com/Kak2X/kof96.git /private/tmp/kof96-disasm
git -C /private/tmp/kof96-disasm checkout 47acd3002897ccd6b46df70809e8d6236ed3ebc3
python scripts/extract_character_bitmaps.py ../../graphs/ntkof96.gb \
  --disasm /private/tmp/kof96-disasm --output assets/character_bitmaps
python scripts/extract_projectile_bitmaps.py \
  --disasm /private/tmp/kof96-disasm --output assets/projectile_bitmaps
python scripts/compose_fighter_projectile_actions.py
python -m unittest tests.test_fighter_playback tests.test_fighter_gif
```
