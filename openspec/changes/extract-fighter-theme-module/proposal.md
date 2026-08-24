# Change: 将 KOF96 Fighter Provider 抽为独立 ZMK 模块

## Why

Provider 脚本、约七千张源位图、播放计划、测试与 OpenSpec 原散置于 zmk-config；实际
播放器则在 zmk-dongle-display。此耦合令动画迭代必须提交主配置仓，且难以由其他 ZMK
配置复用。商业 ROM 又不可随模块发布，须明确外部输入边界。

## What Changes

- 新建 `zmk-dongle-fighter-theme` Zephyr/ZMK 模块仓库。
- 移入生成器、缓存器、ROM 析取／复合脚本、播放计划、角色／道具位图、文档、测试及
  Fighter 相关 OpenSpec 历史。
- zmk-config 仅保留 ROM 于原 `graphs/ntkof96.gb` 路径及消费端配置；West manifest 固定
  新模块 revision。
- 消费端 generator 路径改指模块；构建产物仍写主仓 `.build`，不污染模块源码。

## Impact

- Affected specs: `fighter-theme-module`
- Affected repositories: `zmk-dongle-fighter-theme`, `zmk-config`
- No runtime ABI change; zmk-dongle-display remains the player owner
- No ROM is copied or committed to the module
