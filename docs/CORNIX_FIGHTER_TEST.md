# Cornix Dongle 十五人物 define 测试结论

> 历史快照：本页保留 301-frame 启动故障调查时的实机与链接证据，不代表当前 roster、
> ROM timing 或构建尺寸。现行时序见 `ROM_ANALYSIS.md`，每次发布须重新生成 manifest 与
> Zephyr Flash/SRAM 报告。

## 当前角色

资源源文件保留 20 个 `FIGHTER_ENABLE_*`，当前默认启用 15 人：Kyo、Daimon、Terry、Andy、Ryo、Robert、Athena、Mai、Orochi Leona、Geese、Krauser、Mr. Big、Mature、Goenitz、Orochi Iori。

关闭普通 Leona、普通 Iori、Chizuru、Boss Kagura、Mr. Karate。ELF 中 `kof96_animation_packs` 为 60 B，即 15 个四字节 pack 指针；换角仅遍历上述角色。

## 动画与长度守门

当前编入 367 个逻辑帧、角色内去重后 301 个唯一帧，净图像 156520 B、描述符约 7224 B。idle 最多 8 帧、fast 最多 12 帧、其余档最多 16 帧；超长动作均匀抽样并保留首尾帧，动作总时长按输出帧数计算。

LVGL AnimImage 的 `pic_count` 为 `int8_t`。Provider 宏对全部动作加入 `_Static_assert(count <= 127)`，运行时再次拒绝 0 或超过 127 的序列。当前最长单动作为 16 帧。

Kyo 当前四档为：待机 `win_b` 胜利动作 4 帧；slow 下重腿 `kick_ch` 由 5 帧采样至 4 帧；mid `oni_yaki_l` 鬼烧由 7 帧采样至 6 帧；fast `ura_orochi_nagi_s` 大蛇薙完整 8 帧。对应总时长为 2000/600/1440/1600 ms。

Krauser mid 已由十帧投技 `kaiser_suplex_l` 改为非投技 `leg_tomahawk_l`，由 7 帧采样至 3 帧，总时长为 720 ms。其释放的四张 unique 图像预算用于提高 Kyo 鬼烧；大蛇薙保留完整 8 帧。

Andy idle 源动作虽有 50 帧，固件仅采样 8 帧；时长现按输出帧计算，由 25000 ms 降至 4000 ms。NEXT 仍等待当前动作结束，但不再需要额外按键抢占，最长 idle 等待为 4 秒。

此前 320 unique 与 305 unique 版本均在实机出现死机，故当前版回滚至已验证的 301 unique/156520 B。生成器按实际唯一位图而非逻辑帧守门，若超限即失败。

所有人物统一放大 1.5 倍。升速立即切档，降速等待动作结束。启动以 cycle counter 取模随机选择人物；显示唤醒或 Debug 层 `&animation_next` 增加 NEXT 请求，当前整套动作结束后仅按 Provider 顺序切至下一人。

画布仍为固定 `64×64`，人物缩放仍为 1.5 倍，本轮未改变动画尺寸。为避免显示初始化阻塞，仅启动随机使用非阻塞 `k_cycle_get_32()`；NEXT 不再读取任何随机源。最终 animation 对象无 `sys_rand` 或 entropy 引用。

最终人物头由构建调用 `scripts/cache_cornix_fighter_provider.py` 生成至消费工作区 `.build/_graphs/.../kof96_provider.h`；源码树不保存最终 Provider。输入内容哈希未变时复用缓存且不改写文件。zmk-dongle-display 仅保留版本化 registry/pack/action/band ABI 与通用播放器；旧 `&fighter_next` 仅作兼容适配器。

通用动画总开关默认关闭。Velvet 验证中仅编译旧 `bongo_cat.c/images`，最终 ELF 不含 `zmk_dongle_animation*` 或通用 NEXT 符号；故未启用时无通用动画二进制开销。

Debug 层第二行第四位新增具名 `&dongle_bootloader`；其仅封装标准 `&bootloader`，由中央 dongle 执行。最终 DTS 已确认该键位引用正确，未修改 ZMK core 或其他 `zmodules/` 源码。

像素转换已恢复最初版本的 2×2 ordered dithering：Game Boy 色阶 0/1/2/3 分别映射为 0%/25%/75%/100% 前景。不使用后续二值阈值或邻域过滤。

## 构建与容量

使用 Zephyr SDK 0.16.9/Picolibc 构建，ZMK core 保持 clean。ELF 的 `text/data/bss` 为 `436408/266068/127628`。

当前 `_flash_used=702484`，代码分区尚余 161772 B；`_image_ram_size=137464`，RAM 尚余 124680 B。UF2 共 2745 块，目标范围 `0x1000..0xAC900`，未触及 storage 或 bootloader。

固件为 `firmware/cornix_dongle.uf2`，UF2 容器大小 1405440 B，SHA-256 为 `c2dda692db622260d76d491e9ce6ab91c08a9432c6362bc2f9842f5e67049c05`。

## 刷写

必须使用已确认 UF2 卷的普通文件复制，勿用 `pico-dfu` raw `dd`。当前结果已通过构建、长度断言、ELF 角色计数、Flash/RAM 与 UF2 地址检查；十五人物启动仍须实机验证。
