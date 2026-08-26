# Dongle Display 通用动画扩展

## 启用

自定义 Provider 仅需在目标 `.conf` 增加：

```ini
CONFIG_ZMK_DONGLE_DISPLAY_CUSTOM_ANIMATION_PROVIDER=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_HEADER="animations/my_provider.h"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_ROTATE_ON_WAKE=y
```

路径相对 `ZMK_CONFIG`。`CUSTOM_ANIMATION_PROVIDER` 自动开启通用动画总开关；若未开启，模块仍编译旧 Bongo Cat 路径，通用引擎、Provider、校验、随机及 NEXT 不进入最终 ELF。

## Provider 头文件

Provider 头只需包含 `<zmk/dongle_display/animation.h>`，以宏定义 action、pack 与 registry：

```c
ZMK_DONGLE_ANIMATION_ACTION_DEFINE(idle, idle_frames, 1000);
ZMK_DONGLE_ANIMATION_PACK_WPM4_DEFINE(character, "Character", idle, slow, mid, fast,
                                      5, 30, 70);
ZMK_DONGLE_ANIMATION_REGISTRY_DEFINE(64, 64, character);
```

普通帧数组自动推导帧数；动作须为 1 至 127 帧、时长非零。所有 pack 共用固定画布。KOF96 最终头由消费端构建生成至 `.build/_graphs/.../kof96_provider.h`。

Cornix 启用 generated-provider 模式。`scripts/cache_cornix_fighter_provider.py` 对生成器、缓存脚本、播放计划、位图 manifest 与全部 BMP 内容取 SHA-256；命中不重写头文件，失配方在临时目录生成并原子替换。旧容量证据保存在 `docs/CORNIX_FIGHTER_BUILD_EVIDENCE.json`，每次正式构建仍须重新量测。

## 自定义播放序列

`data/fighter_playback.json` 可按角色及档位声明有限播放序列。`animation` 用于防止动作选择变更后误套旧计划；`order` 中每项皆为位图 manifest 内的原始动作帧索引：

```json
{
  "version": 1,
  "characters": {
    "Kyo": {
      "fast": {
        "animation": "ura_orochi_nagi_d",
        "order": [0, 1, 2, 1, 2, 3, 4, 5, 6, 7]
      }
    }
  }
}
```

显式序列优先于该档位的均匀抽帧限制，允许重复、跳帧与改变顺序。生成器只转换被引用的唯一源帧，再将顺序展开为原有 `const void *const frames[]`；重复步骤不复制图片数据，亦不增加运行时解码状态或 RAM。空序列、越界索引及超过 127 步会在生成期报出角色、档位和有效范围。传入 `--no-playback-plan` 可恢复原有均匀抽帧及递增播放。

已迁移的 mid／fast 可另带严格 `timing`：其中记录反汇编 revision、Move ID、动作表、move／
projectile code、选定分支、Super Sparkle 是否并行、hitstop 归属、逐步 `step_ticks`、起手
与收招边界。生成器依约 59.7275Hz 展开源状态，再以
`--source-ticks-per-display-frame N` 量化；默认 N=2，目标约 29.864Hz。默认路径保证每个
逻辑状态至少占一个完整显示槽，故一 tick 的人物／道具／隐藏态亦不会因偶奇相位消失；
此类短态会依原版死亡慢放式显示而拉长。只有显式传入 `--allow-source-frame-drop` 才按
窗口抽样并维持 ROM 墙钟时长。相同最终图、位置及移动语义的连续槽会合并为一次较长
保持；报告分别列源 tick、源时长、显示槽、最终播放步、显示时长及合并槽。预览器加
`--details-json FILE` 可输出同一报告。

动作还可用与 `order` 等长的 `movement` 指定每步为 `fixed` 或 `move`。首步必须 fixed；fixed 保持前一 X，move 方推进一个等分，最后一个 move 精确到达 action 目标。省略此字段则保持旧行为，即除首步外每步皆移动。Kyo MAX 大蛇薙以蓄力及准备步骤 fixed、四个释放步骤 move，避免蓄力循环期间人物滑行。

若招式在突进后后撤，可另设 `return_step` 指向回程首步。其前方的 move 独立等分至目标，其后方的 move 独立等分回原点；逐帧配置仍只有 fixed/move。Orochi Leona Super Moon Slasher 以此表达八轮 `4→5→6` 连斩后，自第 7 源帧起跳回右侧。

飞行道具动作可改用与 `order` 等长的 `x_offsets`，每项为相对右侧起点的有符号 X 偏移；此字段不得与 `movement` 或 `return_step` 并用。ABI v9 另生成同长度 `frame_roles`：人物步骤更新常驻人物并隐藏道具，道具步骤保留人物、只更新第二 `lv_image`。二对象均直接引用 Flash descriptor，不增加 timer、canvas、framebuffer、bitmap RAM 或逐帧 heap。八神终爆只令火焰层闪烁；空手道先生的霸王翔吼拳独立前行，人物收招姿态始终保留。

同一序列可用标准库预览器生成测试 GIF，无须 Pillow：

```sh
python scripts/render_fighter_gif.py --character Kyo --sequence fast \
  --output .build/previews/kyo-fast.gif
python scripts/render_fighter_gif.py --character Kyo --sequence fast \
  --order 0,1,2,1,2,3,4,5,6,7 \
  --movement fixed,fixed,fixed,fixed,fixed,fixed,move,move,move,move \
  --output .build/previews/kyo-custom.gif
python scripts/render_fighter_gif.py --character Mr_Karate --sequence fast \
  --output .build/previews/mr-karate-fast-projectile.gif
```

预览器复用固件生成器的源帧缩放、播放计划、首末帧时长及水平位移算法；mid/fast 默认绘制战斗 HUD。`--no-hud` 可只看人物，`--scale 1..8` 控制输出倍率。

## Fighter 动画制作与提取准则

本节记录 KOF96 Fighter 动画数轮实机修正所得规则。后续增加或更换角色时必须先按
此节核对；“能生成 GIF”或“帧数相近”皆不足以证明招式选择和播放逻辑正确。

### 证据顺序与表达边界

1. 先核 ROM 动作表、move code、道具表及成功命中分支，再决定动作名和播放顺序。
   动作名、帧数或视觉相似仅可作为搜索入口，不可作为最终依据。
2. 区分图片资源、动作表与运行时状态机。原作中的循环次数、落地、命中、输入蓄力、
   随机道具位置和纵向物理，常不直接写在图片表内；必须追到控制它们的代码。
3. OLED 演示只表达已确认且可有限展开的视觉语义。无法表达的 Y 轴物理、对手位置、
   命中／格挡分支或输入时长应在文档中明确标作近似，不得称为原作逻辑的完整复刻。
4. 每次修改须分别记录：源动作、源帧数、唯一转换图片数、展开播放步骤数、动作时长、
   位移步骤、回程分界、道具来源及仍未表达的游戏状态。

### 选招与抽帧

- idle、slow、mid、fast 是显示语义，不代表按源动作帧数自动排序。应先确定角色最具
  辨识度且在 OLED 上可读的招式，再映射至档位。
- mid 与 fast 可均匀抽帧，但必须保留起势、关键打击／释放、转折、收招与落地。
  有显式 `order` 时，以 ROM 原始帧索引为准，禁止先抽样再对临时索引编排。
- 默认 30Hz 量化只改每步时长，不得改 `order`、图片、位移或飞行物相位；若为容量测试
  确需丢源帧，必须显式启用 `--allow-source-frame-drop`，且验收不得与默认固件混称。
- 缩放应覆盖所选帧的联合边界；允许宽度超过 64px，不得为塞入 64px 而裁掉人物、
  火焰或飞行道具内容。高度超过 64px 时按联合边界等比缩放。
- 重复帧只重复 descriptor 指针，不复制 bitmap。新增循环前先核唯一图片增量，避免
  把 pointer table 的少量增长误判为位图重复。
- 禁用角色只从默认生成 profile／registry 排除，不删除 BMP、manifest、播放计划或
  显式全量 profile；如此方可复核旧提取并在空间允许时恢复。

### 播放顺序与位移

- `order` 表达帧重复、跳转和乱序；`movement` 只表达该播放步骤是 `fixed` 或 `move`。
  二者职责不可混用。第 0 步必须 fixed，最后一个 move 必须精确到达目标。
- 蓄力、举起、命中后的连击和原地爆发应保持 fixed；只有原作确有前突、奔跑、后跳
  或道具飞行的步骤方可 move。不可因播放表重复了同一图片而让人物继续滑动。
- 有去程和回程时以 `return_step` 分段计算，不以一条单调曲线伪造。若原作会回到
  右侧，预览和固件都必须出现回程，而非停在左边或瞬移。
- 显式 `x_offsets` 用于人物／道具双轨时间线，不与 computed motion、`movement` 或
  `return_step` 混用。任一时刻至多显示一个人物及一个当前道具。
- 突进应短促。原作只有一个高速冲刺姿态时，不可为“看清动作”而重复成漫长跑步；
  到达命中位置后应立即进入命中／举起阶段。

### 飞行道具与闪烁

- 飞行道具帧少时，人物 image 始终保持最近姿态；第二 LVGL image 只承载一个当前
  道具，可换图、移动或隐藏，不增加 timer、canvas 或 bitmap RAM。
- 多次火焰或龙卷须核清是同时存在还是覆盖旧对象。现有双轨只支持一个当前道具；
  后续道具更新会替换此前道具，不得描述成多个道具并存。
- 闪烁只作用于道具 image。连续重复火焰图会变成常亮，不再具有原作爆炸节奏。
- 飞行道具的位置应来自 ROM 规则或明确的有限演示落点；若原作使用随机位置，应记录
  演示采用预定位置，不伪称复现随机数状态机。
- 合成时人物的多段动作（如乱舞、升龙、后跳、收招）须共用一组联合边界与缩放；逐段
  各自居中会令同一角色忽大忽小或跳位。飞行物各 mapping 的原点差须转为只读 X/Y
  相位表，不得因逐图归一化而把吉斯左右光柱或暴风旋风叠到同一坐标。

### 时长与动作边界

- Fighter mid／fast 的首帧与末帧各停 500ms，且首帧停时从图片完成绘制后计算；
  中间每播放步骤 200ms。不要另加与动作 timer 竞争的最短展示 timer。
- 上述 500／200ms 仅为无逐步时长表的通用 cadence。飞行道具若 ROM 明载 instant
  映射、对象寿命或被后枚覆盖时刻，须用与 `order` 等长的 `durations_ms`；不可仍以
  每步 200ms 播放。已迁移 mid／fast 默认令每一逻辑状态占满两个 59.7275Hz source ticks，
  目标约 29.864Hz；原来仅一 tick 的状态会扩为约 33.5ms，原来三 tick 的状态会扩为四
  tick。每项须为 1..65535ms，总和须等于量化后的 action 显示时长。
- 默认量化不得删去任何 `order` 状态；报告中的 `source_total_ms` 保留 ROM 分支基线，
  `total_ms` 则是 OLED 实播时长。显式丢帧模式方可使用轮换窗口与
  `sampling_required_frames`；若所选 N 无法容纳必保变体，生成期失败，不静默删去 D/S、
  光柱或 thrown 映射。
- 重复步骤属于动作总时长。动作结束只发生在末帧完整停留后；NEXT、降档、换人、
  集气奖励和 fast 门控皆在此边界处理。
- 被 WPM 升档打断的 slow／mid 不算完整动作，不得加气。普通集气模式完整 slow `+5`、
  完整 mid `+10`；WPM 对 fast 的请求必须钳至 mid，满 100 方由完成状态机启动 fast。
- EvalKit 的 `demo+charge` 固定为
  `站立 → slow → slow → mid → mid → 满气待机 → fast → 换人`。演示 slow 不加气，
  两次 mid 各加 50。第二次 mid 后气槽保持 100，完整展示一次满气待机；待机结束
  方启动 fast 并归零。

### HUD 与层级规则

- 层级语义为人物最低、battle HUD 居中、normal dongle 状态最高。mid／fast 隐藏
  normal layer，但 HUD 必须持续可见；动画根和 HUD 根皆透明，不填充全屏背景。
- 纯黑背景来自 LVGL screen 默认背景。禁止为“保证黑底”另画全屏矩形、canvas、
  时域抖动背景或灰度噪点；实机已证明低密度抖动会令画面变脏。
- 顶部体力槽上横线贴 `y=0`，保留白色上下横线表示全长。底部气槽宽为单侧体力槽
  一半，中心与右体力槽一致；总高 5px，依次为黑色隔离 1px、上白线 1px、灰阶
  2px、下白线 1px，末行贴 `y=63`，不显示数字。
- **强制展示满气待机动画时不得隐藏 HUD。** 此处确为待机动画，不称“代理动画”；
  但它仍处于战斗 HUD 阶段，必须隐藏 normal layer、保持 fullscreen 底对齐，并让
  满格气槽可见一整个待机动作。素材 action 的普通布局不得覆盖状态机指定的层级。
- 强制插入人物恢复帧、无火焰帧或举起保持帧时，同样不得让 HUD 因图片来源 action
  的 flags 而闪退；HUD 可见性由整段战斗阶段决定，不由单张图片决定。

### 已确认的角色案例

| 角色 | 正确选择与有限表达 | 后续提取须保留的关键语义 |
|---|---|---|
| Kyo | fast 取 MAX 大蛇薙 | 蓄力往返 fixed，释放段方移动；输入决定的无限蓄力只作有限展开 |
| Mai | mid 固定选龙炎舞；fast 展开超必杀忍蜂 | 准备固定、空中段前移、落地前循环；不得以通用帧数规则改选 mid |
| Orochi Leona | fast 取 Super Moon Slasher | `4→5→6` 八轮后必须以后撤跳回右侧并落地，不能停在左边 |
| Iori | fast 取 MAX 八稚女成功命中路径 | 奔跑短促，连击固定；终结火焰插在 `#19` 后，以无火焰人物帧穿插闪烁三轮 |
| Orochi Iori | 依 move code 展开确定循环 | 命中前前移，命中后循环固定，不把普通 Iori 的配置误套入 |
| Ryo／Robert | 龙虎乱舞成功段转重升龙收尾 | 两张空中升龙姿态正反交替三轮，继而下落着地；不得用乱舞备用落地帧 |
| Terry | fast 采用隐藏 Power Geyser MAX | 多个不同地涌位置是覆盖式交替，不是一个固定道具，也不是多对象并存 |
| Goenitz | 单个突进帧至中央，接 mid 重投 | 举起后先保持举起，再以风／举起交替两轮；不可立刻跳起或拉长突进 |
| Mr Karate | 龙虎乱舞、暂烈拳、后跳、霸王翔吼拳 | 收招后跳与向外飞行的两道具帧必须完整出现 |

### 反例与纠正记录

| 反例 | 画面／逻辑后果 | 正确做法 |
|---|---|---|
| 仅按帧数或动作名猜 fast | Mai、Iori、Orochi Leona 等招式与游戏内逻辑不符 | 追 ROM 动作表、move code 和成功命中分支后再选招 |
| 为适配 64px 宽度裁剪 mid／fast | 人物或招式内容缺失，动作辨识度下降 | 等比缩放联合边界，允许宽度超过 64px |
| 所有重复帧都推进 X | 蓄力、举起和原地连击发生滑行 | 逐步标 fixed／move，只在原作移动阶段推进 |
| Orochi Leona 连斩后不回右侧 | Super Moon Slasher 收招方向错误 | 设 `return_step`，明确去程和回程 |
| Iori 火焰连续常亮或插入点过早 | 终爆不像原作，收招顺序错误 | 在 `#19` 后以火焰／无火焰人物帧交替三轮 |
| Goenitz 突进重复过长，举起后立刻跳起 | 高速突进变长跑，龙卷阶段缺少举起保持 | 突进帧只播一次；风与举起交替后方续投技跳跃 |
| Ryo／Robert 直接使用乱舞落地帧 | 缺少游戏内升龙收尾 | 转入重升龙动作并复用空中两姿态完成升降视觉 |
| 为黑底主动填充或加低密度灰点 | 出现全白、花屏、画面脏或额外绘制开销 | 沿用 LVGL 黑底，所有动画／HUD 根透明 |
| HUD 与 animation 层级混乱 | 只见 HUD、人物消失，或 HUD 被人物盖住／切换闪退 | 固定人物 < HUD < normal 层级，并由 action 阶段统一切换 |
| 满气后立即清零并进入 fast | 满格仅存在一个回调，肉眼不可见 | 满 100 后完整展示一次保持 HUD 的满气待机，再清零进 fast |
| 满气待机沿用普通 idle 布局 | HUD 被隐藏且 normal 状态层出现 | 待机仍属战斗 HUD 阶段，强制保持 HUD 与 fullscreen 布局 |
| 将满气待机称为“代理动画” | 混淆真实待机动作与临时替身概念 | 统一称“满气待机动画”，只说明其 HUD 状态不同于普通待机 |
| 以图片 payload 大小代替最终 ROM 风险 | 无法解释不同板型与链接内容造成的启动差异 | 可选守门应看最终链接 ROM；图片数／字节仅作归因证据 |
| 为节省空间删除角色源配置 | 失去复核和恢复能力 | 仅从生产 profile 排除，保留素材、manifest 与播放计划 |

### 每个角色的交付检查表

1. 写明 ROM 动作名、动作表位置、move code／道具表证据及采用的成功分支。
2. 生成角色 slow、mid、fast GIF；逐帧核对关键姿态、循环次数、去程、回程、收招。
3. 对照 `order`、`movement`、`return_step`、`x_offsets` 长度和源帧范围，运行严格测试。
4. 检查唯一图片数与播放步骤数分别增长多少；确认重复步骤未复制 bitmap。
5. 已迁移 mid／fast 须核对 `timing.step_ticks`、首帧绘制后起计及末帧硬直；普通飞行
   道具另核对采样后显隐占空、覆盖时刻与对象寿命。仅未迁移条目方沿用通用 cadence。
6. 核对 battle HUD 在 mid／fast、满气待机及强制插帧期间不消失，normal layer 不闪现。
7. 构建后检查最终 `.config`、ROM／RAM、Provider profile 与被排除角色；不得只看生成成功。
8. 静态 GIF、构建成功、SWD 启动和实屏观感须分开记录；未上硬件不得宣称实屏通过。

## 内置 Fighter Theme demo

未使用自定义 Provider 时，`CONFIG_ZMK_DONGLE_DISPLAY_FIGHTER_PACK=y` 会注册 `Fighter Demo`。其四档动作全部复用已经链接的 Bongo Cat 图片描述符；mid/fast 开启 Fighter HUD 与全屏分层，并以 fixed／move 表演示蓄力固定、释放移动。此路径不编译 `fighter_images.c`，故 demo 不带第二套位图 payload。自定义 Provider 仍完全接管 registry，不混入内置 demo。

EvalKit 可直接构建 `wave-dongle-fighter-demo`；该目标关闭外部 generated provider、启用内置 Bongo 与 Fighter Demo 并自动轮播。

## 播放与切换

WPM band 升高时立即抢占，降低时等待当前动作结束。动作总时长以展开后的播放步骤数计算；Fighter mid/fast 首末步骤各 500ms，中间步骤各 200ms。启动索引以 `.noinit` boot nonce、`k_cycle_get_32()` 及 32 位 avalanche 混合后取模；nonce 在软复位间保留并递增，避免确定启动路径反复命中同一角色。NEXT 固定按 `(current + 1) % pack_count` 顺序轮换，不读取随机源。请求使用 atomic 计数，每个动作边界消费一次。动画初始化不得调用可能同步等待 entropy 的 `sys_rand32_get()`，亦不为随机起角写 settings／flash。

键位节点使用 `zmk,behavior-dongle-animation-next`，绑定为 `&animation_next`。Cornix 已置于 Debug 层原换人位置；旧 `fighter_next` 仅保留为兼容适配器。

## 验证

### 当前实现边界（2026-08-23）

- Provider ABI 已为 v8；action 可带 `frame_durations_ms` 与只读 `frame_y_offsets`。人物
  腾空仍取 `0/-10px`；飞行物另可用有符号 int8 Y 相位保存对象表原点。两者皆直接叠加
  既有 origin，不增 LVGL object、timer 或堆内存；旧宏省略该字段仍为 NULL。首项从图片
  绘制完成后起计，生成器与 GIF 读取同一时长及 Y 表。
- 生产十四角 fast 皆已记录 revision、动作表、move code、成功分支、逐步 tick 及末帧
  硬直；Andy、Ryo、Robert、Athena、Mai、Orochi Leona、Mr Karate 之 ROM 确认腾空段上移
  10px，其余七角不由图片边界猜测腾空。
- 同源 GIF 由 `scripts/render_fighter_gif.py` 临时生成，不纳入版本历史；保留但默认不编译
  的六角尚未迁移。
- 下列旧验证记录只说明当时对应构建状态，不替代本次工作树的重新构建，亦不构成实屏
  节奏证据。

### 独立模块与 30Hz 降采样重验（2026-08-24）

Provider 已移入 `zmk-dongle-fighter-theme`；Cornix、dongle demo 与 EvalKit 皆从模块脚本
生成。默认 N=2 保留全部计划状态；N=4、N=8 亦不删图，只进一步拉长短态。显式
`--allow-source-frame-drop` 方沿用窗口采样；其 N=8 因 Mr Karate S 图无法在该密度保留而
明确失败。37 项宿主测试另覆盖全部 timed mid/fast 的位图集合不丢失、复合相位及 GIF。

2026-08-24 同日修正：Geese 四光柱由对象表原点形成 `-36/0/-24/-13px` 左右相位，同形
非翻转／翻转图各自复用；Athena 蓄球置于手侧后向前抛；Goenitz 补齐对象表中间旋风，
以左／中／右三位与举起帧交替两轮；Mr Karate、Ryo、Robert 等多段人物动作改用共享
联合边界，避免换段缩放跳变。mid/fast I1 删去战斗层底对齐下等价的透明顶部行，屏上
坐标不变；当前实启 293 unique、156311B I1，仍低于 301 帧／156520B 既有闸值。
此数专指生成器默认十三角；构建所用历史名 `eighteen` profile 实启十四角（另含
Mr Karate），为 330 unique、175295B I1。二者不可混作同一 roster 的前后比较。

同日以项目本地 Nix 串行重建。`eighteen` manifest 为 428 logical、330 unique、
175295B I1、7920B descriptor；宿主 37 项 Python 测试、动画数学 C 测试与两项 OpenSpec
strict 校验皆过。最终链接与产物为：

| 目标 | Flash used / region | SRAM image / total | 余 Flash | 余 SRAM | UF2 SHA-256 |
|---|---:|---:|---:|---:|---|
| `wave-dongle-animation` | 600436 / 1048576 B | 92556 / 262144 B | 448140 B | 169588 B | `0854f3c9d1460e69b59474602d294d57fed16d7036d71e169d3f2ee9b0262c03` |
| `cornix_dongle` | 731836 / 864256 B | 139644 / 262144 B | 132420 B | 122500 B | `70a377cc27f59bef9576e214f19ff915610c77e673ac3de5f522dd0320eb85d3` |

相较下列首次模块迁移构建，Flash 因保留原先误删的短态及新增相位表而增加约 17KiB，
SRAM 数值完全相同；两目标仍有明确余量。此为静态／构建证据，未刷写，实屏节奏另验。

以下为修正前首次模块迁移记录：`eighteen` 历史 profile 实启十四角；当时 manifest 为
526 logical、417 unique、109 次
图片去重、227720B 全素材 I1；实启部分为 372 logical、296 unique、160960B I1、7104B
descriptor，最终 866 播放步骤。与下列 2026-08-23 基线相比，实启 I1 少 13904B，
descriptor 少 624B。

| 目标 | Flash used / region | SRAM image / total | 余 Flash | 余 SRAM | UF2 SHA-256 |
|---|---:|---:|---:|---:|---|
| `wave-dongle-animation` | 583440 / 1048576 B | 92556 / 262144 B | 465136 B | 169588 B | `c64948b08e2f49cd8775413b5d2757a7778da27e572505ea087d03322022965f` |
| `cornix_dongle` | 714836 / 864256 B | 139644 / 262144 B | 149420 B | 122500 B | `a87450a445d8edcb918c3469786d621807ef483fb1aac97b5a892ee5ea629811` |

较旧同 roster 构建，Flash 分别少 14732B 与 14736B，SRAM 数值不变。图、descriptor、
pointer、duration、movement 与 offset 均为 `static const`；本轮未引入 atlas 解压画布、
第二 image、heap 或 timer。上述为静态／构建证据，尚未刷写。

2026-08-23 以项目本地 Nix 重验：`align-fighter-super-timing` strict 校验、播放计划／GIF
30 项测试与宿主动画数学 C 测试皆通过；`wave-dongle-animation` 与 `cornix_dongle` 均以
pristine 串行构建成功。外部 Provider manifest 启用十四角、415 logical frames、322
unique frames、174864 B I1 payload、7728 B descriptor 及 842 播放步骤；重复步骤不复制
bitmap。最终链接 map 与 UF2 摘要如下：

| 目标 | Flash | RAM | UF2 SHA-256 |
|---|---:|---:|---|
| `wave-dongle-animation` | 598172 / 1048576 B | 92556 / 262144 B | `54acc6318d037d7671eacd399e2fc43cad36a855c76488f9dcc7081f402c7eab` |
| `cornix_dongle` | 729572 / 1048576 B | 139644 / 262144 B | `c795b5ae5824406c17bb37569f7e14430cdb96b04bf265226bf57dd42aa9f178` |

`eighteen` 为 profile 历史名，实际十四角以 manifest 为准。Zephyr 报告脚本因当前环境缺
`anytree` 未执行，故上述 Flash／RAM 直接读最终 map 的 `_flash_used`／`_image_ram_size`；
固件构建不受影响。本轮未刷写，尚无新增 SWD 或 OLED 实屏证据。初次并行构建曾竞争
共享 Provider 缓存而留下旧 manifest；验收数据均取重新生成缓存后的串行 pristine 构建。

- `velvet_central_dongle`：扩展关闭，仅编译旧 Bongo 源，ELF 无通用动画符号。
- `cornix_dongle`：旧记录曾为 15 packs；现行十四角及容量以上述 2026-08-23 重验为准。
- Cornix 左右片、Velvet 左右片：通用 behavior 兼容构建通过。
- 最小一帧 Provider：无需额外 CMake，独立构建通过。
- 缺失 Provider：CMake 配置期明确失败；128 帧动作：编译期静态断言失败。
- 随机索引 helper：宿主边界测试通过。
