# Fighter Theme 使用说明

`zmk-dongle-fighter-theme` 仅提供 KOF96 人物位图、动作计划与构建期 Provider
生成器；动画播放器、人物／HUD／dongle 分层、飞行道具、血条、电池及集气条均由
`zmk-dongle-display` 提供。因此，二者须成对使用。

## 必须使用特殊版 Dongle Display

本模块依赖 `hitsmaxft/zmk-dongle-display` 的 `custom_anima` 特殊分支及其
Provider ABI 8，不兼容原上游或该仓库的普通 `main` 分支。为使构建可复现，推荐在
West manifest 中锁定已经验证的提交：

```yaml
manifest:
  projects:
    - name: zmk-dongle-display
      url: https://github.com/hitsmaxft/zmk-dongle-display
      revision: 8ccc86daf044c03d98a818e9c112126973b26da8
      path: zmodules/zmk-dongle-display
    - name: zmk-dongle-fighter-theme
      url: https://github.com/hitsmaxft/zmk-dongle-fighter-theme
      revision: main
      path: zmodules/zmk-dongle-fighter-theme
```

若使用 `config/deps.yml` 导入依赖，亦须令 `zmk-dongle-display` 指向
`custom_anima`，不可误用普通 `main`。更新依赖后，应确认实际检出的 display 提交
包含 ABI 8：

```sh
git -C zmodules/zmk-dongle-display rev-parse HEAD
rg "ZMK_DONGLE_ANIMATION_PROVIDER_ABI_VERSION 8" \
  zmodules/zmk-dongle-display/include/zmk/dongle_display/animation.h
```

构建目标仍须启用 `dongle_display` shield。保留原有 dongle adapter／键盘 shield，
并把 `dongle_display` 加在同一目标，例如：

```yaml
include:
  - board: nice_nano//zmk
    shield: <你的_dongle_shield> dongle_display
```

此处 `<你的_dongle_shield>` 仅为占位符，应替换为项目中实际的 dongle shield 名称。

## 推荐配置

在 dongle 构建目标的 `.conf` 中加入：

```conf
CONFIG_ZMK_DONGLE_DISPLAY_CUSTOM_ANIMATION_PROVIDER=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATED=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATOR="../zmodules/zmk-dongle-fighter-theme/scripts/cache_cornix_fighter_provider.py"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATOR_ARGS="--profile default --source-ticks-per-display-frame 2"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_CACHE_DIR="../.build/_graphs/kof96-fighter-default"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_HEADER="kof96_provider.h"

# 推荐用于正常使用；demo 仅供无人操作时循环展示。
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_DEMO_MODE=n
```

所有生成器与缓存路径皆相对 `ZMK_CONFIG`。`--source-ticks-per-display-frame 2`
把游戏约 60 tick/s 的逻辑时序量化为约 30 次/s 的 OLED 更新，同时保留动作总时长。
除非正在做容量或抽帧实验，不建议加入 `--allow-source-frame-drop`。

### 默认人物

推荐保留 `--profile default`，不要为日常固件改用 `eighteen` 或 `twenty`。现行默认
编译 13 人：

- Kyo、Daimon、Terry、Andy、Ryo、Robert
- Athena、Mai、Orochi Leona
- Geese、Krauser、Goenitz、Orochi Iori

此名单是当前在动画完整度与 Flash 占用之间的默认取舍。`twenty` 适合容量测试，
不作为稳定运行的推荐配置。

## 选择播放模式

普通模式与集气模式是 Kconfig `choice`，只能选择一个。首次使用推荐普通模式；希望
fast 必杀不能被 WPM 直接触发时，再选集气模式。两种模式均建议关闭 demo。

### 普通模式（默认，推荐）

```conf
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_WPM_MODE=y
# CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_CHARGE_MODE is not set
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_DEMO_MODE=n
```

WPM 直接选择 idle、slow、mid、fast 四档，达到 fast 阈值即可播放 fast 动作。此模式
行为直接、额外状态最少，适合先验证屏幕、人物及动作是否正常，也适合日常使用。

### 集气模式（Charge）

```conf
# CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_WPM_MODE is not set
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_CHARGE_MODE=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_DEMO_MODE=n
```

WPM 最多只能请求到 mid；每完整播放一次 slow 增加 5 点气，每完整播放一次 mid
增加 10 点气。气槽达到 100 后播放一次 fast，随后归零。该模式会启用 Fighter
集气条，适合希望 fast 具有蓄力条件的使用方式。

`CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_DEMO_MODE=y` 会忽略正常 WPM 选择并自动换档、
换人；在集气 demo 中，每次 mid 特意增加 50 点气，以便快速演示。因此 demo 的集气
速度不代表正常使用行为，正式固件应保持 `n`。

## 构建检查

构建日志应出现 Provider cache hit 或 cache miss，而非退回 Bongo Cat。构建后可检查
最终配置：

```sh
rg "CONFIG_ZMK_DONGLE_DISPLAY_(CUSTOM_ANIMATION_PROVIDER|ANIMATION_PROVIDER_GENERATED|ANIMATION_WPM_MODE|ANIMATION_CHARGE_MODE|ANIMATION_DEMO_MODE)" \
  .build/<构建目标>/zephyr/.config
```

至少应确认：

- `CUSTOM_ANIMATION_PROVIDER=y` 且 `ANIMATION_PROVIDER_GENERATED=y`；
- `WPM_MODE=y` 或 `CHARGE_MODE=y`，但不可同时启用；
- 正式固件中 `ANIMATION_DEMO_MODE` 未启用；
- Provider 生成参数为 `--profile default --source-ticks-per-display-frame 2`。

若需限制已链接固件的总 ROM 大小，可另设
`CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_ROM_MAX_BYTES`。其限制的是最终固件 ROM 总量，
而非单独的动画图片字节；默认值 `0` 表示关闭该可选守门。
