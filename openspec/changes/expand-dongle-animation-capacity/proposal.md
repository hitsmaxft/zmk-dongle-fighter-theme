# Change: 扩展 Dongle 动画至二十角色并量化启动容量

## Why

KOF96 Provider 的资源库已有二十角色，但默认只启用十五角色，且既有记录仅知 301 unique frame 能启动、305 与 320 会在实机死机。当前 `custom_anima` 还含一处 LVGL 9 点类型不兼容，无法在本仓精确依赖组合中链接。因此不能以“单动作超过三十帧”作为未经验证的根因。

## What Changes

- 令生成器可明确选择并构建全部二十角色，并以可审计的 unique-frame、图像字节、Flash 与 RAM 门槛约束产物。
- 修复 Provider/显示模块与本仓 LVGL 9 API 的编译兼容性，且不以关闭类型错误代替修复。
- 增加专用 `waveshare_nrf52840_ek` 动画试验 target，使 DAPLink/ST-Link 可观测的 nRF52840 EvalKit 实际运行同一 Provider 与显示启动路径。
- 加入分层容量矩阵：保持动作/角色数据可重复，仅改变单动作帧数与 unique-frame 总量，记录启动、日志/断言、Flash、RAM 与复位原因。
- 将动画注册表由“启动时深度遍历全部人物与帧”改为“启动时浅校验、当前人物/动作按需校验”，且同一动作循环时不重复设置 LVGL source 与输出 INFO 日志。
- 保持 Provider ABI 与零拷贝帧表不变；以最终链接 ROM 守门，不以图片字节或新增 RAM 解码缓冲替代。
- 以 EvalKit 物理启动、显示首帧及受控 NEXT/唤醒操作，判定“超过三十帧不启动”的实际限制；若限制来自总资源而非单动作长度，文档须明确其因果边界。

## Impact

- Affected specs: `dongle-display-animation-extension`
- Affected code: KOF96 generator/configuration, EvalKit build matrix, dongle-display validation/playback hot path and custom animation branch
- Hardware: DAPLink/ST-Link attached nRF52840 EvalKit with其实际接线的显示屏
- Compatibility: 旧十五角色构建仍应可复现；未启用动画扩展的目标不引入资源
