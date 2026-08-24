#!/usr/bin/env python3
"""Generate fixed-origin LVGL I1 fighter actions for Cornix."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import zlib
from pathlib import Path


CANVAS_W = 64
CANVAS_H = 64
SEQUENCE_SCALES = {
    "idle": (3, 2),
    "slow": (3, 2),
    "mid": (3, 2),
    "fast": (3, 2),
}
SEQUENCE_FRAME_MS = {
    "idle": 500,
    "slow": 150,
    "mid": 200,
    "fast": 200,
}
FIGHTER_ENDPOINT_HOLD_MS = 500
SEQUENCE_FRAME_LIMIT = {
    "idle": 8,
    "slow": 16,
    "mid": 16,
    "fast": 12,
}
CHARACTER_SEQUENCE_FRAME_LIMIT = {
    # Keep Kyo's four requested signature actions within the previously proven
    # unique-frame budget while preserving each original action duration.
    "Kyo": {"idle": 4, "slow": 4, "mid": 6, "fast": 8},
    "Krauser": {"mid": 3},
}
DEFAULT_ENABLED_UNIQUE_FRAME_BUDGET = 301
DEFAULT_ENABLED_IMAGE_BUDGET_BYTES = 156520
DEFAULT_ENABLED_CHARACTERS = {
    "Kyo",
    "Daimon",
    "Terry",
    "Andy",
    "Ryo",
    "Robert",
    "Athena",
    "Mai",
    "Orochi_Leona",
    "Geese",
    "Krauser",
    "Goenitz",
    "Orochi_Iori",
}
BAYER_2X2 = ((0, 2), (3, 1))
INK_LEVEL = (0, 1, 3, 4)
GB_VBLANK_HZ_NUMERATOR = 597275
GB_VBLANK_HZ_DENOMINATOR = 10000
DEFAULT_SOURCE_TICKS_PER_DISPLAY_FRAME = 2
GB_LOGIC_MS_NUMERATOR = 1000 * GB_VBLANK_HZ_DENOMINATOR


def gb_logic_durations(step_ticks: list[int]) -> list[int]:
    """Convert 59.7275 Hz source ticks to cumulatively rounded milliseconds."""
    durations: list[int] = []
    cumulative_ticks = 0
    previous_ms = 0
    for position, ticks in enumerate(step_ticks):
        if not isinstance(ticks, int) or isinstance(ticks, bool) or ticks <= 0:
            raise ValueError(f"step_ticks[{position}]={ticks!r} must be a positive integer")
        cumulative_ticks += ticks
        cumulative_ms = (
            cumulative_ticks * GB_LOGIC_MS_NUMERATOR
            + GB_VBLANK_HZ_NUMERATOR // 2
        ) // GB_VBLANK_HZ_NUMERATOR
        duration = cumulative_ms - previous_ms
        if not 1 <= duration <= 65535:
            raise ValueError(
                f"step_ticks[{position}] produces {duration}ms outside provider bound 1..65535"
            )
        durations.append(duration)
        previous_ms = cumulative_ms
    return durations


def gb_logic_ms(ticks: int) -> int:
    return (ticks * GB_LOGIC_MS_NUMERATOR + GB_VBLANK_HZ_NUMERATOR // 2) // GB_VBLANK_HZ_NUMERATOR


def validate_timing(
    timing: object, order: list[int], context: str
) -> dict[str, object]:
    if not isinstance(timing, dict):
        raise ValueError(f"{context} timing must be an object")
    allowed = {
        "schema", "rom_move", "clock", "branch", "disassembly_revision", "evidence",
        "super_sparkle", "hitstop", "startup", "step_ticks", "recovery", "total_ticks",
    }
    unknown = set(timing) - allowed
    if unknown:
        raise ValueError(f"{context} timing has unknown keys: {sorted(unknown)}")
    required = allowed - {"super_sparkle"}
    missing = required - set(timing)
    if missing:
        raise ValueError(f"{context} timing is missing keys: {sorted(missing)}")
    if timing["schema"] != 2:
        raise ValueError(f"{context} timing schema must be 2")
    for key in ("rom_move", "branch"):
        if not isinstance(timing[key], str) or not timing[key]:
            raise ValueError(f"{context} timing {key} must be a nonempty string")
    if timing["clock"] != "gb-vblank":
        raise ValueError(f"{context} timing clock must be 'gb-vblank'")
    revision = timing["disassembly_revision"]
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError(f"{context} timing disassembly_revision must be a lowercase SHA-1")

    evidence = timing["evidence"]
    if not isinstance(evidence, dict):
        raise ValueError(f"{context} timing evidence must be an object")
    allowed_evidence = {"animation_table", "move_code", "projectile_code", "object_table"}
    unknown_evidence = set(evidence) - allowed_evidence
    if unknown_evidence:
        raise ValueError(
            f"{context} timing evidence has unknown keys: {sorted(unknown_evidence)}"
        )
    if not {"animation_table", "move_code"}.issubset(evidence):
        raise ValueError(f"{context} timing evidence requires animation_table and move_code")
    if any(not isinstance(value, str) or not value for value in evidence.values()):
        raise ValueError(f"{context} timing evidence values must be nonempty strings")

    step_ticks = timing["step_ticks"]
    if not isinstance(step_ticks, list) or len(step_ticks) != len(order):
        raise ValueError(
            f"{context} timing step_ticks must contain exactly {len(order)} steps"
        )
    gb_logic_durations(step_ticks)
    total_ticks = timing["total_ticks"]
    if not isinstance(total_ticks, int) or isinstance(total_ticks, bool) or total_ticks != sum(step_ticks):
        raise ValueError(f"{context} timing total_ticks must equal the step tick sum")

    def validate_boundary(name: str, keys: set[str]) -> dict[str, object]:
        value = timing[name]
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError(f"{context} timing {name} must contain exactly {sorted(keys)}")
        if any(not isinstance(value[key], int) or isinstance(value[key], bool)
               for key in keys - {"source"}):
            raise ValueError(f"{context} timing {name} numeric fields must be integers")
        if not isinstance(value["source"], str) or not value["source"]:
            raise ValueError(f"{context} timing {name} source must be a nonempty string")
        return value

    startup = validate_boundary("startup", {"step", "frame", "ticks", "source"})
    if not 0 <= startup["step"] < len(order) or startup["ticks"] != step_ticks[startup["step"]]:
        raise ValueError(f"{context} timing startup must reference a matching playback step")
    recovery = validate_boundary(
        "recovery", {"start_step", "frame", "ticks", "exclusive_tail_ticks", "source"}
    )
    if not 0 <= recovery["start_step"] < len(order):
        raise ValueError(f"{context} timing recovery start_step is outside playback")
    if recovery["ticks"] != sum(step_ticks[recovery["start_step"]:]):
        raise ValueError(f"{context} timing recovery ticks must equal its playback suffix")
    if recovery["exclusive_tail_ticks"] != step_ticks[-1]:
        raise ValueError(f"{context} timing recovery exclusive_tail_ticks must equal the last step")

    sparkle = timing.get("super_sparkle")
    if sparkle is not None:
        if not isinstance(sparkle, dict) or set(sparkle) != {"ticks", "parallel", "source"}:
            raise ValueError(
                f"{context} timing super_sparkle must contain ticks, parallel, and source"
            )
        if (not isinstance(sparkle["ticks"], int) or isinstance(sparkle["ticks"], bool)
                or sparkle["ticks"] <= 0 or sparkle["parallel"] is not True
                or not isinstance(sparkle["source"], str) or not sparkle["source"]):
            raise ValueError(f"{context} timing super_sparkle must be positive and parallel")

    hitstop = timing["hitstop"]
    if not isinstance(hitstop, dict) or set(hitstop) != {"ticks", "scope", "source"}:
        raise ValueError(f"{context} timing hitstop must contain ticks, scope, and source")
    if (not isinstance(hitstop["ticks"], int) or isinstance(hitstop["ticks"], bool)
            or hitstop["ticks"] < 0 or not isinstance(hitstop["scope"], str)
            or not hitstop["scope"] or not isinstance(hitstop["source"], str)
            or not hitstop["source"]):
        raise ValueError(f"{context} timing hitstop is invalid")

    return dict(timing)


def adapt_timed_playback(
    entry: dict[str, object],
    timing: dict[str, object],
    source_ticks_per_display_frame: int,
    context: str,
) -> dict[str, object]:
    """Sample a 59.7275 Hz ROM timeline into deterministic OLED display slots."""
    if not 1 <= source_ticks_per_display_frame <= 16:
        raise ValueError(f"{context} source ticks per display frame must be in 1..16")

    step_ticks = timing["step_ticks"]
    source_steps = [
        step
        for step, ticks in enumerate(step_ticks)
        for _ in range(ticks)
    ]
    total_ticks = len(source_steps)
    recovery_tick = sum(step_ticks[: int(timing["recovery"]["start_step"])])
    return_step = entry.get("return_step")
    return_tick = (
        sum(step_ticks[: int(return_step)]) if return_step is not None else None
    )

    sampled_steps: list[int] = []
    window_ticks: list[int] = []
    sampled_windows: list[tuple[int, int]] = []
    required_frames = set(entry.get("sampling_required_frames", []))
    sampled_required_frames: set[int] = set()

    for window_index, start in enumerate(
        range(0, total_ticks, source_ticks_per_display_frame)
    ):
        end = min(start + source_ticks_per_display_frame, total_ticks)
        preferred_tick = min(
            start + window_index % source_ticks_per_display_frame,
            end - 1,
        )
        selected_tick = preferred_tick
        # A simple phase rotation can still alias a four-state D/S projectile.
        # Composite plans name each low-frame effect that must survive sampling;
        # select an unseen required frame when its window first offers one.
        unseen_candidates = [
            tick
            for tick in range(start, end)
            if entry["order"][source_steps[tick]]
            in required_frames - sampled_required_frames
        ]
        if unseen_candidates:
            selected_tick = min(
                unseen_candidates,
                key=lambda tick: (tick - preferred_tick) % (end - start),
            )
        if start == 0:
            selected_tick = 0
        elif start <= recovery_tick < end:
            selected_tick = recovery_tick
        elif return_tick is not None and start <= return_tick < end:
            selected_tick = return_tick
        elif end == total_ticks:
            selected_tick = total_ticks - 1
        sampled_steps.append(source_steps[selected_tick])
        sampled_required_frames.add(entry["order"][source_steps[selected_tick]])
        window_ticks.append(end - start)
        sampled_windows.append((start, end))

    if len(sampled_steps) > 127:
        raise ValueError(
            f"{context} becomes {len(sampled_steps)} display steps at "
            f"{source_ticks_per_display_frame} source ticks/frame; valid bound is 1..127"
        )
    missing_required_frames = required_frames - sampled_required_frames
    if missing_required_frames:
        raise ValueError(
            f"{context} cannot preserve required source frames "
            f"{sorted(missing_required_frames)} at {source_ticks_per_display_frame} "
            "source ticks/frame"
        )

    adapted: dict[str, object] = {
        "animation": entry["animation"],
        "order": [entry["order"][step] for step in sampled_steps],
        "durations_ms": gb_logic_durations(window_ticks),
        "timing": timing,
    }
    if required_frames:
        adapted["sampling_required_frames"] = sorted(required_frames)

    movement_steps = entry.get("movement_steps")
    if movement_steps is not None:
        sampled_movement = [0]
        for previous_step, step in zip(sampled_steps, sampled_steps[1:]):
            sampled_movement.append(
                int(
                    step > previous_step
                    and any(movement_steps[previous_step + 1 : step + 1])
                )
            )
        adapted["movement_steps"] = sampled_movement
        if return_tick is not None:
            adapted["return_step"] = next(
                index for index, (start, end) in enumerate(sampled_windows)
                if start <= return_tick < end
            )

    for key in ("x_offsets", "y_offsets"):
        values = entry.get(key)
        if values is not None:
            adapted[key] = [values[step] for step in sampled_steps]

    sampled_display_slots = len(adapted["order"])
    return_slot = adapted.get("return_step")
    can_merge_holds = "movement_steps" in adapted or "x_offsets" in adapted
    if can_merge_holds:
        compressed: dict[str, list[int]] = {
            "order": [],
            "durations_ms": [],
        }
        for key in ("movement_steps", "x_offsets", "y_offsets"):
            if key in adapted:
                compressed[key] = []
        slot_to_step: list[int] = []
        for slot, frame in enumerate(adapted["order"]):
            movement = adapted.get("movement_steps")
            same_state = bool(compressed["order"] and compressed["order"][-1] == frame)
            for key in ("x_offsets", "y_offsets"):
                if key in adapted:
                    same_state = same_state and compressed[key][-1] == adapted[key][slot]
            if movement is not None and movement[slot]:
                same_state = False
            if return_slot is not None and slot == return_slot:
                same_state = False
            if same_state:
                compressed["durations_ms"][-1] += adapted["durations_ms"][slot]
            else:
                compressed["order"].append(frame)
                compressed["durations_ms"].append(adapted["durations_ms"][slot])
                for key in ("movement_steps", "x_offsets", "y_offsets"):
                    if key in adapted:
                        compressed[key].append(adapted[key][slot])
            slot_to_step.append(len(compressed["order"]) - 1)
        for key, values in compressed.items():
            adapted[key] = values
        if return_slot is not None:
            adapted["return_step"] = slot_to_step[return_slot]

    adapted["timing_report"] = timing_report(
        timing,
        adapted["durations_ms"],
        source_ticks_per_display_frame,
        sampled_display_slots,
    )
    return adapted


def timing_report(
    timing: dict[str, object],
    durations_ms: list[int],
    source_ticks_per_display_frame: int,
    sampled_display_slots: int,
) -> dict[str, int | str]:
    startup_step = int(timing["startup"]["step"])
    recovery_step = int(timing["recovery"]["start_step"])
    step_ticks = timing["step_ticks"]
    startup_ticks = sum(step_ticks[: startup_step + 1])
    recovery_ticks = sum(step_ticks[recovery_step:])
    total_ticks = int(timing["total_ticks"])
    return {
        "clock": str(timing["clock"]),
        "source_hz_millihertz": round(
            GB_VBLANK_HZ_NUMERATOR * 1000 / GB_VBLANK_HZ_DENOMINATOR
        ),
        "source_ticks_per_display_frame": source_ticks_per_display_frame,
        "target_hz_millihertz": round(
            GB_VBLANK_HZ_NUMERATOR * 1000
            / (GB_VBLANK_HZ_DENOMINATOR * source_ticks_per_display_frame)
        ),
        "sampled_display_slots": sampled_display_slots,
        "playback_steps": len(durations_ms),
        "collapsed_hold_slots": sampled_display_slots - len(durations_ms),
        "startup_ticks": startup_ticks,
        "body_ticks": total_ticks - startup_ticks - recovery_ticks,
        "recovery_ticks": recovery_ticks,
        "hitstop_ticks": int(timing["hitstop"]["ticks"]),
        "total_ticks": total_ticks,
        "startup_ms": gb_logic_ms(startup_ticks),
        "body_ms": gb_logic_ms(startup_ticks + total_ticks - startup_ticks - recovery_ticks)
        - gb_logic_ms(startup_ticks),
        "recovery_ms": gb_logic_ms(total_ticks)
        - gb_logic_ms(total_ticks - recovery_ticks),
        "total_ms": sum(durations_ms),
    }


def read_bmp8(path: Path) -> tuple[int, int, list[list[int]]]:
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise ValueError(f"not a BMP: {path}")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    if width <= 0 or height <= 0 or bpp != 8:
        raise ValueError(f"expected bottom-up 8-bit BMP: {path}")
    stride = (width + 3) & ~3
    rows = []
    for output_y in range(height):
        source_y = height - 1 - output_y
        start = pixel_offset + source_y * stride
        rows.append(list(data[start : start + width]))
    return width, height, rows


def foreground_mask(source: list[list[int]]) -> list[list[int]]:
    return source


def render_frame(
    frame_path: Path,
    frame: dict[str, object],
    source_bounds: tuple[int, int, int, int],
    scale_num: int,
    scale_den: int,
    canvas_width: int,
    canvas_height: int,
) -> list[list[int]]:
    width, height, source = read_bmp8(frame_path)
    if width != frame["width"] or height != frame["height"]:
        raise ValueError(f"manifest size mismatch: {frame_path}")
    source_left, source_top, source_right, source_bottom = source_bounds
    scaled_union_width = math.ceil((source_right - source_left) * scale_num / scale_den)
    scaled_union_height = math.ceil((source_bottom - source_top) * scale_num / scale_den)
    canvas_left = (canvas_width - scaled_union_width) // 2
    canvas_top = canvas_height - scaled_union_height
    left = canvas_left + (int(frame["origin_x"]) - source_left) * scale_num // scale_den
    top = canvas_top + (int(frame["origin_y"]) - source_top) * scale_num // scale_den
    scaled_width = (width * scale_num + scale_den - 1) // scale_den
    scaled_height = (height * scale_num + scale_den - 1) // scale_den
    if (
        left < 0
        or top < 0
        or left + scaled_width > canvas_width
        or top + scaled_height > canvas_height
    ):
        raise ValueError(f"scaled frame would be clipped: {frame_path}")
    source_mask = foreground_mask(source)
    canvas = [[0] * canvas_width for _ in range(canvas_height)]
    for y in range(scaled_height):
        source_y = min(height - 1, y * scale_den // scale_num)
        for x in range(scaled_width):
            source_x = min(width - 1, x * scale_den // scale_num)
            target_x, target_y = left + x, top + y
            if 0 <= target_x < canvas_width and 0 <= target_y < canvas_height:
                color = source_mask[source_y][source_x]
                level = INK_LEVEL[color]
                canvas[target_y][target_x] = int(
                    BAYER_2X2[target_y & 1][target_x & 1] < level
                )
    return canvas


def pack_i1(canvas: list[list[int]]) -> bytes:
    # Transparent background lets the procedural battle backdrop show through.
    packed = bytearray((0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0xFF))
    for row in canvas:
        for start in range(0, len(row), 8):
            value = 0
            for bit, pixel in enumerate(row[start : start + 8]):
                value |= pixel << (7 - bit)
            packed.append(value)
    return bytes(packed)


def png_gray(path: Path, width: int, height: int, pixels: bytes) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(
        b"\0" + pixels[y * width : (y + 1) * width] for y in range(height)
    )
    output = b"\x89PNG\r\n\x1a\n"
    output += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    output += chunk(b"IDAT", zlib.compress(rows, 9))
    output += chunk(b"IEND", b"")
    path.write_bytes(output)


def c_array(name: str, data: bytes, width: int, height: int) -> str:
    lines = []
    for start in range(0, len(data), 12):
        values = ", ".join(f"0x{value:02x}" for value in data[start : start + 12])
        lines.append(f"    {values},")
    return (
        f"static const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST uint8_t {name}_map[] = {{\n"
        + "\n".join(lines)
        + "\n};\n\n"
        + f"static const lv_img_dsc_t {name} = {{\n"
        + "    .header.cf = LV_COLOR_FORMAT_I1,\n"
        + f"    .header.w = {width},\n"
        + f"    .header.h = {height},\n"
        + f"    .data_size = {len(data)},\n"
        + f"    .data = {name}_map,\n"
        + "};\n"
    )


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def enable_macro(value: str) -> str:
    return f"FIGHTER_ENABLE_{slug(value).upper()}"


def sample_frame_indices(frame_count: int, limit: int) -> list[int]:
    if frame_count <= limit:
        return list(range(frame_count))
    if limit == 1:
        return [0]
    return [
        round(index * (frame_count - 1) / (limit - 1)) for index in range(limit)
    ]


def load_playback_plan(
    path: Path | None,
    available: dict[str, object],
    source_ticks_per_display_frame: int = DEFAULT_SOURCE_TICKS_PER_DISPLAY_FRAME,
) -> dict[tuple[str, str], dict[str, object]]:
    if path is None:
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read fighter playback plan {path}: {error}") from error
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError(f"fighter playback plan {path} must have version 1")
    unknown_top_level = set(document) - {"version", "characters"}
    if unknown_top_level:
        raise ValueError(
            f"fighter playback plan {path} has unknown keys: {sorted(unknown_top_level)}"
        )
    characters = document.get("characters")
    if not isinstance(characters, dict):
        raise ValueError(f"fighter playback plan {path} must contain a characters object")

    result: dict[tuple[str, str], dict[str, object]] = {}
    for character_name, sequences in characters.items():
        if character_name not in available:
            raise ValueError(
                f"fighter playback plan character {character_name!r} is not in the bitmap manifest"
            )
        if not isinstance(sequences, dict):
            raise ValueError(
                f"fighter playback plan {character_name!r} must contain a sequence object"
            )
        for sequence, entry in sequences.items():
            context = f"fighter playback plan {character_name}/{sequence}"
            if sequence not in SEQUENCE_FRAME_LIMIT:
                raise ValueError(f"{context} uses an unknown sequence")
            if not isinstance(entry, dict):
                raise ValueError(f"{context} must be an object")
            unknown_entry = set(entry) - {
                "animation",
                "order",
                "movement",
                "return_step",
                "x_offsets",
                "y_offsets",
                "durations_ms",
                "sampling_required_frames",
                "timing",
            }
            if unknown_entry:
                raise ValueError(f"{context} has unknown keys: {sorted(unknown_entry)}")
            animation = entry.get("animation")
            if not isinstance(animation, str):
                raise ValueError(f"{context} animation must be a string")
            animations = available[character_name]["animations"]
            if animation not in animations:
                raise ValueError(f"{context} references unknown animation {animation!r}")
            order = entry.get("order")
            if not isinstance(order, list) or not order:
                raise ValueError(f"{context} order must contain 1..127 source-frame indices")
            if len(order) > 127:
                raise ValueError(
                    f"{context} expands to {len(order)} steps; valid bound is 1..127"
                )
            source_frame_count = len(animations[animation]["frames"])
            validated_order: list[int] = []
            for position, source_index in enumerate(order):
                if (
                    not isinstance(source_index, int)
                    or isinstance(source_index, bool)
                    or not 0 <= source_index < source_frame_count
                ):
                    raise ValueError(
                        f"{context} order[{position}]={source_index!r} is outside valid "
                        f"source-frame bound 0..{source_frame_count - 1}"
                    )
                validated_order.append(source_index)
            movement = entry.get("movement")
            movement_steps: list[int] | None = None
            if movement is not None:
                if not isinstance(movement, list) or len(movement) != len(validated_order):
                    raise ValueError(
                        f"{context} movement must contain exactly {len(validated_order)} steps"
                    )
                if sequence not in ("mid", "fast"):
                    raise ValueError(f"{context} cannot move an idle or slow action")
                invalid = [
                    (position, mode)
                    for position, mode in enumerate(movement)
                    if mode not in ("fixed", "move")
                ]
                if invalid:
                    position, mode = invalid[0]
                    raise ValueError(
                        f"{context} movement[{position}]={mode!r}; expected 'fixed' or 'move'"
                    )
                if movement[0] != "fixed":
                    raise ValueError(f"{context} movement[0] must be 'fixed'")
                if "move" not in movement[1:]:
                    raise ValueError(f"{context} movement must contain at least one moving step")
                movement_steps = [int(mode == "move") for mode in movement]
            return_step = entry.get("return_step")
            if return_step is not None:
                if movement_steps is None:
                    raise ValueError(f"{context} return_step requires a movement table")
                if (
                    not isinstance(return_step, int)
                    or isinstance(return_step, bool)
                    or not 1 <= return_step < len(validated_order)
                ):
                    raise ValueError(
                        f"{context} return_step must be inside 1..{len(validated_order) - 1}"
                    )
                if not any(movement_steps[1:return_step]):
                    raise ValueError(f"{context} must move before return_step")
                if not any(movement_steps[return_step:]):
                    raise ValueError(f"{context} must move at or after return_step")
            x_offsets = entry.get("x_offsets")
            validated_x_offsets: list[int] | None = None
            if x_offsets is not None:
                if not isinstance(x_offsets, list) or len(x_offsets) != len(validated_order):
                    raise ValueError(
                        f"{context} x_offsets must contain exactly {len(validated_order)} steps"
                    )
                if movement_steps is not None or return_step is not None:
                    raise ValueError(f"{context} cannot mix x_offsets with computed movement")
                for position, offset in enumerate(x_offsets):
                    if (not isinstance(offset, int) or isinstance(offset, bool) or
                            not -127 <= offset <= 127):
                        raise ValueError(
                            f"{context} x_offsets[{position}]={offset!r} is outside -127..127"
                        )
                if x_offsets[0] != 0:
                    raise ValueError(f"{context} x_offsets[0] must be zero")
                validated_x_offsets = list(x_offsets)
            y_offsets = entry.get("y_offsets")
            validated_y_offsets: list[int] | None = None
            if y_offsets is not None:
                if sequence not in ("mid", "fast"):
                    raise ValueError(f"{context} y_offsets are only supported for mid/fast actions")
                if not isinstance(y_offsets, list) or len(y_offsets) != len(validated_order):
                    raise ValueError(
                        f"{context} y_offsets must contain exactly {len(validated_order)} steps"
                    )
                for position, offset in enumerate(y_offsets):
                    if not isinstance(offset, int) or isinstance(offset, bool) or offset not in (0, -10):
                        raise ValueError(
                            f"{context} y_offsets[{position}]={offset!r}; expected 0 or -10"
                        )
                if -10 not in y_offsets:
                    raise ValueError(f"{context} y_offsets must contain an airborne -10 step")
                validated_y_offsets = list(y_offsets)
            durations_ms = entry.get("durations_ms")
            timing = entry.get("timing")
            sampling_required_frames = entry.get("sampling_required_frames")
            validated_sampling_required_frames: list[int] | None = None
            if sampling_required_frames is not None:
                if timing is None:
                    raise ValueError(
                        f"{context} sampling_required_frames requires ROM timing"
                    )
                if not isinstance(sampling_required_frames, list) or not sampling_required_frames:
                    raise ValueError(
                        f"{context} sampling_required_frames must be a nonempty list"
                    )
                if len(set(sampling_required_frames)) != len(sampling_required_frames):
                    raise ValueError(
                        f"{context} sampling_required_frames must not contain duplicates"
                    )
                for source_index in sampling_required_frames:
                    if (
                        not isinstance(source_index, int)
                        or isinstance(source_index, bool)
                        or source_index not in validated_order
                    ):
                        raise ValueError(
                            f"{context} sampling_required_frames contains {source_index!r} "
                            "outside the playback order"
                        )
                validated_sampling_required_frames = list(sampling_required_frames)
            validated_durations_ms: list[int] | None = None
            validated_timing: dict[str, object] | None = None
            if timing is not None:
                if durations_ms is not None:
                    raise ValueError(f"{context} cannot mix timing with durations_ms")
                if sequence not in ("mid", "fast"):
                    raise ValueError(f"{context} ROM timing is only supported for mid/fast actions")
                validated_timing = validate_timing(timing, validated_order, context)
            if durations_ms is not None:
                if not isinstance(durations_ms, list) or len(durations_ms) != len(validated_order):
                    raise ValueError(
                        f"{context} durations_ms must contain exactly {len(validated_order)} steps"
                    )
                for position, duration in enumerate(durations_ms):
                    if (not isinstance(duration, int) or isinstance(duration, bool) or
                            not 1 <= duration <= 65535):
                        raise ValueError(
                            f"{context} durations_ms[{position}]={duration!r} is outside 1..65535"
                        )
                validated_durations_ms = list(durations_ms)
            result_entry: dict[str, object] = {
                "animation": animation,
                "order": validated_order,
            }
            if movement_steps is not None:
                result_entry["movement_steps"] = movement_steps
            if return_step is not None:
                result_entry["return_step"] = return_step
            if validated_x_offsets is not None:
                result_entry["x_offsets"] = validated_x_offsets
            if validated_y_offsets is not None:
                result_entry["y_offsets"] = validated_y_offsets
            if validated_sampling_required_frames is not None:
                result_entry["sampling_required_frames"] = validated_sampling_required_frames
            if validated_timing is not None:
                result_entry = adapt_timed_playback(
                    result_entry,
                    validated_timing,
                    source_ticks_per_display_frame,
                    context,
                )
            elif validated_durations_ms is not None:
                result_entry["durations_ms"] = validated_durations_ms
            result[(character_name, sequence)] = result_entry
    return result


def write_contact_sheet(path: Path, canvases: list[list[list[int]]]) -> None:
    columns = 5
    rows = (len(canvases) + columns - 1) // columns
    cell_width = max(len(canvas[0]) for canvas in canvases)
    cell_height = max(len(canvas) for canvas in canvases)
    contact = bytearray([255]) * (columns * cell_width * rows * cell_height)
    contact_width = columns * cell_width
    for index, canvas in enumerate(canvases):
        x0 = (index % columns) * cell_width + (cell_width - len(canvas[0])) // 2
        y0 = (index // columns) * cell_height + cell_height - len(canvas)
        for y, row in enumerate(canvas):
            start = (y0 + y) * contact_width + x0
            contact[start : start + len(row)] = bytes(0 if pixel else 255 for pixel in row)
    png_gray(path, contact_width, rows * cell_height, bytes(contact))


def select_animations(character_name: str, character: dict[str, object]) -> dict[str, str]:
    if character_name == "Kyo":
        return {
            "idle": "win_b",
            "slow": "kick_ch",
            "mid": "oni_yaki_l",
            "fast": "ura_orochi_nagi_d",
        }
    if character_name == "Krauser":
        return {
            "idle": "idle",
            "slow": "punch_l",
            "mid": "leg_tomahawk_l",
            "fast": "kaiser_wave_s",
        }

    items = list(character["animations"].items())
    indexed = list(enumerate(items))

    def usable(entries: list[tuple[int, tuple[str, dict[str, object]]]]) -> list[tuple[int, str, dict[str, object], int]]:
        return [
            (index, name, info, len(info["frames"]))
            for index, (name, info) in entries
            if not info["unused_or_placeholder"]
        ]

    light = max(
        (
            (index, name, info, len(info["frames"]))
            for index, (name, info) in indexed
            if name in ("punch_l", "kick_l")
        ),
        key=lambda entry: entry[3],
    )
    specials = usable(indexed[35:49])
    supers = usable(indexed[49:53])
    if not specials or not supers:
        raise ValueError(f"cannot classify special/super animations for {character_name}")

    if character_name == "Kyo":
        fast = next(
            (index, name, info, len(info["frames"]))
            for index, (name, info) in indexed
            if name == "oni_yaki_l"
        )
    else:
        compact_supers = [entry for entry in supers if entry[3] <= 24]
        fast = (
            max(compact_supers, key=lambda entry: entry[3])
            if compact_supers
            else min(supers, key=lambda entry: entry[3])
        )

    # Aim near ten frames so the middle band is readable without monopolizing flash.
    # Supers are valid here when they have at least six frames, as requested.
    mid_candidates = [
        entry
        for entry in specials + supers
        if entry[1] != fast[1] and entry[3] >= 6
    ]
    mid = min(mid_candidates, key=lambda entry: (abs(entry[3] - 10), -entry[3]))
    selected = {"idle": "idle", "slow": light[1], "mid": mid[1], "fast": fast[1]}
    if character_name == "Mai":
        selected["mid"] = "ryu_en_bu_h"
    return selected


def main() -> None:
    module_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bitmaps", type=Path, default=module_root / "assets/character_bitmaps"
    )
    parser.add_argument("--character", dest="characters", action="append")
    parser.add_argument("--enabled-character", dest="enabled_characters", action="append")
    parser.add_argument("--frame-limit", action="append", default=[], metavar="SEQUENCE=COUNT")
    parser.add_argument(
        "--source-ticks-per-display-frame",
        type=int,
        default=DEFAULT_SOURCE_TICKS_PER_DISPLAY_FRAME,
        metavar="COUNT",
        help="sample each ROM-timed action once per COUNT 59.7275 Hz source ticks (default: 2)",
    )
    parser.add_argument("--profile-label", default="manual")
    parser.add_argument("--idle-animation")
    parser.add_argument("--slow-animation")
    parser.add_argument("--mid-animation")
    parser.add_argument("--fast-animation")
    parser.add_argument("--output-dir", type=Path, default=Path("cornix_fighter_test"))
    parser.add_argument("--provider-header", type=Path)
    parser.add_argument("--no-previews", action="store_true")
    playback_group = parser.add_mutually_exclusive_group()
    playback_group.add_argument(
        "--playback-plan",
        type=Path,
        default=module_root / "data/fighter_playback.json",
    )
    playback_group.add_argument(
        "--no-playback-plan", dest="playback_plan", action="store_const", const=None
    )
    args = parser.parse_args()

    manifest_path = args.bitmaps / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    available = manifest["characters"]
    if not 1 <= args.source_ticks_per_display_frame <= 16:
        parser.error("--source-ticks-per-display-frame must be in 1..16")
    playback_plan = load_playback_plan(
        args.playback_plan,
        available,
        args.source_ticks_per_display_frame,
    )
    requested = args.characters or ["Kyo"]
    characters = list(available) if requested == ["all"] else requested
    missing = [name for name in characters if name not in available]
    if missing:
        raise SystemExit(f"unknown character directories: {missing}")

    enabled_requested = args.enabled_characters or sorted(DEFAULT_ENABLED_CHARACTERS)
    if enabled_requested == ["all"]:
        enabled_characters = set(characters)
    else:
        enabled_characters = set(enabled_requested)
    unknown_enabled = sorted(enabled_characters - set(characters))
    if unknown_enabled:
        raise SystemExit(f"enabled characters are not being generated: {unknown_enabled}")
    if not enabled_characters:
        raise SystemExit("at least one character must be enabled")

    frame_limits: dict[str, int] = {}
    for option in args.frame_limit:
        if "=" not in option:
            raise SystemExit(f"invalid frame limit {option!r}; expected SEQUENCE=COUNT")
        sequence, raw_count = option.split("=", 1)
        if sequence not in SEQUENCE_FRAME_LIMIT:
            raise SystemExit(f"unknown animation sequence {sequence!r}")
        try:
            count = int(raw_count)
        except ValueError as error:
            raise SystemExit(f"invalid frame count in {option!r}") from error
        if not 1 <= count <= 127:
            raise SystemExit(f"frame limit for {sequence!r} must be in 1..127")
        frame_limits[sequence] = count

    args.output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir = args.output_dir / "frames"
    contacts_dir = args.output_dir / "contacts"
    if not args.no_previews:
        preview_dir.mkdir(parents=True, exist_ok=True)
        contacts_dir.mkdir(parents=True, exist_ok=True)
        for old_preview in preview_dir.glob("fighter_*.png"):
            old_preview.unlink()
        for old_contact in contacts_dir.glob("*.png"):
            old_contact.unlink()

    unique_generated: list[dict[str, object]] = []
    logical_frames: list[dict[str, object]] = []
    playback_step_count = 0
    character_results: dict[str, object] = {}
    table_data: dict[str, dict[str, object]] = {}
    all_contacts: dict[str, list[list[list[int]]]] = {}

    for character_name in characters:
        character = available[character_name]
        character_slug = slug(character_name)
        unique_by_data: dict[tuple[int, int, bytes], str] = {}
        sequence_animations = select_animations(character_name, character)
        overrides = {
            "idle": args.idle_animation,
            "slow": args.slow_animation,
            "mid": args.mid_animation,
            "fast": args.fast_animation,
        }
        sequence_animations.update(
            {sequence: animation for sequence, animation in overrides.items() if animation}
        )
        sequence_results: dict[str, object] = {}
        table_data[character_name] = {}
        all_contacts[character_name] = []

        for sequence, animation in sequence_animations.items():
            playback_entry = playback_plan.get((character_name, sequence))
            if playback_entry is not None:
                animation = str(playback_entry["animation"])
            if animation not in character["animations"]:
                raise ValueError(f"{character_name} has no animation named {animation}")
            all_frames = character["animations"][animation]["frames"]
            frame_limit = frame_limits.get(
                sequence,
                CHARACTER_SEQUENCE_FRAME_LIMIT.get(character_name, {}).get(
                    sequence, SEQUENCE_FRAME_LIMIT[sequence]
                ),
            )
            if playback_entry is not None:
                playback_order = list(playback_entry["order"])
                movement_steps = playback_entry.get("movement_steps")
                selected_source_indices = list(dict.fromkeys(playback_order))
            else:
                selected_source_indices = sample_frame_indices(len(all_frames), frame_limit)
                playback_order = list(selected_source_indices)
                movement_steps = None
            frames = [all_frames[index] for index in selected_source_indices]
            source_left = min(int(frame["origin_x"]) for frame in frames)
            source_top = min(int(frame["origin_y"]) for frame in frames)
            source_right = max(
                int(frame["origin_x"]) + int(frame["width"]) for frame in frames
            )
            source_bottom = max(
                int(frame["origin_y"]) + int(frame["height"]) for frame in frames
            )
            source_bounds = (source_left, source_top, source_right, source_bottom)
            scale_num, scale_den = SEQUENCE_SCALES[sequence]
            source_height = source_bottom - source_top
            if sequence in ("mid", "fast") and source_height * scale_num > CANVAS_H * scale_den:
                divisor = math.gcd(CANVAS_H, source_height)
                scale_num = CANVAS_H // divisor
                scale_den = source_height // divisor
            scaled_width = math.ceil((source_right - source_left) * scale_num / scale_den)
            scaled_height = math.ceil(source_height * scale_num / scale_den)
            canvas_width = max(CANVAS_W, scaled_width) if sequence in ("mid", "fast") else CANVAS_W
            canvas_height = CANVAS_H
            output_left = (canvas_width - scaled_width) // 2
            output_top = canvas_height - scaled_height
            generated_symbols = []
            symbol_by_source_index: dict[int, str] = {}

            for sequence_index, (source_index, frame) in enumerate(
                zip(selected_source_indices, frames, strict=True)
            ):
                logical_symbol = f"fighter_{character_slug}_{sequence}_{sequence_index:03d}"
                source = args.bitmaps / character_name / animation / frame["file"]
                canvas = render_frame(
                    source,
                    frame,
                    source_bounds,
                    scale_num,
                    scale_den,
                    canvas_width,
                    canvas_height,
                )
                packed = pack_i1(canvas)
                image_key = (canvas_width, canvas_height, packed)
                symbol = unique_by_data.get(image_key)
                if symbol is None:
                    symbol = logical_symbol
                    unique_by_data[image_key] = symbol
                    unique_generated.append(
                        {
                            "character": character_name,
                            "symbol": symbol,
                            "packed": packed,
                            "data_size": len(packed),
                            "width": canvas_width,
                            "height": canvas_height,
                        }
                    )
                preview = bytes(0 if pixel else 255 for row in canvas for pixel in row)
                preview_name = f"{logical_symbol}.png"
                if not args.no_previews:
                    png_gray(
                        preview_dir / preview_name,
                        canvas_width,
                        canvas_height,
                        preview,
                    )
                logical_frames.append(
                    {
                        "character": character_name,
                        "symbol": symbol,
                        "logical_symbol": logical_symbol,
                        "sequence": sequence,
                        "animation": animation,
                        "source": str(source),
                        "source_frame": frame["file"],
                        "source_frame_index": source_index,
                        "origin_x": frame["origin_x"],
                        "origin_y": frame["origin_y"],
                        "scale": [scale_num, scale_den],
                        "preview": f"frames/{preview_name}",
                    }
                )
                generated_symbols.append(symbol)
                symbol_by_source_index[source_index] = symbol
                if not args.no_previews:
                    all_contacts[character_name].append(canvas)

            symbols = [symbol_by_source_index[index] for index in playback_order]
            playback_step_count += len(symbols)
            frame_durations_ms = (
                playback_entry.get("durations_ms") if playback_entry is not None else None
            )
            duration_ms = (
                sum(frame_durations_ms)
                if frame_durations_ms is not None
                else 2 * FIGHTER_ENDPOINT_HOLD_MS
                + max(0, len(symbols) - 2) * SEQUENCE_FRAME_MS[sequence]
                if sequence in ("mid", "fast")
                else len(symbols) * SEQUENCE_FRAME_MS[sequence]
            )
            table_name = f"fighter_{character_slug}_{sequence}_images"
            table_data[character_name][sequence] = {
                "name": table_name,
                "symbols": symbols,
                "movement_steps": movement_steps,
                "return_step": playback_entry.get("return_step") if playback_entry else None,
                "x_offsets": playback_entry.get("x_offsets") if playback_entry else None,
                "y_offsets": playback_entry.get("y_offsets") if playback_entry else None,
                "durations_ms": frame_durations_ms,
                "timing": playback_entry.get("timing") if playback_entry else None,
                "timing_report": playback_entry.get("timing_report") if playback_entry else None,
                "duration_ms": duration_ms,
            }
            sequence_results[sequence] = {
                "animation": animation,
                "scale": [scale_num, scale_den],
                "source_bounds": list(source_bounds),
                "output_bounds": [
                    output_left,
                    output_top,
                    output_left + scaled_width,
                    output_top + scaled_height,
                ],
                "canvas": {"width": canvas_width, "height": canvas_height},
                "cropped": False,
                "frame_count": len(symbols),
                "playback_step_count": len(symbols),
                "selected_frame_count": len(frames),
                "source_frame_count": len(all_frames),
                "frame_limit_applied": playback_entry is None and len(frames) != len(all_frames),
                "custom_playback": playback_entry is not None,
                "selected_source_indices": selected_source_indices,
                "playback_order": playback_order,
                "movement": (
                    ["move" if step else "fixed" for step in movement_steps]
                    if movement_steps is not None
                    else None
                ),
                "movement_step_count": (
                    sum(movement_steps)
                    if movement_steps is not None
                    else sum(
                        left != right
                        for left, right in zip(
                            playback_entry.get("x_offsets", [])[:-1],
                            playback_entry.get("x_offsets", [])[1:],
                            strict=True,
                        )
                    )
                    if playback_entry is not None and playback_entry.get("x_offsets") is not None
                    else len(symbols) - 1
                ),
                "return_step": playback_entry.get("return_step") if playback_entry else None,
                "x_offsets": playback_entry.get("x_offsets") if playback_entry else None,
                "y_offsets": playback_entry.get("y_offsets") if playback_entry else None,
                "durations_ms": frame_durations_ms,
                "duration_ms": duration_ms,
                "symbols": symbols,
                "generated_symbols": generated_symbols,
            }
            if playback_entry is not None and playback_entry.get("timing") is not None:
                sequence_results[sequence]["timing"] = playback_entry["timing"]
                sequence_results[sequence]["timing_report"] = playback_entry["timing_report"]
                sequence_results[sequence]["durations_ms"] = frame_durations_ms
        character_results[character_name] = {"sequences": sequence_results}
        if not args.no_previews:
            write_contact_sheet(
                contacts_dir / f"{character_slug}.png", all_contacts[character_name]
            )

    # Preserve the familiar top-level preview as the first character's contact sheet.
    if not args.no_previews:
        write_contact_sheet(args.output_dir / "contact_sheet.png", all_contacts[characters[0]])

    enabled = [name for name in characters if name in enabled_characters]
    enabled_unique = [entry for entry in unique_generated if entry["character"] in enabled_characters]
    enabled_logical = [entry for entry in logical_frames if entry["character"] in enabled_characters]
    enabled_image_bytes = sum(int(entry["data_size"]) for entry in enabled_unique)
    provider_canvas_width = max(int(entry["width"]) for entry in unique_generated)
    if set(enabled) == DEFAULT_ENABLED_CHARACTERS and (
        len(enabled_unique) > DEFAULT_ENABLED_UNIQUE_FRAME_BUDGET
        or enabled_image_bytes > DEFAULT_ENABLED_IMAGE_BUDGET_BYTES
    ):
        raise ValueError(
            "default roster exceeds proven image budget: "
            f"{len(enabled_unique)}/{DEFAULT_ENABLED_UNIQUE_FRAME_BUDGET} unique frames, "
            f"{enabled_image_bytes}/{DEFAULT_ENABLED_IMAGE_BUDGET_BYTES} bytes"
        )

    provider_parts = ["""/* Generated by zmk-dongle-fighter-theme/scripts/generate_cornix_fighter_assets.py; do not hand-edit. */
#pragma once

#include <lvgl.h>
#include <zmk/dongle_display/animation.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_LARGE_CONST
#define LV_ATTRIBUTE_LARGE_CONST
#endif
"""]
    for character_name in characters:
        macro = enable_macro(character_name)
        default = 1 if character_name in enabled_characters else 0
        provider_parts.append(
            f"#ifndef {macro}\n#define {macro} {default}\n#endif\n"
        )
    for character_name in characters:
        provider_parts.append(f"#if {enable_macro(character_name)}")
        for entry in unique_generated:
            if entry["character"] != character_name:
                continue
            provider_parts.append(
                c_array(
                    str(entry["symbol"]),
                    entry["packed"],
                    int(entry["width"]),
                    int(entry["height"]),
                )
            )
            del entry["packed"]
        provider_parts.append("#endif")
    for character_name in characters:
        character_slug = slug(character_name)
        provider_parts.append(f"#if {enable_macro(character_name)}")
        for sequence in ("idle", "slow", "mid", "fast"):
            table = table_data[character_name][sequence]
            refs = ",\n".join(f"    &{symbol}" for symbol in table["symbols"])
            provider_parts.append(
                f"static const void *const {table['name']}[] = {{\n{refs},\n}};\n"
            )
            movement_steps = table["movement_steps"]
            return_step = table["return_step"]
            x_offsets = table["x_offsets"]
            y_offsets = table["y_offsets"]
            frame_durations_ms = table["durations_ms"]
            movement_name = f"{table['name']}_movement"
            offsets_name = f"{table['name']}_x_offsets"
            y_offsets_name = f"{table['name']}_y_offsets"
            durations_name = f"{table['name']}_durations_ms"
            if movement_steps is not None:
                movement_values = ", ".join(str(step) for step in movement_steps)
                provider_parts.append(
                    f"static const uint8_t {movement_name}[] = {{{movement_values}}};"
                )
            if x_offsets is not None:
                offset_values = ", ".join(str(offset) for offset in x_offsets)
                provider_parts.append(
                    f"static const int8_t {offsets_name}[] = {{{offset_values}}};"
                )
            if y_offsets is not None:
                y_offset_values = ", ".join(str(offset) for offset in y_offsets)
                provider_parts.append(
                    f"static const int8_t {y_offsets_name}[] = {{{y_offset_values}}};"
                )
            if frame_durations_ms is not None:
                duration_values = ", ".join(str(duration) for duration in frame_durations_ms)
                provider_parts.append(
                    f"static const uint16_t {durations_name}[] = {{{duration_values}}};"
                )
            if sequence == "mid":
                macro = (
                    "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_MOVEMENT_RETURN_DEFINE"
                    if return_step is not None
                    else "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_MOVEMENT_DEFINE"
                    if movement_steps is not None
                    else "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_DEFINE"
                )
                movement_argument = f", {movement_name}" if movement_steps is not None else ""
                return_argument = f", {return_step}" if return_step is not None else ""
                provider_parts.append(
                    f"{macro}(kof96_{character_slug}_{sequence}, {table['name']}"
                    f"{movement_argument}{return_argument}, "
                    f"{SEQUENCE_FRAME_MS[sequence]}, {FIGHTER_ENDPOINT_HOLD_MS}, "
                    f"ZMK_DONGLE_ANIMATION_MOTION_LEFT_SCREEN_THIRD, "
                    f"ZMK_DONGLE_ANIMATION_FLAG_FULLSCREEN | "
                    f"ZMK_DONGLE_ANIMATION_FLAG_BATTLE_HUD);"
                )
            elif sequence == "fast":
                if y_offsets is not None:
                    movement_argument = movement_name if movement_steps is not None else "NULL"
                    x_argument = offsets_name if x_offsets is not None else "NULL"
                    duration_argument = (
                        durations_name if frame_durations_ms is not None else "NULL"
                    )
                    return_argument = (
                        str(return_step)
                        if return_step is not None
                        else "ZMK_DONGLE_ANIMATION_NO_RETURN_STEP"
                    )
                    motion_argument = (
                        "ZMK_DONGLE_ANIMATION_MOTION_NONE"
                        if x_offsets is not None
                        else "ZMK_DONGLE_ANIMATION_MOTION_LEFT_EDGE"
                    )
                    endpoint_hold = 0 if frame_durations_ms is not None else FIGHTER_ENDPOINT_HOLD_MS
                    provider_parts.append(
                        f"ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_Y_OFFSETS_DEFINE("
                        f"kof96_{character_slug}_{sequence}, {table['name']}, "
                        f"{movement_argument}, {x_argument}, {y_offsets_name}, "
                        f"{duration_argument}, {return_argument}, {table['duration_ms']}, "
                        f"{endpoint_hold}, {motion_argument}, "
                        f"ZMK_DONGLE_ANIMATION_FLAG_FULLSCREEN | "
                        f"ZMK_DONGLE_ANIMATION_FLAG_BATTLE_HUD);"
                    )
                    continue
                if x_offsets is not None:
                    if frame_durations_ms is not None:
                        provider_parts.append(
                            f"ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_TIMED_OFFSETS_DEFINE("
                            f"kof96_{character_slug}_{sequence}, {table['name']}, "
                            f"{offsets_name}, {durations_name}, {table['duration_ms']}, "
                            f"ZMK_DONGLE_ANIMATION_FLAG_FULLSCREEN | "
                            f"ZMK_DONGLE_ANIMATION_FLAG_BATTLE_HUD);"
                        )
                    else:
                        provider_parts.append(
                            f"ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_OFFSETS_DEFINE("
                            f"kof96_{character_slug}_{sequence}, {table['name']}, {offsets_name}, "
                            f"{SEQUENCE_FRAME_MS[sequence]}, {FIGHTER_ENDPOINT_HOLD_MS}, "
                            f"ZMK_DONGLE_ANIMATION_FLAG_FULLSCREEN | "
                            f"ZMK_DONGLE_ANIMATION_FLAG_BATTLE_HUD);"
                        )
                    continue
                if frame_durations_ms is not None:
                    macro = (
                        "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_TIMED_MOVEMENT_RETURN_DEFINE"
                        if return_step is not None
                        else "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_TIMED_MOVEMENT_DEFINE"
                        if movement_steps is not None
                        else "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_TIMED_DEFINE"
                    )
                    movement_argument = f", {movement_name}" if movement_steps is not None else ""
                    return_argument = f", {return_step}" if return_step is not None else ""
                    provider_parts.append(
                        f"{macro}(kof96_{character_slug}_{sequence}, {table['name']}"
                        f"{movement_argument}, {durations_name}{return_argument}, "
                        f"{table['duration_ms']}, ZMK_DONGLE_ANIMATION_MOTION_LEFT_EDGE, "
                        f"ZMK_DONGLE_ANIMATION_FLAG_FULLSCREEN | "
                        f"ZMK_DONGLE_ANIMATION_FLAG_BATTLE_HUD);"
                    )
                    continue
                macro = (
                    "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_MOVEMENT_RETURN_DEFINE"
                    if return_step is not None
                    else "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_MOVEMENT_DEFINE"
                    if movement_steps is not None
                    else "ZMK_DONGLE_ANIMATION_ACTION_LAYOUT_CADENCE_DEFINE"
                )
                movement_argument = f", {movement_name}" if movement_steps is not None else ""
                return_argument = f", {return_step}" if return_step is not None else ""
                provider_parts.append(
                    f"{macro}(kof96_{character_slug}_{sequence}, {table['name']}"
                    f"{movement_argument}{return_argument}, "
                    f"{SEQUENCE_FRAME_MS[sequence]}, {FIGHTER_ENDPOINT_HOLD_MS}, "
                    f"ZMK_DONGLE_ANIMATION_MOTION_LEFT_EDGE, "
                    f"ZMK_DONGLE_ANIMATION_FLAG_FULLSCREEN | "
                    f"ZMK_DONGLE_ANIMATION_FLAG_BATTLE_HUD);"
                )
            else:
                provider_parts.append(
                    f"ZMK_DONGLE_ANIMATION_ACTION_DEFINE(kof96_{character_slug}_{sequence}, "
                    f"{table['name']}, {table['duration_ms']});"
                )
        provider_parts.append(
            f'ZMK_DONGLE_ANIMATION_PACK_WPM4_DEFINE(kof96_{character_slug}_pack, '
            f'"{character_name}", kof96_{character_slug}_idle, kof96_{character_slug}_slow, '
            f'kof96_{character_slug}_mid, kof96_{character_slug}_fast, 5, 30, 70);'
        )
        provider_parts.append("#endif")

    provider_parts.append(
        "static const struct zmk_dongle_animation_pack *const kof96_animation_packs[] = {"
    )
    for character_name in characters:
        provider_parts.append(f"#if {enable_macro(character_name)}")
        provider_parts.append(f"    &kof96_{slug(character_name)}_pack,")
        provider_parts.append("#endif")
    provider_parts.extend(
        [
            "};",
            f"ZMK_DONGLE_ANIMATION_REGISTRY_ARRAY_DEFINE({provider_canvas_width}, 64, kof96_animation_packs);",
            "",
        ]
    )
    provider_header = args.provider_header or args.output_dir / "kof96_provider.h"
    provider_header.parent.mkdir(parents=True, exist_ok=True)
    provider_header.write_text("\n".join(provider_parts), encoding="utf-8")

    result = {
        "characters": character_results,
        "character_order": characters,
        "canvas": {"width": provider_canvas_width, "height": CANVAS_H},
        "color_conversion": "original ordered 2x2 dither: Game Boy indices 0/1/2/3 -> 0/25/75/100 percent foreground",
        "frames": logical_frames,
        "logical_frame_count": len(logical_frames),
        "playback_step_count": playback_step_count,
        "movement_table_bytes": sum(
            len(table["movement_steps"])
            for character_tables in table_data.values()
            for table in character_tables.values()
            if table["movement_steps"] is not None
        ),
        "unique_frame_count": len(unique_generated),
        "deduplicated_frame_count": len(logical_frames) - len(unique_generated),
        "image_bytes": sum(int(entry["data_size"]) for entry in unique_generated),
        "descriptor_bytes": len(unique_generated) * 24,
        "profile_label": args.profile_label,
        "playback_plan": str(args.playback_plan) if args.playback_plan is not None else None,
        "frame_limits": frame_limits,
        "enabled_characters": enabled,
        "enabled_logical_frame_count": len(enabled_logical),
        "enabled_unique_frame_count": len(enabled_unique),
        "enabled_image_bytes": enabled_image_bytes,
        "enabled_descriptor_bytes": len(enabled_unique) * 24,
        "default_enabled_characters": enabled,
        "default_enabled_logical_frame_count": len(enabled_logical),
        "default_enabled_unique_frame_count": len(enabled_unique),
        "default_enabled_image_bytes": enabled_image_bytes,
        "default_enabled_descriptor_bytes": len(enabled_unique) * 24,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"generated {len(logical_frames)} logical / {len(unique_generated)} unique "
        f"I1 frames up to {provider_canvas_width}x{CANVAS_H} "
        f"({result['image_bytes']} bytes) for {len(characters)} characters, "
        f"{len(enabled)} enabled"
    )


if __name__ == "__main__":
    main()
