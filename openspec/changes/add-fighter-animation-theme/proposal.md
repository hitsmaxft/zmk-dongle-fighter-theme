# Change: 增加 Fighter 分层动画主题

## Why

现有通用动画扩展只能在右栏原地播放图片，不能令 Fighter 的中高速动作按真实帧位移，亦无战斗模式所需的左右手电池 HUD。远端 `codex/fighter-animation-theme` 已给出开发方案，但尚无实现。

## What Changes

- 将动画 Provider ABI 最终升为 v7，为 action 增加稳定宽度的 motion、flags、首末帧停留、可选逐步位移表、单次回程分界、可选逐帧 X 偏移及可选逐步时长表，同时保持旧 action 宏源码兼容。
- 以单一 `lv_image` 与 `lv_timer` 同步推进图片帧、坐标和精确帧周期。
- Fighter mid/fast 首个与末个播放步骤绘制完成后各停留 500ms，中间步骤各停留 200ms；动作总时长由实际播放步骤数精确计算。
- 增加构建期自定义播放序列：序列以原始动作帧索引描述，可重复、跳转或改变顺序；生成器将其展开为现有 frame pointer 表，播放顺序本身不需运行时解码状态。
- 为自定义播放序列增加逐步位移标记，每步仅可为 fixed 或 move；fixed 保持前一 X，move 才推进一个等分位移。无标记者保持原有逐帧移动。
- 逐步位移可另设一个 action 级回程分界；分界前的 move 等分到达目标，分界后的 move 等分返回原点，仍不使用逐帧坐标或速度脚本。
- 增加低帧飞行道具模式：人物与飞行道具共用一个 image object 并在时间线上交替出现；逐帧 X 偏移令人物、后跳与道具各自移动，无第二图层、canvas 或堆分配。
- 八神 fast 使用 D／MAX 八稚女，仅令重复的第 1 帧突进；在十六进制 `#19` 终结帧以两张 ROM 火焰图和无火人物图交替三轮，再播放收招。空手道先生 fast 依原作意图串联龙虎乱舞、暂烈拳、后跳与霸王翔吼拳，并令两张可见道具图与收招人物交替前行。
- 续以 ROM move code 校准其余可静态表达的 fast：暴走八神、大门与 Athena 展开其确定次数的循环；Ryo 与 Robert 重复命中前的前突帧，并在乱舞末尾分别转入重 Ko Hou 与重 Ryuu Ga，以两张空中姿态正反往复后落地；Andy 则保留受纵速驱动的原始帧序。依赖对手位置或未抽取道具的动作仍保留原序，不伪称原作完整演出。
- Terry fast 改取隐藏 MAX `Power Geyser E`；抽其两种可见地涌道具图，以不相邻预定落点交错人物收势，表达原作每次重生道具即覆盖旧道具的随机连发。
- Goenitz fast 以绝望超杀前段突至屏幕中央，续接其 mid 所用重投技至举起帧；同位以 ROM 夜之风两张镜像龙卷图交替两轮，继而恢复投技下压、落地及收束帧。
- 增加内置 50x26 Fighter pack，并支持 EvalKit 以自定义 Fighter provider 验收；生产 roster 不编译 Chizuru、Boss Kagura、Mature、普通 Iori、普通 Leona 与 Mr Big，但保留其素材、播放计划及显式全量测试能力，并继续启用 Orochi Iori 与 Orochi Leona。
- mid/fast 可均匀抽帧，但被选帧按高度缩放且不得裁切；宽度可按原始纵横比超过 64px。
- mid/fast 战斗背景保持纯黑，不分配全屏 canvas 或背景帧缓冲。
- 将状态屏拆为普通、动画、战斗 HUD 三层；Fighter mid/fast 隐藏普通层并显示左右手电池 HUD。
- 在模块内置 Provider 中增加 Fighter Theme demo pack，动作表复用既有 Bongo Cat 图片描述符，不再为 demo 编译独立 Fighter bitmap payload。
- 保持自定义 Provider 完全接管 registry；未启用动画扩展时仍走原始 Bongo 路径。

## Impact

- Affected specs: `dongle-display-fighter-theme`
- Affected code: `zmodules/zmk-dongle-display` Provider ABI、动画 widget、状态屏、内置资源、战斗电池 HUD 与文档
- Hardware: 128x64 SH1106 的 `waveshare_nrf52840_ek` 精简人物循环演示目标
- Compatibility: Provider ABI 升为 v7；旧宏 Provider 可重新编译并默认逐帧移动、使用通用 cadence，直接初始化旧 ABI 结构者须迁移；未配置自定义播放序列的动作仍按原始顺序播放
