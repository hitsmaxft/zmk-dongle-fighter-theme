## ADDED Requirements

### Requirement: Config-selectable animation provider
The dongle display SHALL allow a ZMK config to select an external compile-time animation provider without editing module source.

#### Scenario: Select an external provider
- **WHEN** custom-provider support is enabled and a provider header path relative to `ZMK_CONFIG` is configured
- **THEN** the build SHALL compile that provider as the animation registry
- **AND** a missing or invalid provider SHALL fail the build with a diagnostic that identifies the configured path or ABI error

#### Scenario: Integrate a minimal provider header
- **WHEN** a user declares actions, packs, and a registry with the public provider macros
- **THEN** no module-source, CMake, linker-section, or registration-function change SHALL be required
- **AND** ordinary static frame arrays SHALL not require a manually duplicated frame count

#### Scenario: Use the built-in provider
- **WHEN** the generic animation extension is enabled without a custom provider
- **THEN** the generic engine SHALL compile and display its built-in animation without an external header

#### Scenario: Generate a provider during the build
- **WHEN** generated-provider mode, a generator path, a cache directory, and an output header name are configured
- **THEN** CMake SHALL invoke the generator before compiling the provider translation unit
- **AND** the generated header SHALL be included from the configured cache rather than the source tree

#### Scenario: Reuse a generated provider cache
- **WHEN** the generator, cache wrapper, bitmap manifest, source BMP contents, and generation parameters are unchanged
- **THEN** a repeated build SHALL report a cache hit
- **AND** it SHALL NOT rewrite the cached Provider header

#### Scenario: Invalidate a generated provider cache
- **WHEN** any hashed generator or source-bitmap input changes
- **THEN** the build SHALL regenerate the Provider in a temporary directory
- **AND** it SHALL replace the cached output only after successful generation

#### Scenario: Leave the extension disabled
- **WHEN** neither the generic animation extension nor a custom provider is enabled
- **THEN** CMake SHALL compile the original Bongo Cat widget path
- **AND** the generic engine, provider registry, validation, random selection, and NEXT behavior SHALL add no linked symbol or resource

### Requirement: Versioned animation data contract
The module SHALL expose a versioned, read-only contract for animation registries, packs, actions, frames, durations, and WPM mappings.

#### Scenario: Define action metadata
- **WHEN** a provider defines an action from a static frame array
- **THEN** the standard definition macro SHALL derive the frame count from the array
- **AND** the provider SHALL declare the action duration

#### Scenario: Validate provider bounds
- **WHEN** a provider is compiled or initialized
- **THEN** every action SHALL have between 1 and 127 frames and a nonzero duration
- **AND** pack, action, band, canvas, and ABI-version references SHALL be validated before playback

### Requirement: Generic WPM-driven playback
The animation engine SHALL choose actions using each pack's ordered WPM mapping rather than fighter-specific fields.

#### Scenario: Increase the WPM band
- **WHEN** WPM selects a higher band during an action
- **THEN** the current action SHALL be interrupted immediately
- **AND** the mapped higher-band action SHALL begin without traversing intermediate bands

#### Scenario: Decrease the WPM band
- **WHEN** WPM selects a lower band during an action
- **THEN** the current action SHALL play through its final frame
- **AND** the latest lower-band action SHALL begin at the next action boundary

### Requirement: Generic animation-pack NEXT control
The module SHALL provide a zero-parameter central keymap behavior that requests the next animation pack.

#### Scenario: Count a NEXT request
- **WHEN** the NEXT behavior is pressed while an action is playing
- **THEN** one atomic pending request SHALL be added
- **AND** one pending request SHALL be consumed at each action boundary
- **AND** the new pack SHALL choose its action from the current WPM

#### Scenario: Rotate after wake
- **WHEN** wake rotation is enabled and activity returns from Idle or Sleep to Active
- **THEN** the engine SHALL add one NEXT request
- **AND** wake rotation disabled SHALL add no request

### Requirement: Random startup and sequential NEXT
The module SHALL randomly choose only the startup pack and SHALL use stable sequential order for subsequent NEXT requests.

#### Scenario: Select a random pack at startup
- **WHEN** a valid registry is initialized
- **THEN** the engine SHALL select `random_value % pack_count` before the first action starts

#### Scenario: Apply a sequential NEXT step
- **WHEN** NEXT is consumed and the registry contains more than one pack
- **THEN** the engine SHALL advance by one modulo `pack_count`
- **AND** the selected pack SHALL differ from the current pack
- **AND** no random source SHALL be read for NEXT

#### Scenario: Handle a single-pack registry
- **WHEN** startup or NEXT is processed with exactly one pack
- **THEN** pack index zero SHALL remain selected
- **AND** NEXT SHALL read no random source

### Requirement: Stable canvas and static resources
All packs in one registry SHALL use one fixed canvas and compile-time image resources.

#### Scenario: Switch between differently shaped content
- **WHEN** the active pack changes
- **THEN** the LVGL animation object SHALL retain the registry canvas dimensions and origin
- **AND** provider frames SHALL be padded or clipped before compilation rather than resizing the widget at runtime

### Requirement: Fighter prototype migration compatibility
The existing KOF96 prototype SHALL be expressible as an external provider while legacy next-fighter bindings remain temporarily functional.

#### Scenario: Build the migrated KOF96 provider
- **WHEN** Cornix selects the migrated KOF96 provider
- **THEN** the compiled roster, action timing, WPM transition behavior, and fixed canvas SHALL match the accepted prototype
- **AND** fighter-specific asset tables SHALL not remain in the generic module

#### Scenario: Use the legacy fighter-next binding
- **WHEN** an existing keymap invokes the legacy fighter-next behavior during the compatibility period
- **THEN** the engine SHALL process it as a generic NEXT command

### Requirement: Provider build validation
The generic module and external-provider path SHALL be validated on actual dongle targets.

#### Scenario: Build both provider modes
- **WHEN** `velvet_central_dongle` uses the built-in provider and `cornix_dongle` uses KOF96
- **THEN** both builds SHALL complete successfully
- **AND** final DTS, selected Provider, Flash/RAM usage, UF2 address range, and required settings backend SHALL be inspected
