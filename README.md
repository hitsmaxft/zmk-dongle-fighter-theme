# zmk-dongle-fighter-theme

KOF96 Game Boy fighter animation provider for
[`zmk-dongle-display`](https://github.com/hitsmaxft/zmk-dongle-display).

> [!IMPORTANT]
> This provider requires the animation ABI, Fighter HUD, projectile, and charge-mode
> support from the maintainer's special `zmk-dongle-display` `custom_anima` branch.
> It is not compatible with the upstream display module's `main` branch. See the
> [Chinese usage guide](docs/USAGE.md) for the pinned dependency and complete setup.

This module owns the generated-provider pipeline, ROM-derived timing plans,
deduplicated I1 sprite assets, previews, tests, and their OpenSpec history. The
display module continues to own the LVGL player, HUD, and provider ABI.

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
`zmk-dongle-display`.

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
