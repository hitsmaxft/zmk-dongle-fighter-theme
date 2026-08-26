# zmk-dongle-fighter-theme

KOF96 Game Boy fighter animation provider for
[`zmk-dongle-display`](https://github.com/hitsmaxft/zmk-dongle-display).

> [!IMPORTANT]
> This provider requires the animation ABI, Fighter HUD, projectile, and charge-mode
> support from the maintainer's special `zmk-dongle-display` `custom_anima` branch.
> It is not compatible with the upstream display module's `main` branch. See the
> [Chinese usage guide](docs/USAGE.md) for the pinned dependency and complete setup.

This module owns the generated-provider pipeline, ROM-derived timing plans,
deduplicated I1 sprite assets, previews, and tests. Cross-module Fighter OpenSpec
history lives in the parent zmk-config workspace root; the display module continues
to own the LVGL player, HUD, and provider ABI.

## ZMK integration

Add the module to the workspace manifest, then configure a dongle build:

```conf
CONFIG_ZMK_DONGLE_DISPLAY_CUSTOM_ANIMATION_PROVIDER=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATED=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATOR="../zmodules/zmk-dongle-fighter-theme/scripts/cache_cornix_fighter_provider.py"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_GENERATOR_ARGS="--profile default --source-ticks-per-display-frame 2"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_CACHE_DIR="../.build/_graphs/kof96-fighter-default"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_PROVIDER_HEADER="kof96_provider.h"
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_WPM_MODE=y
CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_DEMO_MODE=n
```

All configured paths remain relative to `ZMK_CONFIG`, as required by
`zmk-dongle-display`. For a smaller diagnostic build, the `mini` profile
enables only Kyo, Mai, Mr. Karate, and Terry.

The recommended production configuration uses the 13-character `default`
profile and disables demo mode. Choose exactly one playback mode: the default
WPM mode selects idle/slow/mid/fast directly from typing speed; charge mode
allows slow and mid actions to fill the gauge before fast can play. The full
mode comparison and charge-mode configuration are in [docs/USAGE.md](docs/USAGE.md).

## Local validation

```sh
python -m unittest tests.test_fighter_playback tests.test_fighter_gif
python scripts/render_fighter_gif.py --character Kyo --sequence fast \
  --output /tmp/kyo-fast.gif
```

The default source/display divisor is `2`: KOF96's 59.7275 Hz logic timeline
is sampled at about 29.864 display updates per second while cumulative wall
duration remains equal to the selected ROM path. Consecutive identical final
I1 states are represented by a longer hold rather than duplicate pointer,
duration, movement, or offset entries.

## OLED performance options

The provider does not configure the consuming board's display bus. The parent
workspace's Cornix hardware boots reliably with the interrupt-driven TWI default at
100 kHz. A combined switch to Nordic TWIM with EasyDMA at 400 kHz built successfully
but froze continuous screen rendering on hardware while keyboard input and display wake
still worked; that combination has been rolled back and is not a recommended profile.
The TWI/100 kHz rescue build restored normal startup but did not reduce animation
tearing. Changing only that bus to 400 kHz then preserved startup and removed visible
tearing, with no I2C errors observed during the follow-up CDC sample. TWI/400 kHz is the
recommended Cornix profile; TWIM is unnecessary for this hardware result.

`CONFIG_LV_Z_VDB_SIZE=100` keeps a full monochrome render buffer and conversion
buffer and is the latency-first setting. `25` is a documented memory-balanced option:
on a 128x64 I1 display it reduces those two buffers from about 2064 bytes to 528 bytes,
at the cost of more partial-render callbacks. `13` is an experimental one-page minimum
and should not be used without hardware testing. The complete option matrix and
validation gates are in [docs/USAGE.md](docs/USAGE.md#显示性能选项).

The player now anchors generated 30 Hz timelines to an absolute deadline after the first
required draw event. If synchronous display rendering overruns one or more 33/34 ms
intervals, it selects the frame whose interval contains current wall time and never
replays fully expired steps. This reuses the existing timer and adds only one 64-bit
deadline. ABI v9 adds a read-only role table: the character image remains visible while
one persistent projectile image is independently shown, hidden, moved, or replaced.
There is still no canvas, framebuffer, bitmap copy, second timer, or per-frame allocation.
Tightly cropped projectile dirty rectangles remain an unimplemented fallback.

## ROM and disassembly inputs

No commercial ROM is stored in this repository. In the parent zmk-config
workspace the verified ROM intentionally remains at:

```text
graphs/ntkof96.gb
```

To reproduce source bitmaps, pass that file explicitly together with the
pinned Kak2X disassembly checkout:

```sh
python scripts/extract_character_bitmaps.py ../../graphs/ntkof96.gb \
  --disasm /private/tmp/kof96-disasm --output assets/character_bitmaps
python scripts/extract_projectile_bitmaps.py \
  --disasm /private/tmp/kof96-disasm --output assets/projectile_bitmaps
python scripts/compose_fighter_projectile_actions.py
```

The extractor verifies SHA-1 `63f25bff422a591907b83ab9f14709e938172839`.
