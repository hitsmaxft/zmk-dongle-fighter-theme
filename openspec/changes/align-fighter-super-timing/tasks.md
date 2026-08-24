## 1. Source clock and generator

- [x] 1.1 固定反汇编 revision，统一 `gb-vblank` schema v2
- [x] 1.2 实现累计 59.7275Hz tick 到毫秒换算
- [x] 1.3 新增 `--source-ticks-per-display-frame`（1..16，默认 2）并保持总时长
- [x] 1.4 输出源 ticks、采样槽、最终播放步与合并槽报告
- [x] 1.5 合并同图同位连续保持，不越过移动、return 或收招边界

## 2. ROM migration

- [x] 2.1 为默认生产 roster 的 mid 动作加入 ROM 时间证据
- [x] 2.2 保留已迁移 fast 的起手、主体、腾空与收招证据
- [x] 2.3 补 Athena Shining Crystal Bit projectile 映射与时间线
- [x] 2.4 补 Geese Raging Storm 光柱映射、寿命及动态 mapping speed
- [x] 2.5 复原 Mr Karate D3 后跳速度／重力及 Haoh D 收招

## 3. Resource optimization

- [x] 3.1 同角色跨 mid/fast 以最终 I1 数据共享位图符号
- [x] 3.2 证明生成资源皆为 Flash `static const` 且无新运行时画布
- [x] 3.3 记录暂缓 atlas 的 SRAM／拷贝理由
- [x] 3.4 量测跨角色相同 I1 payload：生产十四角 0B，故不增公共 Flash gate

## 4. Acceptance

- [x] 4.1 宿主测试覆盖采样、时长恒定、去重、Athena、Geese 与 Mr Karate
- [ ] 4.2 生成 Athena、Geese、Mr Karate 同源 GIF 并人工复核
- [x] 4.3 构建 Cornix dongle 与 EvalKit，记录 manifest、Flash 与 SRAM
- [ ] 4.4 在相应硬件上另验实际 30Hz 观感
