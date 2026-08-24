# Fighter Provider 模块边界设计

## Ownership

| Owner | Content |
|---|---|
| zmk-dongle-fighter-theme | assets, plan, ROM evidence, generators, previews, tests, OpenSpec |
| zmk-dongle-display | LVGL player, HUD, timer, charge/demo state, Provider ABI |
| zmk-config | board profile, cache output path, pinned West revision, local ROM |

模块布局为 `assets/`、`data/`、`scripts/`、`tests/`、`docs/`、`openspec/` 及最小
`zephyr/module.yml`。模块 CMake 不编译运行时代码，故仅因加入 West workspace 不增 Flash
或 SRAM；只有消费配置启用 generated custom provider 时，display 模块才调用脚本。

## ROM boundary

模块 `.gitignore` 排除 `*.gb`/`*.gbc`。角色 extractor 强制由命令行收 ROM，并核对已知
SHA-1。README 记录 zmk-config 原路径 `graphs/ntkof96.gb`；manifest 仅留校验摘要与逻辑
来源，不复制 ROM bytes。

## Consumer path

zmk-dongle-display 既有安全约束要求 generator/cache/header 均相对 `ZMK_CONFIG`。故主仓
配置使用 `../zmodules/zmk-dongle-fighter-theme/scripts/...`，cache 仍在 `../.build`。
此法无需修改播放器，亦不把模块绝对路径写入可复现配置。

## Migration and rollback

先复制并在新仓测试，再改消费路径与 West manifest，最后删主仓重复代码／素材；ROM 永不
移动。若消费构建失败，可暂时把 generator 路径指回主仓历史版本，不影响显示 ABI。
