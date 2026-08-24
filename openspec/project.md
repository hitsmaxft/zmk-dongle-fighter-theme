# Project Context

## Purpose
Provide a standalone, reproducible KOF96 fighter-animation Provider for
`zmk-dongle-display`, including ROM-derived timing plans, generated I1 assets,
preview tools, tests, and design evidence.

## Tech Stack
- Python 3.12 generation and GIF tooling
- Zephyr/ZMK module metadata and Kconfig
- Generated C/LVGL I1 image descriptors and Provider macros
- OpenSpec change records

## Project Conventions

### Code Style
Use type-annotated Python, deterministic generation, explicit bounds checks,
and source-evidence strings beside each finite ROM branch.

### Architecture Patterns
The repository owns build-time assets and generation only. The display module
owns runtime widgets, HUD, timers, and Provider ABI. Generated images and tables
are immutable Flash data; no runtime ROM parsing is permitted.

### Testing Strategy
Run host unit tests for timing, sampling, movement, deduplication, and GIF/C
parity; then build Cornix and EvalKit consumers and inspect manifest plus
Zephyr Flash/SRAM reports. Hardware observations remain a separate gate.

### Git Workflow
Commit Provider scripts, assets, tests, and OpenSpec changes in this repository.
Consumer wiring and pinned West revision remain in zmk-config.

## Domain Context
KOF96 advances at approximately 59.7275Hz. `FrameTotal=N` means `N+1` source
ticks. Move code may alter speed, branch on collision/input, spawn projectile
objects, or integrate 8.8 velocity and gravity.

## Important Constraints
- Do not commit commercial ROM files; accept them only as explicit local input.
- Preserve the verified parent-workspace ROM at `graphs/ntkof96.gb`.
- Prefer exact I1 payload reuse and static holds over runtime decompression.
- Do not call a successful build a physical display validation.

## External Dependencies
- `hitsmaxft/zmk-dongle-display` custom animation Provider ABI
- `Kak2X/kof96` disassembly revision `47acd3002897ccd6b46df70809e8d6236ed3ebc3`
- A user-supplied Japanese KOF96 ROM with SHA-1 `63f25bff422a591907b83ab9f14709e938172839`
