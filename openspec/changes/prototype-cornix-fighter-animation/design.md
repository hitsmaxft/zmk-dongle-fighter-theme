## Context

Cornix 最终显示为 `128×64`、1-bit SH1106。现有猫图为八个 `50×26` LVGL `I1` 图像，按 WPM 切换 idle、slow、mid、fast。KOF96 提取帧为四灰阶、紧边裁切，须以 manifest 原点还原到固定画布后再二值化。

## Goals / Non-Goals

- Goals: 验证右侧 `64×64` 人物区、Kyo 动画可读性、布局无重叠、Flash/RAM 可承受、生成过程可复用。
- Non-Goals: 本轮不建立永久上游 fork，不打包全部角色或全部动作，不修改显示硬件与 split 协议。

## Decisions

- 右半屏固定为 `64×64`；人物以脚底/动作原点对齐，不逐帧居中。硬件反馈表明各档倍率不同会在切档时产生比例跳动，故四档统一放大 `1.5×`；越界像素直接裁切。
- 左半屏承载连接、层、修饰键与 HID lock 信息。两侧电池按硬件反馈移回屏幕右上，以单行两个 32 像素槽覆盖于人物画布顶层；电量文字使用紧凑格式。
- 资源格式为 LVGL `I1`。阈值与邻域过滤实机效果均不佳，故按用户要求恢复最初 2×2 ordered dithering：色阶 0/1/2/3 映射为 0%/25%/75%/100% 前景。
- 每角色资源仍以 `FIGHTER_ENABLE_*` 包裹；当前默认启用 15 人，关闭普通 Leona、普通 Iori、Chizuru、Boss Kagura 与 Mr. Karate。去重范围保持在角色内部。
- 恢复 activity 唤醒换角、自定义 behavior 与 Debug key binding；所有换角请求均在动作结束边界应用。
- 测试阶段可改 `zmodules`；生成器、输入清单和结论保存在 `graphs/`，以便日后迁入模块 fork。

## Risks / Trade-offs

- 64 像素高不足以容纳部分 Kyo 动作的 1.5 倍边界；生成器直接裁切越界像素。
- 1-bit 化会丢失 Game Boy 四灰阶细节；以抖动与逐帧预览缓解。
- 临时模块修改会被 `west update` 或重新初始化覆盖；以记录补丁与生成工具缓解。
- 全阵容接近代码分区上限；以至少 100 KiB 剩余空间为构建接受门槛，超限时先缩减长 idle/super 帧数。
- 若 20 人 define 全开低于门槛，则不删人物；idle 最多 8 帧、fast 最多 12 帧，其余档最多 16 帧，均匀抽样并保留首尾帧，动作总时长仍按原序列计算。
- LVGL AnimImage 的 `pic_count` 为 `int8_t`；每个动作表须在生成期与运行时均保证不超过 127 帧。

## Migration Plan

测试成功后，将 widget 的资源选择与布局参数迁入 `zmk-dongle-display` fork，以固定 revision 引用；失败则还原该模块工作树，保留 `graphs/` 分析资产。
