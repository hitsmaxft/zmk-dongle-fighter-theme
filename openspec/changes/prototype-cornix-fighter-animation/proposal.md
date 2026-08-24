# Change: Cornix dongle 人物动画测试版

## Why
现有 Bongo Cat 固定使用右下 `50×26` 的 1-bit 画布，容不下大多数 KOF96 人物原尺寸帧。测试版须重排 `128×64` OLED，使右侧成为稳定的 `64×64` 人物区域，并验证图像转换、动画映射与固件资源开销。

## What Changes
- 临时修改下载的 `zmk-dongle-display` 模块；不将该修改视为可长期更新的依赖方案。
- 将连接、电池、层、修饰键及设备名集中到左侧，右侧保留 `64×64` 人物区域。
- 二十人物仍异常后，define 关闭普通 Leona、普通 Iori、Chizuru、Boss Kagura 与 Mr. Karate，保留 15 人试验集。
- 恢复熄屏唤醒换角与 Debug 手动换角，但换角仍待当前整套动作结束。
- 在 `graphs/` 保存生成工具、尺寸结论、资源映射及后续迁移建议。

## Impact
- Affected specs: `cornix-fighter-animation`（新增）
- Affected code: `zmodules/zmk-dongle-display/boards/shields/dongle_display/`、`graphs/`
- Build target: `cornix_dongle`
- Risk: `zmodules/` 变更会被依赖重拉覆盖；测试结论与生成源须独立保存在 `graphs/`。
- Capacity gate: code partition MUST retain at least 100 KiB and UF2 MUST remain below storage.
