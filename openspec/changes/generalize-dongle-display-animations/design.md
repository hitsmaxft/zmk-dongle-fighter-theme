## Context

当前 `bongo_cat.c` 同时承担 WPM 策略、LVGL AnimImage 生命周期、KOF 动作选择、角色轮换及唤醒事件；`fighter_images.h` 又将数据 ABI 固定为 idle/slow/mid/fast 四字段。目标是使模块只认识通用动画数据，不认识人物或特定动作名。

## Goals / Non-Goals

- Goals: 外部静态 Provider、可声明动作与 WPM 映射、通用 NEXT behavior、无损迁移 KOF96。
- Non-Goals: 运行时上传图片、从文件系统读动画、Studio 动态编辑帧、在固件内缩放或转换源图片。

## Decisions

### Provider 入口

新增：

```text
CONFIG_ZMK_DONGLE_DISPLAY_CUSTOM_ANIMATION_PROVIDER=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATED=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATOR="../graphs/cache_cornix_fighter_provider.py"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_CACHE_DIR="../.build/_graphs/kof96"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_HEADER="kof96_provider.h"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_ROTATE_ON_WAKE=y
```

Provider 路径相对 `ZMK_CONFIG`；模块仅在专用单一翻译单元中 `#include CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_HEADER`。总开关已启用但未选择自定义 Provider 时，通用引擎编入内建 Provider。入口采用头文件而非任意 CMake 脚本，以保持构建依赖可追踪，并允许该头文件继续包含生成的帧 `.inc` 文件。

`CUSTOM_ANIMATION_PROVIDER` 自动选择总开关 `ANIMATION_EXTENSION`。总开关默认关闭；关闭分支由 CMake 仅编译原 `bongo_cat.c` 与 `bongo_cat_images.c`，`animation.c`、`animation_provider.c` 及其 registry 不参与编译。无 NEXT DT 实例时 behavior 定义亦由预处理清空，故默认二进制不为扩展付费。

### 构建生成与缓存

generated-provider 模式在 CMake 配置阶段调用用户指定生成器。Cornix 生成器对生成脚本、缓存脚本、位图 manifest 与全部源 BMP 做 SHA-256；缓存键未变且输出存在时不改写 Provider。失配时在临时目录生成，成功后原子替换 `.build/_graphs/kof96/kof96_provider.h`、manifest 与缓存键。各目标 `--pristine` 仅清理自身目录，不删除 `.build/_graphs`，故缓存可跨重复构建复用。源码树不再保存最终 KOF96 Provider 大头文件。

### 最小用户接口

外部头文件只须包含公开 ABI，并依次调用三类宏：

```c
ZMK_DONGLE_ANIMATION_ACTION_DEFINE(kyo_idle, kyo_idle_frames, 800);
ZMK_DONGLE_ANIMATION_PACK_WPM4_DEFINE(kyo, "Kyo", kyo_idle, kyo_slow, kyo_mid, kyo_fast,
                                      5, 30, 70);
ZMK_DONGLE_ANIMATION_REGISTRY_DEFINE(64, 64, kyo);
```

`ACTION_DEFINE` 自动使用 `ARRAY_SIZE`；常见 idle/slow/mid/fast 用 `PACK_WPM4_DEFINE`，任意动作数方使用底层 `PACK_DEFINE`。用户无需增加 CMake、链接段、注册函数或手写帧数；大帧数据可置于同目录 `.inc`，由入口头文件包含。Provider 头仅由模块单一 `.c` 包含一次，避免重复定义与重复编译。

### 只读数据 ABI

公开 ABI 包含：

- registry：ABI 版本、统一画布尺寸及动画包数组；
- pack：稳定名称、动作数组、升序 WPM band 数组；
- action：稳定名称、LVGL 图像描述符数组、帧数及总时长；
- band：最低 WPM 与动作索引。

所有 pack 共用 registry 画布，避免换包时因对象尺寸变化抖动。常规 action 宏以 `ARRAY_SIZE(frames)` 生成帧数；生成器或非常规指针表可使用显式 count 宏。两者皆静态断言 `1..127`，以满足 LVGL 9 `pic_count` 限制。初始化时再校验空指针、索引、升序阈值、画布与时长。

### 播放与切换

WPM band 顺序即动作速度等级：升至更高 band 立即抢占；降至较低 band 等当前动作完成。NEXT 沿用现有 atomic 请求计数，每个动作边界最多消费一个请求；切包后依当前 WPM 选择新包动作。唤醒轮换为可选 Kconfig，仅增加一个 NEXT 请求。

首次播放前以 `k_cycle_get_32() % pack_count` 选择 pack。其后 NEXT 只计算 `(current + 1) % pack_count`，顺序稳定且不再读取随机源；单包时索引保持零。不维护历史或额外策略状态。显示初始化不得调用 `sys_rand32_get()`：其 Xoshiro 首次播种可能同步等待 nRF entropy，展示随机不应阻塞启动路径。

### Keymap behavior

新增零参数中央 behavior `zmk,behavior-dongle-animation-next`。旧 `zmk,behavior-fighter-next` 暂作同一 NEXT 请求的兼容适配器。

### 迁移

KOF96 帧及 registry 移出模块至 `config/animations/kof96/`；生成器输出 Provider ABI，而非模块私有 `fighter_images.h`。模块恢复内建默认动画，Cornix 以 Provider Kconfig 选择 KOF96；Velvet 可分别验默认与外部 Provider。

## Risks / Trade-offs

- Provider 为编译期 C 数据，配置错误会导致构建失败；以 ABI 版本、静态断言及清晰 CMake/Kconfig 错误收敛。
- 外部资产仍直接占用 Flash；保留 define 裁剪与链接后容量门槛。
- 单入口头文件不自动搜集任意 `.c`；生成器须输出可包含的 `.inc`，换取可重复且无 GLOB 的构建。
- 宏接口覆盖常见四档动作；非常规状态机仍须使用底层 action/band 数据结构。
- atomic 请求计数理论上可溢出，但人工键击范围内远低于该界；不为此引入队列。
- 简单取模存在可忽略偏差，展示用途可接受，换取无历史、无策略及常数级状态。

## Migration Plan

1. 先引入 ABI、内建 Provider 与通用 behavior，保持默认显示不变。
2. 将现有 KOF96 表转换为外部 Provider，Cornix 改用 Provider 参数。
3. 将键位改为通用控制，保留 `fighter_next` 兼容适配器。
4. 分别构建默认 Provider 与 KOF96 Provider，并复核容量、DTS 与硬件切换。
