## 1. Public animation contract
- [x] 1.1 增加版本化 registry/pack/action/band ABI 与定义宏
- [x] 1.2 增加帧数、时长、索引及画布运行时校验
- [x] 1.3 提供内建默认 Provider
- [x] 1.4 提供自动帧数 action 宏及常用四档 pack 便捷宏

## 2. ZMK config integration
- [x] 2.1 增加默认关闭的总开关、自定义 Provider、入口头文件及唤醒轮换 Kconfig
- [x] 2.2 令 Provider 路径相对 `ZMK_CONFIG`，缺失时给出明确构建错误
- [x] 2.3 保证未配置 Provider 的现有用户无需修改即可构建

## 3. Generic playback engine
- [x] 3.1 将播放状态从 fighter 四字段改为 registry/band/action 索引
- [x] 3.2 保留升速抢占、降速完播语义
- [x] 3.3 沿用 atomic 计数，在动作边界处理 NEXT
- [x] 3.4 将唤醒轮换改为可配置通用命令
- [x] 3.5 实现启动随机与 NEXT 顺序步进

## 4. Generic keymap control
- [x] 4.1 增加零参数通用 animation-next behavior 与 binding
- [x] 4.2 保留 fighter-next 兼容适配器
- [x] 4.3 更新 Cornix Debug 键位，并记录 Velvet 可选绑定而不默认启用

## 5. KOF96 provider migration
- [x] 5.1 调整生成器以输出 Provider ABI、静态帧数断言及可包含资产
- [x] 5.2 将 KOF96 Provider 移至 `config/animations/kof96/`
- [x] 5.3 以 Kconfig 参数为 Cornix 选择 KOF96 Provider
- [x] 5.4 从模块移除 fighter 专属表与硬编码角色命名

## 6. Verification and documentation
- [x] 6.1 构建内建 Provider 的 `velvet_central_dongle`
- [x] 6.2 构建外部 KOF96 Provider 的 `cornix_dongle`
- [x] 6.3 核最终 DTS、Provider 选择、Flash/RAM、UF2 地址与 NVS 设置
- [x] 6.4 增加非法帧数、缺失 Provider 负例，并保留索引运行时守门
- [x] 6.5 增加启动随机、NEXT 顺序轮换及单包边界测试
- [x] 6.6 以无额外 CMake 的最小外部头文件作编译验收
- [x] 6.7 验证扩展关闭时仅编译旧 Bongo 路径且 ELF 无通用动画符号
- [x] 6.8 记录 Provider 示例、生成流程、键位用法及兼容迁移

## 7. Build-generated provider cache
- [x] 7.1 增加 generated-provider Kconfig 与 CMake 生成协议
- [x] 7.2 生成器增加无预览构建模式，并实现源内容哈希缓存包装器
- [x] 7.3 将 Cornix 缓存固定于 `.build/_graphs/kof96`
- [x] 7.4 删除源码树最终 KOF96 Provider，验证 cache miss/hit 不改写命中产物
- [x] 7.5 以缓存生成头构建 Cornix，并核固件与直接生成结果一致
