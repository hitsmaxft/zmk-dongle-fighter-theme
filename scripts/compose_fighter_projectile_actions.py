#!/usr/bin/env python3
"""Compose ROM-derived body and projectile frames into virtual fast actions."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import extract_projectile_bitmaps as projectile
import generate_cornix_fighter_assets as fighter
import migrate_default_fighter_timing as fighter_timing


CANVAS = 64
VIRTUAL_ANIMATION = "fighter_fast_projectile"


@dataclass(frozen=True)
class VirtualFrames:
    frames: dict[tuple[str, int] | tuple[str, str], int]
    projectile_offsets: dict[str, tuple[int, int]]

    def __getitem__(self, key: tuple[str, int] | tuple[str, str]) -> int:
        return self.frames[key]

    def projectile(
        self, name: str, x_offset: int = 0, y_offset: int = 0
    ) -> tuple[int, int, int]:
        phase_x, phase_y = self.projectile_offsets[name]
        # A virtual frame is always 64px wide and is anchored in the right half
        # of the 128px OLED.  Keep phase metadata within the visible [-64, 0]
        # travel range while retaining every representable ROM displacement.
        placed_x = max(-64, min(0, x_offset + phase_x))
        return self.frames[("projectile", name)], placed_x, y_offset + phase_y


def bounds(frames: list[dict[str, object]]) -> tuple[int, int, int, int]:
    return (
        min(int(frame["origin_x"]) for frame in frames),
        min(int(frame["origin_y"]) for frame in frames),
        max(int(frame["origin_x"]) + int(frame["width"]) for frame in frames),
        max(int(frame["origin_y"]) + int(frame["height"]) for frame in frames),
    )


def fit_scale(source_bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    left, top, right, bottom = source_bounds
    scale = min(Fraction(3, 2), Fraction(CANVAS, right - left), Fraction(CANVAS, bottom - top))
    return scale.numerator, scale.denominator


def write_virtual_animation(
    bitmaps: Path,
    manifest: dict[str, object],
    projectile_root: Path,
    projectile_manifest: dict[str, object],
    character_name: str,
    body_groups: list[tuple[str, list[int]]],
    projectile_names: list[str],
) -> VirtualFrames:
    character = manifest["characters"][character_name]
    output = bitmaps / character_name / VIRTUAL_ANIMATION
    output.mkdir(parents=True, exist_ok=True)
    for old in output.glob("*.bmp"):
        old.unlink()
    canvases: list[tuple[tuple[str, int] | tuple[str, str], list[list[int]]]] = []
    body_frames: list[tuple[str, int, Path, dict[str, object]]] = []
    for animation_name, indices in body_groups:
        animation = character["animations"][animation_name]
        body_frames.extend(
            (
                animation_name,
                index,
                bitmaps / character_name / animation_name / animation["frames"][index]["file"],
                animation["frames"][index],
            )
            for index in sorted(set(indices))
        )
    if body_frames:
        body_bounds = bounds([frame for _, _, _, frame in body_frames])
        body_scale_num, body_scale_den = fit_scale(body_bounds)
        canvases.extend(
            (
                (animation_name, index),
                fighter.render_frame(
                    path,
                    frame,
                    body_bounds,
                    body_scale_num,
                    body_scale_den,
                    CANVAS,
                    CANVAS,
                ),
            )
            for animation_name, index, path, frame in body_frames
        )

    projectile_offsets: dict[str, tuple[int, int]] = {}
    if projectile_names:
        projectile_frames = [projectile_manifest["frames"][name] for name in projectile_names]
        projectile_bounds = bounds(projectile_frames)
        scale_num, scale_den = fit_scale(projectile_bounds)
        union_left, union_top, union_right, union_bottom = projectile_bounds
        union_width = math.ceil((union_right - union_left) * scale_num / scale_den)
        union_height = math.ceil((union_bottom - union_top) * scale_num / scale_den)
        common_left = (CANVAS - union_width) // 2
        common_top = CANVAS - union_height
        for name, frame in zip(projectile_names, projectile_frames, strict=True):
            frame_bounds = bounds([frame])
            rendered = fighter.render_frame(
                projectile_root / frame["file"],
                frame,
                frame_bounds,
                scale_num,
                scale_den,
                CANVAS,
                CANVAS,
            )
            scaled_width = math.ceil(int(frame["width"]) * scale_num / scale_den)
            scaled_height = math.ceil(int(frame["height"]) * scale_num / scale_den)
            normalized_left = (CANVAS - scaled_width) // 2
            normalized_top = CANVAS - scaled_height
            desired_left = (
                common_left
                + (int(frame["origin_x"]) - union_left) * scale_num // scale_den
            )
            desired_top = (
                common_top
                + (int(frame["origin_y"]) - union_top) * scale_num // scale_den
            )
            projectile_offsets[name] = (
                desired_left - normalized_left,
                desired_top - normalized_top,
            )
            canvases.append((("projectile", name), rendered))

    frame_info = []
    lookup: dict[tuple[str, int] | tuple[str, str], int] = {}
    for index, (key, canvas) in enumerate(canvases):
        filename = f"{index:03d}.bmp"
        pixels = [[3 if pixel else 0 for pixel in row] for row in canvas]
        (output / filename).write_bytes(projectile.bmp8(CANVAS, CANVAS, pixels))
        frame_info.append(
            {"file": filename, "width": CANVAS, "height": CANVAS,
             "origin_x": 0, "origin_y": 0, "sources": [list(key)]}
        )
        lookup[key] = index
    character["animations"][VIRTUAL_ANIMATION] = {
        "logical_move": "FIGHTER_FAST_PROJECTILE",
        "pointer_table": "generated alternating body/projectile timeline",
        "unused_or_placeholder": False,
        "frames": frame_info,
    }
    return VirtualFrames(lookup, projectile_offsets)


def rle_source_timeline(
    states: list[tuple[int, int, int]],
) -> tuple[list[int], list[int], list[int], list[int], list[int]]:
    """Run-length encode (frame, x, y) source-tick states without losing boundaries."""
    order: list[int] = []
    x_offsets: list[int] = []
    y_offsets: list[int] = []
    step_ticks: list[int] = []
    starts: list[int] = []
    for tick, state in enumerate(states):
        frame, x_offset, y_offset = state
        if order and (order[-1], x_offsets[-1], y_offsets[-1]) == state:
            step_ticks[-1] += 1
            continue
        order.append(frame)
        x_offsets.append(x_offset)
        y_offsets.append(y_offset)
        step_ticks.append(1)
        starts.append(tick)
    return order, x_offsets, y_offsets, step_ticks, starts


def geese_raging_storm_mappings() -> list[int]:
    """Simulate the 60-tick pillar mapping speed changes from the projectile code."""
    mappings: list[int] = []
    mapping = 0
    frame_left = 0
    for elapsed in range(60):
        mappings.append(mapping)
        remaining = 59 - elapsed
        frame_total = 2 if remaining < 8 else 1 if remaining < 16 else 0
        if frame_left == 0:
            mapping = (mapping + 1) % 4
            frame_left = frame_total
        else:
            frame_left -= 1
    return mappings


def main() -> None:
    module_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bitmaps", type=Path, default=module_root / "assets/character_bitmaps"
    )
    parser.add_argument(
        "--projectiles", type=Path, default=module_root / "assets/projectile_bitmaps"
    )
    parser.add_argument(
        "--playback-plan", type=Path, default=module_root / "data/fighter_playback.json"
    )
    args = parser.parse_args()
    manifest_path = args.bitmaps / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    projectile_manifest = json.loads(
        (args.projectiles / "manifest.json").read_text(encoding="utf-8")
    )
    plan = json.loads(args.playback_plan.read_text(encoding="utf-8"))

    iori = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Iori",
        [("kin_ya_otome_d", list(range(28)))], ["iori_fire_a", "iori_fire_b"],
    )
    iori_order = [iori[("kin_ya_otome_d", 0)]]
    iori_order.extend([iori[("kin_ya_otome_d", 1)]] * 4)
    iori_order.extend(iori[("kin_ya_otome_d", index)] for index in range(2, 26))
    iori_offsets = [0, -16, -32, -48, -64] + [-64] * (len(iori_order) - 5)
    iori_y_offsets = [0] * len(iori_order)
    plain = iori[("kin_ya_otome_d", 25)]
    for _ in range(3):
        for projectile_name in ("iori_fire_a", "iori_fire_b"):
            flame, flame_x, flame_y = iori.projectile(projectile_name, -64, 0)
            iori_order.extend([flame, plain])
            iori_offsets.extend([flame_x, -64])
            iori_y_offsets.extend([flame_y, 0])
    for index in (26, 27):
        iori_order.append(iori[("kin_ya_otome_d", index)])
        iori_offsets.append(-64)
        iori_y_offsets.append(0)
    iori_durations = [500] + [200] * (len(iori_order) - 2) + [500]
    # The terminal body mapping owns the long MAX finisher window.  Keep the
    # body visible briefly, then spend the remaining 1.02 s flashing flames.
    iori_durations[28] = 60
    iori_durations[29:41] = [80] * 12

    karate = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Mr_Karate",
        [("ryuko_ranbu_s", list(range(21))), ("zenretsuken_h", list(range(9))),
         ("hop_b", list(range(3))), ("haoh_sho_koh_ken_d", list(range(5)))],
        ["mrkarate_haoh_d", "mrkarate_haoh_s"],
    )
    karate_states: list[tuple[int, int, int]] = []
    ranbu_ticks = [2, 1] + [2] * 19
    for index, ticks in enumerate(ranbu_ticks):
        karate_states.extend(
            [(karate[("ryuko_ranbu_s", index)], round(-64 * min(index, 7) / 7), 0)]
            * ticks
        )
    zen_order = [0, 1, 2, 1, 2, 1, 2, 1, 2, 3, 4, 5, 6, 7, 8]
    zen_ticks = [2] + [1] * 11 + [2, 9, 9]
    for index, ticks in zip(zen_order, zen_ticks, strict=True):
        karate_states.extend([(karate[("zenretsuken_h", index)], -64, 0)] * ticks)

    # MOVE_MRKARATE_RYUKO_RANBU_D3: frame #0 owns two source ticks, frame #1
    # owns the remaining thirteen airborne ticks, then frame #2 lands.  Move
    # back to the original edge over those actual gravity ticks rather than
    # jumping through three equally spaced display positions.
    for hop_tick in range(15):
        hop_frame = 0 if hop_tick < 2 else 1
        x_offset = -64 + round(64 * hop_tick / 14)
        karate_states.append((karate[("hop_b", hop_frame)], x_offset, -10))
    karate_states.append((karate[("hop_b", 2)], 0, 0))

    haoh_body_ticks = [2, 2, 2, 31, 5]
    projectile_cycle = [
        ("mrkarate_haoh_d", -8),
        ("mrkarate_haoh_s", -24),
        ("mrkarate_haoh_d", -40),
        ("mrkarate_haoh_s", -56),
    ]
    projectile_tick = 0
    for body_frame, ticks in enumerate(haoh_body_ticks):
        for _ in range(ticks):
            if body_frame == 3 and projectile_tick < 8 and projectile_tick % 2 == 0:
                name, x_offset = projectile_cycle[projectile_tick // 2]
                karate_states.append(karate.projectile(name, x_offset, 0))
            else:
                karate_states.append((karate[("haoh_sho_koh_ken_d", body_frame)], 0, 0))
            if body_frame == 3:
                projectile_tick += 1

    karate_order, karate_offsets, karate_y_offsets, karate_step_ticks, karate_starts = (
        rle_source_timeline(karate_states)
    )

    terry = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Terry",
        [("power_geyser_e", [0, 1, 2])],
        ["terry_geyser_main", "terry_geyser_tail"],
    )
    # Frames #0..#2 are unique. Frames #3..#14 reuse the #2 pose in the ROM
    # object table, but remain distinct timing stages in the move code.
    terry_order = [terry[("power_geyser_e", index)] for index in (0, 1, 2)]
    release = terry[("power_geyser_e", 2)]
    terry_order.extend([release, release])  # source frames #3 and #4
    terry_offsets = [0] * len(terry_order)
    terry_y_offsets = [0] * len(terry_order)
    terry_step_ticks = [21, 3, 9, 9, 6]
    # Frames #4..#12 spawn fifteen replacing geysers at frame end; #13 spawns
    # the sixteenth and changes #14 to a 61-tick recovery. Use deterministic
    # legal display positions while preserving the no-adjacent-repeat rule.
    geyser_offsets = [
        -8, -48, -24, -64, -16, -56, -32, -40,
        -8, -24, -48, -16, -56, -32, -40, -8,
    ]
    # Keep all six mappings; half-speed holds each across two VBlanks.
    short_cycle = [
        ("terry_geyser_main", False), ("terry_geyser_tail", False),
        ("terry_geyser_main", False), (None, True),
        ("terry_geyser_tail", False), (None, True),
    ]
    for spawn_offset in geyser_offsets[:-1]:
        for projectile_name, hidden in short_cycle:
            state = (
                (release, 0, 0)
                if hidden
                else terry.projectile(projectile_name, spawn_offset, 0)
            )
            frame, x_offset, y_offset = state
            terry_order.append(frame)
            terry_offsets.append(x_offset)
            terry_y_offsets.append(y_offset)
            terry_step_ticks.append(1)
    # The final projectile retains all eleven V,V,V,H,V,H,V,H,V,H,V mappings.
    final_cycle = [
        "terry_geyser_main", "terry_geyser_tail", "terry_geyser_main", None,
        "terry_geyser_tail", None, "terry_geyser_main", None,
        "terry_geyser_tail", None, "terry_geyser_main",
    ]
    recovery_start_step = len(terry_order)
    for projectile_name in final_cycle:
        state = (
            (release, 0, 0)
            if projectile_name is None
            else terry.projectile(projectile_name, geyser_offsets[-1], 0)
        )
        frame, x_offset, y_offset = state
        terry_order.append(frame)
        terry_offsets.append(x_offset)
        terry_y_offsets.append(y_offset)
        terry_step_ticks.append(1)
    terry_order.append(release)
    terry_offsets.append(0)
    terry_y_offsets.append(0)
    terry_step_ticks.append(50)  # #14 owns 61 ticks; final projectile overlaps the first 11.
    terry_timing = {
        "schema": 2,
        "rom_move": "MOVE_TERRY_POWER_GEYSER_E",
        "clock": "gb-vblank",
        "branch": "deterministic-projectile-position-demo",
        "disassembly_revision": "47acd3002897ccd6b46df70809e8d6236ed3ebc3",
        "evidence": {
            "animation_table": "src/bank03.asm:MoveAnimTbl_Terry",
            "move_code": "src/bank06.asm:MoveC_Terry_PowerGeyserE",
            "projectile_code": "src/bank06.asm:ProjC_Terry_PowerGeyser",
            "object_table": "data/objlst/char/terry.asm:OBJLstPtrTable_Terry_PowerGeyserE",
        },
        "super_sparkle": {
            "ticks": 20,
            "parallel": True,
            "source": "src/bank02.asm:ExOBJ_SuperSparkle",
        },
        "hitstop": {
            "ticks": 0,
            "scope": "opponent-hit-reaction-only; excluded from player timeline",
            "source": "MoveAnimTbl_Terry PF3_HALFSPEED flag",
        },
        "startup": {
            "step": 0,
            "frame": 0,
            "ticks": 21,
            "source": "MoveAnimTbl_Terry byte4=$14; FrameTotal+1",
        },
        "step_ticks": terry_step_ticks,
        "recovery": {
            "start_step": recovery_start_step,
            "frame": 20,
            "ticks": 61,
            "exclusive_tail_ticks": 50,
            "source": "frame #$13 sets $3C; #$14 ends through Play_Pl_EndMove",
        },
        "total_ticks": sum(terry_step_ticks),
    }

    uppercut_air_order = [0, 1, 2, 3, 2, 3, 2, 3, 4, 5]

    ryo = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Ryo",
        [("ryu_ko_ranbu_s", list(range(22))), ("ko_hou_h", list(range(6)))],
        [],
    )
    ryo_order = [ryo[("ryu_ko_ranbu_s", 0)]]
    ryo_order.extend([ryo[("ryu_ko_ranbu_s", 1)]] * 4)
    ryo_order.extend(ryo[("ryu_ko_ranbu_s", index)] for index in range(2, 22))
    ryo_order.extend(ryo[("ko_hou_h", index)] for index in uppercut_air_order)
    ryo_offsets = [0, -16, -32, -48, -64] + [-64] * (len(ryo_order) - 5)

    robert = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Robert",
        [("ryu_ko_ranbu_s", list(range(17))), ("ryuu_ga_h", list(range(6)))],
        [],
    )
    robert_order = [robert[("ryu_ko_ranbu_s", 0)]]
    robert_order.extend([robert[("ryu_ko_ranbu_s", 1)]] * 4)
    robert_order.extend(robert[("ryu_ko_ranbu_s", index)] for index in range(2, 17))
    robert_order.extend(robert[("ryuu_ga_h", index)] for index in uppercut_air_order)
    robert_offsets = [0, -16, -32, -48, -64] + [-64] * (len(robert_order) - 5)

    goenitz = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Goenitz",
        [("shinyaotome_jissoukoku_dl", list(range(4))),
         ("shinyaotome_throw_h", list(range(7)))],
        ["goenitz_tornado_a", "goenitz_tornado_mid", "goenitz_tornado_b"],
    )
    goenitz_order = [
        goenitz[("shinyaotome_jissoukoku_dl", 0)],
        goenitz[("shinyaotome_jissoukoku_dl", 1)],
        goenitz[("shinyaotome_jissoukoku_dl", 2)],
        goenitz[("shinyaotome_jissoukoku_dl", 3)],
    ]
    goenitz_order.extend(goenitz[("shinyaotome_throw_h", index)] for index in range(3))
    lifted = goenitz[("shinyaotome_throw_h", 2)]
    goenitz_offsets = [0, 0, 0, -32] + [-32] * 3
    goenitz_y_offsets = [0] * len(goenitz_order)
    tornado_bases = {
        "goenitz_tornado_a": -40,
        "goenitz_tornado_mid": -32,
        "goenitz_tornado_b": -24,
    }
    for _ in range(2):
        for projectile_name in (
            "goenitz_tornado_a",
            "goenitz_tornado_mid",
            "goenitz_tornado_b",
        ):
            wind, wind_x, wind_y = goenitz.projectile(
                projectile_name, tornado_bases[projectile_name], 0
            )
            goenitz_order.extend([wind, lifted])
            goenitz_offsets.extend([wind_x, -32])
            goenitz_y_offsets.extend([wind_y, 0])
    goenitz_order.extend(goenitz[("shinyaotome_throw_h", index)] for index in range(3, 7))
    goenitz_offsets.extend([-32] * 4)
    goenitz_y_offsets.extend([0] * 4)
    goenitz_durations = [500] + [200] * (len(goenitz_order) - 2) + [500]
    # Yonokaze itself lives for 0x28 ticks (~670 ms) and never switches to an
    # invisible mapping.  Divide that lifetime over the requested wind/lift
    # alternation while preserving the lifted body pose between wind frames.
    goenitz_durations[7:19] = [56] * 10 + [55] * 2

    athena = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Athena",
        [("shining_crystal_bit_as", list(range(9)))],
        [
            "athena_shcryst_swirl",
            "athena_shcryst_thrown_0",
            "athena_shcryst_thrown_1",
            "athena_shcryst_thrown_2",
        ],
    )
    athena_body_order = [0] + [frame for _ in range(14) for frame in (1, 2)] + list(range(3, 9))
    athena_body_ticks = [9] + [2] * 28 + [2, 1, 41, 4, 20, 4]
    athena_body_source = [
        frame
        for frame, ticks in zip(athena_body_order, athena_body_ticks, strict=True)
        for _ in range(ticks)
    ]
    athena_states: list[tuple[int, int, int]] = []
    thrown_names = [
        "athena_shcryst_thrown_0",
        "athena_shcryst_thrown_1",
        "athena_shcryst_thrown_2",
        "athena_shcryst_thrown_1",
    ]
    thrown_step = 0
    for tick, body_frame in enumerate(athena_body_source):
        recovery = tick >= 133
        show_projectile = tick >= 9 and not recovery and tick % 2 == 1
        if show_projectile:
            if tick < 68:
                projectile_name = "athena_shcryst_swirl"
                x_offset = -8
                y_offset = 6
            else:
                projectile_name = thrown_names[thrown_step % len(thrown_names)]
                x_offset = -min(64, 8 + thrown_step * 4)
                y_offset = -10
                thrown_step += 1
            state = athena.projectile(projectile_name, x_offset, y_offset)
        else:
            state = (
                athena[("shining_crystal_bit_as", body_frame)],
                0,
                0 if recovery else -10,
            )
        athena_states.append(state)
    (
        athena_order,
        athena_offsets,
        athena_y_offsets,
        athena_step_ticks,
        athena_starts,
    ) = rle_source_timeline(athena_states)

    geese = write_virtual_animation(
        args.bitmaps, manifest, args.projectiles, projectile_manifest, "Geese",
        [("raging_storm_s", [0, 1, 2])],
        [f"geese_raging_storm_s{index}" for index in range(4)],
    )
    pillar_mappings = geese_raging_storm_mappings()
    geese_states: list[tuple[int, int, int]] = []
    for tick in range(83):
        if tick < 21:
            body_frame = 0
        elif tick == 21:
            body_frame = 1
        else:
            body_frame = 2
        elapsed = tick - 22
        show_pillar = 0 <= elapsed < len(pillar_mappings) and tick % 2 == 1
        frame = (
            geese.projectile(
                f"geese_raging_storm_s{pillar_mappings[elapsed]}", -18, 0
            )
            if show_pillar
            else (geese[("raging_storm_s", body_frame)], 0, 0)
        )
        geese_states.append(frame)
    (
        geese_order,
        geese_offsets,
        geese_y_offsets,
        geese_step_ticks,
        geese_starts,
    ) = rle_source_timeline(geese_states)

    for name, order, offsets, y_offsets, durations, timing in (
        ("Iori", iori_order, iori_offsets, iori_y_offsets, iori_durations, None),
        ("Mr_Karate", karate_order, karate_offsets, karate_y_offsets, None, None),
        ("Terry", terry_order, terry_offsets, terry_y_offsets, None, terry_timing),
        ("Ryo", ryo_order, ryo_offsets, None, None, None),
        ("Robert", robert_order, robert_offsets, None, None, None),
        (
            "Goenitz",
            goenitz_order,
            goenitz_offsets,
            goenitz_y_offsets,
            goenitz_durations,
            None,
        ),
    ):
        entry = {
            "animation": VIRTUAL_ANIMATION,
            "order": order,
            "x_offsets": offsets,
        }
        if y_offsets is not None:
            entry["y_offsets"] = y_offsets
        if durations is not None:
            entry["durations_ms"] = durations
        if timing is not None:
            entry["timing"] = timing
        plan["characters"].setdefault(name, {})["fast"] = entry

    fighter_timing.apply_migration(plan)

    karate_timing = fighter_timing.timing(
        move=(
            "MOVE_MRKARATE_RYUKO_RANBU_S -> ZENRETSUKEN_H -> "
            "RYUKO_RANBU_D3 -> HAOHS_D"
        ),
        table="src/bank03.asm:MoveAnimTbl_MrKarate",
        code="src/bank02.asm:MoveC_MrKarate_RyukoRanbuS/Zenretsuken/RyukoRanbuD3",
        branch="successful hidden desperation chain with source-gravity back hop",
        order=karate_order,
        ticks=karate_step_ticks,
        recovery_start=karate_starts.index(96),
        projectile="src/bank02.asm:MoveC_Robert_HaohShoukouKen",
    )
    karate_timing["evidence"]["object_table"] = (
        "data/objlst/char/ryo_mrkarate.asm:OBJLstPtrTable_MrKarate_*"
    )
    plan["characters"]["Mr_Karate"]["fast"] = {
        "animation": VIRTUAL_ANIMATION,
        "order": karate_order,
        "x_offsets": karate_offsets,
        "y_offsets": karate_y_offsets,
        "sampling_required_frames": [
            karate[("projectile", "mrkarate_haoh_d")],
            karate[("projectile", "mrkarate_haoh_s")],
        ],
        "timing": karate_timing,
    }

    athena_timing = fighter_timing.timing(
        move="MOVE_ATHENA_SHINING_CRYSTAL_BIT_AS",
        table="src/bank03.asm:MoveAnimTbl_Athena",
        code="src/bank06.asm:MoveC_Athena_ShCryst",
        branch=(
            "air S, fourteen orbit loops, normal-size charge projectile, "
            "deterministic release and landing"
        ),
        order=athena_order,
        ticks=athena_step_ticks,
        recovery_start=athena_starts.index(133),
        projectile="src/bank06.asm:ProjC_Athena_ShCrystCharge/Thrown",
    )
    athena_timing["evidence"]["object_table"] = (
        "data/objlst/proj.asm:OBJLstPtrTable_Proj_Athena_ShCryst_*"
    )
    plan["characters"]["Athena"]["fast"] = {
        "animation": VIRTUAL_ANIMATION,
        "order": athena_order,
        "x_offsets": athena_offsets,
        "y_offsets": athena_y_offsets,
        "sampling_required_frames": [
            athena[("projectile", "athena_shcryst_swirl")],
            athena[("projectile", "athena_shcryst_thrown_0")],
            athena[("projectile", "athena_shcryst_thrown_1")],
            athena[("projectile", "athena_shcryst_thrown_2")],
        ],
        "timing": athena_timing,
    }

    geese_timing = fighter_timing.timing(
        move="MOVE_GEESE_RAGING_STORM_S",
        table="src/bank03.asm:MoveAnimTbl_Geese",
        code="src/bank06.asm:MoveC_Geese_RagingStorm",
        branch="normal super with concurrent 60-tick four-mapping light pillar",
        order=geese_order,
        ticks=geese_step_ticks,
        recovery_start=geese_starts.index(22),
        projectile="src/bank06.asm:ProjC_Geese_RagingStorm",
    )
    geese_timing["evidence"]["object_table"] = (
        "data/objlst/proj.asm:OBJLstPtrTable_Proj_Geese_RagingStormS"
    )
    plan["characters"]["Geese"]["fast"] = {
        "animation": VIRTUAL_ANIMATION,
        "order": geese_order,
        "x_offsets": geese_offsets,
        "y_offsets": geese_y_offsets,
        "sampling_required_frames": [
            geese[("projectile", f"geese_raging_storm_s{index}")]
            for index in range(4)
        ],
        "timing": geese_timing,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.playback_plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
