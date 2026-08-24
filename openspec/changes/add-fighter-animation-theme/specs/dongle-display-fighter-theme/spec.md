## ADDED Requirements

### Requirement: Frame-synchronous fighter motion
The animation engine SHALL advance image source and position from one timer state machine tied to actual frames.

#### Scenario: Complete a moving action
- **WHEN** a moving action with N frames plays from its right-side origin to a valid target
- **THEN** frame zero SHALL appear at the origin and frame N-1 SHALL appear at the exact target
- **AND** the final frame SHALL remain for one complete frame period before reset
- **AND** no displayed frame coordinate SHALL leave the screen

#### Scenario: Hold and advance selected playback steps
- **WHEN** a moving action supplies a movement mode for every playback step
- **THEN** a `fixed` step SHALL retain the previous step's X coordinate
- **AND** a `move` step SHALL advance exactly one of the action's equal movement intervals
- **AND** the final `move` step SHALL reach the action target exactly
- **AND** a `fixed` step after the final `move` SHALL remain at the target

#### Scenario: Omit per-step movement modes
- **WHEN** a moving action has no movement-step table
- **THEN** playback steps 1 through N-1 SHALL all advance movement as before

#### Scenario: Return after a forward phase
- **WHEN** a moving action supplies a valid return-step boundary
- **THEN** `move` steps before the boundary SHALL divide the origin-to-target travel equally
- **AND** the final outbound `move` SHALL reach the target exactly
- **AND** `move` steps beginning at the boundary SHALL divide the target-to-origin travel equally
- **AND** the final return `move` SHALL reach the origin exactly
- **AND** each playback step SHALL still declare only `fixed` or `move`

#### Scenario: Reject invalid per-step movement
- **WHEN** a movement table differs in length from its playback order, starts with `move`, contains another value, contains no `move` for a moving action, or has more moving intervals than available travel pixels
- **THEN** generation or action validation SHALL fail with a contextual error

#### Scenario: Play a fighter mid or fast action
- **WHEN** a Fighter mid or fast action with N playback steps plays
- **THEN** playback step zero and playback step N-1 SHALL each remain visible for 500 milliseconds after that step's image has been painted
- **AND** each playback step between them SHALL remain visible for 200 milliseconds
- **AND** the complete action SHALL last exactly `1000 + 200 * (N - 2)` milliseconds, excluding endpoint paint latency

#### Scenario: Expand a custom playback order
- **WHEN** a generated action declares an ordered list of original source-frame indices
- **THEN** the generated action frame-pointer table SHALL preserve that exact order
- **AND** repeated indices SHALL produce repeated pointer references
- **AND** changing order SHALL NOT require a Provider ABI change or runtime sequence decoding

#### Scenario: Omit a custom playback order
- **WHEN** a generated action has no explicit playback order
- **THEN** its existing uniform sampling and ascending playback behavior SHALL remain unchanged

#### Scenario: Reuse a source frame in a custom order
- **WHEN** a source-frame index occurs more than once in a custom playback order
- **THEN** its image payload SHALL be generated once
- **AND** each occurrence SHALL add only a reference in the action frame-pointer table

#### Scenario: Reject an invalid custom order
- **WHEN** a custom playback order is empty, references a source frame outside the action, or expands beyond 127 playback steps
- **THEN** asset generation SHALL fail with an error identifying the character, action, offending value, and valid bound

#### Scenario: Generate sampled fighter action frames
- **WHEN** a mid or fast source action is uniformly sampled
- **THEN** every selected frame SHALL retain its complete union-bounds content after scaling
- **AND** its generated canvas width MAY exceed 64 pixels to preserve aspect ratio
- **AND** no selected frame content SHALL be clipped by the generated canvas

#### Scenario: Reject impossible motion
- **WHEN** the requested travel distance is less than the number of moving playback steps
- **THEN** action validation SHALL fail with `-ERANGE`

#### Scenario: Alternate a fighter and a low-frame projectile
- **WHEN** a generated action supplies one explicit X offset for every playback step
- **THEN** each step SHALL set the single animation image to either its fighter or projectile descriptor
- **AND** each step SHALL place that image at `origin + offset`
- **AND** the implementation SHALL NOT allocate a second image object, timer, canvas, heap buffer, or runtime compositor

#### Scenario: Reject incompatible explicit offsets
- **WHEN** an action mixes explicit X offsets with computed motion, movement modes, or a return boundary
- **THEN** generation or action validation SHALL fail with a contextual error
- **AND** an offset that leaves any frame outside the screen SHALL fail with `-ERANGE`

#### Scenario: Finish Iori fast with a flashing explosion
- **WHEN** Iori reaches hexadecimal body frame `#19` of the successful Desperation／MAX fast-action sequence
- **THEN** two ROM-derived fire frames SHALL alternate with that no-fire fighter frame for three cycles
- **AND** body frames 26 and 27 SHALL play after the flashing cycles
- **AND** repeated fighter or fire images SHALL reuse existing descriptors rather than duplicate image payload

#### Scenario: Expand a ROM-proven finite fast loop
- **WHEN** a selected Fighter fast move has a fixed loop count in its ROM move code
- **THEN** its custom playback order SHALL preserve that loop count using repeated frame references
- **AND** any command-dependent, opponent-position-dependent, projectile, or unrepresentable vertical phase SHALL NOT be presented as a faithful static replay

#### Scenario: Animate a confirmed forward approach
- **WHEN** a selected Fighter fast move advances until its first hit
- **THEN** the custom playback order MAY repeat the approach source frame for a finite demonstration interval
- **AND** only those repeated approach steps SHALL declare `move`
- **AND** all post-hit steps SHALL remain fixed unless a separately representable movement phase is declared

#### Scenario: Finish Ryo and Robert fast with the transitioned uppercut
- **WHEN** Ryo or Robert reaches the successful transition frame of Ryu Ko Ranbu fast
- **THEN** playback SHALL continue with the character's ROM-derived heavy uppercut action rather than the Ranbu fallback landing frame
- **AND** the two airborne uppercut poses SHALL alternate three times before the descent and landing poses
- **AND** repeated airborne poses SHALL reuse existing image descriptors
- **AND** playback SHALL NOT claim to reproduce runtime Y-position physics

#### Scenario: Play Terry hidden Power Geyser MAX
- **WHEN** Terry fast plays
- **THEN** it SHALL select the hidden `Power Geyser E` body action
- **AND** it SHALL alternate ROM-derived visible geyser phases at non-adjacent predetermined X positions with the body recovery frame
- **AND** it SHALL represent replacement rather than simultaneous projectile instances using one image object

#### Scenario: Play Goenitz fast throw-and-tornado sequence
- **WHEN** Goenitz fast plays
- **THEN** its desperation-super dash frame SHALL advance the fighter to screen center
- **AND** the dash pose SHALL appear once rather than being stretched across repeated playback steps
- **AND** the heavy throw used by Goenitz mid SHALL stop on its pre-jump lift pose at that position
- **AND** two ROM-derived Yonokaze tornado poses SHALL alternate twice at the same position, with the lift pose restored between every tornado pose
- **AND** only after both tornado cycles SHALL the remaining heavy-throw jump, descent, landing, and recovery poses complete
- **AND** repeated tornado and lift poses SHALL reuse existing image descriptors on the existing single image object

#### Scenario: Play Mr Karate fast finisher
- **WHEN** Mr Karate fast plays
- **THEN** it SHALL present Ryuko Ranbu, Zenretsuken, a backward hop, and Haoh Shoukou Ken in order
- **AND** the final projectile phase SHALL alternate two visible ROM projectile frames with the fighter's recovery frame
- **AND** successive projectile appearances SHALL travel away from the fighter

### Requirement: Layered fighter battle mode
The status screen SHALL use separate animation, battle HUD and normal layers, ordered from bottom
to top so the character is lowest, the HUD is in the middle, and normal dongle status is highest.

#### Scenario: Fighter idle or slow
- **WHEN** Fighter selects idle or slow
- **THEN** the normal layer SHALL be visible and the battle HUD SHALL be hidden

#### Scenario: Fighter mid or fast
- **WHEN** Fighter selects mid or fast
- **THEN** the normal layer SHALL be hidden and the battle HUD SHALL remain visible through repeated cycles
- **AND** the animation and HUD root layers SHALL remain transparent rather than painting a full-screen background

### Requirement: Pure black battle backdrop
The battle backdrop SHALL remain black without allocating a full-screen drawing surface.

#### Scenario: Render fighter mid or fast
- **WHEN** a battle-HUD action is visible
- **THEN** the screen background SHALL remain the LVGL-configured black background
- **AND** the animation and HUD roots SHALL remain transparent
- **AND** the implementation SHALL NOT allocate a full-screen canvas, temporal tile, or backdrop framebuffer

#### Scenario: Render idle or slow
- **WHEN** an action does not request the battle HUD
- **THEN** no battle backdrop object SHALL be shown

### Requirement: Peripheral battle battery HUD
The battle HUD SHALL render two configured peripheral battery sources without a full-screen canvas.

#### Scenario: Receive mapped battery levels
- **WHEN** source 0 or source 1 reports a level from 0 through 100
- **THEN** the corresponding side SHALL display its number and a clamped proportional bar
- **AND** the opposite side geometry SHALL be mirrored

#### Scenario: No battery report received
- **WHEN** a configured side has not received a peripheral battery event
- **THEN** it SHALL display `--` with an empty bar

### Requirement: Provider compatibility boundary
The module SHALL expose Provider ABI v7 while preserving source compatibility for existing action macros.

#### Scenario: Recompile an old macro provider
- **WHEN** an external Provider uses the prior `ZMK_DONGLE_ANIMATION_ACTION_DEFINE` macro
- **THEN** it SHALL compile as motion NONE, flags zero, endpoint hold zero, no custom movement table, no explicit offset table, no per-step duration table and no return step under ABI v7

### Requirement: Optional per-step action timing
The animation Provider SHALL optionally assign an independent millisecond duration to every expanded playback step without adding a timer or image object.

#### Scenario: Play an explicitly timed projectile timeline
- **WHEN** an action supplies `frame_durations_ms`
- **THEN** the table SHALL contain exactly one nonzero `uint16_t` duration per playback step
- **AND** its sum SHALL equal the action `duration_ms`
- **AND** the player SHALL use each table value instead of uniform or endpoint cadence
- **AND** timing of the first step SHALL begin after that image has been painted

#### Scenario: Reuse legacy cadence
- **WHEN** an action leaves `frame_durations_ms` null
- **THEN** existing endpoint-hold and derived-frame-period behavior SHALL remain unchanged

#### Scenario: Use a custom Provider
- **WHEN** custom Provider mode is enabled
- **THEN** built-in Bongo and Fighter packs SHALL NOT be mixed into its registry

#### Scenario: Build the reduced production fighter roster
- **WHEN** the EvalKit or Cornix production Fighter Provider is generated
- **THEN** Chizuru, Boss Kagura, Mature, normal Iori, normal Leona, and Mr Big SHALL NOT contribute image arrays, descriptors, actions, packs, or registry entries
- **AND** Orochi Iori and Orochi Leona SHALL remain enabled
- **AND** excluded characters' source bitmaps, manifests, playback plans, and explicit all-character generation path SHALL remain available

### Requirement: Built-in Fighter theme demonstration
The module SHALL provide an optional Fighter theme demonstration without a second bitmap payload.

#### Scenario: Build the Fighter theme demo
- **WHEN** the generic animation engine and built-in Fighter pack are enabled without a custom Provider
- **THEN** the registry SHALL contain a Fighter demo pack using the Fighter HUD and layered mid/fast modes
- **AND** every demo frame SHALL reference an existing Bongo Cat image descriptor
- **AND** the build SHALL NOT compile the separate Fighter bitmap source

#### Scenario: Demonstrate selective movement
- **WHEN** the Fighter demo fast action plays
- **THEN** its charge-like steps SHALL remain fixed
- **AND** its release-like steps SHALL advance toward the configured motion target

### Requirement: Optional animation demonstration
The animation engine SHALL optionally demonstrate four-band packs without WPM or NEXT input.

#### Scenario: Cycle a four-band pack
- **WHEN** demo mode is enabled
- **THEN** the engine SHALL select slow, mid, and fast in order after each action has completed
- **AND** it SHALL use each action's exact duration without adding a minimum display window
- **AND** it SHALL NOT interrupt an action before its complete duration elapses
- **AND** after fast has completed it SHALL select slow on the next pack
- **AND** the sequence SHALL wrap from the final pack to the first pack

#### Scenario: Disable demo mode
- **WHEN** demo mode is disabled
- **THEN** WPM selection, NEXT requests, and wake rotation SHALL retain their normal behavior

### Requirement: Selectable charge playback mode
The Fighter animation engine SHALL offer charge playback as an alternative to direct WPM and
automatic demonstration playback without changing the Provider ABI.

#### Scenario: Charge from a completed slow loop
- **WHEN** charge mode completes one slow action loop
- **THEN** the charge level SHALL increase by 5, saturated at 100
- **AND** an interrupted slow action SHALL award no charge

#### Scenario: Charge from a completed mid action
- **WHEN** charge mode completes one full mid action
- **THEN** the charge level SHALL increase by 10, saturated at 100
- **AND** an interrupted mid action SHALL award no charge

#### Scenario: Prevent direct fast selection
- **WHEN** WPM requests the fast band while charge mode is active and charge is below 100
- **THEN** the engine SHALL select no band above mid
- **AND** no WPM event or NEXT request SHALL directly start fast

#### Scenario: Spend a full charge
- **WHEN** a completed slow or mid action raises charge to 100
- **THEN** the engine SHALL start exactly one fast action through the completion state machine
- **AND** charge SHALL reset to zero when that fast action starts
- **AND** after fast completes the current WPM selection SHALL resume, clamped to mid

#### Scenario: Demonstrate charge mode
- **WHEN** demo mode and charge mode are enabled together
- **THEN** each fighter SHALL play idle, slow, slow, mid, mid, a full-charge idle, and fast in that order
- **AND** the two completed slow actions SHALL award no demo charge
- **AND** each completed mid action SHALL add 50 charge
- **AND** the same fighter SHALL complete mid twice before fast starts
- **AND** the second completed mid SHALL reach 100 and enter the full-charge idle through the completion state machine
- **AND** the gauge SHALL remain at 100 throughout one complete idle action before fast starts
- **AND** the full-charge idle SHALL retain fullscreen positioning and the visible battle HUD
- **AND** the normal status layer SHALL remain hidden throughout the full-charge idle
- **AND** charge SHALL reset only when fast starts after that idle action
- **AND** fast SHALL reset charge to zero and advance to the next fighter's idle only after it completes
- **AND** the combined mode SHALL use the frame timer as its sole transition clock

### Requirement: Low-memory charge HUD
Charge mode SHALL show a numberless gauge using the battle health-bar visual language.

#### Scenario: Render the charge gauge
- **WHEN** charge mode is enabled
- **THEN** the gauge SHALL use open white top and bottom rails with proportional gray fill
- **AND** its visible height SHALL be four pixels: one top rail, two fill rows and one bottom rail
- **AND** its width SHALL equal half of one health bar
- **AND** its horizontal center SHALL match the right health bar
- **AND** it SHALL be located at the bottom of the screen below the fighter
- **AND** exactly one black pixel row SHALL separate the fighter from the gauge top rail
- **AND** the gauge bottom rail SHALL touch the bottom screen edge
- **AND** it SHALL display no numeric charge value
- **AND** it SHALL use one directly drawn transparent LVGL object without a canvas, bitmap buffer, or timer
