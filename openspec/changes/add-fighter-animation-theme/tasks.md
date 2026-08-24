## 1. Contract and executor

- [ ] 1.1 保存远端方案并建立本地实现分支
- [x] 1.2 实现 ABI v3 基础契约、兼容宏及非法 layout 校验
- [ ] 1.3 扩充纯数学函数与主机测试
- [ ] 1.4 以单 timer 重写帧、周期、位移及 pending 状态机
- [x] 1.5 令 Fighter mid/fast 首末帧绘制完成后各停 500ms、中间帧各停 200ms，并令演示 timer 依动作总长切换

## 2. Theme and layers

- [ ] 2.1 增加 50x26 内置 Fighter 资源及四级 action
- [ ] 2.2 注册 Bongo 与 Fighter pack，并保持自定义 Provider 完全接管
- [ ] 2.3 将状态屏拆为 normal、animation、battle HUD 三层
- [ ] 2.4 实现左右手电池数字框、镜像血条及 source 映射
- [x] 2.5 增加可选的 slow/mid/fast 完整动作轮播演示，并在 EvalKit 启用十八人物循环
- [x] 2.6 从演示 roster 移除 Leona 与 Mr Big，并令 mid/fast 缩放保全被选帧内容而允许宽于 64px
- [x] 2.7 回滚时域抖动背景，令战斗画面沿用 LVGL 纯黑底且不分配背景 canvas
- [x] 2.8 增加复用 Bongo Cat 位图的内置 Fighter Theme demo，并停止为该 demo 编译独立 Fighter 图片
- [x] 2.9 精简生产 roster，不编译 Chizuru、Boss Kagura、Mature、普通 Iori、普通 Leona 与 Mr Big，同时保留素材、配置及全量测试 profile
- [x] 2.10 增加 WPM／集气／演示三选一播放模式，并实现完整 slow `+5`、mid `+10`、满气唯一触发 fast 与启动归零
- [x] 2.11 以单对象直绘右侧半长体力槽样式的底部集气 HUD，不显示数字或分配 canvas
- [x] 2.12 令演示可叠加集气：站立、slow 两次、mid 两次、满气待机保持 HUD、fast，继而换人

## 3. Custom super-move playback

- [x] 3.1 核对原版 ROM 动作表与 move code，确认 Kyo 蓄力回跳及 Mai 落地前循环由输入／物理状态驱动
- [x] 3.2 定义以原始动作帧索引表示的有限播放计划及严格校验
- [x] 3.3 令生成器去重转换被引用图片，并将重复、跳转和乱序展开为既有 frame pointer 表
- [x] 3.4 令时长、manifest 与缓存摘要采用展开后的播放步骤，并分别报告源帧、唯一图片与播放步骤数
- [x] 3.5 为 Kyo fast 与 Mai fast 加入有限循环示例，不移植输入／物理状态机
- [x] 3.6 增加顺序、重复、越界、127 步上限、默认兼容及 bitmap 不重复生成测试
- [x] 3.7 增加可指定角色、档位及播放顺序的无依赖测试 GIF 生成器
- [x] 3.8 将 Provider ABI 升至 v4，以可空只读表表达逐步 fixed／move 且保持旧宏默认逐帧移动
- [x] 3.9 扩展播放计划、生成器、manifest 与 GIF 预览器，严格校验逐步移动表
- [x] 3.10 为 Kyo MAX fast 固定蓄力步骤、仅移动释放步骤，并增加数学、生成器与 GIF 测试
- [x] 3.11 依逆向 move code 修正 Mai fast 的静止准备、前进及落地循环
- [x] 3.12 为单次回程分界升级 ABI v5，并依原作八轮连斩与后撤跳修正 Orochi Leona fast
- [x] 3.13 依成功命中分支展开 Iori Super 八稚女的八步奔跑及完整 2..19 原地连击，排除格挡专用源帧 20
- [x] 3.14 升级 ABI v6，以一字节逐帧 X 偏移支持单对象人物／飞行道具交替时间线
- [x] 3.15 从 ROM 公共道具档抽取八神火焰及霸王翔吼拳两组低帧图片，并纳入可复现生成脚本
- [x] 3.16 令八神终爆闪烁三轮；令空手道先生 fast 串联龙虎乱舞、暂烈拳、后跳及交替道具收招
- [x] 3.17 依 ROM move code 展开 Orochi Iori、大门与 Athena 的确定循环，并为 Andy、Ryo、Robert 的命中前前突补足重复帧与选择性横移
- [x] 3.18 为第二批 fast 序列表增加展开顺序、移动区间、时长与 bitmap 去重复用回归测试
- [x] 3.19 改用 Terry 隐藏 MAX，并以两种 ROM 地涌帧及不相邻落点交替重现其覆盖式随机连发
- [x] 3.20 将普通八神 fast 改为 D／MAX 八稚女，修正突进位移范围及终爆插入点
- [x] 3.21 令 Ryo／Robert 龙虎乱舞成功段转入各自重升龙，以空中两姿态往复三轮后下落着地，并复用位图 descriptor
- [x] 3.22 令 Goenitz fast 以单个高速突进帧至中央，复用 mid 重投并停于起跳前举起姿态，以“风／举起”交替两轮后续完投技收招
- [x] 3.23 升级 ABI v7，以可选逐步毫秒表表达飞行道具显隐、覆盖寿命及收招时长，并保持旧 cadence 宏兼容
- [x] 3.24 依原作映射顺序及 30fps OLED 时基校正霸王翔吼拳与 Terry 地涌时间线，并令 GIF 与固件共用同一时长表

## 4. Verification

- [x] 4.1 主机测试位移端点、单调性与精确周期和
- [ ] 4.2 以项目本地 Nix 构建未启用扩展、内置双 pack EvalKit 及外部 Provider Cornix
- [ ] 4.3 检查最终配置、Flash/RAM、唯一图片／播放步骤数、镜像范围及 SHA-256
- [ ] 4.4 租用并识别 EvalKit，刷写后分列 SWD 启动与实屏证据
- [ ] 4.5 更新 README 与实现审查记录
