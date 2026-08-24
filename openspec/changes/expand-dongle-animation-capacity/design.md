## Context

当前 Provider ABI 允许每 action `1..127` 帧；因此“30 帧”不是 ABI 的硬上限。既有实机材料只证明：15 角色、301 unique frame、约 156520 B 图像时可启动；305 与 320 unique frame 曾死机。二十角色要求先将角色数、逻辑帧数、unique frame、图像字节与运行时显示启动分开测量。

本仓已有专用 EvalKit 动画 target：`waveshare_nrf52840_ek` + `dongle_evalkit dongle_display`，以 SH1106 复用同一 Provider ABI 与显示初始化路径；另有 `snake_adapter dongle_demo` 旧目标，不得混作本次动画验收对象。

## Goals / Non-Goals

- Goals: 构建二十角色 Provider；修正 LVGL 9 类型兼容；在 EvalKit 上分离单动作帧数与总资源容量的启动影响。
- Goals: 记录精确模块 SHA、UF2/ELF hash、FICR 身份、复位原因、显示首帧与每级资源数据。
- Non-Goals: 不以禁用编译诊断、降低优化级别或盲目擦除芯片换取通过；不将 EvalKit 启动结论夸大为 USB HID、无线或量产硬件结论。

## Decisions

### 启动与运行时访问

LVGL 9 的 `lv_animimg_set_src()` 只保存传入的帧表指针与帧数，并不复制帧表或图像。当前十五角色、限帧二十角色及全帧二十角色的 `_image_ram_size` 相同；故本次不得以新增全量 RAM cache 解决 ROM/启动时序问题。

启动时只校验 registry 顶层字段，并仅校验随机选中的当前 pack、WPM band 与 action 帧表。其余 pack 在首次 NEXT/唤醒切换至该人物时按需校验。生成器仍须在构建期验证全部人物、动作、帧数与非空引用；Provider ABI 保持版本 1，不改变既有外部 Provider 的静态数据布局。

同一人物与同一 action 完成一轮后，仅重启既有 LVGL animation；只有人物或 WPM action 改变时，方重新调用 `lv_animimg_set_src()`、设置 duration/repeat，并输出一次 INFO 转换日志。如此避免每轮重复遍历/设置和串口日志负载，而不增加图片 RAM。

暂不采用 RLE、XOR delta 或运行时解压。此等方案虽可减少 ROM，却会引入解码 CPU、至少一帧工作缓冲及更复杂的首帧/跳帧状态，可能使已观测的蓝牙 prepare 延迟更坏。若惰性校验与零重复设置仍不足，须另以独立容量矩阵评估压缩方案。

### 容量自变量

测试矩阵将分开控制：

1. 固定 20 pack，仅改变每个 action 的输出帧数；
2. 固定每 action 的最长帧数，仅改变角色/unique-frame 总量；
3. 保持画布 64x64、色深、动作时长映射与启动逻辑不变。

每级均由生成器输出 manifest；启动失败时以最后启动标记、reset reason、RAM/Flash、显示初始化/首帧状态归因。只有跨级重复的变量才可称为限制根因。

可选的 Cornix 构建门槛以最终链接符号 `_flash_used` 为准，而非 Provider manifest 的图片字节。作安全构建时，上限应取同一工具链、同一功能组合已通过硬件启动之基线；作全量容量及优化验证时须能以值 `0` 明确关闭，保留完整二十角色与全部帧。启用后超限须由链接器断言拒绝产物，并在错误中说明经验性启动风险及关闭方法。此门槛是已验证组合的可选安全界线，不等同于证明 ROM 容量本身是蓝牙时序异常的唯一物理根因。

### LVGL 9 兼容

`lv_line_set_points()` 所需的点数组类型必须与本仓 LVGL 9 的 `lv_point_precise_t` 一致。修复应进入维护该代码的自定义 dongle-display 分支；本仓 manifest 锁定已验证提交，不修改下载依赖以制造未记录漂移。

### EvalKit 验收

先读取 DAPLink/ST-Link、FICR、目标电压/复位状态及既有镜像，并取得设备租约。只在可恢复的 EvalKit 上刷写应用；每次刷写前记录目标、镜像 hash 和地址范围。验收需有实际显示首帧或等价显示初始化观测，单纯 SWD 连接或 ELF 成功不算启动通过。

## Risks / Trade-offs

- 二十角色可能超过已知 301 unique-frame 启动预算；成功目标不应掩盖失败阈值，必要时以帧采样而非删角色满足预算。
- EvalKit 与 Cornix 虽同用 SH1106，板级 I2C 引脚、电源与上拉仍不同；它证明同一软件路径在该硬件拓扑启动，不证明 Cornix 屏幕的电气可靠性。
- 物理 flash 会替换 EvalKit 当前应用；先备份与记录，再在 ST-Link 持续可恢复条件下进行。
- 惰性校验会令坏 Provider 中尚未访问的人物延后报错；生成器全量校验及按需切换错误日志用于补偿，且不得越界访问无效 action/frame。
- 最终 ROM 上限会受编译器、链接顺序与功能开关影响；每次越限应检查 map，而非仅删图至能链接。

## Migration Plan

1. 固定并修复可构建的 LVGL 9 dongle-display 依赖。
2. 为 EvalKit 增加显式动画 target 及启动观测。
3. 运行 15/20 角色与帧数/unique-frame 矩阵，先构建与静态容量核验。
4. 将注册表改为当前 pack/action 按需校验，并消除同一动作循环的重复 source 设置与 INFO 日志。
5. 在已租用 EvalKit 依次刷写可恢复镜像，收集启动证据。
6. 写明实际阈值、失败层与二十角色最终预算；保留十五角色回归构建。
