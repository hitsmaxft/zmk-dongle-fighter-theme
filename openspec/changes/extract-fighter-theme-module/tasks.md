## 1. Repository extraction

- [x] 1.1 克隆私有远端并保留既有 main 历史
- [x] 1.2 建立 Zephyr module、Kconfig、West 与 ignore 元数据
- [x] 1.3 复制脚本、位图、播放计划、文档、测试与 Fighter OpenSpec
- [x] 1.4 改脚本与测试为模块相对路径
- [x] 1.5 排除 ROM、缓存与频繁变化的 preview

## 2. Consumer wiring

- [x] 2.1 在 zmk-config 的 West/deps manifest 加入固定模块 revision
- [x] 2.2 将 Cornix、dongle demo、EvalKit generator 路径改指模块
- [x] 2.3 删除 zmk-config 中重复 Provider 代码、资产、测试与 Fighter OpenSpec
- [x] 2.4 验证 `graphs/ntkof96.gb` 及本地 ROM 变体均留原位

## 3. Acceptance

- [x] 3.1 新模块独立宿主测试通过
- [x] 3.2 Cornix 与 EvalKit 由模块路径完成 Provider 生成及固件构建
- [ ] 3.3 模块提交并推送，主仓 manifest 固定所推 SHA
