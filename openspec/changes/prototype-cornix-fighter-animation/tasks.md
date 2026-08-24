## 1. Asset pipeline
- [x] 1.1 选择 Kyo 测试动作并计算统一原点边界
- [x] 1.2 生成 `64×64` LVGL `I1` 图像与预览图
- [x] 1.3 记录帧清单、二值化策略与资源大小

## 2. Temporary display integration
- [x] 2.1 临改 Bongo Cat 图像与 WPM 动画表为 Kyo 测试资源
- [x] 2.2 重排状态部件至左侧，并确保右侧 `64×64` 无侵入
- [x] 2.3 保留透明背景及固定画布，避免帧间抖动

## 3. Verification
- [x] 3.1 构建 `cornix_dongle`
- [x] 3.2 检查最终 DTS、`.config`、Flash/RAM 与图像段大小
- [x] 3.3 在 `graphs/` 写入测试结论、复现命令与长期迁移建议

## 4. Hardware feedback iteration
- [x] 4.1 按档位放大 Kyo，改善人物清晰度
- [x] 4.2 将 fast 动画改为完整鬼烧，并延长至 1400 ms
- [x] 4.3 重建 `cornix_dongle`，复核资源差异并更新当前目录结论

## 5. Scale and transition iteration
- [x] 5.1 将四档统一为 1.5 倍并允许画布裁切
- [x] 5.2 实现升速立即抢占、降速等待整套动作结束
- [x] 5.3 重建并更新预览、补丁、资源证据与结论

## 6. Battery layout iteration
- [x] 6.1 将两侧电池移回右上并改成单行双槽
- [x] 6.2 重建并更新补丁、资源证据与结论

## 7. Wake and manual fighter rotation
- [x] 7.1 扩展生成器以生成全部 20 个角色并全局去重 I1 帧
- [x] 7.2 生成角色动画表，接入熄屏唤醒换角
- [x] 7.3 在 Debug 层空位加入手动换角 behavior
- [x] 7.4 保证换角等待当前动作结束，并保持最新 WPM 档
- [x] 7.5 重建并记录全角色 Flash/RAM、补丁与复用结论

## 8. Minimal rollback
- [x] 8.1 回退为单一 Kyo 与 20 个逻辑帧
- [x] 8.2 移除唤醒换角、Debug behavior、keymap binding 与全目标 CMake 注册
- [x] 8.3 使用 Zephyr SDK 0.16.9/Picolibc pristine 构建
- [x] 8.4 更新资源证据、补丁与当前目录结论

## 9. Three-fighter step test
- [x] 9.1 生成 Kyo、Daimon、Terry 三人资源并全局去重
- [x] 9.2 恢复唤醒与 Debug 手动换角
- [x] 9.3 使用 Zephyr SDK/Picolibc pristine 构建 dongle、左片与右片
- [x] 9.4 更新容量、UF2 范围、补丁与复用结论

## 10. Full-roster step test
- [x] 10.1 生成全部 20 个角色并全局去重
- [x] 10.2 使用已验证工具链构建 dongle
- [x] 10.3 核 Flash 至少剩余 100 KiB，UF2 不触及 storage/bootloader
- [x] 10.4 更新全阵容证据、补丁与复用结论

## 11. Define-gated ten-fighter test
- [x] 11.1 为 20 个角色生成 `FIGHTER_ENABLE_*` define，默认启用 10 人
- [x] 11.2 改为角色内去重，确保关闭角色可由预处理完全裁剪
- [x] 11.3 增加 LVGL int8_t 帧数静态断言与运行时守门
- [x] 11.4 构建并核 ELF 角色数、Flash/RAM 与 UF2 地址范围

## 12. Enable all twenty fighters
- [x] 12.1 将 20 个 `FIGHTER_ENABLE_*` 默认值全部设为 1
- [x] 12.2 构建并核 ELF 角色数、Flash/RAM 与 UF2 地址范围
- [x] 12.3 若低于容量门槛，仅优化资源复用，不改运行逻辑
- [x] 12.4 更新固件散列、补丁与结论

## 13. Fifteen-fighter reduction
- [x] 13.1 关闭 Leona、Iori、Chizuru、Boss Kagura、Mr. Karate define
- [x] 13.2 构建并核 ELF 角色数为 15
- [x] 13.3 核 Flash/RAM 与 UF2 地址范围
- [x] 13.4 更新固件散列、补丁与结论

## 14. Edge filtering
- [x] 14.1 将 ordered dithering 改为 2/3 前景二值阈值
- [x] 14.2 重生成 15 人预览并检查动态边缘所用像素模式
- [x] 14.3 构建并更新固件散列、容量与结论

## 15. Black-background hair detail
- [x] 15.1 为色阶 1 增加八邻域强前景连接过滤
- [x] 15.2 重生成 15 人预览并抽查头发与孤点
- [x] 15.3 构建并更新固件散列、容量与结论

## 16. Weak-threshold rollback
- [x] 16.1 移除色阶 1 邻域保留，回退稳定二值阈值
- [x] 16.2 保持 15 人 define 不变并重生成资源
- [x] 16.3 构建并更新固件散列、容量与结论

## 17. Restore original rendering
- [x] 17.1 恢复最初 2×2 ordered dithering
- [x] 17.2 保持 15 人 define、动作长度与换角逻辑不变
- [x] 17.3 构建并更新固件散列、补丁与结论

## 18. Dongle bootloader binding
- [x] 18.1 增加具名 dongle bootloader macro
- [x] 18.2 将其绑定至 Cornix Debug 层空位
- [x] 18.3 构建 `cornix_dongle` 并核最终 keymap DTS

## 19. Kyo action refinement
- [x] 19.1 将待机改为 `win_b`，三档动作改为荒咬、鬼烧、大蛇薙
- [x] 19.2 重生成 KOF96 Provider，并核四个新动作映射与时长
- [x] 19.3 构建 `cornix_dongle` 并更新容量、UF2 与散列证据

## 20. Kyo black-screen safety reduction
- [x] 20.1 保留四个新动作，将 Kyo 采样限制为 4/8/4/4 帧
- [x] 20.2 保持动作原总时长并将 Kyo 总帧恢复至已验证的 20 帧预算
- [x] 20.3 重建并核十五 pack、Flash/RAM、UF2 地址与散列

## 21. Non-blocking startup selection
- [x] 21.1 移除动画初始化与 NEXT 路径中的 `sys_rand32_get()`
- [x] 21.2 启动改用非阻塞 `k_cycle_get_32()`，NEXT 改为顺序步进
- [x] 21.3 重建并复核画布、十五 pack、容量与固件散列

## 22. Unique-frame budget guard
- [x] 22.1 将 Kyo 采样收为 4/4/3/3，令唯一帧回到已验证上限
- [x] 22.2 生成器增加 301 unique / 156520 B 硬预算，超限立即失败
- [x] 22.3 重建并确认固件不大于已验证十五人版本

## 23. Krauser-to-Kyo frame reallocation
- [x] 23.1 将 Krauser mid 从十帧投技改为七帧 `leg_tomahawk_l`
- [x] 23.2 将 Kyo 配额改为 4/5/6/8，并完整保留八帧大蛇薙
- [x] 23.3 确认仅初始人物随机、NEXT 顺序轮换及 305 unique 硬预算后构建

## 24. Roll back to 301 unique with Naraku Otoshi
- [x] 24.1 将 Kyo slow 从 `walk_f` 改为奈落落 `attack_a`
- [x] 24.2 将 Krauser mid 收至3帧，把四张 unique 分给 Kyo 鬼烧
- [x] 24.3 Kyo 配额定为 4/4/6/8，硬预算恢复为 301 unique / 156520 B 并重建

## 25. Compiled-frame duration
- [x] 25.1 动作时长改为输出帧数乘每帧时长，移除采样后的长时间停帧
- [x] 25.2 核 Andy idle 从 25000 ms 降至 4000 ms
- [x] 25.3 重生成并构建，确认301 unique、十五 pack 与容量不变

## 26. Kyo crouching heavy kick
- [x] 26.1 将 Kyo slow 从奈落落改为下重腿 `kick_ch`
- [x] 26.2 保持 slow 输出4帧与301 unique硬预算
- [x] 26.3 由构建缓存重生成 Provider 并构建验证
