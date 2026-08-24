## ADDED Requirements

### Requirement: Standalone fighter Provider module
The KOF96 fighter assets, plans, generators, tests, documentation, and Fighter-specific OpenSpec records SHALL be owned by a standalone ZMK module repository.

#### Scenario: Consume the module from zmk-config
- **WHEN** a Cornix or EvalKit generated-provider build is configured
- **THEN** its generator SHALL resolve from `zmodules/zmk-dongle-fighter-theme`
- **AND** generated cache output SHALL remain under the consumer workspace `.build`
- **AND** the zmk-dongle-display runtime Provider ABI SHALL remain unchanged

#### Scenario: Iterate on Fighter behavior
- **WHEN** timing, assets, generation, or Fighter tests change
- **THEN** those changes SHALL be committed in the fighter-theme module
- **AND** zmk-config SHALL change only when its pinned module revision or board profile changes

### Requirement: External ROM boundary
The fighter-theme module SHALL NOT store or distribute a commercial KOF96 ROM.

#### Scenario: Re-extract assets
- **WHEN** a developer reproduces character assets
- **THEN** the ROM SHALL be supplied as an explicit local path
- **AND** the extractor SHALL verify the supported ROM digest
- **AND** the parent workspace ROM at `graphs/ntkof96.gb` SHALL remain in place

#### Scenario: Inspect repository content
- **WHEN** the module is committed
- **THEN** no `.gb` or `.gbc` file SHALL be tracked
- **AND** generated caches and transient previews SHALL be excluded
