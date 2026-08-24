## ADDED Requirements

### Requirement: Dedicated fighter canvas
The Cornix dongle display SHALL reserve the rightmost `64×64` pixels for a fixed-origin fighter animation canvas.

#### Scenario: Status widgets remain outside the fighter canvas
- **WHEN** the Cornix status screen is created
- **THEN** connection, layer, modifier, and indicator widgets SHALL remain within the leftmost 64 pixels
- **AND** the two peripheral batteries SHALL occupy one horizontal row at the top-right
- **AND** each battery SHALL fit within one 32-pixel slot over the fighter canvas

### Requirement: Reproducible fighter assets
The prototype SHALL generate LVGL `I1` frames from a named KOF96 character and an explicit animation-frame selection.

#### Scenario: Generate a fixed-origin frame set
- **WHEN** the Kyo prototype assets are generated
- **THEN** every output frame SHALL use a `64×64` canvas
- **AND** manifest origin metadata SHALL preserve stable feet and body placement across frames
- **AND** the generator inputs and result summary SHALL be stored under `graphs/`

#### Scenario: Enlarge the fighter for the OLED
- **WHEN** the Kyo prototype assets are generated after hardware legibility feedback
- **THEN** every WPM sequence SHALL render at `1.5×` source scale
- **AND** pixels beyond the `64×64` canvas SHALL be clipped
- **AND** every sequence SHALL retain a stable shared origin within its `64×64` canvas

### Requirement: WPM-driven fighter animation
The prototype SHALL preserve the existing four WPM bands while replacing Bongo Cat imagery with selected fighter sequences.

#### Scenario: Change animation by typing speed
- **WHEN** WPM crosses the idle, slow, mid, or fast threshold
- **THEN** the corresponding fighter sequence SHALL start and repeat
- **AND** only the frames required by those sequences SHALL be linked into firmware

#### Scenario: Select the minimal Kyo action set
- **WHEN** the prototype asset set is generated
- **THEN** idle SHALL use the four-frame victory action `win_b`
- **AND** slow SHALL use the crouching heavy kick `kick_ch`
- **AND** mid SHALL use Oniyaki `oni_yaki_l`
- **AND** fast SHALL use Orochinagi `ura_orochi_nagi_s`
- **AND** the four actions SHALL be sampled to 4, 4, 6, and 8 frames with durations based on their compiled frame counts
- **AND** the default 15-pack provider SHALL not exceed 301 unique frames or 156520 image bytes

#### Scenario: Reallocate Krauser frames to Kyo
- **WHEN** the KOF96 provider is generated
- **THEN** Krauser mid SHALL use `leg_tomahawk_l` sampled from seven to three frames instead of the ten-frame `kaiser_suplex_l`
- **AND** Kyo Orochinagi SHALL retain all eight source frames
- **AND** the default 15-pack provider SHALL remain within the proven unique-image budget

#### Scenario: Generate the define-gated roster
- **WHEN** the roster assets are generated
- **THEN** the source SHALL contain all 20 extracted fighter forms
- **AND** compile-time defines SHALL enable exactly 15 forms by default
- **AND** disabled forms SHALL not contribute images, descriptors, tables, or roster entries

#### Scenario: Play Oniyaki at the fastest band
- **WHEN** Kyo is active and WPM is at least 70
- **THEN** the complete seven-frame `oni_yaki_l` sequence SHALL repeat
- **AND** one complete sequence SHALL last at least `1400 ms`

#### Scenario: Increase typing speed during an animation
- **WHEN** WPM moves to a faster band before the current sequence completes
- **THEN** the current sequence SHALL be interrupted immediately
- **AND** the faster sequence SHALL start without traversing intermediate bands

#### Scenario: Decrease typing speed during an animation
- **WHEN** WPM moves to a slower band before the current sequence completes
- **THEN** the current sequence SHALL continue through its final frame
- **AND** the latest requested slower sequence SHALL start only after completion

#### Scenario: Render both peripheral batteries in one row
- **WHEN** both peripheral battery states are visible
- **THEN** they SHALL be arranged horizontally rather than vertically
- **AND** neither battery slot SHALL extend outside the 64-pixel right half

### Requirement: Prototype validation
The prototype SHALL be validated against the actual `cornix_dongle` build output.

#### Scenario: Build and inspect the prototype
- **WHEN** `cornix_dongle` is built
- **THEN** the build SHALL complete successfully
- **AND** the final DTS SHALL report a `128×64` display
- **AND** the final configuration SHALL retain 1-bit LVGL output
- **AND** Flash and RAM usage deltas SHALL be recorded under `graphs/`

### Requirement: Define-gated roster rotation
The step-test prototype SHALL rotate only through the 15 fighters enabled at compile time.

#### Scenario: Request rotation after wake
- **WHEN** activity returns to Active after Idle or Sleep
- **THEN** one fighter change SHALL be queued
- **AND** the current action SHALL finish before the change is applied

#### Scenario: Request rotation manually
- **WHEN** the Debug-layer fighter-next binding is pressed
- **THEN** one fighter change SHALL be queued
- **AND** consecutive presses SHALL not be lost

#### Scenario: Enforce the compiled-roster capacity gate
- **WHEN** the define-gated dongle image is linked
- **THEN** at least 100 KiB SHALL remain in the code partition
- **AND** no UF2 target address SHALL reach storage or bootloader

#### Scenario: Enforce LVGL animation length
- **WHEN** fighter sequence tables are generated or started
- **THEN** each sequence SHALL contain between 1 and 127 frames
- **AND** generation SHALL fail at compile time when the upper bound is exceeded

#### Scenario: Sample long actions for capacity
- **WHEN** an idle or fast action exceeds its configured frame cap
- **THEN** frames SHALL be sampled uniformly with first and last frames retained
- **AND** the action duration SHALL equal compiled frame count times the configured per-frame duration

### Requirement: Dongle bootloader binding
The Cornix Debug layer SHALL expose a dedicated binding that places the central dongle into bootloader mode.

#### Scenario: Enter the dongle bootloader from the Debug layer
- **WHEN** the dedicated dongle-bootloader binding is pressed on the Debug layer
- **THEN** the central dongle SHALL execute the standard ZMK bootloader behavior
- **AND** the binding SHALL not require a source change under `zmodules/`
