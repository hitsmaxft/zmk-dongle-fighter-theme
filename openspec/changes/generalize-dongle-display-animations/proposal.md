# Change: 泛化 Dongle Display 多动画扩展

## Why
`custom_anima` 现将 KOF 人物表、四档动作、切换状态及 `fighter_next` behavior 直接耦合于 Bongo Cat widget。每增一套动画皆须修改模块源码，且动作帧数、持续时间与角色切换规则无稳定契约，难以供不同 ZMK config 复用。

## What Changes
- 将动画播放、WPM 动作选择、动画包切换与具体图像数据分离。
- 提供只读 Provider ABI；用户在 ZMK config 中以 Kconfig 参数指定 Provider 入口头文件，无须修改或复制模块源码。
- 通用动画总开关默认关闭；未启用时继续编译原 Bongo widget，通用引擎、Provider、校验、随机与 NEXT 不进入链接。
- Provider 显式声明动画包、动作、帧表、时长与 WPM 映射；普通数组的帧数由宏自动推导，并保留显式帧数入口供生成代码使用。
- 支持构建期 Provider 生成；生成物持久化至 `.build/_graphs`，以源内容哈希复用缓存，不再提交最终大头文件。
- 提供零参数通用中央 `NEXT` behavior；请求沿用 atomic 计数，并在当前动作结束后逐个消费。
- 启动时以非阻塞 cycle counter 随机选择动画包；其后 NEXT 仅按 Provider 顺序步进，单包时保持不变。
- 保留内建动画作为未配置 Provider 时的回退，并将现有 KOF96 数据迁至当前 ZMK config，作为外部 Provider 示例与验收对象。
- 将 `fighter_next` 暂留为兼容别名，内部转为通用 `NEXT`，后续另案移除。

## Impact
- Affected specs: `dongle-display-animation-extension`（新增）
- Affected code: `zmk-dongle-display` 动画 widget、Kconfig/CMake、behavior 与公开头文件；本仓 `config/animations/`、键位及生成器
- Build targets: `cornix_dongle`、`velvet_central_dongle`
- Compatibility: 默认配置继续显示内建动画；旧 `&fighter_next` 在迁移期保持可用
- Disabled cost: 未启用通用动画扩展时，最终二进制不得含通用动画符号或资源
- Resource constraint: Provider 静态链接，不引入文件系统、堆分配或运行时图像解码
- Randomness: 仅用于展示，使用非阻塞 cycle counter 与简单取模；不得在显示初始化中等待 entropy
