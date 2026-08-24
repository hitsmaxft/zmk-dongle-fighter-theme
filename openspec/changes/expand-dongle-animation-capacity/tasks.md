## 1. Baseline and compatibility

- [ ] 1.1 记录 ZMK、Zephyr、LVGL、dongle-display 与 Provider 生成器的精确提交
- [ ] 1.2 修复并锁定 LVGL 9 点类型兼容，不以放宽类型错误替代
- [ ] 1.3 建立十五角色回归构建及 ELF/资源基线

## 2. Twenty-character provider and capacity matrix

- [ ] 2.1 令生成器显式支持全部二十角色及可配置资源预算
- [ ] 2.2 生成固定角色数、可变单动作帧数的测试矩阵
- [ ] 2.3 生成固定动作帧数、可变 unique-frame 总量的测试矩阵
- [ ] 2.4 为每个产物记录 manifest、Flash、RAM、最长 action、逻辑帧及 unique-frame 数

## 3. Startup and playback access

- [ ] 3.1 将启动全注册表深度遍历改为顶层浅校验及当前 pack/action 按需校验
- [ ] 3.2 令同一 action 循环仅重启动画，人物/action 改变时方重设 source、duration 与转换日志
- [ ] 3.3 增加坏 registry、坏 pack/action、惰性人物切换及同动作循环的主机测试
- [ ] 3.4 核验优化前后 RAM 不增加，并记录启动校验访问量与运行时重设次数

## 4. EvalKit target and hardware evidence

- [ ] 4.1 增加 `waveshare_nrf52840_ek` 动画 target，并核对其实际显示接线/分辨率
- [ ] 4.2 在刷写前记录 DAPLink/ST-Link、FICR、既有镜像与恢复条件
- [ ] 4.3 以 ST-Link/DAPLink 逐级刷写并记录启动标记、reset reason 与显示首帧
- [ ] 4.4 验证二十角色镜像的启动和至少一次 NEXT 或唤醒轮换
- [ ] 4.5 区分并报告单 action 帧数限制、总资源限制与硬件接线/显示初始化故障

## 5. Verification and documentation

- [ ] 5.1 运行生成器及容量守门的主机测试
- [ ] 5.2 构建十五角色回归、二十角色及 EvalKit 目标
- [ ] 5.3 核验 ELF/UF2 地址范围、SHA-256 与 NVS/设置配置
- [ ] 5.4 将每个硬件 gate 以 build、SWD、显示硬件等独立证据记录
