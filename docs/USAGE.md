# Fighter Theme 使用说明

`zmk-dongle-fighter-theme` 仅提供 KOF96 人物位图、动作计划与构建期 Provider
生成器；动画播放器、人物／HUD／dongle 分层、飞行道具、血条、电池及集气条均由
`zmk-dongle-display` 提供。因此，二者须成对使用。

## 必须使用特殊版 Dongle Display

本模块依赖 `hitsmaxft/zmk-dongle-display` 的 `custom_anima` 特殊分支及其
Provider ABI 9，不兼容原上游或该仓库的普通 `main` 分支。为使构建可复现，推荐在
West manifest 中锁定已经验证的提交。下列历史 revision 尚早于本工作树的 ABI v9
双对象改动；在 display 与 theme 新提交发布前，应直接使用当前父工作区中的两个 module，
不可仅凭该 revision 宣称具备 ABI v9：

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
包含 ABI 9：

```sh
git -C zmodules/zmk-dongle-display rev-parse HEAD
rg "ZMK_DONGLE_ANIMATION_PROVIDER_ABI_VERSION 9" \
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

cache generator 对 `default`、`mini` 等缩减 profile 仅输出实际启用人物的 C
资产与 manifest，不再先生成二十人物的大头文件后交由预处理器丢弃。此优化只降低
生成时间、头文件大小与编译峰值内存，不改变启用人物的帧、时序或最终图片字节；
`twenty` 仍保留完整二十人物容量路径。

## 显示性能选项

Fighter Theme 只提供 Provider；OLED 总线由消费端 shield 配置。Cornix 当前已知可
正常持续刷新的基线为 TWI／100kHz：

```dts
&i2c0 {
    compatible = "nordic,nrf-twi";
};
```

曾同时改为 `nordic,nrf-twim` 与 400kHz：构建及初始画面皆成功，然实屏持续渲染冻结；
键盘输入及按键唤醒屏幕仍正常，连续二十秒 CDC 日志亦未见 NACK、timeout 或 bus
recovery。故只能判定“TWIM／400kHz 组合失败”，不能单独归因于 DMA 或总线频率；默认
已退回 TWI／100kHz。实屏复测确认该救援版正常启动、按键与唤醒正常，但动画撕裂与
此前相同，故 100kHz 稳定而带宽不足。不得把 TWIM／400kHz 失败组合列为推荐配置。

后续保持 `nordic,nrf-twi`，仅增加 `clock-frequency = <I2C_BITRATE_FAST>`。实屏确认
此 TWI／400kHz 版本正常启动、持续刷新且不再撕裂；随后两路 CDC 各采样十秒，未见
I²C error、NACK、timeout 或 bus recovery。故 Cornix 推荐配置改为 TWI／400kHz，
不再试无必要且已有组合失败证据的 TWIM。

该版本最终仍为 `CONFIG_I2C_NRFX_TWI=y`，DTS 频率为 400000，VDB 仍为 100、display
tick 仍为 10ms；故无撕裂结果可归因于单一频率变化，而非 VDB、调度或帧表。

LVGL 单色输出同时持有行式 render buffer 与 SH1106 竖向 conversion buffer。
128×64 I1 下可按目标选 `CONFIG_LV_Z_VDB_SIZE`：

| 取值 | 两缓冲合计 | 定位 | 状态 |
|---:|---:|---|---|
| `100` | 约 2064B | 刷新延迟优先，Cornix 当前默认 | 已构建 |
| `25` | 约 528B | RAM／回调次数平衡，约省 1536B | 可选，待实屏 |
| `13` | 约 282B | 单页级最小缓冲，约省 1782B | 实验，非默认 |

减小 VDB 不会减少同一脏区须写入 OLED 的总字节，且会增加 LVGL 分段回调；故其用途
是省 RAM，不是提帧率。当前显示线程每 10ms 调用一次 LVGL，而刷新周期为 33ms；若
实测 CPU 空闲唤醒偏高，可试 `CONFIG_ZMK_DISPLAY_TICK_PERIOD_MS=16`，但须复测按键状态
显示延迟。不可仅把 tick 改成 33ms，因动画 timer 与刷新 timer 同相时可能增加整帧等待。

播放器现已采用绝对 deadline 合帧：首个须等绘制的步骤仍由 `LV_EVENT_DRAW_POST` 确定
动作 epoch；其后每个 deadline 从前一 deadline 累加。若同步 SH1106 flush 令显示队列
错过一个或多个 33／34ms 区间，下一 timer callback 直接选择当前墙钟所在步骤，不再
逐帧补画过期状态。此逻辑复用原 frame timer，只增加一个 64 位 deadline，不增加线程、
对象、canvas 或 heap allocation。Cornix 构建较未合帧版增 304B Flash、8B RAM。

ABI v9 将复合招式改为双常驻对象：人物 image 保留最近人物帧，永不因道具可见而消失；
道具 image 独立显／隐、换图及移动。生成器从素材 manifest 的 `sources` 自动生成逐步
`frame_roles[]`；人物步骤更新人物并隐藏道具，道具步骤只更新覆盖层。30Hz 跳帧会先
归并所有过期 role，再向 LVGL 提交一次最终双轨状态，故不会因跳帧丢失人物姿态。

此方案不新增 timer、canvas、framebuffer 或 bitmap RAM。Cornix 相较单对象 deadline
版本增加 1224B Flash、32B 静态 RAM；第二 `lv_image_t` 基体由既有 8KB LVGL heap
分配 92B，另有少量 allocator／style 元数据。未含 role 的旧 Provider 不创建道具对象。

Cornix 首次双对象实屏在 8KB LVGL heap 下出现黑屏而 ZMK／USB 仍运行，故诊断配置将
`CONFIG_LV_Z_MEM_POOL_SIZE` 提至 9216，并在完成建屏后打印 heap total／free／max_used／
used／fragmentation。此版尚待实屏，未验证前不可把 heap 耗尽写作最终根因；若恢复，
应依日志余量回收至仍有安全裕量的最小值，而非继续扩大。

紧裁剪脏区仍非可用配置：若未来其他屏幕仍有转换或写屏压力，方考虑避免人物／道具以
64×64 透明画布在远距离位置间切换。

紧裁剪若允许逐帧不同尺寸，仍须同步扩充坐标锚点与运行时校验。离线预合成 128×64
整帧会扩大脏区并重复人物 bitmap，不列为性能选项。

性能验收须依次记录：最终 DTS／Kconfig、Flash／RAM、I²C NACK 或 bus recovery 日志、
Terry 与 Mr. Karate 道具段实测帧间隔、动作总时长及显示线程 CPU 占用。未具硬件证据时，
文档只可写“已构建”，不可写“已达 30fps”。

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
