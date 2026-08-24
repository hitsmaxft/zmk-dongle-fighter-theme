## MODIFIED Requirements

### Requirement: ROM-derived mid and fast timing
Each migrated Fighter mid or fast action SHALL derive its visible startup, body, projectile, airborne, and recovery timeline from a pinned KOF96 animation table and executed move-code path.

#### Scenario: Preserve ROM boundaries
- **WHEN** a migrated action is generated
- **THEN** `FrameTotal=N` SHALL contribute `N+1` source ticks
- **AND** the first image SHALL be painted before startup timing begins
- **AND** recovery SHALL hold the source-confirmed final visible state until the selected path ends
- **AND** parallel Super Sparkle time SHALL NOT be added as a player freeze without source evidence

#### Scenario: Audit a finite branch
- **WHEN** source behavior depends on input, collision, random state, or landing
- **THEN** the plan SHALL name the selected finite branch and disassembly revision
- **AND** source evidence SHALL name the animation table, move code, and projectile/object code when used
- **AND** physics-derived landing SHALL use the source velocity and gravity values

### Requirement: Parameterized display sampling
The generator SHALL adapt the 59.7275Hz source timeline to a configurable display update rate without changing the selected move's cumulative wall-clock duration.

#### Scenario: Generate the default 30Hz timeline
- **WHEN** `source_ticks_per_display_frame` is 2
- **THEN** the nominal target rate SHALL be approximately 29.864Hz
- **AND** the first, recovery, return, and final boundaries SHALL remain represented
- **AND** required low-frame projectile variants SHALL remain represented rather than being erased by sampling alias

#### Scenario: Lower the display frame rate
- **WHEN** the divisor is increased within 1 through 16
- **THEN** sampled display slots SHALL decrease
- **AND** total source ticks and cumulative milliseconds SHALL remain unchanged
- **AND** no action SHALL exceed the Provider playback bound after sampling
- **AND** generation SHALL fail with the missing source-frame indices if the selected divisor cannot preserve required variants

### Requirement: Flash-oriented playback deduplication
The generated Provider SHALL reuse identical final I1 images and collapse identical display holds without allocating a runtime image-composition buffer.

#### Scenario: Reuse mid frames in fast
- **WHEN** mid and fast produce equal canvas dimensions and identical packed I1 pixels for a character
- **THEN** both action tables SHALL reference one Flash image symbol
- **AND** the duplicate payload SHALL NOT be emitted again

#### Scenario: Collapse an identical hold
- **WHEN** adjacent sampled slots have the same image, X/Y offsets, and no new movement or return boundary
- **THEN** their durations SHALL be summed into one playback entry
- **AND** reported source ticks and total milliseconds SHALL remain unchanged
- **AND** pointer, duration, movement, and offset tables SHALL shrink by the number of collapsed slots

#### Scenario: Avoid unmeasured atlas overhead
- **WHEN** direct I1 images remain readable from Flash by LVGL
- **THEN** the implementation SHALL NOT add an atlas decompression or composition buffer without measured net Flash benefit and non-increasing SRAM

### Requirement: Correct composite projectiles and airborne recovery
Composite moves SHALL include source-confirmed projectile mappings and source-confirmed airborne motion.

#### Scenario: Render Athena and Geese effects
- **WHEN** Athena fast or Geese fast is generated
- **THEN** Athena SHALL reference Shining Crystal Bit swirl and thrown mappings
- **AND** Geese SHALL reference all Raging Storm S pillar mappings according to its 60-tick object lifetime and speed changes

#### Scenario: Render Mr Karate's ending
- **WHEN** Mr Karate's successful hidden desperation path reaches `RyukoRanbuD3`
- **THEN** the back-hop SHALL use the source 2/13/1 tick mapping durations and source velocity/gravity
- **AND** airborne states SHALL use `-10px` Y offset before returning to baseline
- **AND** Haoh Shoukou Ken D body and projectile states SHALL follow before final recovery
