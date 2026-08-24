## MODIFIED Requirements

### Requirement: Provider build validation
The generic module and external-provider path SHALL be validated on actual dongle targets.

#### Scenario: Build both provider modes
- **WHEN** `velvet_central_dongle` uses the built-in provider and `cornix_dongle` uses KOF96
- **THEN** both builds SHALL complete successfully
- **AND** final DTS, selected Provider, Flash/RAM usage, UF2 address range, and required settings backend SHALL be inspected

#### Scenario: Validate twenty-character capacity on EvalKit
- **WHEN** the KOF96 Provider enables all twenty supported characters and the dedicated nRF52840 EvalKit target is built
- **THEN** the build SHALL record longest action frame count, logical-frame count, unique-frame count, image bytes, Flash and RAM usage
- **AND** the EvalKit SHALL be flashed only after its probe, target identity, recovery state and artifact hash are recorded
- **AND** acceptance SHALL require observed firmware startup and display initialization or first-frame output

#### Scenario: Distinguish frame length from aggregate resource limits
- **WHEN** a capacity matrix varies action-frame count and aggregate unique-frame count independently
- **THEN** each hardware outcome SHALL identify the exact matrix inputs and reset/startup evidence
- **AND** the resulting documentation SHALL NOT attribute an observed failure to a fixed frame-count threshold without controlled evidence

### Requirement: Bounded animation registry access
The animation extension SHALL avoid startup work proportional to every compiled character and frame while retaining safe access to the active animation data.

#### Scenario: Initialize a multi-character provider
- **WHEN** a provider contains multiple packs and the display widget initializes
- **THEN** startup SHALL validate the registry and only the selected pack/action needed for the first animation
- **AND** packs not selected at startup SHALL be validated before their first use
- **AND** invalid lazy data SHALL produce an error without an out-of-bounds frame access

#### Scenario: Repeat the current action
- **WHEN** the current pack and WPM action complete a playback cycle without a NEXT request or action change
- **THEN** the widget SHALL restart the existing LVGL animation without resetting its source table, duration, or repeat configuration
- **AND** it SHALL NOT emit an INFO transition log for every repeated cycle

#### Scenario: Preserve zero-copy frame access
- **WHEN** a generated Provider supplies constant frame tables in ROM
- **THEN** LVGL SHALL retain direct pointers to the active frame table without copying all frame tables or image bytes into RAM
- **AND** the optimized build SHALL NOT increase final image RAM usage relative to the equivalent pre-optimization configuration

### Requirement: Total linked ROM guard
Animation-enabled targets SHALL optionally reject firmware whose complete linked ROM usage exceeds a target-specific verified budget.

#### Scenario: Linked firmware exceeds the target budget
- **WHEN** `_flash_used` is greater than the configured animation ROM maximum
- **THEN** the final link SHALL fail with a diagnostic naming the total linked ROM budget
- **AND** the diagnostic SHALL state the empirical startup reason and that setting `CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_ROM_MAX_BYTES=0` disables the guard
- **AND** the decision SHALL NOT be based only on generated bitmap byte count

#### Scenario: Disable the ROM guard for optimization testing
- **WHEN** `CONFIG_ZMK_DONGLE_DISPLAY_ANIMATION_ROM_MAX_BYTES` is zero
- **THEN** the linker SHALL NOT enforce an animation ROM budget
- **AND** a twenty-character Provider SHALL retain all source frames unless another explicit profile limit is selected
