# Fighter 分层动画主题设计

远端方案原文保存于 `zmodules/zmk-dongle-display/docs/fighter-animation-theme-plan.md`。本变更依其单 timer 帧状态机、三层屏幕及双侧电池 HUD 实施，并将逐步位移、单次回程、交替道具及逐步时长契约扩为 Provider ABI v7。

## 实施状态（2026-08-23）

此变更之主题、HUD、集气演示、自定义序列、位移／回程、单对象道具时间线及 ABI v7
逐步时长基础设施皆已有代码。运行时会校验逐步时长非零且总和等于 action 总时长，首步
亦从实际绘制完成后计时；生成器与 GIF 共用 `fighter_playback.json` 的顺序、位置及时长。

当前 Iori、Mr Karate、Goenitz 三项 fast 仍以旧 `durations_ms` 近似；Terry 已改用
`timing` 证据结构，由原作 tick 累计生成同一毫秒表、manifest 报告及 GIF。生成器已不再
要求逐步时长与 `x_offsets` 同用，普通 fixed／move／return action 亦有 ABI v7 兼容宏。

逐角精确迁移另由 `align-fighter-super-timing` 管理：须解除时长表仅限显式 X 偏移之限制，
并为起手、主体、命中／循环及最终硬直建立 ROM tick 证据。依该较严口径，当前生产
14 角中 Terry 候选实现已完成静态、测试与构建验收，惟尚待 GIF 人工审核，故正式完成数
仍为 **0/14**；保留但默认禁用角色为 **0/6**。
本变更中未打勾的旧任务不得因代码片段存在而自动视为验收完成，硬件实屏证据亦须与
主机测试、固件构建及 SWD 启动分列。

本次工作树验证结果如下：两项相关 OpenSpec 均通过 strict 校验；播放计划／GIF 共
27 项 Python 测试通过，动画数学 C 测试亦通过；项目本地 Nix 成功构建外部 Provider 的
EvalKit、Cornix 及复用 Bongo 位图的内置 Fighter demo。链接 map 所载资源为：

| 目标 | Provider／模式 | Flash | RAM | UF2 SHA-256 |
|---|---|---:|---:|---|
| `wave-dongle-animation` | 外部 KOF96，14 角，集气＋演示 | 597648 / 1048576 B | 92552 / 262144 B | `c57a1462985ce811954799b1476e656c1019fdb81beb07ddfefe6670328d1425` |
| `cornix_dongle` | 外部 KOF96，14 角，演示 | 729048 / 1048576 B | 139640 / 262144 B | `aff275a63a68b1f841ee00fa2d194c93f8fa8b6fcee92b55affd15bdcf280035` |
| `wave-dongle-fighter-demo` | 内置 Bongo 复用，集气＋演示 | 409628 / 1048576 B | 92552 / 262144 B | `9abfdb56833fa5490d847d7452814ad2a81e88ec61b071ed54a85d324195235a` |

目标名所用 `eighteen` profile 乃历史名；当前实际由 manifest 明列十四角，并排除 Leona、
Iori、Chizuru、Boss Kagura、Mature、Mr Big。Zephyr `rom_report/ram_report` 辅助目标因
本地 Python 缺 `anytree` 未运行，表中数值直接取最终链接 map 的 `_flash_used` 与
`_image_ram_size`。本轮未刷写，故无新增 SWD 启动或实屏节奏证据。

## Decisions

- action 的 `motion`、`flags` 与 `return_step` 使用 `uint8_t`，不将编译器 enum 布局纳入 ABI；ABI v7 保留可空的只读 `movement_steps`、`frame_x_offsets` 与 `frame_durations_ms` 指针，并以 `UINT8_MAX` 表示无回程。
- 每次 timer 回调只推进一个播放步骤；步骤可引用任意已生成图片帧，末步骤完整停留一周期后，方处理 pending NEXT 或降档。
- Fighter mid/fast 以 action 内的 `endpoint_hold_ms=500` 表示首末播放步骤绘制完成后的停留，中间步骤各 200ms；`duration_ms = 1000 + 200 * (frame_count - 2)`，其中 `frame_count` 为展开后的播放步骤数，故重复帧亦计入动作时长。
- 首末帧不调用同步 `lv_refr_now()`；image 收到正常 `LV_EVENT_DRAW_POST` 后方复位并启动 endpoint timer，避免冷启动时强制刷新未完成的 widget 树。
- mid/fast 保留均匀抽帧；每个 action 依所选帧联合边界按高度缩放至 64px 内，宽度不截断且可超过 64px。播放器以 action 实际宽高定位，不以 Provider 最大画布宽度误移窄动作。
- Mai 的 mid 固定选用强版龙炎舞 `ryu_en_bu_h`，不再由通用“接近十帧”规则自动选择。
- 战斗背景沿用 LVGL screen 的纯黑默认背景；animation 与 HUD 根层保持透明，不另建 canvas、tile 或背景帧缓冲。
- 演示切换完全由 action 实际总时长驱动；动作完成即换下一档，不另设最短展示窗，故 slow 不会在末帧额外滞留。
- WPM 升档可立即打断，降档及主题轮换等待当前 action 完成。
- 播放模式由 Kconfig 选择 WPM 直控或集气，自动演示则可独立叠加。集气模式仍以
  WPM 选择 idle／slow／mid，但将所有 WPM fast 请求钳至 mid；slow 完整循环加
  5，mid 完整播放加 10，未完成或被打断的 action 不计气。气值饱和至 100，且
  仅在完整 slow／mid 结束后由状态机启动一次 fast，并在 fast 真正启动时归零。
- 演示与集气同时启用时，不沿用旧演示对 fast 的直接选择；每个人物依次完整播放
  `站立→slow→slow→mid→mid→满气待机→fast`。两次 slow 仅展示，不加演示气；
  两次 mid 各加 50，第二次满气后先以 100 气完整展示一次待机动画。此待机属于
  战斗 HUD 阶段，故强制保持 fullscreen 底对齐、隐藏 normal layer 且保持 battle
  HUD。待机结束后，同一完成状态机方启动 fast 并归零；fast 完成后轮换至下一人物。
  此组合不另建 demo timer，动作自己的帧 timer 即为唯一时基。
- 集气 HUD 复用体力槽的开口白色上下横线与灰阶填充，不显示数值；宽度为单侧
  体力槽的一半，中心对齐右侧体力槽，置于屏幕底部人物足下。它仅用一个透明
  LVGL 对象直接绘制，不分配 canvas、图片缓存或额外 timer。对象高 5px，顶行
  先以背景色清除人物像素作为 1px 黑色间隔，其下 4px 槽体依次为 1px 顶白线、
  2px 灰阶填充及 1px 底白线，底线贴屏幕底边。
- 自定义 Provider 不自动混入内置 Fighter，免致符号冲突与不可控 Flash 增量。
- HUD 以 LVGL 矩形及 label 组成，不分配全屏 L8 canvas。
- EvalKit 与 Cornix 的生产 profile 不将 Chizuru、Boss Kagura、Mature、普通 Iori、普通 Leona 与 Mr Big 编入 registry；Orochi Iori 与 Orochi Leona 仍参与循环。被排除角色的 BMP、manifest、播放计划及生成代码均保留，显式 `twenty` profile 仍可作全量容量测试。

## Custom playback sequence

原版 ROM 的动作表并非完整的播放时序。Kyo 的里百八式大蛇薙会在蓄力状态回跳，Mai 的超必杀忍蜂会在落地前反复播放中间帧；其循环次数分别受输入与物理状态控制。Dongle 演示没有这些游戏状态，故只抽取其视觉语义，并以有限序列展开，不试图移植完整战斗状态机。

- 播放计划以角色及动作档位为键，`order` 中的整数引用 ROM manifest 中的原始动作帧索引，而非均匀抽帧后的临时位置。
- 动作存在显式 `order` 时，该序列优先于该动作的均匀 `frame-limit`；生成器只转换序列实际引用的唯一源帧，再按 `order` 展开现有 `const void *const frames[]`。重复引用只增加一个只读指针，不复制 bitmap payload。
- 动作没有显式 `order` 时，继续使用当前均匀抽帧与递增播放顺序，保持既有输出。
- 生成器拒绝空序列、越界源帧索引及展开后超过 127 步的动作。计划内容须纳入缓存摘要，避免复用旧生成物。
- manifest 同时记录源帧数、唯一生成帧数、播放步骤数与展开顺序，以便核对 Flash 增量来自 bitmap 还是 pointer table。
- 运行时仍逐项读取 `action->frames[frame_index]`；重复和乱序帧本身无额外 RAM、堆分配或运行时解码。

## Per-step fighter movement

- 播放计划可选 `movement`，长度必须与展开后的 `order` 相等，每项仅为 `fixed` 或 `move`；第 0 步必须是 `fixed`。
- `fixed` 令该步骤保持前一步 X；`move` 令该步骤向 action 既定目标推进一个等分。等分数取整个 action 中 `move` 的数量，故最后一个 `move` 精确到达目标，其后的 `fixed` 仍停在目标。
- 未提供 `movement` 时 `movement_steps=NULL`，运行时将步骤 1..N-1 全视为 `move`，保持 ABI v3 之前的逐帧位移效果与旧宏源码兼容。
- 逐步表以一字节 `0/1` 生成到只读存储，不复制 bitmap；播放器只扫描至多 127 项计算总移动数及当前移动序号，不保存额外状态。此处刻意不用曲线、速度或坐标脚本。
- 有全局 motion 却没有任何 `move`、表值非 0/1、首步为 move，或移动步数超过可用像素距离时，action 校验失败。
- Kyo MAX 大蛇薙的蓄力往返及下蹲准备步骤固定，火焰释放步骤方移动；这避免重复蓄力帧令人物提前滑行。
- 可选 `return_step` 指向回程阶段首个播放步骤。分界前的 move 独立等分 `origin→target`，分界起的 move 独立等分 `target→origin`；两段至少各有一个 move。逐帧仍只保存 fixed/move，不保存坐标、方向或速度。
- Mai MAX 忍蜂的 0..3 准备／追加打击步骤固定，4..9 及 `8↔9` 空中循环前移，落地 10 固定。由地面起跳速度 `-$0500`、逐 tick 重力 `+$0060` 及 instant 动画计时可得第 26 物理 tick 落地，故 8／9 完整循环十二轮。
- Orochi Leona Super Moon Slasher 依 move code 展开 `4→5→6` 八轮；第 7 源帧所在播放步骤为回程分界，7..11 后撤跳回右侧，12 落地固定。
- Iori fast 改取 Desperation／MAX 八稚女 `kin_ya_otome_d` 的成功命中路径 0..27。第 1 帧以 7px/tick 最多奔跑 `$12` tick，命中即转第 2 帧；演示有限展开四个第 1 帧并等分 64px 行程，其后 2..27 均固定于命中位置。十六进制 `#19`（十进制 25）施加终结伤害并停留 `$3C` tick，故终爆插在该帧之后、26 与 27 收招之前。

## Alternating projectile timeline

- 可选 `frame_x_offsets` 与展开后的 frame pointer 表等长，每项为相对右侧 origin 的有符号一字节 X 偏移。使用此表时不得同时声明 motion、movement 或 return；运行时只执行一次换图与一次设坐标。
- 人物帧及飞行道具帧仍置于同一 `frames[]`；所谓交替模式并非叠加两个对象，而是时间线相邻步骤分别引用人物及道具描述符，故任一时刻仅有一张 I1 图片参与绘制。
- ROM 公共飞行道具档只提取八神两张火焰图及空手道先生霸王翔吼拳两张可见图。原作道具表自身在可见图之间插入 invisible 帧；演示以人物收招帧替代 invisible，既保留闪烁节奏，又令人物与道具交替。
- 八神 MAX 八稚女到达十六进制 `#19` 终结帧后，以 `fire A → #19 人物 → fire B → #19 人物` 循环三次，再播放 26、27 收招；火焰与人物固定于命中侧，不复制相同 bitmap。
- 空手道先生采用 REV_VER_2 中留存的 MAX 意图路径：龙虎乱舞成功段、暂烈拳四轮、长后跳、霸王翔吼拳 D。道具段以 D/S 两张图向左推进，中间恢复收招人物帧。
- 明确偏移必须令完整 64px action canvas 留在 128px 屏内；越界在 action 校验时返回 `-ERANGE`。坐标表仅占每步一字节 ROM，不增加 widget RAM、timer、LVGL object 或 heap。
- 可选 `frame_durations_ms` 与展开步骤等长，每项为 1..65535ms，且总和必须严格等于 `duration_ms`。此表只与显式 X 偏移时间线同用；存在时不再套首末 500ms／中间 200ms cadence，首步仍从图片实际绘出后计时。旧 action 留空该指针，继续循既有 cadence。
- 原作约 59.7275Hz，一 tick 约 16.74ms。OLED 道具时间线仿原作死亡慢放：`wPlaySlowdownSpeed=$01` 时保留 GFX buffer、跳过一次对象处理，再执行一次完整逻辑，故不是丢弃偶数帧，而是每个映射跨两个 VBlank。固件据此以 33／34ms 保留每一可见或隐藏映射。霸王翔吼拳 D/S 与暗拂仍保持 `可见→隐藏→可见→隐藏` 占空；Terry Power Geyser 仍保持十一映射 `V,V,V,H,V,H,V,H,V,H,V`，前十枚在六个半速显示帧后被后枚覆盖，末枚方走完十一帧。Goenitz Yonokaze 无隐藏映射，仍按 `$28` 原作 tick 的总寿命约 670ms 表达。

## Built-in Fighter theme demo

- 非自定义 Provider 可选的内置 Fighter pack 定位为主题功能演示，而非 KOF 资源包；其 idle/slow/mid/fast frame pointer 表全部引用已经链接的 Bongo Cat 图片描述符。
- demo 的 mid/fast 使用战斗 HUD、全屏标志及逐步 fixed／move 表，以极小只读表验证 Fighter 分层和选择性位移；不编译 `fighter_images.c`，因而不增加第二套 bitmap payload。
- 自定义 Provider 模式仍完全接管 registry，不自动混入 Bongo 或 Fighter demo。

首批自定义序列用于验证两类原作语义：Kyo fast 选用 `ura_orochi_nagi_d` Desperation／MAX 版并有限展开蓄力帧往返，Mai fast 有限展开落地前循环。具体重复次数是演示策略，不宣称等同于由玩家输入与角色落地动态决定的原作循环次数。

第二批 fast 只纳入 ROM 中可由有限帧序和单轴 fixed／move 表忠实表达者。Orochi Iori 的八稚女在命中后将 `2..5` 循环四次、再将 `8↔9` 循环四次；其命中前连续重播第 1 帧并横移四步。Daimon 的天地返普通超杀令 `5..12` 完整循环两次。Athena 的 Shining Crystal Bit 首段将 `1↔2` 循环十四次。后二者以全零 `x_offsets` 明定原地，免旧兼容规则把未声明 movement 的步骤尽作横移。Ryo 与 Robert 的龙虎乱舞将命中前第一帧显式展开；成功分支分别在源帧十六进制 `#15` 与 `#10` 转入重 Ko Hou／重 Ryuu Ga，而非播放各自乱舞表中的落地备用帧。收尾复用升龙源图 `0,1,2,3,2,3,2,3,4,5`：2、3 两张空中姿态正反往复三轮，继而以下落 4、落地 5 结束；重复步骤只复用 descriptor。原作升降依纵速与重力控制，现有 ABI 不保存 Y 坐标，故仅保留源图自身的垂直姿态，不虚构逐步高度。Andy 的超裂破弹保留其受纵速推进的原始六帧，仅以四段横移近似其前突，且不伪造 `2↔3` 回环。Andy 的纵向抛物线亦不模拟 Y 坐标。

Terry 的隐藏 MAX `Power Geyser E` 于 `#$04..#$12` 十五帧及 `#$13` 帧末各生成一枚
道具，共十六枚；每次随机 X 为 `(Rand & $38) + $18`，若与上次相同再加 `$08`，且新
对象会覆盖仍在场的旧对象。固件以十六处确定、相邻不重复落点代替随机数；前十五枚各
只及头六个映射，末枚方走完十一映射。人物 `#$00..#$04` 依 `21,3,9,9,6` tick 起步，
末枚与 `#$14` 的 61 tick 收招重叠十一 tick，其后人物独占保持 50 tick。全动作 199 tick
累计换算 6664ms，仍只用一个 image object 及五张唯一图。

Goenitz fast 取 `shinyaotome_jissoukoku_dl` 的 0..3；第 3 突进帧仅显示一次即将 64px action canvas 由右侧 origin 移至 `x=-32` 的屏幕中央，免将高速突进拖成长跑。命中后不采用其大量连击状态机，而复用既有 mid 的 `shinyaotome_throw_h`：先播 0..2，停在尚未起跳的举起姿态；随后以 `OBJLstPtrTable_Proj_Goenitz_Yonokaze` 的全高本体及其 X 镜像两图按 `风 A→举起→风 B→举起` 原位替换两轮，使风段之间始终可见举起人物；风毕才续播投技 3..6 的跃起、下压、落地与收束。龙卷原图虽高 128px，生成时统一缩至 64px；重复轮次仍只引用两张风图与一张举起图的 descriptor，且全过程只用一个 image object。

## Risks

- ABI v7 会拒绝未重编译或硬编码旧布局的 Provider；错误日志须明确版本。
- OLED 实际可见帧率与尺寸须由实屏确认；SWD 启动仅证明 CPU 运行，不代替屏显证据。
- 显式播放序列会增加只读 pointer table 长度与动作时长；构建须分别报告唯一图片数和播放步骤数，避免把指针增量误判为重复图片数据。
- 集气奖励依赖“完整动作结束”边界；若未来允许在相同档位中途重启，须保持未完成动作不计气，免由 WPM 抖动重复获益。
- 满气待机若错误沿用普通待机布局，会误隐藏 HUD、露出 normal layer；强制展示
  待机动画时必须保持其所属战斗阶段的 HUD 与 fullscreen 布局。
